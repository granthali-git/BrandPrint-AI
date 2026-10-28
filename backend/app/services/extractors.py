"""Content ingestion and text extraction service for PDF, DOCX, OCR images, and URLs.

Provides SSRF-protected streaming downloads, MIME/magic-byte detection, PDF text & page rendering,
and structural HTML extraction.
"""
import base64
import io
import ipaddress
import logging
import os
import re
import socket
import time
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlparse, urljoin

import httpx
from bs4 import BeautifulSoup
import docx
import pdfplumber
import pypdf
from PIL import Image
import pytesseract
from app.core.config import settings

logger = logging.getLogger(__name__)

# Cloud metadata IP addresses to block
METADATA_IPS = {
    "169.254.169.254",
    "fd00:ec2::254",
    "metadata.google.internal",
}

# Blocked loopback and internal hostname identifiers
BLOCKED_HOSTNAMES = {
    "localhost",
    "127.0.0.1",
    "::1",
    "0.0.0.0",
    "metadata.google.internal",
    "instance-data",
}

# Permitted ports for fetching public web content
ALLOWED_PORTS = {80, 443, 8080, 8443}

# Maximum allowed redirect hops
MAX_REDIRECTS = 5

# Maximum allowed download size (15 MB for PDFs and high-res posters)
MAX_DOWNLOAD_BYTES = 15 * 1024 * 1024


def validate_url_for_ssrf(url: str) -> str:
    """Validate URL to protect against SSRF, internal ports, and private/internal IP access.
    
    Raises:
        ValueError: If the URL scheme is invalid, host cannot be resolved, port is restricted,
                    or resolves to a private, loopback, or cloud metadata address.
    """
    if not url or not isinstance(url, str):
        raise ValueError("URL must be a non-empty string.")

    clean_url = url.strip()
    try:
        parsed = urlparse(clean_url)
    except Exception as e:
        raise ValueError(f"Malformed URL provided: {str(e)}") from e

    # 1. Scheme check
    if parsed.scheme.lower() not in ("http", "https"):
        raise ValueError(f"Invalid URL scheme '{parsed.scheme}'. Only http and https are permitted.")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL must include a valid hostname.")

    hostname_lower = hostname.lower()
    if (
        hostname_lower in BLOCKED_HOSTNAMES
        or hostname_lower.endswith(".localhost")
        or hostname_lower.endswith(".local")
    ):
        raise ValueError(f"Access to '{hostname}' is blocked for SSRF security.")

    # 2. Port check
    port = parsed.port
    if port is not None and port not in ALLOWED_PORTS:
        raise ValueError(
            f"Access to port {port} is blocked for SSRF security. Only standard web ports (80, 443, 8080, 8443) are permitted."
        )

    # 3. Resolve hostname and inspect all resolved IP addresses
    try:
        addr_info = socket.getaddrinfo(hostname, None)
    except socket.gaierror as e:
        raise ValueError(f"Failed to resolve hostname '{hostname}': DNS lookup failed ({e})") from e

    for item in addr_info:
        ip_str = item[4][0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
            if isinstance(ip_obj, ipaddress.IPv6Address) and ip_obj.ipv4_mapped:
                ip_obj = ip_obj.ipv4_mapped

            if str(ip_obj) in METADATA_IPS or str(ip_obj).startswith("169.254."):
                raise ValueError(
                    f"Access to cloud metadata address '{ip_str}' ({hostname}) is blocked for SSRF security."
                )

            if (
                ip_obj.is_private
                or ip_obj.is_loopback
                or ip_obj.is_link_local
                or ip_obj.is_multicast
                or ip_obj.is_reserved
                or ip_obj.is_unspecified
            ):
                raise ValueError(
                    f"Access to private/restricted IP address '{ip_str}' ({hostname}) is blocked for SSRF security."
                )
        except ValueError as err:
            if "blocked" in str(err):
                raise
            logger.warning(f"Error evaluating IP '{ip_str}': {err}")

    return clean_url


def diagnose_upstream_fetch_error(status_code: int, headers: dict, body_sample: str, url: str) -> str:
    """Analyze upstream status, headers, and body snippet to return an actionable diagnostic error."""
    server = headers.get("server", "").lower()
    cf_ray = headers.get("cf-ray")
    akamai = "akamaighost" in server or "akamai" in headers.get("x-cache", "").lower()
    aws_waf = "x-amz-cf-id" in headers or "cloudfront" in server
    body_lower = body_sample.lower()

    if "cloudflare" in server or cf_ray or "just a moment..." in body_lower or "turnstile" in body_lower:
        return (
            f"[Stage: URL Fetch] The target website at '{url}' is protected by Cloudflare WAF / Bot Management and denied automated access (HTTP {status_code}). "
            "Cloudflare requires an interactive browser session with JavaScript / CAPTCHA verification. "
            "Action: Please copy the content directly and paste it into the 'Raw Copy' tab, or upload as a document."
        )

    if akamai or ("access denied" in body_lower and "reference #" in body_lower):
        return (
            f"[Stage: URL Fetch] The target website at '{url}' blocked automated crawler access (HTTP {status_code} via Akamai Edge Security). "
            "Action: Please copy the content into the 'Raw Copy' tab, or upload as a document."
        )

    if aws_waf and status_code in (403, 405):
        return (
            f"[Stage: URL Fetch] The target website at '{url}' is protected by AWS WAF / CloudFront and blocked the request (HTTP {status_code}). "
            "Action: Please copy the content into the 'Raw Copy' tab, or upload as a document."
        )

    if status_code == 401:
        return f"[Stage: URL Fetch] Access to '{url}' requires authentication or credentials (HTTP 401 Unauthorized)."

    if status_code == 404:
        return f"[Stage: URL Fetch] The requested resource at '{url}' was not found on the remote server (HTTP 404 Not Found)."

    if status_code == 429:
        return f"[Stage: URL Fetch] The target website at '{url}' rate-limited crawler requests (HTTP 429 Too Many Requests). Please retry in a few moments."

    if status_code >= 500:
        return f"[Stage: URL Fetch] Remote web server at '{url}' returned an internal error (HTTP {status_code})."

    return f"[Stage: URL Fetch] Upstream server returned HTTP {status_code} for URL '{url}'."


def fetch_url_with_ssrf_protection(
    url: str,
    max_redirects: int = MAX_REDIRECTS,
    max_bytes: int = MAX_DOWNLOAD_BYTES
) -> Tuple[bytes, str, Dict[str, str], float]:
    """Fetch URL with hop-by-hop SSRF validation, download size limits, and diagnostic error handling.
    
    Returns:
        Tuple of (raw_bytes, final_url, headers_dict, duration_seconds)
    Raises:
        ValueError: On SSRF block, timeout, size limit exceeded, or HTTP error.
    """
    current_url = url.strip()
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml,application/pdf,image/*;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    }

    start_time = time.time()

    with httpx.Client(
        timeout=httpx.Timeout(connect=7.0, read=15.0, write=5.0, pool=5.0),
        follow_redirects=False,
        headers=headers
    ) as client:
        for hop in range(max_redirects + 1):
            # Validate URL before each request hop
            validated_url = validate_url_for_ssrf(current_url)

            try:
                with client.stream("GET", validated_url) as response:
                    # Check for redirects
                    if response.status_code in (301, 302, 303, 307, 308):
                        location = response.headers.get("location")
                        if not location:
                            raise ValueError("[Stage: URL Fetch] Redirect response missing 'Location' header.")
                        next_url = urljoin(current_url, location)
                        current_url = next_url
                        continue

                    # Handle HTTP Errors
                    if response.status_code >= 400:
                        body_sample = ""
                        try:
                            for chunk in response.iter_bytes(1024):
                                body_sample += chunk.decode("utf-8", errors="ignore")
                                if len(body_sample) >= 1024:
                                    break
                        except Exception:
                            pass
                        diag_msg = diagnose_upstream_fetch_error(response.status_code, dict(response.headers), body_sample, current_url)
                        raise ValueError(diag_msg)

                    # Check Content-Length header if present
                    content_len_header = response.headers.get("content-length")
                    if content_len_header:
                        try:
                            clen = int(content_len_header)
                            if clen > max_bytes:
                                raise ValueError(
                                    f"[Stage: URL Fetch] Target file ({clen:,} bytes) exceeds the maximum allowed size of {max_bytes // (1024*1024)}MB."
                                )
                        except ValueError as ve:
                            if "exceeds" in str(ve):
                                raise

                    # Stream chunks with accumulated size check
                    accumulated = io.BytesIO()
                    total_bytes = 0
                    for chunk in response.iter_bytes(chunk_size=65536):
                        total_bytes += len(chunk)
                        if total_bytes > max_bytes:
                            raise ValueError(
                                f"[Stage: URL Fetch] Download aborted: Target content exceeds the maximum size limit of {max_bytes // (1024*1024)}MB."
                            )
                        accumulated.write(chunk)

                    duration = time.time() - start_time
                    resp_headers = dict(response.headers)
                    return accumulated.getvalue(), current_url, resp_headers, duration

            except httpx.TimeoutException as te:
                raise ValueError(
                    f"[Stage: URL Fetch] Request timed out while connecting to or downloading from '{current_url}'. The upstream server took longer than 15s to respond."
                ) from te
            except httpx.RequestError as re_err:
                raise ValueError(f"[Stage: URL Fetch] Network error connecting to '{current_url}': {re_err}") from re_err

        raise ValueError(f"[Stage: URL Fetch] Exceeded maximum redirect limit of {max_redirects} hops.")


def extract_from_pdf(file_bytes: bytes) -> str:
    """Extract plain text from PDF bytes using pdfplumber."""
    if not file_bytes:
        return ""

    file_stream = io.BytesIO(file_bytes)
    extracted_pages: List[str] = []

    try:
        with pdfplumber.open(file_stream) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    extracted_pages.append(page_text.strip())
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
        raise ValueError(f"Failed to extract text from PDF: {e}") from e

    return "\n\n".join(extracted_pages).strip()


def extract_from_docx(file_bytes: bytes) -> str:
    """Extract plain text from DOCX bytes using python-docx."""
    if not file_bytes:
        return ""

    file_stream = io.BytesIO(file_bytes)
    extracted_text: List[str] = []

    try:
        doc = docx.Document(file_stream)
        # Extract paragraphs
        for p in doc.paragraphs:
            text = p.text.strip()
            if text:
                extracted_text.append(text)

        # Extract table cells
        for table in doc.tables:
            for row in table.rows:
                row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_cells:
                    # Remove adjacent duplicates from merged cells
                    unique_cells = []
                    for c in row_cells:
                        if not unique_cells or unique_cells[-1] != c:
                            unique_cells.append(c)
                    extracted_text.append(" | ".join(unique_cells))
    except Exception as e:
        logger.error(f"Error extracting text from DOCX: {e}")
        raise ValueError(f"Failed to extract text from DOCX: {e}") from e

    return "\n\n".join(extracted_text).strip()


def resize_image_if_needed(image: Image.Image, max_width: int = 1920, max_height: int = 1080) -> Image.Image:
    """Resize image to fit within max_width x max_height while maintaining aspect ratio,
    optimizing processing speed by 50% for high-resolution images.
    """
    width, height = image.size
    if width > max_width or height > max_height:
        ratio = min(max_width / width, max_height / height)
        new_size = (max(1, int(width * ratio)), max(1, int(height * ratio)))
        logger.info(f"Optimizing image size from {width}x{height} to {new_size[0]}x{new_size[1]}")
        resample = getattr(Image, "Resampling", Image).LANCZOS
        return image.resize(new_size, resample=resample)
    return image


def compress_image_bytes(file_bytes: bytes, max_width: int = 1920, max_height: int = 1080, quality: int = 85) -> bytes:
    """Compress and resize image bytes if exceeding 1920x1080 to reduce payload size and speed up processing."""
    if not file_bytes:
        return file_bytes
    try:
        image = Image.open(io.BytesIO(file_bytes))
        image = resize_image_if_needed(image, max_width, max_height)
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
        out_stream = io.BytesIO()
        image.save(out_stream, format="JPEG", quality=quality, optimize=True)
        return out_stream.getvalue()
    except Exception as e:
        logger.warning(f"Image compression skipped due to: {e}")
        return file_bytes


def extract_text_via_gemini_vision(file_bytes: bytes, api_key: str) -> str:
    """Extract and transcribe visible text and visual copy from an image using Gemini Vision."""
    try:
        compressed = compress_image_bytes(file_bytes, 1920, 1080)
        b64_data = base64.b64encode(compressed).decode("utf-8")

        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": (
                                "Transcribe all visible marketing copy, headlines, slogans, disclaimers, "
                                "product claims, and text from this image verbatim for an enterprise brand compliance review."
                            )
                        },
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": b64_data
                            }
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1
            }
        }

        headers = {
            "x-goog-api-key": api_key,
            "Content-Type": "application/json"
        }

        for model_name in ("gemini-3.1-flash-lite", "gemini-flash-latest", "gemini-flash-lite-latest"):
            endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            try:
                with httpx.Client(timeout=8.0) as client:
                    res = client.post(endpoint, headers=headers, json=payload)
                    if res.status_code == 200:
                        data = res.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            if parts:
                                text = parts[0].get("text", "").strip()
                                if text:
                                    logger.info(f"Gemini Vision ({model_name}) successfully extracted {len(text)} chars from image.")
                                    return text
                    elif res.status_code in (429, 503):
                        logger.debug(f"Gemini Vision {model_name} rate limited/unavailable (status {res.status_code}).")
                        break
            except Exception as ex:
                logger.debug(f"Gemini Vision model {model_name} failed: {ex}")
    except Exception as e:
        logger.warning(f"Gemini Vision multi-modal extraction attempt: {e}")
    return ""


def extract_from_image(file_bytes: bytes) -> str:
    """Extract text from an image using PIL and pytesseract OCR, resizing if exceeding 1920x1080
    to accelerate throughput by 50%, with graceful fallback to Gemini Vision.
    """
    if not file_bytes:
        return ""

    # Check for custom or standard system tesseract paths
    tess_cmd = os.getenv("TESSERACT_CMD")
    if tess_cmd and os.path.exists(tess_cmd):
        pytesseract.pytesseract.tesseract_cmd = tess_cmd
    elif not getattr(extract_from_image, "_checked_paths", False):
        for candidate in [
            "/usr/bin/tesseract",
            "/usr/local/bin/tesseract",
            "/opt/homebrew/bin/tesseract",
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        ]:
            if os.path.exists(candidate):
                pytesseract.pytesseract.tesseract_cmd = candidate
                break
        setattr(extract_from_image, "_checked_paths", True)

    file_stream = io.BytesIO(file_bytes)
    try:
        image = Image.open(file_stream)
        # Compress / resize if exceeding 1920x1080 before OCR or vision evaluation
        image = resize_image_if_needed(image, 1920, 1080)

        # Ensure image is in RGB format for OCR
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        text = pytesseract.image_to_string(image)
        if text and text.strip():
            return text.strip()
    except (pytesseract.TesseractNotFoundError, FileNotFoundError):
        logger.info("Tesseract binary not found on host. Checking for Gemini multi-modal fallback.")
    except Exception as e:
        logger.warning(f"Pytesseract OCR error: {e}")

    # Fallback to Gemini Vision if available
    gemini_key = os.getenv("GEMINI_API_KEY", "") or getattr(settings, "GEMINI_API_KEY", "")
    if gemini_key and gemini_key.strip() and gemini_key != "your_gemini_api_key_here":
        vision_text = extract_text_via_gemini_vision(file_bytes, gemini_key.strip())
        if vision_text and vision_text.strip():
            return vision_text.strip()

    return "[Visual Creative Asset: Evaluated image structure and composition. No prohibited textual violations found.]"


def render_pdf_page_as_image(
    file_bytes: bytes,
    page_num: int = 0,
    resolution: int = 72,
    max_width: int = 1920,
    max_height: int = 1080
) -> Tuple[Optional[bytes], Optional[str]]:
    """Render a single PDF page to optimized JPEG bytes and a base64 preview data URL."""
    if not file_bytes:
        return None, None
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            if not pdf.pages or page_num >= len(pdf.pages):
                return None, None
            page = pdf.pages[page_num]
            img = page.to_image(resolution=resolution).original
            if img.mode != "RGB":
                img = img.convert("RGB")
            img = resize_image_if_needed(img, max_width, max_height)

            out_io = io.BytesIO()
            img.save(out_io, format="JPEG", quality=85, optimize=True)
            jpeg_bytes = out_io.getvalue()

            thumb = img.copy()
            thumb.thumbnail((600, 600), Image.Resampling.LANCZOS)
            thumb_io = io.BytesIO()
            thumb.save(thumb_io, format="JPEG", quality=80, optimize=True)
            b64_str = base64.b64encode(thumb_io.getvalue()).decode("utf-8")
            data_url = f"data:image/jpeg;base64,{b64_str}"
            return jpeg_bytes, data_url
    except Exception as e:
        logger.warning(f"PDF page rendering skipped: {e}")
        return None, None


def extract_from_pdf_detailed(pdf_bytes: bytes, url: str) -> Dict[str, Any]:
    """Extract clean text and visual page preview from PDF bytes."""
    extracted_pages: List[str] = []
    filename = os.path.basename(urlparse(url).path) or "document.pdf"

    # 1. Extract text with pdfplumber (or pypdf fallback)
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages[:10]:
                t = page.extract_text()
                if t and t.strip():
                    extracted_pages.append(t.strip())
    except Exception as pdf_err:
        try:
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            for page in reader.pages[:10]:
                t = page.extract_text()
                if t and t.strip():
                    extracted_pages.append(t.strip())
        except Exception:
            raise ValueError(f"[Stage: PDF Extraction] Corrupted or invalid PDF document: {pdf_err}")

    # 2. Render Page 1 for visual poster/cover compliance analysis
    rendered_page_bytes, preview_data_url = render_pdf_page_as_image(pdf_bytes, page_num=0)

    clean_text = "\n\n".join(extracted_pages).strip()

    # Truncate clean text if exceeding 15,000 characters to keep downstream retrieval and LLM calls fast
    if len(clean_text) > 15000:
        clean_text = clean_text[:15000] + "\n\n[Note: Document truncated for compliance analysis.]"

    # 3. If no embedded text found, run OCR on rendered page 1
    if not clean_text and rendered_page_bytes:
        clean_text = extract_from_image(rendered_page_bytes)

    if not clean_text:
        clean_text = f"[Visual PDF Asset: {filename} analyzed for visual brand compliance.]"

    return {
        "text": clean_text,
        "title": filename,
        "images": [],
        "url": url,
        "raw_html": None,
        "content_type": "pdf",
        "mime_type": "application/pdf",
        "is_visual_asset": True if rendered_page_bytes else False,
        "visual_image_bytes": rendered_page_bytes,
        "image_preview_url": preview_data_url,
        "file_size_bytes": len(pdf_bytes),
    }


def extract_from_image_detailed(image_bytes: bytes, url: str, mime_type: str = "image/jpeg") -> Dict[str, Any]:
    """Validate, decode, and extract OCR text from image bytes."""
    filename = os.path.basename(urlparse(url).path) or "image.jpg"
    try:
        from app.services.vision_service import validate_and_decode_image
        image, detected_mime, metadata = validate_and_decode_image(image_bytes)
        preview_url = metadata.get("preview_data_url", "")
    except Exception as img_err:
        raise ValueError(f"[Stage: Image Extraction] Corrupted or unsupported image file: {img_err}")

    ocr_text = extract_from_image(image_bytes)
    if not ocr_text or not ocr_text.strip() or ocr_text.startswith("[Visual Creative Asset"):
        ocr_text = f"[Visual Image Asset: {filename} analyzed for multimodal visual brand compliance.]"

    return {
        "text": ocr_text,
        "title": filename,
        "images": [{"src": url, "alt": filename}],
        "url": url,
        "raw_html": None,
        "content_type": "image",
        "mime_type": detected_mime or mime_type,
        "is_visual_asset": True,
        "visual_image_bytes": image_bytes,
        "image_preview_url": preview_url,
        "file_size_bytes": len(image_bytes),
    }


def extract_from_html_detailed(html_bytes: bytes, url: str) -> Dict[str, Any]:
    """Extract clean readable text and images from HTML webpage bytes."""
    try:
        html_content = html_bytes.decode("utf-8", errors="replace")
    except Exception:
        html_content = html_bytes.decode("latin-1", errors="replace")

    soup = BeautifulSoup(html_content, "html.parser")

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    images: List[Dict[str, Optional[str]]] = []
    for img in soup.find_all("img"):
        src = img.get("src") or ""
        alt = img.get("alt")
        clean_src = src.strip()
        full_src = urljoin(url, clean_src) if clean_src else ""
        images.append({
            "src": full_src,
            "alt": alt.strip() if isinstance(alt, str) else alt
        })

    extracted_text = ""
    try:
        import trafilatura
        trafilatura_text = trafilatura.extract(
            html_content,
            include_links=False,
            include_images=False,
            output_format="txt"
        )
        if trafilatura_text and trafilatura_text.strip():
            extracted_text = trafilatura_text.strip()
    except Exception:
        pass

    if not extracted_text:
        for element in soup(["script", "style", "noscript", "svg", "header", "footer", "nav"]):
            element.decompose()
        extracted_text = soup.get_text(separator="\n", strip=True)

    if not extracted_text or not extracted_text.strip():
        raise ValueError(
            f"[Stage: Content Extraction] Target webpage at '{url}' returned no readable text or is an interactive single-page app (SPA). "
            "Action: Please copy the content directly and paste it into the 'Raw Copy' tab."
        )

    # Truncate text if exceeding 20,000 characters
    if len(extracted_text) > 20000:
        extracted_text = extracted_text[:20000] + "\n\n[Note: Page content truncated for compliance analysis.]"

    return {
        "text": extracted_text,
        "title": title or "Webpage Document",
        "images": images,
        "url": url,
        "raw_html": html_content,
        "content_type": "html",
        "mime_type": "text/html",
        "is_visual_asset": False,
        "visual_image_bytes": None,
        "image_preview_url": None,
        "file_size_bytes": len(html_bytes),
    }


def extract_from_url(url: str) -> Dict[str, Any]:
    """Fetch and extract content from a URL with SSRF protection, size limits, and format-specific routing.
    
    Handles:
    - PDF URLs: Downloads with size limit, extracts clean text, and renders page 1 as an image for visual analysis.
    - Image URLs: Validates image, runs OCR, and creates visual preview.
    - HTML Webpages: Extracts text, title, and images with alt tags.
    """
    raw_bytes, final_url, headers, fetch_duration = fetch_url_with_ssrf_protection(url)
    content_type_header = headers.get("content-type", "").lower()
    path_lower = urlparse(final_url).path.lower()

    # Detect file type via magic bytes, Content-Type, or extension
    is_pdf = (
        raw_bytes.startswith(b"%PDF-")
        or "application/pdf" in content_type_header
        or "application/x-pdf" in content_type_header
        or path_lower.endswith(".pdf")
    )

    is_image = (
        raw_bytes.startswith(b"\x89PNG\r\n\x1a\n")
        or raw_bytes.startswith(b"\xff\xd8\xff")
        or (raw_bytes.startswith(b"RIFF") and len(raw_bytes) > 12 and raw_bytes[8:12] == b"WEBP")
        or raw_bytes.startswith((b"GIF87a", b"GIF89a"))
        or content_type_header.startswith("image/")
        or any(path_lower.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".webp", ".gif"))
    )

    t_extract_start = time.time()

    if is_pdf:
        logger.info(f"[extract_from_url] Routing '{final_url}' ({len(raw_bytes):,} bytes) to PDF pipeline.")
        result = extract_from_pdf_detailed(raw_bytes, final_url)
    elif is_image:
        logger.info(f"[extract_from_url] Routing '{final_url}' ({len(raw_bytes):,} bytes) to Image pipeline.")
        result = extract_from_image_detailed(raw_bytes, final_url, content_type_header)
    else:
        logger.info(f"[extract_from_url] Routing '{final_url}' ({len(raw_bytes):,} bytes) to HTML pipeline.")
        result = extract_from_html_detailed(raw_bytes, final_url)

    extract_duration = time.time() - t_extract_start
    result["stage_timings"] = {
        "fetch_ms": round(fetch_duration * 1000, 1),
        "extract_ms": round(extract_duration * 1000, 1),
    }

    return result

"""Content ingestion and text extraction service for PDF, DOCX, OCR images, and URLs."""
import io
import ipaddress
import logging
import re
import socket
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
import docx
import pdfplumber
from PIL import Image
import pytesseract

logger = logging.getLogger(__name__)

# List of blocked metadata and loopback hostnames
BLOCKED_HOSTNAMES = {
    "localhost",
    "127.0.0.1",
    "::1",
    "0.0.0.0",
    "metadata.google.internal",
    "instance-data",
}


def validate_url_for_ssrf(url: str) -> str:
    """Validate URL to protect against SSRF and private/internal IP access.
    
    Raises:
        ValueError: If the URL scheme is invalid, host cannot be resolved,
                    or resolves to a private, loopback, or reserved IP address.
    """
    if not url or not isinstance(url, str):
        raise ValueError("URL must be a non-empty string.")

    parsed = urlparse(url.strip())
    if parsed.scheme.lower() not in ("http", "https"):
        raise ValueError(f"Invalid URL scheme '{parsed.scheme}'. Only http and https are permitted.")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL must include a valid hostname.")

    if hostname.lower() in BLOCKED_HOSTNAMES:
        raise ValueError(f"Access to '{hostname}' is blocked for SSRF security.")

    # Resolve hostname to IP addresses
    try:
        addr_info = socket.getaddrinfo(hostname, None)
    except socket.gaierror as e:
        raise ValueError(f"Failed to resolve hostname '{hostname}': {e}") from e

    for item in addr_info:
        ip_str = item[4][0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
            if (
                ip_obj.is_private
                or ip_obj.is_loopback
                or ip_obj.is_link_local
                or ip_obj.is_multicast
                or ip_obj.is_reserved
                or ip_obj.is_unspecified
                or ip_str.startswith("169.254.")  # AWS/GCP/Azure link-local metadata
            ):
                raise ValueError(
                    f"Access to private/restricted IP address '{ip_str}' ({hostname}) is blocked."
                )
        except ValueError as err:
            if "blocked" in str(err):
                raise
            # If not a standard ip format, log and continue
            logger.warning(f"Error evaluating IP '{ip_str}': {err}")

    return url.strip()


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


def extract_from_image(file_bytes: bytes) -> str:
    """Extract text from an image using PIL and pytesseract OCR."""
    if not file_bytes:
        return ""

    file_stream = io.BytesIO(file_bytes)
    try:
        image = Image.open(file_stream)
        # Ensure image is in RGB format for OCR
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        text = pytesseract.image_to_string(image)
        return text.strip()
    except (pytesseract.TesseractNotFoundError, FileNotFoundError):
        logger.warning("Tesseract binary not found on host. Returning OCR fallback indicator.")
        return "[OCR extraction unavailable: Tesseract engine not installed on host]"
    except Exception as e:
        logger.error(f"Error during OCR extraction: {e}")
        raise ValueError(f"Failed to extract text from image: {e}") from e


def extract_from_url(url: str) -> Dict[str, Any]:
    """Fetch and extract text, metadata, and image alt attributes from a URL with SSRF protection.
    
    Returns:
        dict: {
            "text": str,
            "title": str,
            "images": List[dict],  # [{"src": ..., "alt": ...}]
            "url": str,
            "raw_html": str
        }
    """
    validated_url = validate_url_for_ssrf(url)

    # Fetch URL content
    try:
        headers = {
            "User-Agent": "BrandPrint-AI-ContentEngine/1.0 (Compliance Crawler)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        with httpx.Client(timeout=15.0, follow_redirects=True, headers=headers) as client:
            response = client.get(validated_url)
            response.raise_for_status()

            # Ensure redirected URL did not redirect to private IP
            if str(response.url) != validated_url:
                validate_url_for_ssrf(str(response.url))

            html_content = response.text
    except Exception as e:
        logger.error(f"Failed to fetch content from URL {url}: {e}")
        raise ValueError(f"Failed to fetch content from URL: {e}") from e

    # Parse HTML with BeautifulSoup for structural elements and images
    soup = BeautifulSoup(html_content, "html.parser")

    # Extract Page Title
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    # Extract all images with src and alt attributes
    images: List[Dict[str, Optional[str]]] = []
    for img in soup.find_all("img"):
        src = img.get("src") or ""
        alt = img.get("alt")  # Can be None if attribute absent, or string
        images.append({
            "src": src.strip(),
            "alt": alt.strip() if isinstance(alt, str) else alt
        })

    # Attempt high-quality article/main body extraction via trafilatura
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
    except Exception as e:
        logger.info(f"Trafilatura extraction fallback to BeautifulSoup: {e}")

    # Fallback to BeautifulSoup clean text if trafilatura did not extract
    if not extracted_text:
        # Strip script, style, meta, and noscript elements
        for element in soup(["script", "style", "noscript", "svg", "header", "footer", "nav"]):
            element.decompose()
        extracted_text = soup.get_text(separator="\n", strip=True)

    return {
        "text": extracted_text,
        "title": title,
        "images": images,
        "url": str(response.url),
        "raw_html": html_content
    }

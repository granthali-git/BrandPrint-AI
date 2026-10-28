"""Web scraper service with strict SSRF protection and upstream error diagnosis.

Extracts clean, structured text from public documentation URLs (Notion, Google Docs, Company Wikis).
Guards against SSRF, DNS rebinding, private subnet access, and redirect hijacking while
providing clear diagnostic errors for WAF / Cloudflare bot-challenged endpoints.
"""

import ipaddress
import logging
import re
import socket
from typing import Optional, Set
from urllib.parse import urlparse, urljoin
import httpx
from bs4 import BeautifulSoup
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

# Cloud metadata IP addresses to block
METADATA_IPS: Set[str] = {
    "169.254.169.254",
    "fd00:ec2::254",
    "metadata.google.internal",
}

# Permitted ports for scraping web documentation
ALLOWED_PORTS: Set[int] = {80, 443, 8080, 8443}

# Maximum allowed redirect hops to prevent redirect loops and rebinding
MAX_REDIRECTS = 5

# Maximum allowed payload size (10 MB)
MAX_PAYLOAD_BYTES = 10 * 1024 * 1024


def validate_url_for_ssrf(url: str) -> str:
    """Validate that the given URL does not target localhost, private subnets,
    link-local addresses, sensitive internal ports, or cloud metadata endpoints.
    Returns cleaned URL with protocol scheme ensured.
    """
    if not url or not isinstance(url, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid URL string is required."
        )

    clean_url = url.strip()
    if not clean_url.startswith(("http://", "https://")):
        if "://" not in clean_url:
            clean_url = "https://" + clean_url
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid URL scheme in '{url}'. Only 'http' and 'https' protocols are allowed."
            )

    try:
        parsed = urlparse(clean_url)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Malformed URL provided: {str(e)}"
        )

    # 1. Enforce HTTP/HTTPS scheme
    scheme = parsed.scheme.lower()
    if scheme not in ("http", "https"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid URL scheme '{parsed.scheme}'. Only 'http' and 'https' protocols are allowed."
        )

    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL is missing a valid hostname."
        )

    # 2. Enforce standard web ports (block internal database, ssh, and redis ports)
    port = parsed.port
    if port is not None and port not in ALLOWED_PORTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Access to port {port} is restricted for security (SSRF Protection). Only standard web ports (80, 443, 8080, 8443) are permitted."
        )

    # 3. Block direct localhost / internal metadata string identifiers
    hostname_lower = hostname.lower()
    if (
        hostname_lower in ("localhost", "127.0.0.1", "::1", "0.0.0.0", "metadata.google.internal", "instance-data")
        or hostname_lower.endswith(".localhost")
        or hostname_lower.endswith(".local")
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Access to internal host '{hostname}' is prohibited (SSRF Protection)."
        )

    # 4. Resolve DNS and inspect all resolved IP addresses
    try:
        addr_info = socket.getaddrinfo(hostname, None)
    except socket.gaierror as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to resolve host '{hostname}': DNS lookup failed ({str(e)})."
        )

    for entry in addr_info:
        ip_str = entry[4][0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            continue

        # Handle IPv4-mapped IPv6 addresses (e.g. ::ffff:127.0.0.1)
        if isinstance(ip_obj, ipaddress.IPv6Address) and ip_obj.ipv4_mapped:
            ip_obj = ip_obj.ipv4_mapped

        # Check for cloud metadata endpoint
        if str(ip_obj) in METADATA_IPS or str(ip_obj).startswith("169.254."):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Access to cloud metadata services is strictly prohibited (SSRF Protection)."
            )

        # Check for private, loopback, link-local, reserved, or multicast IPs
        if (
            ip_obj.is_private
            or ip_obj.is_loopback
            or ip_obj.is_link_local
            or ip_obj.is_reserved
            or ip_obj.is_multicast
            or ip_obj.is_unspecified
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Access to private/local network IP '{ip_str}' is prohibited (SSRF Protection)."
            )

    return clean_url


def diagnose_upstream_error(response: httpx.Response, url: str) -> str:
    """Analyze upstream response headers, status, and body to generate an accurate,

    actionable diagnostic error message for the user.
    """
    status_code = response.status_code
    server = response.headers.get("server", "").lower()
    content_type = response.headers.get("content-type", "").lower()
    
    # Check for CDN / WAF identifiers
    cf_ray = response.headers.get("cf-ray")
    akamai = "akamaighost" in server or "akamai" in response.headers.get("x-cache", "").lower()
    aws_waf = "x-amz-cf-id" in response.headers or "cloudfront" in server
    
    body_sample = response.text[:1000] if response.text else ""
    body_lower = body_sample.lower()

    # Log safe diagnostic details (no authorization headers or cookies)
    waf_info = f"cf_ray={cf_ray}" if cf_ray else ("akamai" if akamai else ("aws_waf" if aws_waf else "generic"))
    sanitized_preview = re.sub(r"\s+", " ", body_sample[:150]).strip()
    logger.warning(
        f"Upstream fetch failure for '{url}': HTTP {status_code} | "
        f"Server: {server or 'unknown'} | WAF: {waf_info} | Body snippet: {sanitized_preview}"
    )

    # 1. Cloudflare Bot Challenge / WAF Detection
    if "cloudflare" in server or cf_ray or "just a moment..." in body_lower or "cf-challenge" in body_lower or "turnstile" in body_lower:
        return (
            f"The target website at '{url}' is protected by Cloudflare WAF / Bot Management and denied automated access (HTTP {status_code}). "
            "Cloudflare requires an interactive browser session with JavaScript / CAPTCHA verification. "
            "Action: Please copy the guideline text directly and paste it into the 'Raw Copy' tab, or upload the guidelines as a PDF/Word document."
        )

    # 2. Akamai Bot Manager / Access Denied
    if akamai or ("access denied" in body_lower and "reference #" in body_lower):
        return (
            f"The target website at '{url}' blocked automated crawler access (HTTP {status_code} via Akamai Edge Security). "
            "Action: Please copy the guideline text into the 'Raw Copy' tab, or upload the guidelines as a document."
        )

    # 3. AWS WAF / CloudFront Block
    if aws_waf and status_code in (403, 405):
        return (
            f"The target website at '{url}' is protected by AWS WAF / CloudFront and blocked the request (HTTP {status_code}). "
            "Action: Please copy the guideline text into the 'Raw Copy' tab, or upload as a document."
        )

    # 4. Standard HTTP 403 Forbidden
    if status_code == 403:
        return (
            f"Access to '{url}' was denied by the remote server (HTTP 403 Forbidden). "
            "The page may be private, require internal company VPN access, or restrict automated clients. "
            "Action: Copy the guideline text into the 'Raw Copy' tab, or upload as a document."
        )

    # 5. HTTP 401 Unauthorized
    if status_code == 401:
        return (
            f"The webpage at '{url}' requires authentication or credentials (HTTP 401 Unauthorized). "
            "Action: Please sign in, copy the guideline text into the 'Raw Copy' tab, or upload as a document."
        )

    # 6. HTTP 404 Not Found
    if status_code == 404:
        return (
            f"The webpage at '{url}' was not found on the remote server (HTTP 404 Not Found). "
            "Please check the URL for typos or broken paths."
        )

    # 7. HTTP 429 Rate Limiting
    if status_code == 429:
        return (
            f"The remote server at '{url}' rate-limited the connection (HTTP 429 Too Many Requests). "
            "Please wait a few minutes before retrying."
        )

    # 8. HTTP 5xx Server Errors
    if status_code >= 500:
        return (
            f"The remote server at '{url}' encountered an internal server error (HTTP {status_code}). "
            "The host website is temporarily experiencing technical difficulties."
        )

    # Default fallback
    return f"Remote server returned HTTP {status_code} while fetching '{url}'."


async def scrape_guideline_url(url: str) -> str:
    """Scrape and extract structured guideline text from a public web page with

    strict SSRF protection, hop-by-hop redirect verification, content-type checks,
    and detailed upstream diagnostic error reporting.
    """
    # 1. Initial SSRF validation on the submitted URL
    validate_url_for_ssrf(url)

    # Standard browser headers to ensure maximum compatibility with public web documentation
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
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

    # 2. Hop-by-hop redirect following with strict SSRF validation before each request
    current_url = validate_url_for_ssrf(url)
    redirect_count = 0
    final_response: Optional[httpx.Response] = None

    timeout_config = httpx.Timeout(connect=8.0, read=15.0, write=8.0, pool=5.0)

    try:
        async with httpx.AsyncClient(timeout=timeout_config, follow_redirects=False) as client:
            while redirect_count <= MAX_REDIRECTS:
                # Validate URL before dispatching each HTTP request
                current_url = validate_url_for_ssrf(current_url)

                try:
                    response = await client.get(current_url, headers=headers)
                except httpx.ConnectTimeout:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Connection to '{current_url}' timed out while establishing handshake. The host server is unreachable."
                    )
                except httpx.ReadTimeout:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Request to '{current_url}' timed out after 15 seconds. The remote server took too long to deliver content."
                    )
                except httpx.ConnectError as ce:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Failed to connect to '{current_url}': Host connection refused or DNS unreachable ({str(ce)})."
                    )
                except httpx.RequestError as re_err:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Network error while connecting to '{current_url}': {str(re_err)}"
                    )

                # Check if response is a redirect
                if response.is_redirect:
                    redirect_count += 1
                    if redirect_count > MAX_REDIRECTS:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Exceeded maximum redirect limit ({MAX_REDIRECTS}) while fetching '{url}'."
                        )

                    location = response.headers.get("location")
                    if not location:
                        # Redirect without Location header
                        final_response = response
                        break

                    # Resolve relative redirect against current_url
                    next_url = urljoin(current_url, location)

                    # Strictly validate the next hop for SSRF BEFORE following it!
                    next_url = validate_url_for_ssrf(next_url)
                    current_url = next_url
                    continue
                else:
                    final_response = response
                    break

    except HTTPException:
        raise
    except Exception as general_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unexpected error while fetching '{url}': {str(general_err)}"
        )

    if not final_response:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to obtain a response from '{url}'."
        )

    # 3. Check HTTP status code
    if final_response.status_code >= 400:
        diagnostic_msg = diagnose_upstream_error(final_response, current_url)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=diagnostic_msg
        )

    # 4. Check Content-Type & Format (supports HTML pages and public PDF guideline documents)
    content_type_header = final_response.headers.get("content-type", "").lower()
    base_content_type = content_type_header.split(";")[0].strip() if content_type_header else ""
    body_bytes = final_response.content

    # 5. Check Content-Length to protect against oversized payloads
    if len(body_bytes) > MAX_PAYLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The resource at '{current_url}' exceeds the maximum allowed size of 10 MB ({len(body_bytes) // (1024 * 1024)} MB)."
        )

    is_pdf = (
        body_bytes.startswith(b"%PDF-")
        or base_content_type in ("application/pdf", "application/x-pdf")
        or current_url.lower().endswith(".pdf")
    )

    if is_pdf:
        logger.info(f"Extracting guideline text from PDF URL: {current_url}")
        from app.services.document_parser import extract_from_pdf
        pdf_text = extract_from_pdf(body_bytes, current_url)
        if not pdf_text or len(pdf_text.strip()) < 30:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Successfully downloaded PDF from '{current_url}', but could not extract readable guideline text. The document may be scanned or empty."
            )
        logger.info(f"Successfully extracted {len(pdf_text)} characters of guideline text from PDF URL '{current_url}'.")
        return pdf_text

    if base_content_type in ("application/zip", "application/octet-stream") or base_content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"The URL '{current_url}' returned a binary file format ('{base_content_type}') instead of an HTML web page or PDF document. "
                "To import image creative assets or archives, please use the 'Upload Document' tab."
            )
        )

    html_content = final_response.text

    # 6. Parse HTML and extract structured content
    try:
        soup = BeautifulSoup(html_content, "html.parser")

        # Strip scripts, styles, navigation, headers, footers, and non-content elements
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript", "svg", "iframe", "form"]):
            tag.decompose()

        # Target main content area if available
        main_content = (
            soup.find("main")
            or soup.find("article")
            or soup.find("div", {"id": "content"})
            or soup.find("div", {"class": "content"})
            or soup.find("div", {"role": "main"})
            or soup.body
        )

        if not main_content:
            main_content = soup

        extracted_lines = []

        # Iterate through structural elements in document order
        for el in main_content.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "blockquote", "table"]):
            tag_name = el.name.lower()
            text = el.get_text(separator=" ", strip=True)
            if not text:
                continue

            if tag_name in ("h1", "h2"):
                extracted_lines.append(f"\n## {text}\n")
            elif tag_name in ("h3", "h4"):
                extracted_lines.append(f"\n### {text}\n")
            elif tag_name in ("h5", "h6"):
                extracted_lines.append(f"\n#### {text}\n")
            elif tag_name == "li":
                extracted_lines.append(f"• {text}")
            elif tag_name == "blockquote":
                extracted_lines.append(f"> {text}")
            elif tag_name == "table":
                rows = []
                for tr in el.find_all("tr"):
                    cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                    if cells:
                        rows.append(" | ".join(cells))
                if rows:
                    extracted_lines.append("\n" + "\n".join(rows) + "\n")
            else:
                extracted_lines.append(f"{text}\n")

        clean_text = "\n".join(extracted_lines).strip()

        # Fallback to general get_text if structured traversal was minimal
        if len(clean_text) < 40:
            clean_text = main_content.get_text(separator="\n", strip=True)

        if len(clean_text) < 30:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Successfully connected to '{current_url}', but could not extract readable guideline text. "
                    "The page appears to require client-side JavaScript rendering (Single-Page Application) or user authentication. "
                    "Action: Please copy the visible guideline text and paste it into the 'Raw Copy' tab."
                )
            )

        logger.info(f"Successfully scraped {len(clean_text)} characters of guideline text from '{current_url}'.")
        return clean_text

    except HTTPException:
        raise
    except Exception as parse_err:
        logger.error(f"Error parsing HTML from '{current_url}': {parse_err}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse readable content from webpage: {str(parse_err)}"
        )

"""Web scraper service with strict SSRF protection for brand guideline ingestion.
Extracts clean, structured text from public documentation URLs (Notion, Google Docs, Company Wikis).
"""
import ipaddress
import logging
import socket
from urllib.parse import urlparse
from typing import Optional
import httpx
from bs4 import BeautifulSoup
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

# Cloud metadata IP addresses to block
METADATA_IPS = {"169.254.169.254", "fd00:ec2::254"}


def validate_url_for_ssrf(url: str) -> None:
    """Validate that the given URL does not target localhost, private subnets,

    link-local addresses, or cloud metadata endpoints.
    """
    if not url or not isinstance(url, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid URL string is required."
        )

    clean_url = url.strip()
    try:
        parsed = urlparse(clean_url)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Malformed URL provided: {str(e)}"
        )

    # 1. Enforce HTTP/HTTPS scheme
    if parsed.scheme.lower() not in ("http", "https"):
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

    # 2. Block direct localhost strings
    hostname_lower = hostname.lower()
    if hostname_lower in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Access to localhost / loopback addresses is prohibited (SSRF Protection)."
        )

    # 3. Resolve DNS and inspect resolved IP addresses
    try:
        addr_info = socket.getaddrinfo(hostname, None)
    except socket.gaierror as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to resolve host '{hostname}': {str(e)}"
        )

    for entry in addr_info:
        ip_str = entry[4][0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            continue

        # Check for cloud metadata endpoint
        if ip_str in METADATA_IPS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Access to cloud metadata services is strictly prohibited (SSRF Protection)."
            )

        # Check for private, loopback, link-local, or reserved IPs
        if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_reserved or ip_obj.is_multicast:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Access to private/local network IP '{ip_str}' is prohibited (SSRF Protection)."
            )


async def scrape_guideline_url(url: str) -> str:
    """Scrape and extract structured guideline text from a public web page with SSRF protection."""
    # 1. SSRF Validation
    validate_url_for_ssrf(url)

    headers = {
        "User-Agent": "BrandPrintAI-ComplianceBot/1.0 (+https://brandprint.ai/bot; enterprise-brand-safety)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    # 2. Fetch page content via AsyncClient
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            
            # Re-validate destination URL after redirects
            if response.history:
                final_url = str(response.url)
                validate_url_for_ssrf(final_url)

            if response.status_code >= 400:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Remote server returned HTTP {response.status_code} while fetching '{url}'."
                )

            html_content = response.text

    except HTTPException:
        raise
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Request to '{url}' timed out after 15 seconds. Please ensure the page is accessible."
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Network error while connecting to '{url}': {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to fetch content from '{url}': {str(e)}"
        )

    # 3. Parse HTML and extract structured content
    try:
        soup = BeautifulSoup(html_content, "html.parser")

        # Strip scripts, styles, navigation, headers, and footers
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript", "svg", "iframe", "form"]):
            tag.decompose()

        # Target main content area if available
        main_content = soup.find("main") or soup.find("article") or soup.find("div", {"id": "content"}) or soup.find("div", {"class": "content"}) or soup.body

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
                # Standard paragraph
                extracted_lines.append(f"{text}\n")

        clean_text = "\n".join(extracted_lines).strip()

        # If structured element traversal produced too little, fallback to get_text
        if len(clean_text) < 30:
            clean_text = main_content.get_text(separator="\n", strip=True)

        if len(clean_text) < 20:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"The webpage at '{url}' did not contain readable guideline text or requires authentication/JavaScript."
            )

        logger.info(f"Successfully scraped {len(clean_text)} characters of guideline text from '{url}'.")
        return clean_text

    except HTTPException:
        raise
    except Exception as parse_err:
        logger.error(f"Error parsing HTML from '{url}': {parse_err}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse readable content from webpage: {str(parse_err)}"
        )

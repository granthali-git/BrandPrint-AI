"""Test suite for URL Guideline Ingestion, SSRF Protection, and Upstream Diagnostics.

Covers:
1. Successful public page ingestion and rule extraction
2. Upstream HTTP 403 (Cloudflare WAF / anti-bot challenge) with actionable diagnosis
3. Connection and Read Timeout handling
4. Invalid URL, unsupported scheme, and restricted port rejection
5. Redirect to blocked internal/metadata address (SSRF hop-by-hop protection)
6. Page with no useful text (Single-Page App / JavaScript-dependent shell)
7. Full API endpoint verification (POST /api/guidelines/ingest-url)
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
import httpx

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.scraper_service import (
    validate_url_for_ssrf,
    diagnose_upstream_error,
    scrape_guideline_url
)
from app.models.brand import Brand
from app.models.user import User, UserRole
from app.core.security import get_password_hash, create_access_token
from tests.conftest import TestingSessionLocal, client


# ============================================================================
# 1. SUCCESSFUL PUBLIC PAGE INGESTION
# ============================================================================
@pytest.mark.anyio
async def test_successful_public_page_scraping():
    """Verify that a standard public documentation HTML page is cleanly scraped."""
    sample_html = """
    <!DOCTYPE html>
    <html>
    <head><title>AstraForge Brand Guidelines</title></head>
    <body>
        <nav><a href="/">Home</a></nav>
        <main>
            <h1>AstraForge Brand Standards</h1>
            <p>Welcome to our official design and voice governance documentation.</p>
            <h2>Tone of Voice</h2>
            <p>Always communicate with executive clarity, active phrasing, and technical precision.</p>
            <h2>Prohibited Claims</h2>
            <ul>
                <li>Never promise 100% bug-free uptime or zero latency without certified SOC-2 audit proof.</li>
                <li>Never advertise unbeatable prices or claim to be the number one cheapest solution.</li>
            </ul>
        </main>
        <footer>Copyright 2026 AstraForge</footer>
    </body>
    </html>
    """
    mock_resp = httpx.Response(
        status_code=200,
        headers={"content-type": "text/html; charset=utf-8"},
        text=sample_html,
        request=httpx.Request("GET", "https://example.com/brand-guidelines")
    )

    with patch.object(httpx.AsyncClient, "get", return_value=mock_resp):
        with patch("app.services.scraper_service.validate_url_for_ssrf", return_value=None):
            extracted = await scrape_guideline_url("https://example.com/brand-guidelines")
            assert "AstraForge Brand Standards" in extracted
            assert "Tone of Voice" in extracted
            assert "100% bug-free" in extracted
            assert "Copyright 2026" not in extracted  # Footer stripped
            assert "Home" not in extracted  # Nav stripped


# ============================================================================
# 2. UPSTREAM HTTP 403 (CLOUDFLARE / ANTI-BOT DIAGNOSIS)
# ============================================================================
@pytest.mark.anyio
async def test_upstream_403_cloudflare_waf_diagnosis():
    """Verify that upstream 403 (Cloudflare WAF / anti-bot challenge) produces an actionable error."""
    cloudflare_html = """
    <!DOCTYPE html><html lang="en-US">
    <head><title>Just a moment...</title></head>
    <body>
        <h1>Attention Required! | Cloudflare</h1>
        <p>Please enable JavaScript and cookies to continue.</p>
    </body>
    </html>
    """
    mock_resp = httpx.Response(
        status_code=403,
        headers={
            "server": "cloudflare",
            "cf-ray": "8e3b123456789abc-IAD",
            "content-type": "text/html; charset=utf-8"
        },
        text=cloudflare_html,
        request=httpx.Request("GET", "https://www.ox.ac.uk/brand/guidelines")
    )

    with patch.object(httpx.AsyncClient, "get", return_value=mock_resp):
        with patch("app.services.scraper_service.validate_url_for_ssrf", return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await scrape_guideline_url("https://www.ox.ac.uk/brand/guidelines")

            err = exc_info.value
            assert err.status_code == 400
            assert "Cloudflare WAF / Bot Management" in err.detail
            assert "Raw Copy" in err.detail
            assert "Upload" in err.detail or "PDF" in err.detail


# ============================================================================
# 3. CONNECTION & READ TIMEOUT HANDLING
# ============================================================================
@pytest.mark.anyio
async def test_connection_and_read_timeouts():
    """Verify that network and read timeouts produce clear error messages."""
    with patch.object(httpx.AsyncClient, "get", side_effect=httpx.ReadTimeout("Server took too long")):
        with patch("app.services.scraper_service.validate_url_for_ssrf", return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await scrape_guideline_url("https://slow-site.example.com/docs")

            err = exc_info.value
            assert err.status_code == 400
            assert "timed out after 15 seconds" in err.detail

    with patch.object(httpx.AsyncClient, "get", side_effect=httpx.ConnectTimeout("Handshake failed")):
        with patch("app.services.scraper_service.validate_url_for_ssrf", return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await scrape_guideline_url("https://unreachable-host.example.com/docs")

            err = exc_info.value
            assert err.status_code == 400
            assert "timed out while establishing handshake" in err.detail


# ============================================================================
# 4. INVALID URL, SCHEME & PORT VALIDATION
# ============================================================================
def test_invalid_urls_and_restricted_ports():
    """Verify that malformed URLs, non-HTTP schemes, and internal ports are blocked."""
    # Empty string
    with pytest.raises(HTTPException) as exc:
        validate_url_for_ssrf("")
    assert "A valid URL string is required" in exc.value.detail

    # Non-HTTP/HTTPS scheme
    with pytest.raises(HTTPException) as exc:
        validate_url_for_ssrf("ftp://example.com/resource")
    assert "Only 'http' and 'https' protocols are allowed" in exc.value.detail

    # Missing hostname
    with pytest.raises(HTTPException) as exc:
        validate_url_for_ssrf("https:///path")
    assert "missing a valid hostname" in exc.value.detail

    # Restricted sensitive port (e.g., SSH 22, Redis 6379, MySQL 3306)
    with pytest.raises(HTTPException) as exc:
        validate_url_for_ssrf("http://example.com:22/docs")
    assert "Access to port 22 is restricted" in exc.value.detail

    with pytest.raises(HTTPException) as exc:
        validate_url_for_ssrf("http://example.com:6379/data")
    assert "Access to port 6379 is restricted" in exc.value.detail


# ============================================================================
# 5. REDIRECT TO BLOCKED ADDRESS (SSRF HOP-BY-HOP)
# ============================================================================
def test_direct_ssrf_prohibitions():
    """Verify direct localhost and cloud metadata targets are rejected."""
    prohibited_urls = [
        "http://localhost:8080/admin",
        "http://127.0.0.1/internal",
        "http://0.0.0.0/",
        "http://169.254.169.254/latest/meta-data/",
        "http://metadata.google.internal/computeMetadata/v1/",
    ]
    for bad_url in prohibited_urls:
        with pytest.raises(HTTPException) as exc:
            validate_url_for_ssrf(bad_url)
        assert exc.value.status_code == 400
        assert "prohibited" in exc.value.detail.lower() or "blocked" in exc.value.detail.lower()


@pytest.mark.anyio
async def test_redirect_to_internal_ip_blocked():
    """Verify that a public URL redirecting to an internal IP or cloud metadata is stopped."""
    redirect_resp = httpx.Response(
        status_code=302,
        headers={"location": "http://169.254.169.254/latest/meta-data/"},
        request=httpx.Request("GET", "https://public-site.com/login")
    )

    with patch.object(httpx.AsyncClient, "get", return_value=redirect_resp):
        with patch("app.services.scraper_service.validate_url_for_ssrf", side_effect=[None, HTTPException(status_code=400, detail="Access to cloud metadata services is strictly prohibited (SSRF Protection).")]):
            with pytest.raises(HTTPException) as exc_info:
                await scrape_guideline_url("https://public-site.com/login")

            assert "cloud metadata" in exc_info.value.detail


# ============================================================================
# 6. PAGE WITH NO USEFUL TEXT (SPA / JAVASCRIPT SHELL)
# ============================================================================
@pytest.mark.anyio
async def test_page_with_no_useful_text_spa():
    """Verify that empty client-side rendering shells produce an informative 422 error."""
    spa_empty_html = """
    <!DOCTYPE html>
    <html>
    <head><title>App</title><script src="/bundle.js"></script></head>
    <body>
        <div id="root"></div>
    </body>
    </html>
    """
    mock_resp = httpx.Response(
        status_code=200,
        headers={"content-type": "text/html; charset=utf-8"},
        text=spa_empty_html,
        request=httpx.Request("GET", "https://spa.example.com")
    )

    with patch.object(httpx.AsyncClient, "get", return_value=mock_resp):
        with patch("app.services.scraper_service.validate_url_for_ssrf", return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await scrape_guideline_url("https://spa.example.com")

            err = exc_info.value
            assert err.status_code == 422
            assert "could not extract readable guideline text" in err.detail
            assert "Single-Page Application" in err.detail
            assert "Raw Copy" in err.detail


# ============================================================================
# 7. FULL API ENDPOINT INTEGRATION (POST /api/guidelines/ingest-url)
# ============================================================================
def test_full_api_ingest_url_endpoint():
    """Verify the FastAPI endpoint returns candidate rules for review."""
    db = TestingSessionLocal()
    user = User(
        email="test_scraper_admin@acme.com",
        hashed_password=get_password_hash("Pass123!"),
        role=UserRole.BrandManager
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    brand = Brand(name="Scraper Brand", created_by=user.id)
    db.add(brand)
    db.commit()
    db.refresh(brand)
    brand_id = brand.id
    user_id = str(user.id)
    user_email = user.email
    db.close()

    token = create_access_token({"sub": user_id, "email": user_email, "role": "BrandManager"})
    auth_header = {"Authorization": f"Bearer {token}"}

    sample_guidelines_text = """
    ## Brand Identity Standards
    1. Always use approved hex color #0B3C49 for headers.
    2. Never claim #1 rankings without third-party proof.
    """

    with patch("app.routes.guidelines.scrape_guideline_url", return_value=sample_guidelines_text):
        res = client.post(
            "/api/guidelines/ingest-url",
            json={
                "brand_id": brand_id,
                "url": "https://company.example.com/brand-manual",
                "auto_commit": False,
                "preview_only": True
            },
            headers=auth_header
        )
        assert res.status_code == 201, res.text
        data = res.json()
        assert data["brand_id"] == brand_id
        assert data["rules_extracted_count"] >= 1
        assert len(data["rules"]) >= 1
        assert "extracted for review" in data["message"]

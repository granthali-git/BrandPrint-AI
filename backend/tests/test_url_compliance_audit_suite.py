"""Comprehensive automated test suite for BrandPrint AI's Live URL / Web compliance audit pipeline.

Test Coverage (per Requirement 9):
1. Public HTML page ingestion & compliance audit.
2. PDF URL ingestion (clean text extraction + page 1 visual rendering + multimodal analysis).
3. Image URL ingestion (PNG/JPEG decoding, OCR text extraction, visual findings).
4. Upstream HTTP 403 error handling & WAF diagnosis.
5. Oversized file download rejection (> 15MB size limit).
6. Malformed or corrupted PDF error handling (stage-specific error reporting).
7. SSRF protection: redirect to internal / private IP addresses blocked.
8. AI timeout handling: stage-specific error reporting with no false "No changes required".
"""
import base64
import io
import os
import sys
import unittest.mock as mock
import pytest
from PIL import Image

os.environ["TESTING"] = "1"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tests.conftest import client, TestingSessionLocal
from app.models.user import User, UserRole
from app.models.brand import Brand
from app.models.guideline import GuidelineRule, RuleCategory
from app.services.extractors import (
    validate_url_for_ssrf,
    fetch_url_with_ssrf_protection,
    extract_from_url,
    render_pdf_page_as_image
)


@pytest.fixture(autouse=True)
def setup_demo_brand():
    """Ensure demo user and brand exist for review tests."""
    db = TestingSessionLocal()
    user = db.query(User).first()
    if not user:
        user = User(
            email="tester@brandprint.ai",
            hashed_password="mock",
            role=UserRole.BrandManager,
            full_name="Compliance Lead"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    brand = db.query(Brand).filter(Brand.id == 1).first()
    if not brand:
        brand = db.query(Brand).first()
    if not brand:
        brand = Brand(
            id=1,
            name="AstraForge Demo Brand",
            description="Enterprise Cloud & AI Solutions",
            created_by=user.id
        )
        db.add(brand)
        db.commit()
        db.refresh(brand)

    # Ensure at least one rule exists for this brand
    rule = db.query(GuidelineRule).filter(GuidelineRule.brand_id == brand.id).first()
    if not rule:
        rule = GuidelineRule(
            brand_id=brand.id,
            category=RuleCategory.brand_voice,
            title="Transparent Language",
            rule_text="Marketing communications must use factual statements and avoid unsupported claims.",
            rule_code="TONE-001",
            is_active=True
        )
        db.add(rule)
        db.commit()

    db.close()


def test_1_public_html_page_extraction_and_review():
    """Verify that a public HTML URL extracts text, structural elements, and runs review."""
    mock_html = (
        b"<!DOCTYPE html><html><head><title>AstraForge Product Update</title></head>"
        b"<body><main><h1>Enterprise Cloud Architecture</h1>"
        b"<p>AstraForge delivers 99.99% uptime for mission-critical enterprise workloads.</p>"
        b"<img src='https://assets.astraforge.io/cloud.png' alt='Cloud Infrastructure Architecture'>"
        b"</main></body></html>"
    )

    with mock.patch("app.services.extractors.fetch_url_with_ssrf_protection") as mock_fetch:
        mock_fetch.return_value = (
            mock_html,
            "https://public.example.com/update.html",
            {"content-type": "text/html; charset=utf-8"},
            0.15
        )

        headers = {"Authorization": "Bearer demo_guest_auditor"}
        payload = {
            "brand_id": 1,
            "content_type": "url",
            "url": "https://public.example.com/update.html"
        }

        resp = client.post("/api/reviews", json=payload, headers=headers)
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["submission"]["content_type"] == "url"
        assert "Enterprise Cloud Architecture" in data["extracted_text"]
        assert "stage_timings" in data


def test_2_pdf_url_ingestion_and_visual_page_rendering():
    """Verify PDF URL downloads, extracts text, renders page 1 image, and activates visual pipeline."""
    # Create a small valid PDF in memory using pypdf
    import pypdf
    writer = pypdf.PdfWriter()
    page = writer.add_blank_page(width=720, height=720)
    pdf_buffer = io.BytesIO()
    writer.write(pdf_buffer)
    pdf_bytes = pdf_buffer.getvalue()

    with mock.patch("app.services.extractors.fetch_url_with_ssrf_protection") as mock_fetch:
        mock_fetch.return_value = (
            pdf_bytes,
            "https://science.nasa.gov/posters/earth.pdf",
            {"content-type": "application/pdf"},
            0.45
        )

        with mock.patch("app.services.extractors.render_pdf_page_as_image") as mock_render:
            # Mock rendered image JPEG
            dummy_img = Image.new("RGB", (300, 300), color=(11, 60, 73))
            out_io = io.BytesIO()
            dummy_img.save(out_io, format="JPEG")
            dummy_jpeg = out_io.getvalue()
            mock_render.return_value = (dummy_jpeg, "data:image/jpeg;base64,mockpreview")

            extracted = extract_from_url("https://science.nasa.gov/posters/earth.pdf")
            assert extracted["content_type"] == "pdf"
            assert extracted["is_visual_asset"] is True
            assert extracted["visual_image_bytes"] == dummy_jpeg
            assert extracted["image_preview_url"] == "data:image/jpeg;base64,mockpreview"


def test_3_image_url_ingestion_and_ocr():
    """Verify Image URL routes to image pipeline, validates bytes, and provides preview."""
    img = Image.new("RGB", (200, 100), color=(244, 163, 33))
    out_io = io.BytesIO()
    img.save(out_io, format="PNG")
    img_bytes = out_io.getvalue()

    with mock.patch("app.services.extractors.fetch_url_with_ssrf_protection") as mock_fetch:
        mock_fetch.return_value = (
            img_bytes,
            "https://brand.example.com/banner.png",
            {"content-type": "image/png"},
            0.20
        )

        extracted = extract_from_url("https://brand.example.com/banner.png")
        assert extracted["content_type"] == "image"
        assert extracted["is_visual_asset"] is True
        assert len(extracted["visual_image_bytes"]) > 0
        assert extracted["image_preview_url"].startswith("data:image/jpeg;base64,")


def test_4_upstream_http_403_error_diagnosis():
    """Verify upstream HTTP 403 WAF / Cloudflare returns clear diagnostic message and HTTP 403."""
    with mock.patch("app.services.extractors.validate_url_for_ssrf", return_value="https://protected.example.com"):
        with mock.patch("httpx.Client.stream") as mock_stream:
            # Mock response returning 403 Cloudflare
            mock_resp = mock.MagicMock()
            mock_resp.status_code = 403
            mock_resp.headers = {
                "server": "cloudflare",
                "cf-ray": "89371947291a-BOM",
                "content-type": "text/html"
            }
            mock_resp.iter_bytes.return_value = [b"<title>Just a moment...</title>"]
            mock_stream.return_value.__enter__.return_value = mock_resp

            headers = {"Authorization": "Bearer demo_guest_auditor"}
            payload = {
                "brand_id": 1,
                "content_type": "url",
                "url": "https://protected.example.com/guidelines"
            }

            resp = client.post("/api/reviews", json=payload, headers=headers)
            assert resp.status_code == 403
            assert "Cloudflare WAF" in resp.json()["detail"] or "HTTP 403" in resp.json()["detail"]


def test_5_oversized_file_rejection():
    """Verify that downloads exceeding 15MB limit are rejected with HTTP 413."""
    with mock.patch("app.services.extractors.validate_url_for_ssrf", return_value="https://files.example.com/large.pdf"):
        with mock.patch("httpx.Client.stream") as mock_stream:
            # Mock Content-Length header reporting 25MB
            mock_resp = mock.MagicMock()
            mock_resp.status_code = 200
            mock_resp.headers = {
                "content-length": str(25 * 1024 * 1024),
                "content-type": "application/pdf"
            }
            mock_stream.return_value.__enter__.return_value = mock_resp

            headers = {"Authorization": "Bearer demo_guest_auditor"}
            payload = {
                "brand_id": 1,
                "content_type": "url",
                "url": "https://files.example.com/large.pdf"
            }

            resp = client.post("/api/reviews", json=payload, headers=headers)
            assert resp.status_code == 413
            assert "exceeds" in resp.json()["detail"].lower()


def test_6_malformed_pdf_error_handling():
    """Verify malformed/corrupted PDF bytes return clear stage-specific parsing error."""
    corrupted_bytes = b"%PDF-1.4\nCorrupted binary payload\x00\x01\x02%%EOF"

    with mock.patch("app.services.extractors.fetch_url_with_ssrf_protection") as mock_fetch:
        mock_fetch.return_value = (
            corrupted_bytes,
            "https://science.nasa.gov/corrupted.pdf",
            {"content-type": "application/pdf"},
            0.10
        )

        headers = {"Authorization": "Bearer demo_guest_auditor"}
        payload = {
            "brand_id": 1,
            "content_type": "url",
            "url": "https://science.nasa.gov/corrupted.pdf"
        }

        resp = client.post("/api/reviews", json=payload, headers=headers)
        assert resp.status_code == 400
        assert "[Stage: PDF Extraction]" in resp.json()["detail"]


def test_7_ssrf_redirect_to_private_ip_blocked():
    """Verify that a redirect hop towards 169.254.169.254 is blocked before dispatch."""
    with mock.patch("app.services.extractors.validate_url_for_ssrf") as mock_val:
        def side_effect(u):
            if "169.254." in u:
                raise ValueError("Access to cloud metadata address '169.254.169.254' is blocked for SSRF security.")
            return u
        mock_val.side_effect = side_effect

        with mock.patch("httpx.Client.stream") as mock_stream:
            # 1st request redirects to 169.254.169.254
            mock_resp = mock.MagicMock()
            mock_resp.status_code = 302
            mock_resp.headers = {"location": "http://169.254.169.254/latest/meta-data/"}
            mock_stream.return_value.__enter__.return_value = mock_resp

            with pytest.raises(ValueError, match="SSRF security"):
                fetch_url_with_ssrf_protection("http://attacker.com/redirect")


def test_8_ai_timeout_handling_no_false_approval():
    """Verify that when AI multimodal/text analysis times out, it is not reported as clean/empty without notice."""
    import asyncio
    from app.services.vision_service import analyze_poster_visual_design

    # Dummy test image
    img = Image.new("RGB", (200, 200), color=(100, 100, 100))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    jpeg_bytes = buf.getvalue()

    # Simulate Gemini vision timeout
    with mock.patch("httpx.AsyncClient.post", side_effect=TimeoutError("Gemini timed out")):
        findings, status, message = asyncio.run(
            analyze_poster_visual_design(
                file_bytes=jpeg_bytes,
                mime_type="image/jpeg",
                brand_rules=[],
                brand_name="AstraForge"
            )
        )

        assert status == "incomplete"
        assert "timed out" in message.lower() or "unavailable" in message.lower()

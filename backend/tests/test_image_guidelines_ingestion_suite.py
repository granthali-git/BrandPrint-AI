"""Comprehensive automated test suite for BrandPrint AI Image Guideline Ingestion.

Validates:
1. Supported image formats (PNG, JPG, JPEG, WEBP) decoding and preprocessing with Pillow.
2. Multiple image files in a single submission with order preservation.
3. Accurate extraction of Brand DNA rules (tone, visual, prohibited claims, facts, accessibility).
4. Preservation of source filename and page/image references on each extracted rule.
5. Graceful handling and rejection of unreadable, blank, or blurry images without rule hallucinations.
6. Rejection of unsupported file formats and oversized images (>10MB).
7. Complete administrator review workflow: preview_only extraction followed by bulkSave.
8. Security: authentication validation and brand access isolation.
"""
import io
import os
import sys
import unittest.mock as mock
import pytest
from PIL import Image, ImageDraw

os.environ["TESTING"] = "1"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tests.conftest import client, TestingSessionLocal
from app.models.user import User, UserRole
from app.models.brand import Brand
from app.models.guideline import GuidelineRule, RuleCategory
from app.services.document_parser import (
    extract_text_from_upload,
    extract_from_image_guideline,
    SUPPORTED_EXTENSIONS,
    IMAGE_EXTENSIONS
)
from fastapi import HTTPException


def create_test_image(format_name: str = "PNG", text_content: str = "", size: tuple = (400, 300)) -> bytes:
    """Helper to generate an in-memory image with optional text content."""
    img = Image.new("RGB", size, color="#FBF9F4")
    draw = ImageDraw.Draw(img)
    
    if text_content:
        # Draw header banner
        draw.rectangle([(0, 0), (size[0], 40)], fill="#0B3C49")
        draw.text((10, 10), "AstraForge Brand Policy & Visual Guide", fill="#FFFFFF")
        
        # Draw text lines
        y = 50
        for line in text_content.splitlines():
            if line.strip():
                draw.text((15, y), line.strip(), fill="#1A272B")
                y += 20
    
    buf = io.BytesIO()
    fmt = format_name.upper()
    if fmt == "JPG":
        fmt = "JPEG"
    img.save(buf, format=fmt)
    return buf.getvalue()


@pytest.fixture(autouse=True)
def setup_demo_brand():
    """Ensure demo user and brand exist for guideline tests."""
    db = TestingSessionLocal()
    user = db.query(User).filter(User.email == "tester@brandprint.ai").first()
    if not user:
        user = User(
            email="tester@brandprint.ai",
            hashed_password="mock",
            role=UserRole.BrandManager,
            full_name="Compliance Lead"
        )
        db.add(user)
        try:
            db.commit()
            db.refresh(user)
        except Exception:
            db.rollback()
            user = db.query(User).filter(User.email == "tester@brandprint.ai").first()

    brand = db.query(Brand).first()
    if not brand:
        brand = Brand(
            name="AstraForge Demo Brand",
            description="Enterprise Cloud & AI Solutions",
            created_by=user.id if user else 1
        )
        db.add(brand)
        try:
            db.commit()
            db.refresh(brand)
        except Exception:
            db.rollback()
    db.close()


AUTH_HEADERS = {"Authorization": "Bearer demo_guest_auditor"}


# ============================================================================
# 1. SUPPORTED IMAGE FORMATS & DECODING (PNG, JPG, JPEG, WEBP)
# ============================================================================
def test_image_formats_supported_and_decoded():
    """Verify that PNG, JPG, JPEG, and WEBP formats are recognized and decoded by Pillow."""
    assert ".png" in IMAGE_EXTENSIONS
    assert ".jpg" in IMAGE_EXTENSIONS
    assert ".jpeg" in IMAGE_EXTENSIONS
    assert ".webp" in IMAGE_EXTENSIONS

    for ext, fmt in [(".png", "PNG"), (".jpg", "JPEG"), (".jpeg", "JPEG"), (".webp", "WEBP")]:
        img_bytes = create_test_image(format_name=fmt, text_content="Brand Rule: Always use Deep Ocean Teal for logos.")
        
        # Verify Pillow decodes successfully without error
        img_stream = io.BytesIO(img_bytes)
        pil_img = Image.open(img_stream)
        assert pil_img.format.upper() in ("PNG", "JPEG", "WEBP")


# ============================================================================
# 2. UNSUPPORTED FILE TYPE REJECTION
# ============================================================================
def test_unsupported_file_type_rejected():
    """Verify that non-supported file formats (e.g. .exe, .zip, .mp4) are rejected with HTTP 400."""
    fake_data = b"PK\x03\x04fakezipcontent"
    
    with pytest.raises(HTTPException) as exc_info:
        extract_text_from_upload(fake_data, "guidelines_backup.zip")
    assert exc_info.value.status_code == 400
    assert "Unsupported file type" in exc_info.value.detail


# ============================================================================
# 3. OVERSIZED IMAGE REJECTION (> 10MB)
# ============================================================================
def test_oversized_image_rejected():
    """Verify that images exceeding the 10MB limit are rejected with HTTP 413."""
    oversized_bytes = b"0" * (11 * 1024 * 1024)  # 11 MB
    with pytest.raises(HTTPException) as exc_info:
        extract_from_image_guideline(oversized_bytes, "giant_poster.png")
    assert exc_info.value.status_code == 413
    assert "10MB" in exc_info.value.detail


# ============================================================================
# 4. BLURRY OR UNREADABLE IMAGE HANDLING (NO INVENTED RULES)
# ============================================================================
def test_blurry_or_unreadable_image_handling():
    """Verify that images containing no readable text return an informative error and do not invent rules."""
    blank_bytes = create_test_image(format_name="PNG", text_content="", size=(150, 150))
    
    with mock.patch("app.services.extractors.extract_text_via_gemini_vision", return_value="The image contains no text."):
        response = client.post(
            "/api/guidelines/upload-document",
            data={"brand_id": 1, "auto_commit": "false", "preview_only": "true"},
            files={"file": ("blank.png", blank_bytes, "image/png")},
            headers=AUTH_HEADERS,
        )
        assert response.status_code == 400
        assert "no readable text" in response.text.lower() or "blurry" in response.text.lower()


# ============================================================================
# 5. SINGLE IMAGE GUIDELINE EXTRACTION WITH SOURCE REFERENCE
# ============================================================================
def test_single_image_guideline_extraction():
    """Verify that a guideline image is ingested, extracting rules with source_file metadata."""
    guideline_text = """
    AstraForge Enterprise Brand Governance
    RULE CLAIM-01: Never claim #1 market position without clinical evidence.
    RULE STYLE-01: Primary logo color is Deep Ocean Teal (#0B3C49). Secondary is Warm Amber (#F4A321).
    RULE ACCESS-01: Text contrast ratio must strictly satisfy WCAG 2.1 AA minimum 4.5:1.
    """
    img_bytes = create_test_image(format_name="PNG", text_content=guideline_text)
    
    mocked_rules = [
        {"rule_code": "CLAIM-01", "category": "prohibited_claim", "title": "No Unsubstantiated Claims", "rule_text": "Never claim #1 market position without clinical evidence.", "severity": "critical", "source_file": "brand_visual_policy.png"},
        {"rule_code": "VISUAL-01", "category": "visual", "title": "Corporate Palette Specifications", "rule_text": "Primary logo color is Deep Ocean Teal (#0B3C49).", "severity": "high", "source_file": "brand_visual_policy.png"},
        {"rule_code": "ACCESS-01", "category": "accessibility", "title": "WCAG Minimum Contrast", "rule_text": "Text contrast ratio must strictly satisfy WCAG 2.1 AA minimum 4.5:1.", "severity": "high", "source_file": "brand_visual_policy.png"},
    ]

    with mock.patch("app.services.extractors.extract_text_via_gemini_vision", return_value=guideline_text):
        with mock.patch("app.services.guideline_parser.call_llm_rule_extraction", return_value=mocked_rules):
            response = client.post(
                "/api/guidelines/upload-document",
                data={"brand_id": 1, "auto_commit": "false", "preview_only": "true"},
                files={"file": ("brand_visual_policy.png", img_bytes, "image/png")},
                headers=AUTH_HEADERS,
            )
            assert response.status_code == 201
            data = response.json()
            assert data["brand_id"] == 1
            assert "brand_visual_policy.png" in data["source"]
            assert data["rules_extracted_count"] == 3
            
            # Verify source reference preserved on rules
            for rule in data["rules"]:
                assert rule["source_file"] == "brand_visual_policy.png"
                assert rule["category"] in ["prohibited_claim", "visual", "accessibility"]


# ============================================================================
# 6. MULTIPLE IMAGES IN ONE SUBMISSION (ORDER & SOURCE PRESERVED)
# ============================================================================
def test_multiple_images_guideline_ingestion():
    """Verify that uploading multiple guideline images extracts rules from each while preserving sources and order."""
    page1_text = "RULE CLAIM-01: Never advertise unsubstantiated performance benchmarks."
    page2_text = "RULE VISUAL-01: Corporate font is Plus Jakarta Sans across all assets."
    
    img1_bytes = create_test_image(format_name="PNG", text_content=page1_text)
    img2_bytes = create_test_image(format_name="JPEG", text_content=page2_text)
    
    def mock_vision(b, k):
        if len(b) == len(img1_bytes):
            return page1_text
        return page2_text

    def mock_llm(chunk, api_key=None):
        if "CLAIM" in chunk:
            return [{"rule_code": "CLAIM-01", "category": "prohibited_claim", "title": "No False Claims", "rule_text": "Never advertise unsubstantiated benchmarks.", "severity": "high"}]
        return [{"rule_code": "VISUAL-01", "category": "visual", "title": "Corporate Font", "rule_text": "Corporate font is Plus Jakarta Sans.", "severity": "medium"}]

    with mock.patch("app.services.extractors.extract_text_via_gemini_vision", side_effect=mock_vision):
        with mock.patch("app.services.guideline_parser.call_llm_rule_extraction", side_effect=mock_llm):
            response = client.post(
                "/api/guidelines/upload-document",
                data={"brand_id": 1, "auto_commit": "false", "preview_only": "true"},
                files=[
                    ("files", ("guide_page1.png", img1_bytes, "image/png")),
                    ("files", ("guide_page2.jpg", img2_bytes, "image/jpeg")),
                ],
                headers=AUTH_HEADERS,
            )
            assert response.status_code == 201
            data = response.json()
            assert len(data["sources"]) == 2
            assert data["sources"][0] == "guide_page1.png"
            assert data["sources"][1] == "guide_page2.jpg"
            
            # Verify that both source filenames are represented in the extracted rules
            sources_found = {r["source_file"] for r in data["rules"]}
            assert "guide_page1.png" in sources_found
            assert "guide_page2.jpg" in sources_found


# ============================================================================
# 7. PREVIEW-ONLY REVIEW & BULK SAVE WORKFLOW
# ============================================================================
def test_preview_only_and_bulk_save_workflow():
    """Verify human review: rules returned in preview are approved and committed via bulk-save."""
    sample_text = "RULE STYLE-99: All brand logos require 50% clearspace margin around bounding box."
    img_bytes = create_test_image(format_name="WEBP", text_content=sample_text)
    
    mock_rules = [
        {"rule_code": "VISUAL-99", "category": "visual", "title": "Logo Clear Space", "rule_text": "All brand logos require 50% clearspace margin around bounding box.", "severity": "high"}
    ]

    with mock.patch("app.services.extractors.extract_text_via_gemini_vision", return_value=sample_text):
        with mock.patch("app.services.guideline_parser.call_llm_rule_extraction", return_value=mock_rules):
            # Step 1: Preview extraction (auto_commit=false, preview_only=true)
            res_preview = client.post(
                "/api/guidelines/upload-document",
                data={"brand_id": 1, "auto_commit": "false", "preview_only": "true"},
                files={"file": ("policy_spec.webp", img_bytes, "image/webp")},
                headers=AUTH_HEADERS,
            )
            assert res_preview.status_code == 201
            rules_to_save = res_preview.json()["rules"]
            assert len(rules_to_save) == 1
            assert rules_to_save[0]["source_file"] == "policy_spec.webp"

            # Step 2: Administrator reviews and calls bulk-save
            res_bulk = client.post(
                "/api/guidelines/bulk-save",
                json={
                    "brand_id": 1,
                    "rules": rules_to_save,
                    "source_name": "policy_spec.webp"
                },
                headers=AUTH_HEADERS,
            )
            assert res_bulk.status_code in (200, 201)
            saved_data = res_bulk.json()
            assert saved_data["rules_saved_count"] == 1
            
            # Verify in database
            db = TestingSessionLocal()
            saved_rule = db.query(GuidelineRule).filter(GuidelineRule.source_file == "policy_spec.webp").first()
            assert saved_rule is not None
            assert saved_rule.brand_id == 1
            assert saved_rule.rule_code == "VISUAL-99"
            db.close()


# ============================================================================
# 8. SECURITY & CROSS-ORGANIZATION ISOLATION
# ============================================================================
def test_guideline_security_and_brand_isolation():
    """Verify that requests without authentication or to non-existent brands are rejected."""
    img_bytes = create_test_image(format_name="PNG", text_content="Any guideline text.")
    
    # 1. Non-existent brand
    response_404 = client.post(
        "/api/guidelines/upload-document",
        data={"brand_id": 999999, "auto_commit": "false"},
        files={"file": ("guideline.png", img_bytes, "image/png")},
        headers=AUTH_HEADERS,
    )
    assert response_404.status_code == 404

    # 2. Missing authorization header
    response_401 = client.post(
        "/api/guidelines/upload-document",
        data={"brand_id": 1},
        files={"file": ("guideline.png", img_bytes, "image/png")},
    )
    assert response_401.status_code == 401

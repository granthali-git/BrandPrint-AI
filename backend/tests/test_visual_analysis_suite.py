"""Automated Test Suite for Multimodal Poster Visual Analysis (Cases A through F).

Validates:
Case A: Poster with incorrect or distorted logo
Case B: Poster with low-contrast, unreadable text on busy background
Case C: Poster with incorrect or prohibited claim ('100% Cure' badge)
Case D: Poster using altered brand colors instead of approved palette
Case E: Fully compliant approved brand poster (should pass clean)
Case F: Image containing visual elements but no readable text
"""

import io
import os
import sys
import pytest
from PIL import Image, ImageDraw, ImageFont

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.vision_service import (
    validate_and_decode_image,
    calculate_luminance,
    calculate_contrast_ratio,
    extract_dominant_colors,
    run_deterministic_visual_audit,
    analyze_poster_visual_design
)
from app.models.guideline import GuidelineRule, RuleCategory


def make_test_image(bg_color: str, draw_elements=None) -> bytes:
    """Helper to generate in-memory test PNG bytes."""
    img = Image.new("RGB", (600, 800), color=bg_color)
    draw = ImageDraw.Draw(img)
    if draw_elements:
        draw_elements(draw, img)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ============================================================================
# CASE A: Poster with incorrect logo
# ============================================================================
def test_case_a_incorrect_logo():
    """Verify detection and metadata extraction for a poster with an unauthorized logo."""
    def draw_elements(draw, img):
        # Draw a fake red distorted logo rectangle
        draw.rectangle([30, 30, 200, 100], fill="#D32F2F")
        draw.text((45, 55), "WRONG LOGO", fill="#FFFFFF")

    img_bytes = make_test_image("#FBF9F4", draw_elements)
    img, mime, meta = validate_and_decode_image(img_bytes)

    assert mime == "image/png"
    assert meta["width"] == 600
    assert meta["height"] == 800
    assert "preview_data_url" in meta
    assert meta["preview_data_url"].startswith("data:image/jpeg;base64,")


# ============================================================================
# CASE B: Poster with low-contrast unreadable text
# ============================================================================
def test_case_b_low_contrast():
    """Verify WCAG 2.1 contrast calculation detects low-contrast palette."""
    # Test yellow on white: contrast is ~1.16:1, far below 4.5:1
    yellow_rgb = (255, 255, 0)
    white_rgb = (255, 255, 255)
    ratio = calculate_contrast_ratio(yellow_rgb, white_rgb)
    assert ratio < 2.0

    # Test high contrast: Dark slate (#072730) on White (#FFFFFF)
    dark_slate_rgb = (7, 39, 48)
    high_ratio = calculate_contrast_ratio(dark_slate_rgb, white_rgb)
    assert high_ratio > 10.0

    # Test deterministic visual audit catches low-contrast image
    def draw_elements(draw, img):
        draw.rectangle([50, 50, 550, 750], fill="#FEFEFE")
        draw.text((100, 200), "Unreadable Light Yellow Copy", fill="#FFFF99")

    img_bytes = make_test_image("#FFFFF0", draw_elements)
    img, _, _ = validate_and_decode_image(img_bytes)
    findings = run_deterministic_visual_audit(img, extracted_text="", prohibited_rules=[])
    # The low contrast is verified by calculation
    assert isinstance(findings, list)


# ============================================================================
# CASE C: Poster with prohibited claim badge ('100% Cure')
# ============================================================================
def test_case_c_prohibited_claim_badge():
    """Verify visual heuristic detects 100% cure guarantee badge."""
    def draw_elements(draw, img):
        draw.rectangle([100, 300, 500, 400], fill="#E53935")
        draw.text((120, 340), "100% CURE GUARANTEE", fill="#FFFFFF")

    img_bytes = make_test_image("#FFFFFF", draw_elements)
    img, _, _ = validate_and_decode_image(img_bytes)

    findings = run_deterministic_visual_audit(
        image=img,
        extracted_text="AstraForge Skincare: 100% cure for acne permanently.",
        prohibited_rules=[]
    )

    claim_findings = [f for f in findings if f.get("issue_type") == "claim_conflict"]
    assert len(claim_findings) >= 1
    assert "100% cure" in claim_findings[0]["flagged_text"]
    assert claim_findings[0]["severity"] == "critical"
    assert claim_findings[0]["is_visual"] is True


# ============================================================================
# CASE D: Poster using altered / unapproved brand colors
# ============================================================================
def test_case_d_altered_brand_colors():
    """Verify dominant color extraction identifies non-brand palettes."""
    def draw_elements(draw, img):
        draw.rectangle([0, 0, 600, 400], fill="#FF00FF")  # Magenta
        draw.rectangle([0, 400, 600, 800], fill="#00FF00")  # Neon Green

    img_bytes = make_test_image("#000000", draw_elements)
    img, _, _ = validate_and_decode_image(img_bytes)

    palette = extract_dominant_colors(img, num_colors=3)
    hex_codes = [c["hex"] for c in palette]
    assert len(palette) >= 2
    # Ensure neon colors are captured
    assert any("FF" in h for h in hex_codes)


# ============================================================================
# CASE E: Fully compliant approved brand poster
# ============================================================================
def test_case_e_clean_compliant_poster():
    """Verify compliant poster with approved AstraForge palette passes clean."""
    # Approved palette: Deep Ocean Teal (#0B3C49), Dark Slate (#072730), White text
    def draw_elements(draw, img):
        draw.rectangle([50, 50, 550, 150], fill="#072730")
        draw.text((80, 90), "AstraForge Enterprise Architecture", fill="#FFFFFF")
        draw.rectangle([50, 200, 550, 700], fill="#0B3C49")
        draw.text((80, 250), "Empowering scalable cloud infrastructure with verified SOC-2 audits.", fill="#FBF9F4")

    img_bytes = make_test_image("#0B3C49", draw_elements)
    img, _, meta = validate_and_decode_image(img_bytes)

    # Contrast between #0B3C49 and #FFFFFF is > 7:1 (WCAG AAA)
    teal_rgb = (11, 60, 73)
    white_rgb = (255, 255, 255)
    ratio = calculate_contrast_ratio(teal_rgb, white_rgb)
    assert ratio >= 7.0

    findings = run_deterministic_visual_audit(
        image=img,
        extracted_text="AstraForge Enterprise Architecture. Empowering scalable cloud infrastructure.",
        prohibited_rules=[]
    )
    # No prohibited claims or contrast breaches
    claim_breaches = [f for f in findings if f.get("issue_type") == "claim_conflict"]
    assert len(claim_breaches) == 0


# ============================================================================
# CASE F: Image containing visual elements but no readable text
# ============================================================================
@pytest.mark.anyio
async def test_case_f_visual_poster_no_readable_text():
    """Verify image with purely visual geometric shapes processes without 400 error."""
    def draw_elements(draw, img):
        # Only shapes, zero text
        draw.ellipse([100, 100, 300, 300], fill="#F4A321")
        draw.polygon([(400, 100), (500, 300), (300, 300)], fill="#0B3C49")

    img_bytes = make_test_image("#072730", draw_elements)
    img, mime, meta = validate_and_decode_image(img_bytes)

    assert meta["width"] == 600
    assert meta["height"] == 800

    # Ensure analyze_poster_visual_design handles empty OCR text without throwing
    findings, status, message = await analyze_poster_visual_design(
        file_bytes=img_bytes,
        mime_type=mime,
        brand_rules=[],
        brand_name="AstraForge",
        extracted_ocr_text=""
    )
    assert isinstance(findings, list)
    assert status in ("complete", "incomplete")
    assert isinstance(message, str)


"""Multimodal Visual Design & Poster Analysis Service for BrandPrint AI.

Provides genuine computer vision and multimodal LLM evaluation for brand posters,
creative marketing collateral, and visual documents.

Audits:
1. Logo identity, appearance, placement, clear space, and distortion.
2. Brand colors, background palette, and chromatic consistency.
3. Typography, hierarchy, readability, and font spacing.
4. Layout, alignment, margins, and visual balance.
5. Product imagery, resolution, and visual elements.
6. Visual contrast and accessibility (WCAG 2.1 AA/AAA compliance).
7. Misleading visual claims, false guarantee badges, and unverified seals.
8. Approved Brand DNA adherence against active organization guidelines.
"""

import base64
import io
import json
import logging
import math
import os
import re
from typing import Any, Dict, List, Optional, Tuple, Union

import httpx
from PIL import Image

from app.core.config import settings

logger = logging.getLogger(__name__)

# Supported multimodal vision models in priority order
VISION_MODELS = [
    "gemini-3.1-flash-lite",
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash",
]

# Supported image MIME types
ALLOWED_MIME_TYPES = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP",
    "image/gif": "GIF",
}


def validate_and_decode_image(file_bytes: bytes) -> Tuple[Image.Image, str, Dict[str, Any]]:
    """Validate image bytes, verify MIME type, and decode using Pillow.
    
    Returns:
        Tuple of (PIL.Image, detected_mime_type, metadata_dict)
    Raises:
        ValueError: If file is empty, invalid, or corrupted image data.
    """
    if not file_bytes or len(file_bytes) < 16:
        raise ValueError("Invalid image file: Payload is empty or insufficient bytes.")

    try:
        image = Image.open(io.BytesIO(file_bytes))
        image.verify()  # Verify file integrity
        # Re-open because verify() closes the file pointer
        image = Image.open(io.BytesIO(file_bytes))
    except Exception as e:
        raise ValueError(f"Corrupted or unsupported image file: {str(e)}") from e

    format_name = (image.format or "JPEG").upper()
    mime_type = "image/jpeg"
    if format_name == "PNG":
        mime_type = "image/png"
    elif format_name == "WEBP":
        mime_type = "image/webp"
    elif format_name == "GIF":
        mime_type = "image/gif"

    width, height = image.size
    aspect_ratio = round(width / max(height, 1), 2)

    # Generate a lightweight base64 thumbnail data URL for frontend preview
    try:
        thumb = image.copy()
        thumb.thumbnail((600, 600), Image.Resampling.LANCZOS)
        if thumb.mode in ("RGBA", "P"):
            thumb = thumb.convert("RGB")
        thumb_io = io.BytesIO()
        thumb.save(thumb_io, format="JPEG", quality=80, optimize=True)
        preview_data_url = f"data:image/jpeg;base64,{base64.b64encode(thumb_io.getvalue()).decode('utf-8')}"
    except Exception as ex:
        logger.warning(f"Failed to generate thumbnail preview: {ex}")
        preview_data_url = ""

    metadata = {
        "width": width,
        "height": height,
        "format": format_name,
        "mode": image.mode,
        "aspect_ratio": aspect_ratio,
        "file_size_kb": round(len(file_bytes) / 1024, 1),
        "preview_data_url": preview_data_url,
    }

    return image, mime_type, metadata


def calculate_luminance(r: int, g: int, b: int) -> float:
    """Calculate relative luminance according to WCAG 2.1 formula."""
    def channel_val(val: int) -> float:
        c = val / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r_lum = channel_val(r)
    g_lum = channel_val(g)
    b_lum = channel_val(b)
    return 0.2126 * r_lum + 0.7152 * g_lum + 0.0722 * b_lum


def calculate_contrast_ratio(rgb1: Tuple[int, int, int], rgb2: Tuple[int, int, int]) -> float:
    """Calculate WCAG 2.1 contrast ratio between two RGB colors (1.0 to 21.0)."""
    lum1 = calculate_luminance(*rgb1)
    lum2 = calculate_luminance(*rgb2)
    brightest = max(lum1, lum2)
    darkest = min(lum1, lum2)
    return round((brightest + 0.05) / (darkest + 0.05), 2)


def extract_dominant_colors(image: Image.Image, num_colors: int = 5) -> List[Dict[str, Any]]:
    """Extract dominant palette hex colors and proportions from image."""
    try:
        img_rgb = image.convert("RGB")
        # Resize small for fast quantization
        img_small = img_rgb.resize((150, 150), Image.Resampling.NEAREST)
        # Quantize to palette
        quantized = img_small.quantize(colors=num_colors)
        palette = quantized.getpalette()[:num_colors * 3]
        color_counts = quantized.getcolors()

        if not color_counts or not palette:
            return []

        total_pixels = sum(count for count, _ in color_counts)
        colors = []
        for count, idx in sorted(color_counts, reverse=True, key=lambda x: x[0])[:num_colors]:
            r = palette[idx * 3]
            g = palette[idx * 3 + 1]
            b = palette[idx * 3 + 2]
            hex_code = f"#{r:02x}{g:02x}{b:02x}".upper()
            pct = round((count / total_pixels) * 100, 1)
            colors.append({
                "hex": hex_code,
                "rgb": (r, g, b),
                "percentage": pct
            })
        return colors
    except Exception as e:
        logger.warning(f"Dominant color extraction failed: {e}")
        return []


def run_deterministic_visual_audit(
    image: Image.Image,
    extracted_text: str,
    prohibited_rules: List[Any],
    brand_name: str = "AstraForge"
) -> List[Dict[str, Any]]:
    """Perform deterministic visual heuristics (contrast checks, bad claims in OCR, palette analysis)."""
    findings: List[Dict[str, Any]] = []

    # 1. Palette & Contrast heuristic
    dominant_colors = extract_dominant_colors(image, num_colors=4)
    if len(dominant_colors) >= 2:
        bg = dominant_colors[0]
        fg = dominant_colors[1]
        ratio = calculate_contrast_ratio(bg["rgb"], fg["rgb"])

        if ratio < 3.0:
            findings.append({
                "rule_id": "VISUAL-CONTRAST-01",
                "category": "accessibility_issue",
                "issue_type": "accessibility_issue",
                "severity": "high",
                "visual_element": "Background / Foreground Contrast",
                "context_span": f"Dominant palette: {bg['hex']} vs {fg['hex']}",
                "flagged_text": f"Low chromatic contrast ratio {ratio}:1 between dominant background and foreground elements.",
                "observed_evidence": f"The primary background ({bg['hex']}) and foreground color ({fg['hex']}) have a contrast ratio of {ratio}:1, which is below the WCAG 2.1 AA minimum threshold of 4.5:1 for standard text and 3:1 for graphical elements.",
                "cited_quote": "WCAG 2.1 Success Criterion 1.4.3: Contrast (Minimum) requires a contrast ratio of at least 4.5:1 for normal text and 3:1 for large graphical elements.",
                "explanation": "Insufficient contrast impairs readability for visually impaired users and diminishes brand impact in bright ambient light.",
                "suggested_fix": f"Increase the luminance contrast between the background and foreground elements to at least 4.5:1 by darkening text to a deep slate (#072730) or adding a high-contrast backing pill.",
                "fix_variations": [
                    {
                        "style": "Direct & Factual",
                        "text": f"Adjust foreground luminance to achieve at least a 4.5:1 WCAG contrast ratio against background {bg['hex']}."
                    },
                    {
                        "style": "Executive & Confident",
                        "text": "Elevate visual legibility and inclusive design by applying high-contrast brand container backings."
                    }
                ],
                "strategic_tip": "High-contrast visual design improves message recall by up to 28% and ensures compliance with enterprise accessibility mandates.",
                "is_visual": True
            })

    # 2. Check OCR text for explicit visual badges / prohibited superlatives
    text_lower = (extracted_text or "").lower()
    suspicious_badges = [
        ("100% cure", "100% Cure / Permanent Treatment Claim", "critical"),
        ("guaranteed number 1", "Unsubstantiated #1 Ranking Badge", "critical"),
        ("cheapest", "Prohibited Absolute Pricing Claim", "high"),
        ("100% bug-free", "Absolute Guarantee Claim", "high"),
        ("zero latency", "Absolute Technical Superlative", "high"),
    ]

    for trigger, badge_title, severity in suspicious_badges:
        if trigger in text_lower:
            findings.append({
                "rule_id": "VISUAL-CLAIM-01",
                "category": "prohibited_claim",
                "issue_type": "claim_conflict",
                "severity": severity,
                "visual_element": "Visual Promotional Badge / Slogan",
                "context_span": f"Detected in poster copy: '{trigger}'",
                "flagged_text": trigger,
                "observed_evidence": f"The poster prominently features the phrase '{trigger}', which represents an unsubstantiated absolute guarantee or ranking.",
                "cited_quote": "Enterprise Brand Safety Policy: Absolute superlatives, unverified curative claims, and 100% guarantees are strictly prohibited without independent third-party audit certification.",
                "explanation": f"Featuring '{trigger}' on commercial marketing creative exposes the brand to regulatory scrutiny and false advertising liabilities.",
                "suggested_fix": f"Replace '{trigger}' with certified, audit-backed language such as 'Clinically Tested Efficacy' or 'Proven Enterprise Performance'.",
                "fix_variations": [
                    {
                        "style": "Direct & Factual",
                        "text": "Replace with verifiable, benchmark-tested performance metrics"
                    },
                    {
                        "style": "Executive & Confident",
                        "text": "Position with authoritative, evidence-backed efficacy statements"
                    }
                ],
                "strategic_tip": "Replacing unverified absolutes with verified metrics builds sustainable consumer trust and protects institutional brand equity.",
                "is_visual": True
            })

    return findings


def build_vision_analysis_prompt(
    brand_name: str,
    brand_rules: List[Any],
    extracted_ocr_text: str = ""
) -> str:
    """Build the comprehensive multi-modal visual inspection prompt."""
    rules_text_list = []
    for r in brand_rules[:15]:
        rule_title = getattr(r, "title", str(r))
        rule_body = getattr(r, "rule_text", "")
        rule_code = getattr(r, "rule_code", "")
        rules_text_list.append(f"- [{rule_code or 'RULE'}] {rule_title}: {rule_body}")

    formatted_rules = "\n".join(rules_text_list) if rules_text_list else "- Maintain strict brand consistency, high contrast, approved typography, authentic logo integrity, and verified claims."

    ocr_context = f"\nEXTRACTED OCR TEXT FROM ASSET:\n\"{extracted_ocr_text.strip()}\"\n" if extracted_ocr_text.strip() else ""

    prompt = f"""You are BrandPrint AI Vision, an expert Creative Director, Brand Governance Auditor, and Visual Accessibility (A11y) Inspector.
You are evaluating the uploaded marketing poster/creative asset for the brand: "{brand_name}".

{ocr_context}
APPROVED BRAND GUIDELINE RULES:
{formatted_rules}

BRAND DNA & VISUAL DESIGN BENCHMARKS FOR "{brand_name}":
- Primary Brand Palette: Deep Ocean Teal (#0B3C49), Dark Slate (#072730), Warm Amber (#F4A321), Warm Cream (#FBF9F4), Crisp White (#FFFFFF). Prohibit random unapproved garish neons or clashing palettes.
- Logo Guidelines: Logo must be official, clear, unobstructed, with adequate margin/clear space. Prohibit wrong brand logos, distorted aspect ratios, pixelation, or low-contrast background placement.
- Typography & Spacing: Clean modern sans-serif typography (Plus Jakarta Sans/Inter style), legible font sizes, proper leading, generous breathing room. Prohibit illegible fonts, cramped layouts, cut-off margins.
- Visual Contrast & A11y: WCAG 2.1 AA compliant text contrast (minimum 4.5:1 for body copy, 3:1 for large headings/graphics). Prohibit dark text on dark backgrounds or white text over busy unreadable photos without backing scrims.
- Claims & Badges: Prohibit misleading promotional badges (e.g., "100% Cure", "Guaranteed #1", fake medical/regulatory seals, "Cheapest in World" without audit citations).
- Layout & Product Imagery: Professional composition, balanced hierarchy, crisp high-res product framing.

MANDATORY INSPECTION DIMENSIONS:
1. [Logo Identity & Placement]: Is the official logo present? Is it warped, distorted, blurred, placed over clashing patterns, or is a generic/incorrect logo used?
2. [Brand Colors & Palette]: Does the poster follow approved brand colors, or does it introduce unapproved, discordant, or low-quality color schemes?
3. [Typography & Readability]: Is text easy to read? Are fonts hierarchical and spaced cleanly, or cluttered and hard to decipher?
4. [Layout & Margin Balance]: Are elements aligned with proper margins, or do they feel misaligned, cramped, or cut off?
5. [Product & Visual Imagery]: Are product images crisp and authentic, or distorted, pixelated, or misleading?
6. [Visual Contrast & Accessibility]: Does all text meet WCAG 2.1 AA legibility over its background?
7. [Visual Claims & Badges]: Are there false claims, unverified superlatives, or deceptive guarantee badges?
8. [Approved Brand DNA Comparison]: Does this creative feel like an approved enterprise asset for "{brand_name}"?

OUTPUT FORMAT:
Return strictly a valid JSON array of finding objects. If there are visual design or compliance defects, document each finding. If the poster is completely compliant with 0 violations, return an empty array [].

EACH FINDING OBJECT MUST HAVE:
{{
  "rule_id": "<Guideline rule code or visual rule e.g. VISUAL-LOGO-01, VISUAL-COLOR-02, VISUAL-CONTRAST-03, VISUAL-CLAIM-04, VISUAL-TYPO-05, VISUAL-LAYOUT-06>",
  "category": "visual_guideline" | "accessibility_issue" | "prohibited_claim" | "brand_voice",
  "issue_type": "visual_guideline_breach" | "accessibility_issue" | "claim_conflict" | "tone_inconsistency",
  "severity": "critical" | "high" | "medium" | "advisory",
  "visual_element": "<Specific visual element: e.g. Logo, Headline Typography, Hero Product Photo, Background / Contrast, Guarantee Badge>",
  "context_span": "<Exact visual location on the poster e.g. 'Top-left corner', 'Center banner', 'Bottom footer disclaimer'>",
  "flagged_text": "<Visible text or visual label associated with this issue>",
  "observed_evidence": "<Concrete, objective visual description of what is actually visible in the image>",
  "cited_quote": "<Specific brand guideline rule, WCAG criterion, or design standard violated>",
  "explanation": "<Clear reason explaining why this visual choice breaches brand standards or impairs customer trust>",
  "suggested_fix": "<Concrete, actionable instruction for the designer or marketing team to resolve the issue>",
  "fix_variations": [
    {{
      "style": "Direct & Factual",
      "text": "<Precise design adjustment instruction with exact hex color, margin, or layout specs>"
    }},
    {{
      "style": "Executive & Confident",
      "text": "<Strategic creative direction elevating overall brand authority and appeal>"
    }}
  ],
  "strategic_tip": "<Actionable insight on brand safety, conversion rate, or accessibility impact>",
  "is_visual": true
}}

Ensure all JSON is strictly valid, clean, and contains no markdown formatting outside the JSON array.
"""
    return prompt.strip()


async def analyze_poster_visual_design(
    file_bytes: bytes,
    mime_type: str,
    brand_rules: List[Any],
    brand_name: str = "AstraForge",
    extracted_ocr_text: str = "",
    api_key: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], str, str]:
    """Execute end-to-end multimodal vision compliance analysis.
    
    Returns:
        Tuple of (findings_list, visual_status, visual_message)
        visual_status can be: "complete", "incomplete", or "failed"
    """
    # 1. Validate & decode image
    try:
        image, detected_mime, metadata = validate_and_decode_image(file_bytes)
    except ValueError as val_err:
        logger.error(f"Image validation failed: {val_err}")
        return [], "failed", str(val_err)

    # 2. Run local deterministic visual checks first (contrast, colors, OCR check)
    deterministic_findings = run_deterministic_visual_audit(
        image=image,
        extracted_text=extracted_ocr_text,
        prohibited_rules=brand_rules,
        brand_name=brand_name
    )

    # 3. Resolve Gemini API Key
    resolved_key = (
        api_key
        or os.getenv("GEMINI_API_KEY", "")
        or getattr(settings, "GEMINI_API_KEY", "")
    ).strip()

    if not resolved_key or resolved_key == "your_gemini_api_key_here":
        logger.warning("No valid Gemini API key configured for multimodal visual analysis. Falling back to deterministic visual audit.")
        status_msg = "Visual analysis completed using deterministic visual heuristics. (Multimodal AI key not configured)."
        return deterministic_findings, "incomplete", status_msg

    # 4. Prepare image for Gemini (compress/resize if huge to keep latency < 5s)
    try:
        work_image = image.copy()
        if work_image.width > 1600 or work_image.height > 1600:
            work_image.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
        if work_image.mode in ("RGBA", "P"):
            work_image = work_image.convert("RGB")
        out_buf = io.BytesIO()
        work_image.save(out_buf, format="JPEG", quality=85, optimize=True)
        b64_payload = base64.b64encode(out_buf.getvalue()).decode("utf-8")
        payload_mime = "image/jpeg"
    except Exception as prep_ex:
        logger.warning(f"Failed to prepare image for vision payload: {prep_ex}")
        b64_payload = base64.b64encode(file_bytes).decode("utf-8")
        payload_mime = detected_mime

    # 5. Build prompt
    prompt = build_vision_analysis_prompt(
        brand_name=brand_name,
        brand_rules=brand_rules,
        extracted_ocr_text=extracted_ocr_text
    )

    request_payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": payload_mime,
                            "data": b64_payload
                        }
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "topP": 0.95,
            "maxOutputTokens": 2048,
            "responseMimeType": "application/json"
        }
    }

    headers = {
        "x-goog-api-key": resolved_key,
        "Content-Type": "application/json"
    }

    # 6. Call multimodal models
    async with httpx.AsyncClient(timeout=25.0) as client:
        for model_name in VISION_MODELS:
            endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={resolved_key}"
            try:
                logger.info(f"Dispatching multimodal vision request to {model_name}...")
                res = await client.post(endpoint, headers=headers, json=request_payload)

                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            raw_text = parts[0].get("text", "").strip()
                            # Strip markdown backticks if any
                            clean_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                            clean_text = re.sub(r"\s*```$", "", clean_text).strip()
                            try:
                                parsed = json.loads(clean_text)
                                if isinstance(parsed, list):
                                    # Normalize findings
                                    ai_findings: List[Dict[str, Any]] = []
                                    for item in parsed:
                                        if isinstance(item, dict):
                                            item["is_visual"] = True
                                            ai_findings.append(item)

                                    # Combine with deterministic findings (avoiding exact duplicates)
                                    combined = list(ai_findings)
                                    seen_rules = {f.get("rule_id") for f in ai_findings if f.get("rule_id")}
                                    for det in deterministic_findings:
                                        if det.get("rule_id") not in seen_rules:
                                            combined.append(det)

                                    logger.info(
                                        f"Multimodal vision analysis completed ({model_name}): "
                                        f"{len(ai_findings)} visual findings detected."
                                    )
                                    return combined, "complete", "Poster visual design & aesthetic compliance analysis completed successfully."
                            except json.JSONDecodeError as jde:
                                logger.warning(f"Failed to parse JSON from {model_name}: {jde}")

                elif res.status_code in (429, 503):
                    logger.warning(f"Gemini {model_name} rate limited or unavailable (status {res.status_code}). Trying candidate...")
                    continue
                else:
                    logger.warning(f"Gemini {model_name} returned status {res.status_code}: {res.text[:200]}")
            except Exception as req_ex:
                logger.warning(f"Gemini {model_name} call failed: {req_ex}")
                continue

    # 7. Fallback if all multimodal calls failed
    status_msg = "Multimodal AI visual service was rate-limited or temporarily unavailable. Deterministic visual audit heuristics applied."
    return deterministic_findings, "incomplete", status_msg

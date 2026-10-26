"""Deterministic compliance checks engine executing before LLM evaluation.

Covers:
1. Banned terms / competitor mentions (regex matching against prohibited claims)
2. Expired dates and promotions matching
3. Image accessibility (missing or generic alt text)
4. Color contrast utility (WCAG 2.1 relative luminance and contrast ratio)
"""
import logging
from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional, Tuple, Union
from bs4 import BeautifulSoup
import dateparser

logger = logging.getLogger(__name__)

# Common competitor terms and banned superlatives
DEFAULT_PROHIBITED_TERMS = [
    "best in the world",
    "guaranteed 100% cure",
    "miracle cure",
    "risk-free investment",
    "zero risk",
    "100% safe",
    "unbeatable prices",
    "cheapest on earth",
]

# Generic/placeholder alt text indicators
PLACEHOLDER_ALT_PATTERNS = {
    "image",
    "img",
    "picture",
    "photo",
    "graphic",
    "banner",
    "logo",
    "icon",
    "placeholder",
    "untitled",
    "screenshot",
    "sample",
    "file",
}


# ============================================================================
# 1. BANNED TERMS / COMPETITOR MENTIONS WITH CONTEXTUAL NEGATION GUARDS
# ============================================================================

def is_negated_or_disclaimed_context(content: str, match_start: int, match_end: int) -> bool:
    """Analyze preceding grammatical context and sentence structure to determine if
    a matched phrase is negated, disclaimed, cited comparatively, or part of a non-assertion.

    Returns True if the term is NOT an affirmative violation (should NOT be falsely flagged).
    """
    if not content or match_start < 0:
        return False

    # Extract the clause leading up to the match within the current sentence
    prefix_start = max(0, match_start - 140)
    preceding_text = content[prefix_start:match_start]

    # Find the most recent sentence boundary (., !, ?, or newline)
    sentence_delims = [m.end() for m in re.finditer(r"[.?!;\n]", preceding_text)]
    if sentence_delims:
        clause_prefix = preceding_text[sentence_delims[-1]:].strip()
    else:
        clause_prefix = preceding_text.strip()

    # 1. Direct preceding negation phrases: e.g. "do not claim to be the", "we do not claim", "never claim"
    negation_patterns = [
        # Auxiliary / modal verb negation before claim
        r"\b(?:do|does|did|can|could|will|would|shall|should|may|might|must|is|are|was|were)\s+not\s+(?:claim|state|advertise|promise|assert|guarantee|say|purport|pretend|make)\s+(?:to\s+be\s+|that\s+(?:we\s+are\s+)?|(?:the\s+)|(?:a\s+))?",
        # Simple negation verbs / adverbs
        r"\b(?:do\s+not|does\s+not|did\s+not|is\s+not|are\s+not|was\s+not|were\s+not|not|never|neither|nor|without|stop|avoid|refuse\s+to|disclaim(?:s|ed|ing)?)\s+(?:claim(?:ing|s|ed)?\s+(?:to\s+be\s+|that\s+)?|make\s+|promis(?:e|ing)\s+|assert(?:ing)?\s+)?(?:the\s+)?",
        # Explicit "no [superlative / claim / guarantee]"
        r"\b(?:no|zero)\s+(?:guarantee|claim|superlative|promise|unsubstantiated)\b",
        # "not guaranteed", "no guarantee", "never guaranteed"
        r"\b(?:not\s+guaranteed|no\s+guarantee|never\s+guaranteed?|without\s+(?:any\s+)?guarantee)\b",
        # "not intended as", "does not constitute"
        r"\b(?:not\s+intended\s+as|does\s+not\s+constitute|not\s+a\s+substitute\s+for|not\s+applicable)\b",
        # Negation followed by list/or e.g. "do not claim to be the cheapest or"
        r"\b(?:do\s+not|never)\s+claim\s+to\s+be\s+.*?\b(?:or|nor|and)\s+(?:the\s+)?",
    ]

    for pat in negation_patterns:
        if re.search(pat, clause_prefix, re.IGNORECASE):
            return True

    # 2. Contrastive / Concession clauses
    # e.g. "While some claim to be the cheapest, we focus on..."
    # e.g. "Unlike competitors who claim..."
    comparative_patterns = [
        r"\b(?:while|although|though|whereas|even\s+if)\s+(?:some|others?|competitors?|many|third\s+parties)\s+(?:claim|boast|advertise|assert)\s+(?:to\s+be\s+)?",
        r"\b(?:unlike|contrary\s+to|in\s+contrast\s+to)\s+(?:competitors?|others?)\b",
    ]

    for pat in comparative_patterns:
        if re.search(pat, clause_prefix, re.IGNORECASE):
            return True

    # 3. Direct negative lookbehind on the immediately preceding tokens (e.g. "not cheapest", "no guarantee")
    if re.search(r"\b(?:not|no|never|neither|without)\s+$", clause_prefix, re.IGNORECASE):
        return True

    # 4. Check following qualifying context within the sentence (e.g. "...guarantee as required by law")
    suffix_end = min(len(content), match_end + 90)
    following_text = content[match_end:suffix_end]
    following_sentence_end = re.search(r"[.?!;\n]", following_text)
    if following_sentence_end:
        clause_suffix = following_text[:following_sentence_end.start()].strip()
    else:
        clause_suffix = following_text.strip()

    if re.search(r"\b(?:as\s+required\s+by\s+law|under\s+statutory\s+warranty|pursuant\s+to\s+regulations|under\s+applicable\s+law)\b", clause_suffix, re.IGNORECASE):
        return True

    return False


def check_banned_terms(
    content: str,
    prohibited_terms: Optional[List[str]] = None,
    prohibited_rules: Optional[List[Any]] = None,
    competitors: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Detect banned terms, unverified superlatives, and competitor mentions with full contextual negation guards."""
    findings: List[Dict[str, Any]] = []
    if not content:
        return findings

    terms_to_check: List[Dict[str, Any]] = []

    # Direct prohibited terms list
    if prohibited_terms:
        for p_term in prohibited_terms:
            if isinstance(p_term, str) and p_term.strip():
                terms_to_check.append({
                    "term": p_term.strip(),
                    "reason": f"Use of prohibited phrase or competitor: '{p_term.strip()}'.",
                    "rule_id": None,
                    "severity": "high",
                })

    # Prohibited claims from guideline rules
    if prohibited_rules:
        for rule in prohibited_rules:
            # Handle SQLAlchemy model or dict
            rule_id = getattr(rule, "id", None) or (rule.get("id") if isinstance(rule, dict) else None)
            category = getattr(rule, "category", "") or (rule.get("category", "") if isinstance(rule, dict) else "")
            title = getattr(rule, "title", "") or (rule.get("title", "") if isinstance(rule, dict) else "")
            rule_text = getattr(rule, "rule_text", "") or (rule.get("rule_text", "") if isinstance(rule, dict) else "")

            cat_str = category.value if hasattr(category, "value") else str(category)
            if cat_str in ("prohibited_claim", "fact", "tone", "legal_compliance", "brand_voice"):
                # 1. Rule title
                terms_to_check.append({
                    "term": title,
                    "reason": f"Violates brand guideline: '{title}' ({rule_text})",
                    "rule_id": rule_id,
                    "severity": "critical" if cat_str in ("prohibited_claim", "legal_compliance") else "high",
                })
                # 2. Quoted phrases from rule_text e.g. 'trash', 'garbage', 'obsolete' or 'completely free forever'
                quoted_phrases = re.findall(r"['\"]([^'\"]{3,40})['\"]", rule_text)
                for qp in quoted_phrases:
                    terms_to_check.append({
                        "term": qp.strip(),
                        "reason": f"Uses prohibited phrase '{qp.strip()}' restricted by brand guideline '{title}'.",
                        "rule_id": rule_id,
                        "severity": "critical" if cat_str in ("prohibited_claim", "legal_compliance") else "high",
                    })
                # 3. Technical & operational patterns mentioned in rule text
                for target_pat in [
                    r"\bzero\s+latency\b",
                    r"\b100%\s+bug-free(?:\s+uptime)?\b",
                    r"\bcompletely\s+free(?:\s+forever)?\b",
                    r"\blowest\s+rate\s+guaranteed\b",
                ]:
                    m_pat = re.search(target_pat, rule_text, re.IGNORECASE)
                    if m_pat:
                        terms_to_check.append({
                            "term": m_pat.group(0),
                            "reason": f"Asserts restricted claim '{m_pat.group(0)}' violating brand guideline '{title}'.",
                            "rule_id": rule_id,
                            "severity": "high",
                        })

    # Default prohibited superlatives
    for def_term in DEFAULT_PROHIBITED_TERMS:
        terms_to_check.append({
            "term": def_term,
            "reason": f"Use of prohibited unverified superlative: '{def_term}'.",
            "rule_id": None,
            "severity": "high",
        })

    # Competitor mentions
    if competitors:
        for comp in competitors:
            if comp.strip():
                terms_to_check.append({
                    "term": comp.strip(),
                    "reason": f"Direct competitor mention '{comp.strip()}' without comparative authorization.",
                    "rule_id": None,
                    "severity": "high",
                })

    # Execute regex searches with negative lookbehinds and contextual negation checks
    for item in terms_to_check:
        term = item["term"]
        if not term or len(term.strip()) < 2:
            continue

        # Use negative lookbehind for immediate preceding negations ("not", "no", "never", "without")
        pattern = re.compile(rf"(?<!\bnot\s)(?<!\bno\s)(?<!\bnever\s)(?<!\bwithout\s)\b{re.escape(term)}\b", re.IGNORECASE)
        for match in pattern.finditer(content):
            # Evaluate sentence-level semantic context: skip if disclaimed, negated, or comparative
            if is_negated_or_disclaimed_context(content, match.start(), match.end()):
                continue

            start = max(0, match.start() - 40)
            end = min(len(content), match.end() + 40)
            context_snippet = content[start:end].replace("\n", " ").strip()

            findings.append({
                "severity": item["severity"],
                "issue_type": "Prohibited Claim / Term",
                "flagged_text": match.group(0),
                "explanation": item["reason"],
                "suggested_fix": f"Remove or substantiate the claim '{match.group(0)}'.",
                "is_deterministic": True,
                "cited_quote": f"...{context_snippet}...",
                "rule_id": item["rule_id"],
                "user_action": "pending",
            })

    return findings


# ============================================================================
# 2. EXPIRED DATES & PROMOTIONS REGEX MATCHING
# ============================================================================

DATE_PATTERNS = [
    # "valid until October 24, 2024", "expires 12/31/2023", "ends on 2024-01-15"
    re.compile(
        r"(?:valid\s+(?:until|through)|expires?(?:\s+on)?|ends?(?:\s+on)?|expiry\s+date|offer\s+ends?)\s*[:\-]?\s*"
        r"([A-Za-z]{3,9}\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}|\d{4}[/-]\d{1,2}[/-]\d{1,2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        re.IGNORECASE,
    ),
    # "save 20% until Nov 30 2023"
    re.compile(
        r"(?:sale|discount|deal|promo(?:tion)?|save\s+\d+%)\s+.*?(?:until|through|by)\s+"
        r"([A-Za-z]{3,9}\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}|\d{4}[/-]\d{1,2}[/-]\d{1,2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        re.IGNORECASE,
    ),
]


def check_expired_dates_and_promotions(
    content: str,
    reference_date: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """Detect time-sensitive promotional dates that have expired."""
    findings: List[Dict[str, Any]] = []
    if not content:
        return findings

    ref_date = reference_date or datetime.now(timezone.utc)
    # Ensure ref_date is comparable (naive vs aware)
    if ref_date.tzinfo is not None:
        ref_date = ref_date.astimezone(timezone.utc).replace(tzinfo=None)

    for pattern in DATE_PATTERNS:
        for match in pattern.finditer(content):
            matched_phrase = match.group(0)
            date_str = match.group(1)

            # Parse date string
            parsed_dt = dateparser.parse(
                date_str,
                settings={"PREFER_DATES_FROM": "past", "RELATIVE_BASE": ref_date}
            )

            if parsed_dt:
                # Standardize to naive UTC for clean comparison
                if parsed_dt.tzinfo is not None:
                    parsed_dt = parsed_dt.astimezone(timezone.utc).replace(tzinfo=None)

                if parsed_dt < ref_date:
                    days_expired = (ref_date - parsed_dt).days
                    findings.append({
                        "severity": "high",
                        "issue_type": "Expired Promotion",
                        "flagged_text": matched_phrase,
                        "explanation": (
                            f"The promotional claim contains an expired date '{date_str}' "
                            f"(expired approximately {days_expired} days ago on {parsed_dt.strftime('%Y-%m-%d')})."
                        ),
                        "suggested_fix": (
                            "Update the promotion date to an active campaign schedule "
                            "or archive the promotional material."
                        ),
                        "is_deterministic": True,
                        "cited_quote": matched_phrase,
                        "rule_id": None,
                        "user_action": "pending",
                    })

    return findings


def check_expired_dates(
    content: str,
    reference_date: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """Alias for check_expired_dates_and_promotions to detect past validity/promotional dates."""
    return check_expired_dates_and_promotions(content, reference_date=reference_date)


# ============================================================================
# 3. IMAGE ACCESSIBILITY (ALT TEXT AUDIT)
# ============================================================================

def check_image_accessibility(
    images_or_html: Union[List[Dict[str, Any]], str]
) -> List[Dict[str, Any]]:
    """Detect images missing alt text or possessing generic/placeholder alt descriptions."""
    findings: List[Dict[str, Any]] = []

    images_list: List[Dict[str, Any]] = []
    if isinstance(images_or_html, str):
        soup = BeautifulSoup(images_or_html, "html.parser")
        for img in soup.find_all("img"):
            images_list.append({
                "src": img.get("src", ""),
                "alt": img.get("alt")
            })
    elif isinstance(images_or_html, list):
        images_list = images_or_html

    for img_idx, img in enumerate(images_list, start=1):
        src = img.get("src", f"image_{img_idx}")
        alt = img.get("alt")

        # 1. Missing alt attribute entirely
        if alt is None:
            findings.append({
                "severity": "high",
                "issue_type": "Accessibility: Missing Alt Text",
                "flagged_text": f'<img src="{src}">',
                "explanation": (
                    f"Image '{src}' is missing an 'alt' attribute. Screen readers require descriptive "
                    "alt text to convey visual content to visually impaired users."
                ),
                "suggested_fix": (
                    f'Add a descriptive alt attribute describing the image purpose, e.g., '
                    f'alt="Product demonstration of BrandPrint AI dashboard".'
                ),
                "is_deterministic": True,
                "cited_quote": f'<img src="{src}">',
                "rule_id": None,
                "user_action": "pending",
            })
            continue

        # 2. Empty alt text
        trimmed_alt = alt.strip()
        if not trimmed_alt:
            findings.append({
                "severity": "medium",
                "issue_type": "Accessibility: Empty Alt Text",
                "flagged_text": f'<img src="{src}" alt="">',
                "explanation": (
                    f"Image '{src}' has an empty alt attribute. If this is a decorative image, "
                    "verify compliance; if it conveys content, a descriptive label is required."
                ),
                "suggested_fix": (
                    "Provide informative description of the image content unless strictly decorative."
                ),
                "is_deterministic": True,
                "cited_quote": f'<img src="{src}" alt="">',
                "rule_id": None,
                "user_action": "pending",
            })
            continue

        # 3. Generic or placeholder alt text (e.g., "image", "photo", "logo")
        if trimmed_alt.lower() in PLACEHOLDER_ALT_PATTERNS or len(trimmed_alt) < 4:
            findings.append({
                "severity": "medium",
                "issue_type": "Accessibility: Generic Alt Text",
                "flagged_text": f'alt="{alt}"',
                "explanation": (
                    f"Image '{src}' uses generic placeholder alt text '{alt}'. Alt text should be "
                    "specific, descriptive, and avoid redundant words like 'photo' or 'image'."
                ),
                "suggested_fix": (
                    f"Replace '{alt}' with meaningful contextual description of what is depicted."
                ),
                "is_deterministic": True,
                "cited_quote": f'<img src="{src}" alt="{alt}">',
                "rule_id": None,
                "user_action": "pending",
            })

    return findings


def check_missing_alt_text(
    images_or_html: Union[List[Dict[str, Any]], str]
) -> List[Dict[str, Any]]:
    """Flag any images lacking descriptive alt attributes."""
    return check_image_accessibility(images_or_html)



# ============================================================================
# 4. COLOR CONTRAST UTILITY (WCAG 2.1 AA: 4.5:1)
# ============================================================================

def parse_color_to_rgb(color_val: Union[str, Tuple[int, int, int]]) -> Tuple[int, int, int]:
    """Parse hex string (#FFF, #FFFFFF) or RGB tuple to (r, g, b) integers in range 0-255."""
    if isinstance(color_val, (tuple, list)) and len(color_val) == 3:
        return int(color_val[0]), int(color_val[1]), int(color_val[2])

    if isinstance(color_val, str):
        color_clean = color_val.strip()
        # Handle RGB format: rgb(255, 255, 255)
        rgb_match = re.match(r"rgb\s*\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)", color_clean, re.I)
        if rgb_match:
            return int(rgb_match.group(1)), int(rgb_match.group(2)), int(rgb_match.group(3))

        # Handle Hex format
        if color_clean.startswith("#"):
            hex_str = color_clean[1:]
        else:
            hex_str = color_clean

        if len(hex_str) == 3:
            hex_str = "".join([c * 2 for c in hex_str])
        if len(hex_str) == 6:
            return int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16)

    raise ValueError(f"Unsupported color format '{color_val}'. Provide Hex (#RRGGBB) or RGB tuple.")


def calculate_relative_luminance(color: Union[str, Tuple[int, int, int]]) -> float:
    """Calculate WCAG 2.1 relative luminance for an sRGB color.
    
    L = 0.2126 * R + 0.7152 * G + 0.0722 * B
    """
    r, g, b = parse_color_to_rgb(color)
    srgb = [c / 255.0 for c in (r, g, b)]

    # Linearize RGB components according to sRGB formula
    linearized = []
    for c in srgb:
        if c <= 0.04045:
            linearized.append(c / 12.92)
        else:
            linearized.append(((c + 0.055) / 1.055) ** 2.4)

    return 0.2126 * linearized[0] + 0.7152 * linearized[1] + 0.0722 * linearized[2]


def calculate_contrast_ratio(
    color_a: Union[str, Tuple[int, int, int]],
    color_b: Union[str, Tuple[int, int, int]]
) -> float:
    """Calculate WCAG contrast ratio between two colors (range: 1.0 to 21.0).
    
    Formula: (L1 + 0.05) / (L2 + 0.05) where L1 is the lighter color.
    """
    lum_a = calculate_relative_luminance(color_a)
    lum_b = calculate_relative_luminance(color_b)

    lighter = max(lum_a, lum_b)
    darker = min(lum_a, lum_b)

    ratio = (lighter + 0.05) / (darker + 0.05)
    return round(ratio, 2)


def evaluate_contrast_compliance(
    foreground: Union[str, Tuple[int, int, int]],
    background: Union[str, Tuple[int, int, int]],
    is_large_text: bool = False
) -> Dict[str, Any]:
    """Evaluate contrast ratio against WCAG 2.1 Level AA and AAA standards.
    
    WCAG AA thresholds:
    - Normal text: >= 4.5:1
    - Large text (>= 18pt or 14pt bold): >= 3.0:1
    """
    ratio = calculate_contrast_ratio(foreground, background)
    aa_threshold = 3.0 if is_large_text else 4.5
    aaa_threshold = 4.5 if is_large_text else 7.0

    passes_aa = ratio >= aa_threshold
    passes_aaa = ratio >= aaa_threshold

    return {
        "contrast_ratio": ratio,
        "passes_aa": passes_aa,
        "passes_aaa": passes_aaa,
        "aa_threshold": aa_threshold,
        "aaa_threshold": aaa_threshold,
        "is_large_text": is_large_text,
        "foreground": str(foreground),
        "background": str(background),
    }


def check_html_color_contrast(html_content: str, default_bg: str = "#FFFFFF") -> List[Dict[str, Any]]:
    """Scan HTML for inline color styles and evaluate contrast compliance."""
    findings: List[Dict[str, Any]] = []
    if not html_content:
        return findings

    # Look for style="...color: ...; background(-color)?: ...;"
    style_pattern = re.compile(
        r'style=["\']([^"\']*(?:color|background)[^"\']*)["\']',
        re.IGNORECASE
    )

    for match in style_pattern.finditer(html_content):
        style_str = match.group(1)
        fg_match = re.search(r'(?:^|;|\s)color\s*:\s*(#[0-9a-fA-F]{3,6}|rgb\([^)]+\))', style_str, re.I)
        bg_match = re.search(r'(?:^|;|\s)background(?:-color)?\s*:\s*(#[0-9a-fA-F]{3,6}|rgb\([^)]+\))', style_str, re.I)

        fg_color = fg_match.group(1) if fg_match else None
        bg_color = bg_match.group(1) if bg_match else default_bg

        if fg_color:
            try:
                eval_res = evaluate_contrast_compliance(fg_color, bg_color)
                if not eval_res["passes_aa"]:
                    findings.append({
                        "severity": "high",
                        "issue_type": "Accessibility: Low Color Contrast",
                        "flagged_text": f"color: {fg_color}; background: {bg_color}",
                        "explanation": (
                            f"Color contrast ratio of {eval_res['contrast_ratio']}:1 fails the WCAG AA minimum "
                            f"threshold of {eval_res['aa_threshold']}:1."
                        ),
                        "suggested_fix": (
                            f"Increase contrast between text ({fg_color}) and background ({bg_color}) "
                            f"to achieve at least 4.5:1 ratio."
                        ),
                        "is_deterministic": True,
                        "cited_quote": match.group(0),
                        "rule_id": None,
                        "user_action": "pending",
                    })
            except Exception as e:
                logger.debug(f"Could not parse colors '{fg_color}', '{bg_color}': {e}")

    return findings


def check_color_contrast(foreground_hex: str, background_hex: str) -> Dict[str, Any]:
    """Calculate relative luminance and WCAG 2.1 contrast ratio.
    
    Returns if it passes AA standard (minimum 4.5:1 for normal text).
    """
    res = evaluate_contrast_compliance(foreground_hex, background_hex, is_large_text=False)
    return {
        "foreground_hex": foreground_hex,
        "background_hex": background_hex,
        "contrast_ratio": res["contrast_ratio"],
        "passes_aa": res["passes_aa"],
        "passes_aaa": res["passes_aaa"],
        "aa_threshold": res["aa_threshold"],
        "is_deterministic": True
    }



# ============================================================================
# COMBINED DETERMINISTIC ENGINE RUNNER
# ============================================================================

def run_all_deterministic_checks(
    content: str,
    raw_html: Optional[str] = None,
    images: Optional[List[Dict[str, Any]]] = None,
    prohibited_rules: Optional[List[Any]] = None,
    competitors: Optional[List[str]] = None,
    reference_date: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """Execute all code-based deterministic checks before calling any LLM.
    
    Runs:
    1. Prohibited terms and competitor mentions
    2. Expired promotional dates
    3. Image accessibility (alt text)
    4. Color contrast compliance (if HTML provided)
    """
    all_findings: List[Dict[str, Any]] = []

    # 1. Banned terms
    all_findings.extend(check_banned_terms(content, prohibited_rules=prohibited_rules, competitors=competitors))

    # 2. Expired dates
    all_findings.extend(check_expired_dates_and_promotions(content, reference_date=reference_date))

    # 3. Image accessibility
    if images:
        all_findings.extend(check_image_accessibility(images))
    elif raw_html:
        all_findings.extend(check_image_accessibility(raw_html))

    # 4. Color contrast
    if raw_html:
        all_findings.extend(check_html_color_contrast(raw_html))

    return all_findings

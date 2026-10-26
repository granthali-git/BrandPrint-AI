"""Grounding Validator: Strict verification safety layer for AI-generated compliance findings.

Checks:
1. Does rule_id exist in active brand guidelines?
2. Does cited_quote actually appear in original rule text (exact substring or fuzzy match > 0.85)?
3. If unverified: Discards or tags findings as 'unverified_gap' so hallucinations never reach the user.
"""
import difflib
import logging
import re
from typing import Any, Dict, List, Optional, Tuple, Union
from sqlalchemy.orm import Session

from app.models.guideline import GuidelineRule

logger = logging.getLogger(__name__)


def normalize_text_for_comparison(text: Optional[str]) -> str:
    """Normalize text by lowercasing, stripping punctuation, and collapsing whitespace."""
    if not text:
        return ""
    cleaned = re.sub(r"[^\w\s]", "", text.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def fuzzy_quote_match(quote: str, full_text: str, threshold: float = 0.85) -> bool:
    """Check if quote exists in full_text via exact normalized substring or windowed fuzzy match > threshold."""
    norm_quote = normalize_text_for_comparison(quote)
    norm_full = normalize_text_for_comparison(full_text)
    if not norm_quote or not norm_full:
        return False

    # 1. Exact normalized substring match
    if norm_quote in norm_full:
        return True

    # 2. Windowed SequenceMatcher fuzzy match
    q_words = norm_quote.split()
    f_words = norm_full.split()
    k = len(q_words)
    if k == 0:
        return False

    for i in range(max(1, len(f_words) - k + 1)):
        window = " ".join(f_words[i:i + k])
        ratio = difflib.SequenceMatcher(None, norm_quote, window).ratio()
        if ratio >= threshold:
            return True

    # Check whole sequence ratio if relatively concise
    if len(norm_full) <= len(norm_quote) * 2:
        if difflib.SequenceMatcher(None, norm_quote, norm_full).ratio() >= threshold:
            return True

    return False


def verify_finding_grounding(
    finding: Dict[str, Any],
    rules_by_id: Dict[str, Any],
    db_session: Optional[Session] = None
) -> Tuple[bool, Optional[str], Optional[Any]]:
    """Verify a single finding against verified brand rules.
    
    Returns:
        Tuple[is_grounded, failure_reason, matched_rule_id]
    """
    raw_rule_id = finding.get("rule_id")
    issue_type = str(finding.get("issue_type", "")).lower()
    category = str(finding.get("category", "")).lower()

    # Pass-through for dedicated Inconsistency & Quality Audit findings
    is_inconsistency_finding = (
        issue_type in {
            "tone_inconsistency", "factual_drift", "claim_conflict",
            "visual_guideline_breach", "accessibility_issue", "language_style_shift"
        } or
        category in {
            "accessibility_issue", "brand_voice", "factual_accuracy",
            "claim_conflict", "visual_guideline", "visual_guideline_breach",
            "language_style", "language_style_shift"
        } or
        (isinstance(raw_rule_id, str) and any(
            raw_rule_id.upper().startswith(prefix)
            for prefix in ("A11Y-", "TONE-", "FACT-", "CLAIM-", "VISUAL-", "STYLE-")
        ))
    )
    if is_inconsistency_finding:
        return True, None, raw_rule_id

    if raw_rule_id is None:
        return False, "Finding has no rule_id specified.", None

    str_rule_id = str(raw_rule_id).strip()
    rule = rules_by_id.get(str_rule_id)

    # Secondary check in database if session available and not in in-memory map
    if not rule and db_session is not None:
        try:
            if str_rule_id.isdigit():
                target_id = int(str_rule_id)
                db_rule = db_session.query(GuidelineRule).filter(GuidelineRule.id == target_id).first()
                if db_rule:
                    rule = db_rule
                    rules_by_id[str_rule_id] = db_rule
        except Exception:
            pass

    # Check 1: Does rule_id exist for this brand?
    if not rule:
        return (
            False,
            f"Rule ID '{str_rule_id}' does not exist in active guidelines for this brand.",
            None,
        )

    # Check 2: Does cited_quote appear in original rule text?
    cited_quote = finding.get("cited_quote")
    if not cited_quote or not str(cited_quote).strip():
        return (
            False,
            "Finding does not provide a cited quote from the brand rule.",
            str_rule_id,
        )

    clean_quote = str(cited_quote).strip()
    if len(clean_quote) < 3:
        return (
            False,
            f"Cited quote '{cited_quote}' is too short to substantiate compliance.",
            str_rule_id,
        )

    rule_text = getattr(rule, "rule_text", "") or (rule.get("rule_text", "") if isinstance(rule, dict) else "")
    rule_title = getattr(rule, "title", "") or (rule.get("title", "") if isinstance(rule, dict) else "")
    full_rule_content = f"{rule_title} {rule_text}"

    # Fuzzy and substring matching
    if not fuzzy_quote_match(clean_quote, full_rule_content, threshold=0.85):
        return (
            False,
            f"Cited quote '{cited_quote}' was not found in the original rule text.",
            str_rule_id,
        )

    # Match ID
    matched_id = getattr(rule, "id", None) or (rule.get("id") if isinstance(rule, dict) else str_rule_id)
    return True, None, matched_id


def validate_findings(
    findings: List[Dict[str, Any]],
    candidate_rules: List[Any],
    db_session: Optional[Session] = None,
    discard_ungrounded: bool = False,
    tag_unverified_gap: bool = True
) -> List[Dict[str, Any]]:
    """Execute strict grounding validation on compliance findings.
    
    Verifies that each finding has a valid rule_id in candidate_rules / DB,
    and checks that cited_quote actually exists in original rule text (substring or fuzzy match > 0.85).
    
    If validation fails:
    - If discard_ungrounded is True: Discards the finding completely.
    - If discard_ungrounded is False: Tags validation_status='unverified_gap'
      (or 'needs_human_decision') to flag unverified hallucinations.
      
    Returns:
        List[dict]: Validated findings list.
    """
    if not findings:
        return []

    # Map candidate rules by id and rule_code for fast O(1) lookup
    rules_by_id: Dict[str, Any] = {}
    for r in candidate_rules:
        r_id = getattr(r, "id", None) or (r.get("id") if isinstance(r, dict) else None)
        r_code = getattr(r, "rule_code", None) or (r.get("rule_code") if isinstance(r, dict) else None)
        if r_id is not None:
            rules_by_id[str(r_id)] = r
        if r_code is not None:
            rules_by_id[str(r_code)] = r

    validated_findings: List[Dict[str, Any]] = []

    for f in findings:
        is_grounded, failure_reason, matched_rule_id = verify_finding_grounding(
            finding=f,
            rules_by_id=rules_by_id,
            db_session=db_session
        )

        finding_copy = dict(f)
        if is_grounded:
            finding_copy["is_grounded"] = True
            finding_copy["validation_status"] = "verified"
            finding_copy["rule_id"] = matched_rule_id
            validated_findings.append(finding_copy)
        else:
            logger.warning(
                f"Grounding validation failed: {failure_reason}. "
                f"Flagged text: '{finding_copy.get('flagged_text')}'"
            )
            if not discard_ungrounded:
                finding_copy["is_grounded"] = False
                status_label = "unverified_gap" if tag_unverified_gap else "needs_human_decision"
                finding_copy["validation_status"] = status_label
                finding_copy["user_action"] = "needs_human_decision"
                finding_copy["explanation"] = (
                    f"[{status_label.replace('_', ' ').title()}: {failure_reason}] {finding_copy.get('explanation', '')}"
                )
                validated_findings.append(finding_copy)
            # If discard_ungrounded is True, we drop hallucinated findings entirely

    return validated_findings


def validate_and_ground_findings(
    findings: List[Dict[str, Any]],
    brand_rules: List[Any],
    discard_ungrounded: bool = False,
) -> List[Dict[str, Any]]:
    """Alias for backwards compatibility with tests expecting needs_human_decision status."""
    return validate_findings(
        findings=findings,
        candidate_rules=brand_rules,
        db_session=None,
        discard_ungrounded=discard_ungrounded,
        tag_unverified_gap=False
    )

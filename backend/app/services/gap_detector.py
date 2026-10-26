"""Guideline Gap Detector Service for identifying unverified or vague guidance and proposing formal rules."""
import logging
import re
from typing import Any, Dict, List, Optional, Union
from sqlalchemy.orm import Session

from app.models.finding import Finding
from app.models.guideline import GuidelineRule, RuleCategory
from app.models.submission import ContentSubmission

logger = logging.getLogger(__name__)


def infer_gap_category(text: str, issue_type: str = "") -> RuleCategory:
    """Infer the most appropriate guideline rule category for a detected gap."""
    combined = f"{text} {issue_type}".lower()
    if any(k in combined for k in ("banned", "claim", "prohibit", "forbidden", "unbeatable", "guarantee", "miracle")):
        return RuleCategory.prohibited_claim
    if any(k in combined for k in ("accessibility", "alt text", "contrast", "wcag", "screen reader", "aria")):
        return RuleCategory.accessibility
    if any(k in combined for k in ("color", "logo", "hex", "font", "typography", "visual", "spacing")):
        return RuleCategory.visual
    if any(k in combined for k in ("fact", "statistic", "source", "percent", "citation", "number", "pricing", "warranty")):
        return RuleCategory.fact
    return RuleCategory.tone


def detect_guideline_gaps(
    brand_id: Union[int, str],
    findings: Optional[List[Dict[str, Any]]] = None,
    db_session: Optional[Session] = None
) -> List[Dict[str, Any]]:
    """Aggregates findings flagged as 'unverified_gap' or where AI noted vague guidance,
    and proposes candidate rules for brand managers to review and formalize.
    
    Args:
        brand_id: Target brand identifier.
        findings: Optional list of finding dictionaries from an evaluation.
        db_session: Optional SQLAlchemy DB session to query persisted findings.
        
    Returns:
        List of proposed candidate rules structured for brand manager review.
    """
    target_brand_id = int(brand_id) if str(brand_id).isdigit() else brand_id
    raw_gaps: List[Dict[str, Any]] = []

    # 1. Collect from provided findings list if passed
    if findings:
        for f in findings:
            status = str(f.get("validation_status") or "").lower()
            user_act = str(f.get("user_action") or "").lower()
            explanation = str(f.get("explanation") or "").lower()
            is_grounded = f.get("is_grounded")

            is_gap = (
                status == "unverified_gap"
                or user_act == "needs_human_decision"
                or is_grounded is False
                or "unverified gap" in explanation
                or "vague guidance" in explanation
                or "does not exist in active guidelines" in explanation
            )
            if is_gap:
                raw_gaps.append(f)

    # 2. Query persisted findings from DB if session is available and findings was empty or to complement
    if db_session is not None and not raw_gaps:
        try:
            persisted = (
                db_session.query(Finding)
                .join(ContentSubmission, Finding.submission_id == ContentSubmission.id)
                .filter(ContentSubmission.brand_id == target_brand_id)
                .filter(
                    (Finding.explanation.like("%Unverified Gap%"))
                    | (Finding.explanation.like("%vague%"))
                    | (Finding.explanation.like("%does not exist%"))
                    | (Finding.issue_type.like("%Gap%"))
                )
                .all()
            )
            for pf in persisted:
                raw_gaps.append({
                    "id": pf.id,
                    "submission_id": pf.submission_id,
                    "issue_type": pf.issue_type,
                    "flagged_text": pf.flagged_text or "",
                    "explanation": pf.explanation or "",
                    "suggested_fix": pf.suggested_fix,
                    "severity": pf.severity.value if hasattr(pf.severity, "value") else str(pf.severity),
                })
        except Exception as e:
            logger.warning(f"Error querying persisted gaps for brand {brand_id}: {e}")

    if not raw_gaps:
        return []

    # 3. Cluster gaps by topic/key terms to synthesize cohesive candidate rules
    clusters: Dict[str, Dict[str, Any]] = {}

    for gap in raw_gaps:
        flagged = str(gap.get("flagged_text") or "").strip()
        explanation = str(gap.get("explanation") or "")
        issue_type = str(gap.get("issue_type") or "Brand Guideline Gap")

        # Determine cluster key based on keywords or issue type
        category = infer_gap_category(flagged, issue_type)
        cluster_key = f"{category.value}_{issue_type}"

        if cluster_key not in clusters:
            clusters[cluster_key] = {
                "category": category.value,
                "issue_type": issue_type,
                "samples": [],
                "explanations": [],
                "count": 0
            }

        clusters[cluster_key]["count"] += 1
        if flagged and flagged not in clusters[cluster_key]["samples"]:
            clusters[cluster_key]["samples"].append(flagged)
        if explanation and len(clusters[cluster_key]["explanations"]) < 3:
            # Clean explanation of internal tag prefixes
            clean_exp = re.sub(r"^\[.*?\]\s*", "", explanation)
            clusters[cluster_key]["explanations"].append(clean_exp)

    # 4. Formulate proposed candidate rules
    proposed_rules: List[Dict[str, Any]] = []
    rule_idx = 1

    for c_key, data in clusters.items():
        sample_str = ", ".join(f"'{s}'" for s in data["samples"][:3])
        category = data["category"]

        if category == "prohibited_claim":
            title = f"Prohibited Term Policy: Restrict Unverified Claims"
            rule_text = (
                f"Marketing copy must not use unverified superlative or absolute claims such as {sample_str}. "
                "Ensure all performance and pricing claims are backed by legal documentation."
            )
            gap_reason = "Repeated ungrounded compliance flags on unsubstantiated promotional claims."
        elif category == "fact":
            title = f"Factual Accuracy & Documentation Requirement"
            rule_text = (
                f"Any numerical or policy assertions relating to {sample_str} must cite an official "
                "source of truth or product documentation."
            )
            gap_reason = "Vague or missing factual guidelines for pricing, metrics, or policy terms."
        elif category == "accessibility":
            title = f"Digital Accessibility & Inclusion Standard"
            rule_text = (
                "Ensure all customer-facing media and digital components provide explicit alternative text, "
                "proper contrast ratios, and clear semantic labeling."
            )
            gap_reason = "Missing formal WCAG accessibility requirements in current brand rules."
        elif category == "visual":
            title = f"Visual Consistency & Typography Directive"
            rule_text = (
                "All visual assets must conform strictly to approved brand color palettes, minimum contrast ratios, "
                "and designated typography scale."
            )
            gap_reason = "Inconsistent or uncodified visual styling found in content submissions."
        else:
            title = f"Brand Tone & Voice Directive: Standardizing {data['issue_type']}"
            rule_text = (
                f"Content should maintain an authoritative yet approachable brand voice. Avoid ambiguous phrasing "
                f"around {sample_str}."
            )
            gap_reason = "AI flagged ambiguous or vague tone guidance during content evaluation."

        proposed_rules.append({
            "brand_id": target_brand_id,
            "category": category,
            "proposed_title": title,
            "proposed_rule_code": f"PROP-{rule_idx:03d}",
            "proposed_rule_text": rule_text,
            "gap_reason": gap_reason,
            "source_finding_count": data["count"],
            "sample_flagged_texts": data["samples"][:5],
            "sample_explanations": data["explanations"],
            "suggested_action": "Formalize as an official brand rule in Guideline Rules repository."
        })
        rule_idx += 1

    return proposed_rules

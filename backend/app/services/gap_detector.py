"""Autonomous Guideline Gap & Ambiguity Detector with Managerial Governance Triage.

Identifies:
1. Unregulated Content Claims: Claims in marketing copy that existing guidelines do not govern
   (e.g. "Microbiome-friendly", "Carbon-neutral packaging", "Zero-emission guarantee").
2. Ambiguous/Subjective Rules: Brand rules that are too vague to programmatically verify
   (e.g. "Make posters look luxurious and energetic").
Persists candidate policy proposals into `guideline_gaps` and allows Brand Managers to triage.
"""
import json
import logging
import re
from typing import Any, Dict, List, Optional, Union
from sqlalchemy.orm import Session

from app.models.guideline import GuidelineRule, RuleCategory
from app.models.transparency import GuidelineGap
from app.services.vector_store import index_brand_rules

logger = logging.getLogger(__name__)

GAP_DETECTION_SYSTEM_PROMPT = """You are an Enterprise Brand Governance Architect & Policy Synthesizer.
Analyze the provided marketing content alongside the active brand guideline rules.

Your task is to identify:
1. UNREGULATED CONTENT CLAIMS (`UNCOVERED_TOPIC`):
   Marketing claims or product statements that are made in the content, but for which the active guidelines have NO specific standard, verification requirement, or policy (e.g. carbon-neutral, organic, microbiome-friendly, clinical efficacy, AI-powered).
2. AMBIGUOUS OR SUBJECTIVE RULES (`AMBIGUOUS_RULE`):
   Existing rules in the guidelines that are vague, aspirational, or subjective (e.g. "Make graphics look luxurious and energetic", "Ensure a pleasant vibe"), which cannot be objectively measured or programmatically enforced.

Return strictly a JSON array of gaps:
[
  {
    "claim": "The exact unregulated phrase from content OR the vague rule text",
    "gap_type": "UNCOVERED_TOPIC" | "AMBIGUOUS_RULE",
    "severity": "MEDIUM" | "HIGH",
    "suggested_rule_proposal": "A clear, concrete, enforceable policy specification (e.g. 'All carbon-neutral and eco claims must cite ISO 14021 certification.')"
  }
]
If there are no meaningful gaps or ambiguities, return an empty array []."""


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
    if any(k in combined for k in ("legal", "compliance", "sec", "ftc", "iso", "fda", "gdpr", "disclaimer", "certification")):
        return RuleCategory.legal_compliance
    return RuleCategory.tone


def detect_guideline_gaps(
    brand_id: int,
    findings: Optional[List[Dict[str, Any]]] = None,
    db: Optional[Session] = None
) -> List[Dict[str, Any]]:
    """Detect unverified guideline gaps from findings or database submissions (backwards compatible)."""
    results: List[Dict[str, Any]] = []
    findings_list = findings or []

    if not findings_list and db is not None:
        from app.models.finding import Finding
        from app.models.submission import ContentSubmission
        try:
            db_findings = (
                db.query(Finding)
                .join(ContentSubmission, Finding.submission_id == ContentSubmission.id)
                .filter(ContentSubmission.brand_id == brand_id, Finding.rule_id.is_(None))
                .limit(50)
                .all()
            )
            for f in db_findings:
                findings_list.append({
                    "id": f.id,
                    "rule_id": f.rule_id,
                    "issue_type": f.issue_type,
                    "flagged_text": f.flagged_text,
                    "explanation": f.explanation,
                    "category": f.category,
                })
        except Exception as e:
            logger.debug(f"Could not load db findings for gaps: {e}")

    grouped: Dict[str, Dict[str, Any]] = {}
    for f in findings_list:
        flagged = str(f.get("flagged_text") or "").strip()
        issue = str(f.get("issue_type") or "Brand Policy Gap").strip()
        cat = infer_gap_category(f"{flagged} {issue}")
        cat_val = cat.value if hasattr(cat, "value") else str(cat)
        key = f"{cat_val}:{issue}"

        if key not in grouped:
            grouped[key] = {
                "category": cat_val,
                "proposed_title": f"Formal Standard: {issue}",
                "proposed_rule_text": (
                    f"Brand content must comply with standard guidelines regarding '{flagged}'. "
                    f"All marketing statements of this type require verified substantiation."
                    if flagged else f"Brand content must strictly adhere to formal {issue} requirements."
                ),
                "gap_reason": f"Content flagged under '{issue}' has no formal active guideline rule for Brand #{brand_id}.",
                "source_finding_count": 0,
                "claim": flagged or issue,
                "suggested_rule_proposal": (
                    f"Ensure all claims relating to '{flagged}' adhere to enterprise compliance benchmarks."
                    if flagged else f"Enforce strict rules for {issue}."
                ),
                "gap_type": "UNCOVERED_TOPIC",
                "severity": "MEDIUM",
            }
        grouped[key]["source_finding_count"] += 1

    return list(grouped.values())


def detect_heuristic_gaps(content: str, active_rules: List[Any]) -> List[Dict[str, Any]]:
    """Deterministic heuristic gap detector for unregulated claims and vague rules."""
    gaps: List[Dict[str, Any]] = []
    if not content:
        return gaps

    content_lower = content.lower()
    rule_texts_combined = " ".join([
        (r.rule_text if hasattr(r, "rule_text") else str(r.get("rule_text", ""))).lower()
        for r in active_rules
    ])

    # 1. Unregulated Topics Heuristics (Common modern enterprise copy topics)
    UNREGULATED_PATTERNS = [
        (
            r"\b(?:carbon[- ]neutral|net[- ]zero|eco[- ]friendly|sustainably[- ]sourced|green[- ]certified|climate[- ]positive)\b",
            "Environmental & Carbon-Neutral Claims",
            "All carbon-neutral, net-zero, and eco-friendly claims must reference verified ISO 14021 standards and current third-party audit reports."
        ),
        (
            r"\b(?:microbiome[- ]friendly|dermatologist[- ]approved|clinically[- ]proven|cellular[- ]repair|patented[- ]peptide)\b",
            "Cosmetic & Clinical Efficacy Claims",
            "Any clinical efficacy assertions must cite published double-blind study data and include statutory cosmetic disclaimers."
        ),
        (
            r"\b(?:ai[- ]powered|autonomous[- ]intelligence|machine[- ]learning[- ]guaranteed|fully[- ]automated)\b",
            "AI & Automated Technology Terminology",
            "Marketing statements claiming AI or automated capabilities must clearly define human-in-the-loop governance and avoid deceptive autonomy assertions."
        ),
        (
            r"\b(?:100%[- ]organic|natural[- ]formula|chemical[- ]free|clean[- ]beauty)\b",
            "Purity & Clean Formulation Standards",
            "Content claiming 'organic' or 'chemical-free' must maintain USDA/COSMOS organic certification documentation on file."
        ),
    ]

    for pat, topic_title, proposal in UNREGULATED_PATTERNS:
        match = re.search(pat, content, re.IGNORECASE)
        if match:
            matched_phrase = match.group(0)
            # Check if active rules already cover this topic
            keywords = pat.replace(r"\b", "").replace("[- ]", " ").split("|")
            already_covered = any(k.strip("()") in rule_texts_combined for k in keywords[:2])
            if not already_covered:
                gaps.append({
                    "claim": matched_phrase,
                    "gap_type": "UNCOVERED_TOPIC",
                    "severity": "HIGH",
                    "suggested_rule_proposal": proposal,
                })

    # 2. Vague / Subjective Rules in Active Guidelines
    VAGUE_RULE_PATTERNS = [
        r"\b(?:look\s+(?:luxurious|energetic|modern|cool|fresh|clean)|be\s+(?:friendly|exciting|bold|inspiring))\b",
        r"\b(?:good\s+taste|high\s+quality\s+feel|user[- ]friendly\s+vibe|premium\s+atmosphere)\b"
    ]

    for r in active_rules:
        r_text = (r.rule_text if hasattr(r, "rule_text") else str(r.get("rule_text", "")))
        for vpat in VAGUE_RULE_PATTERNS:
            if re.search(vpat, r_text, re.IGNORECASE):
                gaps.append({
                    "claim": r_text,
                    "gap_type": "AMBIGUOUS_RULE",
                    "severity": "MEDIUM",
                    "suggested_rule_proposal": (
                        f"Replace subjective directive with measurable standards: specify typography, "
                        f"minimum WCAG contrast ratios, and approved palette hex codes."
                    ),
                })
                break

    return gaps


def scan_and_record_guideline_gaps(
    content: str,
    active_rules: List[Any],
    brand_id: int,
    submission_id: Optional[int] = None,
    db: Optional[Session] = None
) -> List[Dict[str, Any]]:
    """Analyzes content and active guidelines for gaps, persists them to `guideline_gaps`."""
    gaps_found: List[Dict[str, Any]] = []

    # 1. Try LLM detection if online
    from app.services.ai_service import call_gemini_api, extract_json_array
    import os
    gemini_key = os.getenv("GEMINI_API_KEY")

    if gemini_key and gemini_key.strip() and not os.environ.get("TESTING"):
        try:
            rules_summary = "\n".join([
                f"- [{getattr(r, 'rule_code', 'RULE')}] {getattr(r, 'title', '')}: {getattr(r, 'rule_text', '')}"
                for r in active_rules[:15]
            ])
            prompt = (
                f"{GAP_DETECTION_SYSTEM_PROMPT}\n\n"
                f"ACTIVE GUIDELINE RULES:\n{rules_summary or 'No active rules defined yet.'}\n\n"
                f"MARKETING CONTENT:\n\"\"\"{content[:4000]}\"\"\""
            )
            # Use candidate model rotation
            from app.core.config import settings
            import httpx
            headers = {"x-goog-api-key": gemini_key.strip(), "Content-Type": "application/json"}
            payload = {
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"}
            }
            with httpx.Client(timeout=4.0) as client:
                res = client.post(
                    "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
                    headers=headers,
                    json=payload
                )
                if res.status_code == 200:
                    data = res.json()
                    parts = data.get("candidates", [])[0].get("content", {}).get("parts", [])
                    if parts:
                        parsed = extract_json_array(parts[0].get("text", ""))
                        if isinstance(parsed, list):
                            for g in parsed:
                                if isinstance(g, dict) and "claim" in g and "suggested_rule_proposal" in g:
                                    gaps_found.append({
                                        "claim": str(g["claim"]).strip(),
                                        "gap_type": g.get("gap_type") or "UNCOVERED_TOPIC",
                                        "severity": g.get("severity") or "MEDIUM",
                                        "suggested_rule_proposal": str(g["suggested_rule_proposal"]).strip(),
                                    })
        except Exception as e:
            logger.debug(f"LLM gap detection failed or timed out: {e}")

    # 2. Heuristic detector fallback / supplement
    if not gaps_found:
        gaps_found = detect_heuristic_gaps(content=content, active_rules=active_rules)

    # 3. Persist to DB if session provided
    persisted_records: List[Dict[str, Any]] = []
    if db is not None and gaps_found:
        try:
            # Check existing active gaps for this brand to avoid duplication
            existing_gaps = (
                db.query(GuidelineGap)
                .filter(GuidelineGap.brand_id == brand_id, GuidelineGap.status == "PENDING_DECISION")
                .all()
            )
            existing_claims = {g.claim.strip().lower()[:60] for g in existing_gaps}

            for gap in gaps_found:
                claim_norm = gap["claim"].strip().lower()[:60]
                if claim_norm in existing_claims:
                    continue

                db_gap = GuidelineGap(
                    brand_id=brand_id,
                    submission_id=submission_id,
                    claim=gap["claim"],
                    gap_type=gap["gap_type"],
                    severity=gap.get("severity", "MEDIUM").upper(),
                    suggested_rule_proposal=gap["suggested_rule_proposal"],
                    status="PENDING_DECISION",
                )
                db.add(db_gap)
                existing_claims.add(claim_norm)
                persisted_records.append(gap)

            db.commit()
        except Exception as e:
            db.rollback()
            logger.warning(f"Error persisting guideline gaps to database: {e}")

    return gaps_found


def triage_guideline_gap(
    db: Session,
    gap_id: int,
    action: str,  # "ACCEPT_PROPOSAL" | "DISMISS" | "REVISE"
    custom_rule_text: Optional[str] = None,
    custom_title: Optional[str] = None,
    category: Optional[str] = None,
) -> Dict[str, Any]:
    """Processes a brand manager's triage decision on a detected guideline gap.
    
    If 'ACCEPT_PROPOSAL' or 'REVISE', automatically creates and activates a new
    GuidelineRule and updates the FAISS vector index.
    """
    gap = db.query(GuidelineGap).filter(GuidelineGap.id == gap_id).first()
    if not gap:
        raise ValueError(f"Guideline gap with ID {gap_id} not found.")

    action_norm = action.upper().strip()

    if action_norm in ("ACCEPT_PROPOSAL", "REVISE"):
        final_rule_text = (custom_rule_text or gap.suggested_rule_proposal).strip()
        if not final_rule_text:
            raise ValueError("Rule specification text cannot be empty.")

        rule_cat = RuleCategory.tone
        if category:
            try:
                rule_cat = RuleCategory(category.lower())
            except Exception:
                rule_cat = infer_gap_category(final_rule_text)
        else:
            rule_cat = infer_gap_category(final_rule_text)

        rule_title = custom_title or f"Policy Standard: {gap.claim[:45].strip()}"
        code_prefix = rule_cat.value[:4].upper()
        rule_code = f"{code_prefix}-GAP-{gap.id:02d}"

        new_rule = GuidelineRule(
            brand_id=gap.brand_id,
            category=rule_cat,
            title=rule_title,
            rule_text=final_rule_text,
            rule_code=rule_code,
            source_file="Guideline Gap Triage System",
            is_active=True,
            version=1,
        )
        db.add(new_rule)
        gap.status = "ADOPTED" if action_norm == "ACCEPT_PROPOSAL" else "REVISED"
        gap.resolution_notes = f"Formalized into brand codex as active rule '{rule_code}'."
        db.commit()
        db.refresh(new_rule)
        db.refresh(gap)

        # Update FAISS vector store
        try:
            active_rules = (
                db.query(GuidelineRule)
                .filter(GuidelineRule.brand_id == gap.brand_id, GuidelineRule.is_active == True)
                .all()
            )
            index_brand_rules(gap.brand_id, active_rules)
        except Exception as e:
            logger.warning(f"Could not re-index FAISS store after gap triage: {e}")

        return {
            "success": True,
            "status": gap.status,
            "gap_id": gap.id,
            "rule_created": {
                "id": new_rule.id,
                "rule_code": new_rule.rule_code,
                "title": new_rule.title,
                "rule_text": new_rule.rule_text,
                "category": new_rule.category.value,
            },
            "message": f"Successfully adopted gap into official active brand guidelines as {new_rule.rule_code}."
        }

    elif action_norm == "DISMISS":
        gap.status = "DISMISSED"
        gap.resolution_notes = "Dismissed as campaign-specific exception by Brand Governance Manager."
        db.commit()
        db.refresh(gap)
        return {
            "success": True,
            "status": gap.status,
            "gap_id": gap.id,
            "message": f"Guideline gap #{gap.id} dismissed."
        }

    else:
        raise ValueError(f"Invalid triage action '{action}'. Must be ACCEPT_PROPOSAL, DISMISS, or REVISE.")

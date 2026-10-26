"""Governance Analytics and Executive Dashboard endpoints."""
import logging
from typing import Any, Dict, List, Optional, Union
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.brand import Brand
from app.models.finding import Finding, SeverityLevel, UserAction
from app.models.guideline import GuidelineRule
from app.models.review import ReviewDecision, ReviewDecisionType
from app.models.submission import ContentSubmission, SubmissionStatus
from app.models.user import User
from app.services.contradiction_service import detect_brand_contradictions

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dashboard", tags=["Dashboard", "Governance Analytics"])


@router.get(
    "/summary",
    summary="Executive Governance Analytics Summary",
    description=(
        "Computes real-time governance metrics: total submissions, status breakdown, "
        "top 5 most frequently violated rules, common issue types, total contradictions, and guideline gaps."
    )
)
def get_dashboard_summary(
    brand_id: Optional[Union[int, str]] = Query(None, description="Filter metrics by Brand ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Compute aggregate governance and brand consistency metrics."""
    target_brand_id = None
    if brand_id is not None:
        target_brand_id = int(brand_id) if str(brand_id).isdigit() else brand_id

    submission_query = db.query(ContentSubmission)
    finding_query = db.query(Finding).join(ContentSubmission, Finding.submission_id == ContentSubmission.id)

    if target_brand_id is not None:
        submission_query = submission_query.filter(ContentSubmission.brand_id == target_brand_id)
        finding_query = finding_query.filter(ContentSubmission.brand_id == target_brand_id)

    # 1. Total Submissions / Checks
    total_submissions = submission_query.count()
    total_checks = total_submissions

    # 2. Status Breakdown (approved, changes_required, rejected, draft, etc.)
    status_counts = {
        s.value: submission_query.filter(ContentSubmission.status == s).count()
        for s in SubmissionStatus
    }
    # Ensure standard expected keys exist
    for key in ("approved", "changes_required", "rejected", "draft"):
        if key not in status_counts:
            status_counts[key] = 0

    # 3. Pass Rate Calculation:
    # A submission passes if either it has status 'approved' OR has 0 critical/high findings
    if total_submissions > 0:
        clean_submissions = (
            submission_query
            .filter(~ContentSubmission.findings.any(Finding.severity.in_([SeverityLevel.critical, SeverityLevel.high])))
            .count()
        )
        pass_rate = round((clean_submissions / total_submissions) * 100.0, 1)
    else:
        pass_rate = 100.0

    # 4. Top 5 Most Frequently Violated Rules
    top_broken_query = (
        db.query(
            Finding.rule_id,
            func.count(Finding.id).label("violation_count")
        )
        .join(ContentSubmission, Finding.submission_id == ContentSubmission.id)
    )
    if target_brand_id is not None:
        top_broken_query = top_broken_query.filter(ContentSubmission.brand_id == target_brand_id)

    top_broken_results = (
        top_broken_query
        .filter(Finding.rule_id.isnot(None))
        .group_by(Finding.rule_id)
        .order_by(desc("violation_count"))
        .limit(5)
        .all()
    )

    top_violated_rules: List[Dict[str, Any]] = []
    for rule_id, count in top_broken_results:
        rule_obj = db.query(GuidelineRule).filter(GuidelineRule.id == rule_id).first()
        top_violated_rules.append({
            "rule_id": rule_id,
            "rule_code": rule_obj.rule_code if rule_obj else "RULE",
            "title": rule_obj.title if rule_obj else "Unknown Rule",
            "category": rule_obj.category.value if rule_obj and hasattr(rule_obj.category, "value") else "general",
            "violation_count": count,
            "count": count
        })

    # 5. Common Issue Types Distribution
    issue_type_query = (
        finding_query
        .with_entities(Finding.issue_type, func.count(Finding.id))
        .group_by(Finding.issue_type)
        .order_by(desc(func.count(Finding.id)))
        .all()
    )
    common_issue_types = {
        str(itype or "General Compliance"): count
        for itype, count in issue_type_query
    }

    # 6. Total Contradictions Detected (Real-time from Supabase)
    total_contradictions_detected = 0
    try:
        rule_query = db.query(GuidelineRule).filter(GuidelineRule.is_active == True)
        if target_brand_id is not None:
            rule_query = rule_query.filter(GuidelineRule.brand_id == target_brand_id)
        active_rules = rule_query.all()

        statements = [{"id": r.id, "title": r.title, "text": r.rule_text} for r in active_rules]
        from app.services.contradiction_service import detect_heuristic_numeric_conflicts
        detected_conflicts = detect_heuristic_numeric_conflicts(statements)
        total_contradictions_detected = len(detected_conflicts)

        finding_contradictions = (
            finding_query
            .filter(Finding.explanation.like("%Contradict%") | Finding.issue_type.like("%Contradict%"))
            .count()
        )
        if finding_contradictions > total_contradictions_detected:
            total_contradictions_detected = finding_contradictions
    except Exception as e:
        logger.warning(f"Error computing total contradictions: {e}")


    # 7. Guideline Gaps Count
    guideline_gaps_count = (
        finding_query
        .filter(
            (Finding.explanation.like("%Unverified Gap%"))
            | (Finding.explanation.like("%vague%"))
            | (Finding.explanation.like("%does not exist%"))
            | (Finding.issue_type.like("%Gap%"))
        )
        .count()
    )

    # 8. Unresolved Contradictions (for backwards compatibility)
    unresolved_contradictions = (
        finding_query
        .filter(Finding.user_action == UserAction.pending)
        .filter(Finding.explanation.like("%Needs Human Decision%") | Finding.explanation.like("%Contradict%"))
        .count()
    )

    # 9. Pending Reviews
    pending_reviews = (
        submission_query
        .filter(ContentSubmission.status.in_([
            SubmissionStatus.ready_for_review,
            SubmissionStatus.in_review,
            SubmissionStatus.findings_ready,
            SubmissionStatus.draft,
        ]))
        .count()
    )

    # 10. Severity Breakdown
    severity_counts = {
        "critical": finding_query.filter(Finding.severity == SeverityLevel.critical).count(),
        "high": finding_query.filter(Finding.severity == SeverityLevel.high).count(),
        "medium": finding_query.filter(Finding.severity == SeverityLevel.medium).count(),
        "low": finding_query.filter(Finding.severity == SeverityLevel.low).count(),
    }

    # 11. Category Breakdown
    category_counts: Dict[str, int] = {}
    for r in top_violated_rules:
        c_val = r.get("category", "general")
        category_counts[c_val] = category_counts.get(c_val, 0) + r.get("count", 1)

    try:
        cat_query = (
            finding_query
            .join(GuidelineRule, Finding.rule_id == GuidelineRule.id)
            .with_entities(GuidelineRule.category, func.count(Finding.id))
            .group_by(GuidelineRule.category)
            .all()
        )
        for cat_obj, c_cnt in cat_query:
            cat_key = cat_obj.value if hasattr(cat_obj, "value") else str(cat_obj)
            category_counts[cat_key] = c_cnt
    except Exception as e:
        logger.debug(f"Error computing category breakdown: {e}")

    return {
        "brand_id": target_brand_id,
        "total_submissions": total_submissions,
        "total_checks": total_checks,
        "status_breakdown": status_counts,
        "status_counts": status_counts,
        "top_violated_rules": top_violated_rules,
        "top_5_broken_rules": top_violated_rules,
        "common_issue_types": common_issue_types,
        "category_breakdown": category_counts,
        "total_contradictions_detected": total_contradictions_detected,
        "total_contradictions": total_contradictions_detected,
        "guideline_gaps_count": guideline_gaps_count,
        "pass_rate_percentage": pass_rate,
        "pass_rate": pass_rate,
        "unresolved_contradictions": unresolved_contradictions,
        "pending_reviews": pending_reviews,
        "severity_breakdown": severity_counts,
        "total_violations_detected": sum(severity_counts.values())
    }

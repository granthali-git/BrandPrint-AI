"""Unit and integration tests for Phase 4 standout features:
- What-If Simulator (content revision diff and draft rule impact)
- Brand Contradiction Detector (pairwise analysis and conflict identification)
- Reviewer Decision Workflow (versioning, status updates, audit records)
- Guideline Gap Detector (unverified gap aggregation and proposed candidate rules)
- Governance Analytics Dashboard (real-time metrics, distributions, breakdowns)
"""
import os
import sys
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.security import create_access_token, get_password_hash
from app.models.brand import Brand
from app.models.finding import Finding, SeverityLevel, UserAction
from app.models.guideline import GuidelineRule, RuleCategory
from app.models.review import ReviewDecision, ReviewDecisionType
from app.models.submission import ContentSubmission, ContentType, SubmissionStatus
from app.models.user import User, UserRole
from app.services.contradiction_service import (
    detect_brand_contradictions,
    detect_guideline_contradictions
)
from app.services.gap_detector import detect_guideline_gaps
from app.services.what_if_service import (
    simulate_content_revision,
    simulate_rule_impact,
    simulate_what_if_review
)
from tests.conftest import TestingSessionLocal, client


# ============================================================================
# 1. WHAT-IF SIMULATOR TESTS
# ============================================================================

def test_what_if_simulator_service_and_rule_impact():
    """Validates simulate_content_revision, simulate_rule_impact, and simulate_what_if_review."""
    db = TestingSessionLocal()
    # Create user & brand
    user = User(email="whatif_lead@acme.com", hashed_password=get_password_hash("Pass123!"), role=UserRole.Creator)
    db.add(user)
    db.commit()
    db.refresh(user)

    brand = Brand(name="WhatIf Brand", description="Testing WhatIf", created_by=user.id)
    db.add(brand)
    db.commit()
    db.refresh(brand)

    # Add active prohibited rule
    rule = GuidelineRule(
        brand_id=brand.id,
        category=RuleCategory.prohibited_claim,
        title="Unbeatable Prices Banned",
        rule_text="Never state unbeatable prices in marketing.",
        rule_code="PROH-001"
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)

    # Initial submission with 1 violation: "unbeatable prices"
    submission = ContentSubmission(
        brand_id=brand.id,
        creator_id=user.id,
        content_type=ContentType.text,
        raw_content="We provide unbeatable prices for enterprise customers.",
        status=SubmissionStatus.findings_ready,
        current_version=1
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    finding1 = Finding(
        submission_id=submission.id,
        version=1,
        rule_id=rule.id,
        severity=SeverityLevel.high,
        issue_type="Prohibited Claim / Term",
        flagged_text="unbeatable prices",
        explanation="Violates guideline PROH-001",
        suggested_fix="competitive rates"
    )
    db.add(finding1)
    db.commit()

    # A. Test simulate_content_revision service function
    diff_resolved = simulate_content_revision(
        original_submission_id=submission.id,
        revised_content="We provide competitive rates for enterprise customers.",
        db_session=db
    )
    assert diff_resolved["original_submission_id"] == submission.id
    assert len(diff_resolved["resolved_issues"]) >= 1
    assert any("unbeatable prices" in r["original_finding"]["flagged_text"] for r in diff_resolved["resolved_issues"])
    assert len(diff_resolved["remaining_issues"]) == 0
    assert len(diff_resolved["introduced_issues"]) == 0
    assert diff_resolved["summary"]["resolved_count"] >= 1
    assert diff_resolved["summary"]["remaining_count"] == 0
    assert diff_resolved["summary"]["new_count"] == 0

    # B. Test introduced issues when a new banned word is added
    diff_introduced = simulate_what_if_review(
        submission=submission,
        revised_content="We provide competitive rates and a miracle cure for enterprise workflows.",
        db=db
    )
    assert len(diff_introduced["introduced_issues"]) >= 1
    assert any("miracle cure" in i["simulated_finding"]["flagged_text"] for i in diff_introduced["introduced_issues"])

    # C. Test simulate_rule_impact on existing content drafts
    proposed_new_rule = {
        "title": "Prohibit 'enterprise workflows'",
        "rule_text": "Do not use the term 'enterprise workflows' without explicit feature qualification.",
        "category": "prohibited_claim"
    }
    impact = simulate_rule_impact(
        brand_id=brand.id,
        proposed_rule=proposed_new_rule,
        sample_submission_ids=[submission.id],
        db_session=db
    )
    assert impact["brand_id"] == brand.id
    assert impact["total_submissions_evaluated"] == 1
    assert "impacted_submissions_count" in impact
    assert "risk_level" in impact

    db.close()


# ============================================================================
# 2. BRAND CONTRADICTION DETECTOR TESTS
# ============================================================================

def test_brand_contradiction_detection_service_and_endpoint():
    """Validates pairwise contradiction detection for policies, duration, and tone."""
    db = TestingSessionLocal()
    reviewer = User(email="contradiction_auditor@acme.com", hashed_password=get_password_hash("Pass123!"), role=UserRole.Reviewer)
    db.add(reviewer)
    db.commit()
    db.refresh(reviewer)

    brand = Brand(name="Contradiction Brand", description="Contradiction testing", created_by=reviewer.id)
    db.add(brand)
    db.commit()
    db.refresh(brand)

    # Create opposing return policy rules in DB
    rule1 = GuidelineRule(
        brand_id=brand.id,
        category=RuleCategory.fact,
        title="Standard 30 Days Return Policy",
        rule_text="All customers are entitled to a 30 days return window for any purchase.",
        rule_code="FACT-010"
    )
    rule2 = GuidelineRule(
        brand_id=brand.id,
        category=RuleCategory.fact,
        title="Clearance 14 Days Return Policy",
        rule_text="Clearance items have a 14 days return policy only.",
        rule_code="FACT-011"
    )
    db.add_all([rule1, rule2])
    db.commit()

    # 1. Test detect_brand_contradictions service function
    db_conflicts = detect_brand_contradictions(brand_id=brand.id, db_session=db)
    assert len(db_conflicts) >= 1
    conflict = db_conflicts[0]
    assert "rule_a_id" in conflict
    assert "rule_b_id" in conflict
    assert "conflict_explanation" in conflict
    assert conflict["severity"] in ("critical", "high")

    # 2. Test POST /api/guidelines/check-contradictions endpoint with query param
    token = create_access_token({"sub": str(reviewer.id), "email": "contradiction_auditor@acme.com", "role": "Reviewer"})
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post(f"/api/guidelines/check-contradictions?brand_id={brand.id}", headers=headers)
    assert res.status_code == 200
    res_data = res.json()
    assert res_data["brand_id"] == brand.id
    assert res_data["contradictions_detected"] >= 1
    assert "conflicts" in res_data
    assert "contradictions" in res_data

    # 3. Test POST with newly uploaded draft statements
    new_draft_res = client.post(
        "/api/guidelines/check-contradictions",
        json={
            "brand_id": brand.id,
            "new_statements": [
                "Customers receive a 60 days return window on luxury goods.",
                "All sales are final with a 7 days return policy strictly."
            ]
        },
        headers=headers
    )
    assert new_draft_res.status_code == 200
    draft_data = new_draft_res.json()
    assert draft_data["contradictions_detected"] >= 1

    db.close()


# ============================================================================
# 3. REVIEWER WORKFLOW & WHAT-IF ENDPOINT TESTS
# ============================================================================

def test_reviewer_decision_workflow_and_versioning():
    """Validates reviewer decision workflow, role authorization, submission status, and simulation endpoint."""
    db = TestingSessionLocal()
    
    # Create Reviewer user
    reviewer = User(email="reviewer_lead_flow@acme.com", hashed_password=get_password_hash("Pass123!"), role=UserRole.Reviewer)
    db.add(reviewer)
    # Create Creator user
    creator = User(email="creator_flow@acme.com", hashed_password=get_password_hash("Pass123!"), role=UserRole.Creator)
    db.add(creator)
    db.commit()
    db.refresh(reviewer)
    db.refresh(creator)

    brand = Brand(name="Aura Fashion", description="Luxury apparel", created_by=reviewer.id)
    db.add(brand)
    db.commit()
    db.refresh(brand)

    submission = ContentSubmission(
        brand_id=brand.id,
        creator_id=creator.id,
        content_type=ContentType.text,
        raw_content="Aura Fashion launches summer collection with sustainable fabrics.",
        status=SubmissionStatus.ready_for_review,
        current_version=2
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    sub_id = str(submission.id)
    reviewer_id = str(reviewer.id)
    creator_id = str(creator.id)
    db.close()

    reviewer_token = create_access_token({"sub": reviewer_id, "email": "reviewer_lead_flow@acme.com", "role": "Reviewer"})
    creator_token = create_access_token({"sub": creator_id, "email": "creator_flow@acme.com", "role": "Creator"})

    # 1. Creator attempts to approve -> 403 Forbidden (RBAC)
    forbidden_res = client.post(
        f"/api/reviews/{sub_id}/decision",
        json={"decision": "approved", "comment": "Trying to self-approve"},
        headers={"Authorization": f"Bearer {creator_token}"}
    )
    assert forbidden_res.status_code == 403

    # 2. Reviewer approves with optional reviewer_id -> 201 Created & tied to current version (v2)
    decision_res = client.post(
        f"/api/reviews/{sub_id}/decision",
        json={
            "decision": "approved",
            "comment": "Copy is compliant with brand tone guidelines.",
            "reviewer_id": int(reviewer_id)
        },
        headers={"Authorization": f"Bearer {reviewer_token}"}
    )
    assert decision_res.status_code in (200, 201)
    dec_data = decision_res.json()
    assert dec_data["decision"] == "approved"
    assert dec_data["version"] == 2
    assert str(dec_data["reviewer_id"]) == str(reviewer_id)
    assert "submission" in dec_data
    assert dec_data["submission"]["status"] == "approved"

    # Verify submission status updated to approved via GET
    detail_res = client.get(f"/api/reviews/{sub_id}", headers={"Authorization": f"Bearer {reviewer_token}"})
    assert detail_res.status_code == 200
    assert detail_res.json()["submission"]["status"] == "approved"

    # 3. Test POST /api/reviews/{id}/simulate endpoint
    sim_res = client.post(
        f"/api/reviews/{sub_id}/simulate",
        json={"revised_content": "Aura Fashion launches sustainable elegance worldwide."},
        headers={"Authorization": f"Bearer {reviewer_token}"}
    )
    assert sim_res.status_code == 200
    sim_data = sim_res.json()
    assert sim_data["original_submission_id"] == int(sub_id)
    assert "resolved_issues" in sim_data
    assert "remaining_issues" in sim_data
    assert "introduced_issues" in sim_data
    assert "summary" in sim_data
    assert "resolved_count" in sim_data["summary"]
    assert "remaining_count" in sim_data["summary"]
    assert "new_count" in sim_data["summary"]


# ============================================================================
# 4. GUIDELINE GAP DETECTOR TESTS
# ============================================================================

def test_guideline_gap_detector_service_and_endpoint():
    """Validates aggregating unverified gaps and proposing structured formal rules."""
    db = TestingSessionLocal()
    admin = User(email="gap_admin@acme.com", hashed_password=get_password_hash("Pass123!"), role=UserRole.Admin)
    db.add(admin)
    db.commit()
    db.refresh(admin)

    brand = Brand(name="Gap Detection Brand", description="Testing Gaps", created_by=admin.id)
    db.add(brand)
    db.commit()
    db.refresh(brand)

    # Simulated findings list containing unverified gaps and vague guidance
    sample_findings = [
        {
            "id": 101,
            "rule_id": None,
            "issue_type": "Prohibited Claim / Term",
            "flagged_text": "guaranteed miracle results in 3 days",
            "explanation": "[Unverified Gap: Rule ID does not exist in active guidelines] Absolute claims need policy.",
            "is_grounded": False,
            "validation_status": "unverified_gap"
        },
        {
            "id": 102,
            "rule_id": None,
            "issue_type": "Digital Accessibility",
            "flagged_text": "hero image missing alt tag",
            "explanation": "[Unverified Gap: vague guidance] No formal alt text policy exists.",
            "is_grounded": False,
            "validation_status": "unverified_gap"
        }
    ]

    # 1. Service function test
    gaps = detect_guideline_gaps(brand_id=brand.id, findings=sample_findings)
    assert len(gaps) >= 1
    for gap in gaps:
        assert "category" in gap
        assert "proposed_title" in gap
        assert "proposed_rule_text" in gap
        assert "gap_reason" in gap
        assert "source_finding_count" in gap
        assert gap["source_finding_count"] >= 1

    # 2. Endpoint test: GET /api/guidelines/gaps?brand_id=...
    token = create_access_token({"sub": str(admin.id), "email": "gap_admin@acme.com", "role": "Admin"})
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(f"/api/guidelines/gaps?brand_id={brand.id}", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["brand_id"] == brand.id
    assert "proposed_rules" in data
    assert "candidate_rules_count" in data

    db.close()


# ============================================================================
# 5. GOVERNANCE ANALYTICS DASHBOARD TESTS
# ============================================================================

def test_governance_dashboard_summary():
    """Validates executive dashboard summary metrics, distributions, and Phase 4 required statistics."""
    db = TestingSessionLocal()
    admin_user = db.query(User).filter(User.email == "admin@brandprint.ai").first()
    if not admin_user:
        admin_user = User(
            email="admin@brandprint.ai",
            hashed_password=get_password_hash("AdminPass123!"),
            role=UserRole.Admin
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)

    admin_id = str(admin_user.id)
    db.close()

    # Generate token
    token = create_access_token({"sub": admin_id, "email": "admin@brandprint.ai", "role": "Admin"})
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/dashboard/summary", headers=headers)
    assert res.status_code == 200
    data = res.json()

    # Phase 4 Required Metrics
    assert "total_submissions" in data
    assert "status_breakdown" in data
    assert "top_violated_rules" in data
    assert "common_issue_types" in data
    assert "total_contradictions_detected" in data
    assert "guideline_gaps_count" in data

    # Backwards Compatibility Metrics
    assert "total_checks" in data
    assert "pass_rate_percentage" in data
    assert "top_5_broken_rules" in data
    assert "unresolved_contradictions" in data
    assert "pending_reviews" in data
    assert "severity_breakdown" in data
    assert isinstance(data["pass_rate_percentage"], float)
    assert isinstance(data["top_violated_rules"], list)
    assert isinstance(data["common_issue_types"], dict)
    assert isinstance(data["status_breakdown"], dict)
    assert "approved" in data["status_breakdown"]
    assert "changes_required" in data["status_breakdown"]
    assert "rejected" in data["status_breakdown"]
    assert "draft" in data["status_breakdown"]

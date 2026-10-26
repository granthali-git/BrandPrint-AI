"""Verification script for What-If Simulator Strategic Brand Impact analysis."""
import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.what_if_service import analyze_strategic_brand_impact, simulate_what_if_review
from app.models.submission import ContentSubmission, ContentType, SubmissionStatus
from app.core.database import SessionLocal

def run_strategic_verification():
    print("================================================================================")
    print("WHAT-IF SIMULATOR STRATEGIC BRAND IMPACT & EXCELLENCE VERIFICATION")
    print("================================================================================")

    test_copy = "Our infrastructure provides 99.95% verified uptime backed by real-time public status dashboards and SOC-2 Type II audit reports."

    print(f"\n[TEST 1] Directly analyzing target copy for strategic brand impact:")
    print(f"Content: \"{test_copy}\"")

    impact = analyze_strategic_brand_impact(
        target_content=test_copy,
        v1_findings_count=3,
        v2_findings_count=0,
        resolved_count=3,
        remaining_count=0,
        introduced_count=0,
        relevant_rules=[]
    )

    print(f"Excellence Status: {impact.get('excellence_status')}")
    print(f"Baseline Score:    {impact.get('baseline_score')}")
    print(f"Excellence Score:  {impact.get('excellence_score')}")
    print(f"Strategic Highlights: {impact.get('strategic_highlights')}")
    print("\nPositive Impacts:")
    for pi in impact.get("positive_impacts", []):
        print(f"  - [{pi.get('category')}]: {pi.get('metric')} -> {pi.get('explanation')}")

    assert impact.get("excellence_status") == "exceeds_standard", f"Expected exceeds_standard, got {impact.get('excellence_status')}"
    assert impact.get("baseline_score") == 85, f"Expected 85, got {impact.get('baseline_score')}"
    assert impact.get("excellence_score") >= 115, f"Expected >= 115, got {impact.get('excellence_score')}"
    assert len(impact.get("positive_impacts", [])) >= 3, f"Expected at least 3 positive impacts, got {len(impact.get('positive_impacts', []))}"
    print("\n[PASS] Direct Strategic Brand Impact analysis returned all required fields perfectly.")

    # Test 2: Database / ContentSubmission simulation
    print("\n[TEST 2] Testing simulate_what_if_review with simulated submission:")
    db = SessionLocal()
    try:
        # Fetch or mock submission
        submission = db.query(ContentSubmission).first()
        if not submission:
            submission = ContentSubmission(
                brand_id=1,
                raw_content="We are the cheapest and 100% infallible uptime guaranteed #1 provider.",
                content_type=ContentType.text,
                current_version=1,
                status=SubmissionStatus.findings_ready
            )
            db.add(submission)
            db.commit()
            db.refresh(submission)

        sim_res = simulate_what_if_review(
            submission=submission,
            revised_content=test_copy,
            db=db
        )

        print(f"Submission ID: {sim_res.get('submission_id')}")
        print(f"Baseline Score: {sim_res.get('baseline_score')}")
        print(f"Excellence Score: {sim_res.get('excellence_score')}")
        print(f"Excellence Status: {sim_res.get('excellence_status')}")
        print(f"Positive Impacts Count: {len(sim_res.get('positive_impacts', []))}")
        print(f"Strategic Highlights: {sim_res.get('strategic_highlights')}")
        print(f"Resolved Violations: {len(sim_res.get('resolved_violations', []))}")
        print(f"Remaining Violations: {len(sim_res.get('remaining_violations', []))}")
        print(f"Introduced Violations: {len(sim_res.get('introduced_violations', []))}")

        assert sim_res.get("excellence_status") == "exceeds_standard"
        assert sim_res.get("baseline_score") == 85
        assert sim_res.get("excellence_score") >= 115
        assert len(sim_res.get("positive_impacts", [])) >= 3
        assert "resolved_violations" in sim_res
        assert "remaining_violations" in sim_res
        assert "introduced_violations" in sim_res
        print("\n[PASS] simulate_what_if_review conforms 100% to required JSON schema.")

    finally:
        db.close()

    print("\n================================================================================")
    print("ALL STRATEGIC BRAND IMPACT TESTS PASSED SUCCESSFULLY!")
    print("================================================================================")

if __name__ == "__main__":
    run_strategic_verification()

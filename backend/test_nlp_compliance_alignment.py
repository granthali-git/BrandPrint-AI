"""Verification test for Context-Aware NLP Compliance Evaluation in BrandPrint AI."""
import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.services.ai_service import analyze_content_against_rules
from app.services.deterministic_checks import check_banned_terms, is_negated_or_disclaimed_context

# Mock brand rules
mock_rules = [
    {
        "id": 101,
        "category": "prohibited_claim",
        "title": "No Superlative or Pricing Guarantees",
        "rule_text": "Never claim to be the number one or cheapest brand without verified audit proof.",
        "rule_code": "PROHIBIT-001"
    },
    {
        "id": 102,
        "category": "legal_compliance",
        "title": "No Absolute Guarantees Without Audit",
        "rule_text": "Do not advertise unconditional performance guarantees or 100% cure claims without formal compliance sign-off.",
        "rule_code": "LEGAL-002"
    }
]

def test_nlp_contextual_evaluation():
    print("=" * 70)
    print(" BRANDPRINT AI - NLP CONTEXTUAL EVALUATION VERIFICATION")
    print("=" * 70)

    # ------------------------------------------------------------------------
    # TEST 1: Negative Test (Negation / Disclaimer -> Should PASS with 0 flags)
    # ------------------------------------------------------------------------
    neg_test_content = "We do not claim to be the cheapest or number one; we focus on steady performance."
    print(f"\n[TEST 1] Negative Test (Author explicitly disclaims superlative claim):")
    print(f"Content: \"{neg_test_content}\"")
    
    # Check deterministic checks first
    det_findings = check_banned_terms(neg_test_content, prohibited_rules=mock_rules)
    print(f"Deterministic Findings Count: {len(det_findings)}")
    assert len(det_findings) == 0, f"Expected 0 deterministic findings, got: {det_findings}"
    print("  [PASS] Deterministic Guard: PASS (0 false positives)")

    # Check full AI analysis pipeline
    ai_findings = analyze_content_against_rules(content=neg_test_content, relevant_rules=mock_rules)
    print(f"AI Analysis Findings Count: {len(ai_findings)}")
    print(f"Findings: {json.dumps(ai_findings, indent=2)}")
    assert len(ai_findings) == 0, f"Expected 0 findings for negated statement, got: {ai_findings}"
    print("  [PASS] AI Evaluation Engine: PASS (0 false positives on negated claim)")

    # ------------------------------------------------------------------------
    # TEST 2: Comparative / Concession Test (Should PASS with 0 flags)
    # ------------------------------------------------------------------------
    comp_test_content = "While some claim to be the cheapest, we focus on verified reliability."
    print(f"\n[TEST 2] Comparative Context Test (Contrastive statement):")
    print(f"Content: \"{comp_test_content}\"")
    
    det_comp = check_banned_terms(comp_test_content, prohibited_rules=mock_rules)
    assert len(det_comp) == 0, f"Expected 0 deterministic findings, got: {det_comp}"
    print("  [PASS] Deterministic Guard: PASS (0 false positives)")

    ai_comp = analyze_content_against_rules(content=comp_test_content, relevant_rules=mock_rules)
    assert len(ai_comp) == 0, f"Expected 0 AI findings for comparative statement, got: {ai_comp}"
    print("  [PASS] AI Evaluation Engine: PASS (0 false positives on comparative clause)")

    # ------------------------------------------------------------------------
    # TEST 3: Statutory Policy / Legal Disclaimer Test (Should PASS with 0 flags)
    # ------------------------------------------------------------------------
    stat_test_content = "We offer a 30-day money-back guarantee as required by law."
    print(f"\n[TEST 3] Statutory Policy Test (Legitimate refund guarantee as required by law):")
    print(f"Content: \"{stat_test_content}\"")
    
    det_stat = check_banned_terms(stat_test_content, prohibited_rules=mock_rules)
    assert len(det_stat) == 0, f"Expected 0 deterministic findings, got: {det_stat}"
    print("  [PASS] Deterministic Guard: PASS (0 false positives)")

    ai_stat = analyze_content_against_rules(content=stat_test_content, relevant_rules=mock_rules)
    assert len(ai_stat) == 0, f"Expected 0 AI findings for statutory refund guarantee, got: {ai_stat}"
    print("  [PASS] AI Evaluation Engine: PASS (0 false positives on statutory policy)")

    # ------------------------------------------------------------------------
    # TEST 4: Positive Test (Direct Affirmative Violation -> Should FLAG)
    # ------------------------------------------------------------------------
    pos_test_content = "Switch now because we are the absolute cheapest and guaranteed number one provider."
    print(f"\n[TEST 4] Positive Test (Explicit affirmative violation):")
    print(f"Content: \"{pos_test_content}\"")

    pos_findings = analyze_content_against_rules(content=pos_test_content, relevant_rules=mock_rules)
    print(f"AI Analysis Findings Count: {len(pos_findings)}")
    print(f"Findings: {json.dumps(pos_findings, indent=2)}")

    assert len(pos_findings) >= 1, "Expected at least 1 violation flagged for positive test!"
    
    first_finding = pos_findings[0]
    print(f"Flagged Text: \"{first_finding.get('flagged_text')}\"")
    print(f"Cited Quote:  \"{first_finding.get('cited_quote')}\"")
    print(f"Explanation:  \"{first_finding.get('explanation')}\"")
    print(f"Severity:     \"{first_finding.get('severity')}\"")
    print(f"Suggested Fix:\"{first_finding.get('suggested_fix')}\"")

    assert first_finding.get("rule_id") in (101, 102, "101", "102"), "Flagged finding must link to valid rule ID"
    assert len(first_finding.get("cited_quote", "")) > 0, "Cited quote must not be empty"
    assert len(first_finding.get("explanation", "")) > 0, "Explanation must not be empty"
    print("  [PASS] AI Evaluation Engine: PASS (Violation accurately flagged with contextual explanation)")

    print("\n" + "=" * 70)
    print("SUCCESS: ALL NLP CONTEXT-AWARE COMPLIANCE VERIFICATION TESTS PASSED!")
    print("=" * 70)

if __name__ == "__main__":
    test_nlp_contextual_evaluation()

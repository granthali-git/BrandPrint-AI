"""Unit and integration tests for FAISS retrieval, AI service, Grounding Validator, and Review routes."""
import os
import sys
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import Base, get_db
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models.brand import Brand
from app.models.finding import Finding, SeverityLevel, UserAction
from app.models.guideline import GuidelineRule, RuleCategory
from app.models.submission import ContentSubmission, ContentType, SubmissionStatus
from app.models.user import User, UserRole
from app.services.ai_service import (
    extract_json_array,
    format_evaluation_prompt,
    analyze_content_with_ai,
    analyze_content_against_rules,
)
from app.services.grounding_validator import (
    normalize_text_for_comparison,
    verify_finding_grounding,
    validate_and_ground_findings,
    validate_findings,
    fuzzy_quote_match,
)
from app.services.vector_store import (
    index_brand_rules,
    search_relevant_rules,
    retrieve_relevant_rules,
    clear_brand_index,
)
from tests.conftest import TestingSessionLocal, client



# ============================================================================
# 1. FAISS VECTOR STORE & SEMANTIC RETRIEVAL TESTS
# ============================================================================

def test_faiss_semantic_search():
    brand_id = "test-brand-faiss"
    
    rule1 = GuidelineRule(
        id="rule-tone-1",
        brand_id=brand_id,
        category=RuleCategory.tone,
        title="Active Optimistic Voice",
        rule_text="Always use forward-looking, upbeat language. Never sound passive or defeatist.",
        rule_code="TONE-001"
    )
    rule2 = GuidelineRule(
        id="rule-color-1",
        brand_id=brand_id,
        category=RuleCategory.visual,
        title="Primary Color Palette",
        rule_text="Our core brand hex color is #0055FF. Use white text on blue for high contrast.",
        rule_code="VISU-001"
    )
    rule3 = GuidelineRule(
        id="rule-claim-1",
        brand_id=brand_id,
        category=RuleCategory.prohibited_claim,
        title="No Unverified Quantum Claims",
        rule_text="Never claim quantum supremacy or 100% security without peer-reviewed accreditation.",
        rule_code="PROH-001"
    )

    # Index the rules in FAISS
    num_indexed = index_brand_rules(brand_id, [rule1, rule2, rule3])
    assert num_indexed == 3

    # Query 1: Color/contrast related query should retrieve rule2 first
    results_color = search_relevant_rules(brand_id, "What is our official hex color for button background?", top_k=1)
    assert len(results_color) == 1
    assert results_color[0].id == "rule-color-1"

    # Query 2: Quantum security claim should retrieve rule3
    results_claim = search_relevant_rules(brand_id, "We guarantee 100% security with quantum speed", top_k=1)
    assert len(results_claim) == 1
    assert results_claim[0].id == "rule-claim-1"

    clear_brand_index(brand_id)


# ============================================================================
# 2. AI SERVICE & JSON PARSING TESTS
# ============================================================================

def test_extract_json_array_formats():
    # Standard clean JSON
    json_str1 = '[{"rule_id": "1", "severity": "high", "flagged_text": "bad", "explanation": "no", "cited_quote": "yes", "suggested_fix": "fix"}]'
    res1 = extract_json_array(json_str1)
    assert len(res1) == 1
    assert res1[0]["rule_id"] == "1"

    # Markdown fenced JSON block
    json_str2 = f"```json\n{json_str1}\n```"
    res2 = extract_json_array(json_str2)
    assert len(res2) == 1

    # Empty array
    assert extract_json_array("[]") == []
    # Empty string
    assert extract_json_array("") == []


def test_format_evaluation_prompt():
    rules = [
        {"id": "r1", "title": "Tone", "category": "tone", "rule_text": "Be kind and concise"}
    ]
    prompt = format_evaluation_prompt("Hello world", rules)
    assert "Hello world" in prompt
    assert "Rule ID: r1" in prompt
    assert "Be kind and concise" in prompt


# ============================================================================
# 3. GROUNDING VALIDATOR TESTS
# ============================================================================

def test_grounding_validator():
    real_rule = {
        "id": "rule-tone-01",
        "title": "Professional Tone",
        "category": "tone",
        "rule_text": "Marketing copy must maintain an active, forward-looking tone without slang.",
        "rule_code": "TONE-001"
    }
    brand_rules = [real_rule]

    # 1. Grounded Finding: Valid rule_id and exact cited quote
    grounded_finding = {
        "rule_id": "rule-tone-01",
        "severity": "medium",
        "flagged_text": "chill vibes only",
        "explanation": "Slang is prohibited by tone guidelines.",
        "cited_quote": "without slang",
        "suggested_fix": "sophisticated atmosphere"
    }

    # 2. Hallucinated Rule ID: Rule does not exist
    hallucinated_rule_id = {
        "rule_id": "non-existent-rule-999",
        "severity": "high",
        "flagged_text": "cheap",
        "explanation": "Fake rule citation",
        "cited_quote": "never say cheap",
        "suggested_fix": "affordable"
    }

    # 3. Hallucinated Quote: Rule exists, but cited quote does not appear in text
    hallucinated_quote = {
        "rule_id": "rule-tone-01",
        "severity": "high",
        "flagged_text": "awesome tech",
        "explanation": "Rule violation",
        "cited_quote": "quantum supremacy must be verified",  # NOT in rule-tone-01!
        "suggested_fix": "great technology"
    }

    validated = validate_and_ground_findings(
        [grounded_finding, hallucinated_rule_id, hallucinated_quote],
        brand_rules=brand_rules,
        discard_ungrounded=False
    )

    # Check grounded finding
    f_valid = next(f for f in validated if f["flagged_text"] == "chill vibes only")
    assert f_valid["is_grounded"] is True
    assert f_valid["validation_status"] == "verified"

    # Check hallucinated rule ID finding
    f_bad_id = next(f for f in validated if f["flagged_text"] == "cheap")
    assert f_bad_id["is_grounded"] is False
    assert f_bad_id["validation_status"] == "needs_human_decision"
    assert "does not exist" in f_bad_id["explanation"]

    # Check hallucinated quote finding
    f_bad_quote = next(f for f in validated if f["flagged_text"] == "awesome tech")
    assert f_bad_quote["is_grounded"] is False
    assert f_bad_quote["validation_status"] == "needs_human_decision"
    assert "was not found in the original rule text" in f_bad_quote["explanation"]

    # When discard_ungrounded=True, only the truly grounded finding should survive
    strictly_filtered = validate_and_ground_findings(
        [grounded_finding, hallucinated_rule_id, hallucinated_quote],
        brand_rules=brand_rules,
        discard_ungrounded=True
    )
    assert len(strictly_filtered) == 1
    assert strictly_filtered[0]["flagged_text"] == "chill vibes only"


# ============================================================================
# 4. REVIEW ENDPOINTS INTEGRATION TESTS
# ============================================================================

def test_full_review_lifecycle_endpoints():
    db = TestingSessionLocal()
    
    # Setup test User & Brand
    user = User(
        email="reviewer_lead@acme.com",
        hashed_password=get_password_hash("Password123!"),
        role=UserRole.Creator
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    brand = Brand(
        name="Horizon Bio",
        description="Biotech therapeutics",
        created_by=user.id
    )
    db.add(brand)
    db.commit()
    db.refresh(brand)

    # Add a guideline rule
    rule = GuidelineRule(
        brand_id=brand.id,
        category=RuleCategory.prohibited_claim,
        title="Zero Risk Prohibited",
        rule_text="Never state or imply zero risk or guaranteed 100% cure in patient marketing.",
        rule_code="PROH-001",
        is_active=True,
        version=1
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)

    user_id = str(user.id)
    user_email = user.email
    brand_id = str(brand.id)
    rule_id = str(rule.id)
    db.close()

    # Create JWT
    token = create_access_token({"sub": user_id, "email": user_email, "role": "Creator"})
    headers = {"Authorization": f"Bearer {token}"}

    # 1. POST /api/reviews with text containing deterministic violation and rule violation
    submission_text = (
        "Horizon Bio introduces revolutionary cellular therapy with zero risk. "
        "Limited time introductory offer valid until December 1, 2020."
    )
    post_res = client.post(
        "/api/reviews",
        data={
            "brand_id": brand_id,
            "content_type": "text",
            "raw_content": submission_text
        },
        headers=headers
    )
    assert post_res.status_code == 201, post_res.text
    review_data = post_res.json()

    assert "submission" in review_data
    assert "findings" in review_data
    submission_id = review_data["submission"]["id"]
    findings = review_data["findings"]
    assert len(findings) >= 2  # Banned term (zero risk) and expired date (Dec 1, 2020)

    # 2. GET /api/reviews/{id}
    get_res = client.get(f"/api/reviews/{submission_id}", headers=headers)
    assert get_res.status_code == 200
    details = get_res.json()
    assert details["submission"]["id"] == submission_id
    assert len(details["findings"]) >= 2

    # 3. POST /api/reviews/{id}/action to accept a finding
    first_finding = findings[0]
    finding_id = first_finding["id"]
    
    action_res = client.post(
        f"/api/reviews/{submission_id}/action",
        json={
            "finding_id": finding_id,
            "action": "accepted",
            "suggested_fix": "rigorously tested safety profile"
        },
        headers=headers
    )
    assert action_res.status_code == 200, action_res.text
    updated_finding = action_res.json()
    assert updated_finding["id"] == finding_id
    assert updated_finding["user_action"] == "accepted"
    assert updated_finding["suggested_fix"] == "rigorously tested safety profile"

    # 4. PATCH /api/reviews/findings/{finding_id}
    patch_res = client.patch(
        f"/api/reviews/findings/{finding_id}",
        json={
            "action": "rejected",
            "suggested_fix": "keep original copy with medical disclaimer"
        },
        headers=headers
    )
    assert patch_res.status_code == 200, patch_res.text
    patched = patch_res.json()
    assert patched["id"] == finding_id
    assert patched["user_action"] == "rejected"
    assert patched["suggested_fix"] == "keep original copy with medical disclaimer"


def test_retrieve_relevant_rules_dict_format():
    """Verify retrieve_relevant_rules accepts dicts and returns top_k=4 active rules as dicts."""
    brand_id = 99
    rules = [
        {"id": 1, "category": "tone", "title": "Empathetic Voice", "rule_text": "Speak with empathy and warm tone."},
        {"id": 2, "category": "visual", "title": "Logo Spacing", "rule_text": "Always leave 24px padding around logo."},
        {"id": 3, "category": "fact", "title": "Study Citation", "rule_text": "Always cite the 2026 clinical study."},
        {"id": 4, "category": "prohibited_claim", "title": "No False Cures", "rule_text": "Never claim 100% cure for ailments."},
        {"id": 5, "category": "accessibility", "title": "Alt Text", "rule_text": "All images need descriptive alt text."},
    ]

    index_brand_rules(brand_id, rules)
    retrieved = retrieve_relevant_rules(brand_id, "We have a cure for all patients with 100% success", top_k=4)
    assert len(retrieved) <= 4
    assert len(retrieved) > 0
    # The No False Cures rule should be top ranked
    titles = [r["title"] for r in retrieved]
    assert "No False Cures" in titles
    assert all(isinstance(r, dict) for r in retrieved)

    clear_brand_index(brand_id)


def test_dual_ai_service_gemini_and_ollama_fallback(monkeypatch):
    """Verify primary Gemini call and automatic Ollama fallback when Gemini fails."""
    from app.services import ai_service

    test_rules = [{"id": 10, "title": "Banned Claim", "category": "prohibited_claim", "rule_text": "Never say miracle cure."}]

    # Case A: Gemini succeeds
    def mock_gemini_success(prompt, api_key):
        return [{
            "rule_id": 10,
            "severity": "high",
            "flagged_text": "miracle cure",
            "explanation": "Violates rule",
            "cited_quote": "Never say miracle cure.",
            "suggested_fix": "effective treatment"
        }]

    monkeypatch.setattr(ai_service, "call_gemini_api", mock_gemini_success)
    findings_gemini = analyze_content_against_rules("This is a miracle cure.", test_rules, gemini_api_key="valid-key")
    assert len(findings_gemini) == 1
    assert findings_gemini[0]["flagged_text"] == "miracle cure"

    # Case B: Gemini raises error -> Fallback to Ollama
    def mock_gemini_failure(prompt, api_key):
        raise RuntimeError("Google Gemini API HTTP 429: ResourceExhausted")

    def mock_ollama_success(prompt, base_url, model_name="llama3"):
        return [{
            "rule_id": 10,
            "severity": "high",
            "flagged_text": "miracle cure",
            "explanation": "Detected via Ollama fallback",
            "cited_quote": "Never say miracle cure.",
            "suggested_fix": "scientifically tested therapy"
        }]

    monkeypatch.setattr(ai_service, "call_gemini_api", mock_gemini_failure)
    monkeypatch.setattr(ai_service, "call_ollama_fallback", mock_ollama_success)

    findings_fallback = analyze_content_against_rules(
        "This is a miracle cure.",
        test_rules,
        gemini_api_key="failed-key",
        ollama_base_url="http://localhost:11434"
    )
    assert len(findings_fallback) == 1
    assert "Ollama fallback" in findings_fallback[0]["explanation"]


def test_grounding_validator_fuzzy_and_unverified_gap():
    """Verify fuzzy quote matching (>0.85) and unverified_gap tagging for hallucinated findings."""
    rules = [{
        "id": 101,
        "title": "Clear Return Policy",
        "category": "fact",
        "rule_text": "Customers may return products within thirty calendar days for a full refund."
    }]

    # 1. Fuzzy quote match (slight punctuation/case variation)
    fuzzy_finding = {
        "rule_id": 101,
        "severity": "medium",
        "flagged_text": "returns within 45 days",
        "explanation": "Return period violation",
        "cited_quote": "return products within thirty calendar days for a full refund",
        "suggested_fix": "return products within 30 days"
    }

    # 2. Hallucinated finding (fabricated rule ID)
    hallucinated = {
        "rule_id": 99999,
        "severity": "high",
        "flagged_text": "made up",
        "explanation": "Fake violation",
        "cited_quote": "imaginary rule text",
        "suggested_fix": "fix"
    }

    # Tag unverified_gap
    validated = validate_findings([fuzzy_finding, hallucinated], rules, tag_unverified_gap=True)
    assert len(validated) == 2
    f_fuzzy = next(f for f in validated if f["rule_id"] == 101)
    assert f_fuzzy["is_grounded"] is True
    assert f_fuzzy["validation_status"] == "verified"

    f_hallucinated = next(f for f in validated if f["rule_id"] == 99999)
    assert f_hallucinated["is_grounded"] is False
    assert f_hallucinated["validation_status"] == "unverified_gap"

    # Discard ungrounded
    discarded = validate_findings([fuzzy_finding, hallucinated], rules, discard_ungrounded=True)
    assert len(discarded) == 1
    assert discarded[0]["rule_id"] == 101


def test_post_reviews_json_payload():
    """Verify POST /api/reviews accepts direct application/json payload."""
    db = TestingSessionLocal()
    user = User(email="json_creator@acme.com", hashed_password=get_password_hash("Pass123!"), role=UserRole.Creator)
    db.add(user)
    db.commit()
    db.refresh(user)

    brand = Brand(name="Starlight Health", description="Wellness products", created_by=user.id)
    db.add(brand)
    db.commit()
    db.refresh(brand)

    token = create_access_token({"sub": str(user.id), "email": user.email, "role": "Creator"})
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    res = client.post(
        "/api/reviews",
        json={
            "brand_id": brand.id,
            "content_type": "text",
            "raw_content": "Starlight Health offers miracle cure with unbeatable prices!"
        },
        headers=headers
    )
    assert res.status_code == 201, res.text
    data = res.json()
    assert "submission" in data
    assert data["submission"]["brand_id"] == brand.id
    assert len(data["findings"]) >= 2


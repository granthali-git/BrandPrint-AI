"""Comprehensive test verification for the Autonomous Contradiction & Regulation Conflict Engine."""
import json
import logging
from app.core.database import SessionLocal
from app.models.guideline import GuidelineRule
from app.models.audit import PolicyAudit
from app.services.contradiction_service import detect_autonomous_contradictions, STANDARD_REGULATORY_BENCHMARKS
import httpx
from app.core.security import create_access_token

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_autonomous_service():
    print("=" * 80)
    print("STEP 1: Testing detect_autonomous_contradictions service")
    print("=" * 80)
    db = SessionLocal()
    try:
        results = detect_autonomous_contradictions(brand_id=1, db_session=db)
        print(f"[PASS] Service returned {len(results)} detected contradictions.")
        assert len(results) > 0, "Expected at least 1 detected contradiction for brand 1"
        
        # Verify schema of the first conflict
        sample = results[0]
        required_keys = ["conflict_id", "rule_a", "rule_b", "tension_type", "severity", "explanation", "suggested_resolution"]
        for k in required_keys:
            assert k in sample, f"Missing required key '{k}' in sample conflict"
        
        print(f"[PASS] Conflict ID: {sample['conflict_id']}")
        print(f"[PASS] Tension Type: {sample['tension_type']}")
        print(f"[PASS] Severity: {sample['severity']}")
        print(f"[PASS] Rule A: {sample['rule_a']['code']} - {sample['rule_a']['title']}")
        print(f"[PASS] Rule B: {sample['rule_b']['code']} - {sample['rule_b']['title']}")
        print(f"[PASS] Explanation: {sample['explanation'][:80]}...")
        print(f"[PASS] Suggested Resolution: {sample['suggested_resolution'][:80]}...")

        # Verify Regulatory Benchmarks are included
        has_reg = any(c['tension_type'] == 'Regulatory Overreach' or 'FTC' in str(c['rule_b'].get('code', '')) for c in results)
        print(f"[PASS] Cross-regulatory benchmark detection active: {has_reg}")
        assert has_reg, "Expected at least one regulatory conflict detected"

    finally:
        db.close()

def test_insufficient_rules_guard():
    print("=" * 80)
    print("STEP 2: Testing insufficient rules guard (< 2 rules)")
    print("=" * 80)
    db = SessionLocal()
    try:
        # Brand 2 has 0 rules
        results = detect_autonomous_contradictions(brand_id=2, db_session=db)
        print(f"[PASS] Insufficient rules returned {len(results)} conflicts as expected.")
        assert len(results) == 0
    finally:
        db.close()

def test_policy_audit_persistence():
    print("=" * 80)
    print("STEP 3: Testing PolicyAudit database record persistence")
    print("=" * 80)
    db = SessionLocal()
    try:
        latest_audit = db.query(PolicyAudit).order_by(PolicyAudit.id.desc()).first()
        assert latest_audit is not None, "PolicyAudit record should have been saved"
        print(f"[PASS] Found PolicyAudit #{latest_audit.id}")
        print(f"[PASS] Brand ID: {latest_audit.brand_id}")
        print(f"[PASS] Rules scanned count: {latest_audit.rules_scanned_count}")
        print(f"[PASS] Conflicts count: {latest_audit.conflicts_count}")
        assert latest_audit.conflicts_count > 0, "Conflicts count should be > 0"
    finally:
        db.close()

def test_live_api_endpoint():
    print("=" * 80)
    print("STEP 4: Testing live POST /api/guidelines/check-contradictions endpoint")
    print("=" * 80)
    token = create_access_token({"sub": "1", "email": "admin@brandprint.ai"})
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Test Brand 1 (Multiple rules)
    res = httpx.post("http://127.0.0.1:8001/api/guidelines/check-contradictions?brand_id=1", headers=headers, timeout=15.0)
    print(f"[API] Brand 1 Status: {res.status_code}")
    assert res.status_code == 200, f"Expected 200 but got {res.status_code}"
    data = res.json()
    print(f"[PASS] Total contradictions: {data.get('total_contradictions')}")
    print(f"[PASS] Message: {data.get('message')}")
    assert data.get("total_contradictions") > 0

    # 2. Test Brand 2 (0 rules -> insufficient rules message)
    res2 = httpx.post("http://127.0.0.1:8001/api/guidelines/check-contradictions?brand_id=2", headers=headers, timeout=10.0)
    print(f"[API] Brand 2 Status: {res2.status_code}")
    assert res2.status_code == 200
    data2 = res2.json()
    print(f"[PASS] Brand 2 Message: {data2.get('message')}")
    assert "Minimum 2 active guidelines" in data2.get("message")

if __name__ == "__main__":
    test_autonomous_service()
    test_insufficient_rules_guard()
    test_policy_audit_persistence()
    test_live_api_endpoint()
    print("\n" + "=" * 80)
    print("ALL 4 AUTONOMOUS CONTRADICTION TESTS PASSED PERFECTLY!")
    print("=" * 80)

import httpx
import json

BASE_URL = "http://localhost:8001"

def test_live_reviews_nlp_context():
    print("Testing live backend server at http://localhost:8001...")
    
    # Login as admin to get token
    login_res = httpx.post(f"{BASE_URL}/api/auth/login", json={"email": "tester@brandprint.ai", "password": "Password123!"}, timeout=10.0)
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Negative Test
    neg_text = "We do not claim to be the cheapest or number one; we focus on steady performance."
    neg_res = httpx.post(f"{BASE_URL}/api/reviews", json={"raw_content": neg_text, "content_type": "text", "brand_id": 1}, headers=headers, timeout=30.0)
    assert neg_res.status_code == 201, f"Negative test submission failed: {neg_res.text}"
    neg_findings = neg_res.json().get("findings", [])
    print(f"\n[Negative Test] \"{neg_text}\"")
    print(f"Findings Count: {len(neg_findings)}")
    print(f"Findings: {json.dumps(neg_findings, indent=2)}")
    assert len(neg_findings) == 0, f"Negative test should have 0 findings, got {len(neg_findings)}"
    print("[PASS] Negative test passed: 0 false positive violations flagged.")

    # 2. Positive Test
    pos_text = "Switch now because we are the absolute cheapest and guaranteed number one provider."
    pos_res = httpx.post(f"{BASE_URL}/api/reviews", json={"raw_content": pos_text, "content_type": "text", "brand_id": 1}, headers=headers, timeout=30.0)
    assert pos_res.status_code == 201, f"Positive test submission failed: {pos_res.text}"
    pos_findings = pos_res.json().get("findings", [])
    print(f"\n[Positive Test] \"{pos_text}\"")
    print(f"Findings Count: {len(pos_findings)}")
    print(f"Findings: {json.dumps(pos_findings, indent=2)}")
    assert len(pos_findings) >= 1, f"Positive test should have >= 1 findings, got {len(pos_findings)}"
    print("[PASS] Positive test passed: violation successfully detected and flagged.")

    print("\nALL LIVE API CONTEXTUAL COMPLIANCE TESTS PASSED!")

if __name__ == "__main__":
    test_live_reviews_nlp_context()

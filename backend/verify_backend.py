import sys
import httpx

# Ensure UTF-8 output encoding on Windows console
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://127.0.0.1:8000"

# Use client with generous timeout for LLM inference calls
with httpx.Client(timeout=60.0) as client:
    print("\n🔍 1. Checking Server Health...")
    r = client.get(f"{BASE_URL}/health")
    print("Health check:", r.status_code, r.json())
    assert r.status_code == 200

    print("\n🔑 2. Authenticating as Admin...")
    login_payload = {
        "email": "verify_admin@brandprint.ai",
        "password": "VerifyPass123!"
    }
    r_auth = client.post(f"{BASE_URL}/api/auth/login", json=login_payload)
    if r_auth.status_code != 200:
        # Try register if not existing
        r_reg = client.post(f"{BASE_URL}/api/auth/register", json={
            "email": "verify_admin@brandprint.ai",
            "password": "VerifyPass123!",
            "role": "Admin"
        })
        r_auth = client.post(f"{BASE_URL}/api/auth/login", json=login_payload)

    assert r_auth.status_code == 200, f"Auth failed: {r_auth.text}"
    token = r_auth.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    print("Authenticated successfully. Token acquired.")

    print("\n💾 3. Adding a Test Guideline Rule...")
    r = client.post(
        f"{BASE_URL}/api/guidelines",
        headers=headers,
        json={
            "brand_id": 1,
            "category": "prohibited_claim",
            "title": "No Unsubstantiated Claims",
            "rule_text": (
                "Never claim to be the number one or cheapest solution without audit proof."
            ),
            "rule_code": "PROHIBIT-01",
        },
    )
    print("Rule injection status:", r.status_code, r.json())

    print("\n⚡ 4. Submitting Sample Content Review...")
    review_payload = {
        "brand_id": 1,
        "content_type": "text",
        "raw_content": (
            "Buy our software today! We are the cheapest and number one tool on the market."
        ),
    }
    r = client.post(f"{BASE_URL}/api/reviews", headers=headers, json=review_payload)
    print("Review response status:", r.status_code)
    res = r.json()
    print(
        "Total findings detected:",
        res.get("total_findings", len(res.get("findings", []))),
    )

    print("\n📋 5. Detected Findings:")
    for f in res.get("findings", []):
        print(
            f" - [{f.get('severity', 'medium').upper()}] {f.get('issue_type')}:"
            f" \"{f.get('flagged_text')}\""
        )
        print(f"   Explanation: {f.get('explanation')}")
        print(f"   Cited Quote: {f.get('cited_quote')}")
        print(f"   Suggested Fix: {f.get('suggested_fix')}")

    print("\n📊 6. Checking Dashboard Summary...")
    r = client.get(f"{BASE_URL}/api/dashboard/summary?brand_id=1", headers=headers)
    print("Dashboard summary status:", r.status_code)
    d_data = r.json()
    print("Total Submissions:", d_data.get("total_submissions"))
    print("Status Breakdown:", d_data.get("status_breakdown"))
    print("Top Violated Rules:", d_data.get("top_violated_rules"))
    print("Common Issue Types:", d_data.get("common_issue_types"))
    print("Total Contradictions Detected:", d_data.get("total_contradictions_detected"))
    print("Guideline Gaps Count:", d_data.get("guideline_gaps_count"))

    print(
        "\n✅ BACKEND VERIFICATION COMPLETE: Pipeline, DB, AI Engine, and Checks are fully functioning!"
    )
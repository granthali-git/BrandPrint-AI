"""Comprehensive verification script for Phase 4 compliance workflow."""
import io
import time
import httpx
from PIL import Image, ImageDraw, ImageFont

BASE_URL = "http://127.0.0.1:8000"
client = httpx.Client(base_url=BASE_URL, timeout=60.0)

print("=" * 60)
print("PHASE 4 WORKFLOW VERIFICATION SUITE")
print("=" * 60)

# 1. Health check
res = client.get("/health")
print("[1] Health Check:", res.status_code, res.json().get("status"), f"(port {res.json().get('port')})")
assert res.status_code == 200

# 2. Login
res = client.post("/api/auth/login", json={"email": "tester@brandprint.ai", "password": "Password123!"})
print("[2] User Login:", res.status_code, "Token acquired")
assert res.status_code == 200
token = res.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 3. Create a realistic marketing poster PNG with text
img = Image.new("RGB", (800, 400), color=(11, 60, 73))
draw = ImageDraw.Draw(img)
draw.rectangle([(20, 20), (780, 380)], outline=(244, 163, 33), width=4)
draw.text((40, 50), "AstraForge Radiant Skin Serum", fill=(251, 249, 244))
draw.text((40, 100), "The absolute cheapest and guaranteed #1 skincare product in the world.", fill=(244, 163, 33))
draw.text((40, 150), "Provides 100% cure for all skin aging with zero risk forever.", fill=(251, 249, 244))
draw.text((40, 200), "Promotion valid until Dec 1, 2019.", fill=(251, 249, 244))

img_bytes = io.BytesIO()
img.save(img_bytes, format="PNG")
png_payload = img_bytes.getvalue()
print(f"[3] Generated Test Image: {len(png_payload) / 1024:.1f} KB PNG")

# 4. Upload Image & Run AI Compliance Review
t0 = time.time()
files = {"file": ("skincare_brand_poster.png", png_payload, "image/png")}
data = {"brand_id": "1", "content_type": "file"}

print("[4] Submitting PNG Image Review to Pipeline...")
res = client.post("/api/reviews", data=data, files=files, headers=headers)
duration = time.time() - t0
print(f"[4] Submission Result: HTTP {res.status_code} in {duration:.2f}s")
assert res.status_code == 201, res.text

review_data = res.json()
submission_id = review_data["submission"]["id"]
findings = review_data.get("findings", [])
total_findings = review_data.get("total_findings", len(findings))

print(f"    - Submission ID: {submission_id}")
print(f"    - Extracted Text: {review_data.get('extracted_text')[:60]}...")
print(f"    - Total Compliance Findings Detected: {total_findings}")
for i, f in enumerate(findings[:3], 1):
    print(f"      {i}. [{f.get('severity', '').upper()}] {f.get('issue_type')}: '{f.get('flagged_text')}'")
    print(f"         Suggested Fix: {f.get('suggested_fix')}")

# 5. Check Poll Status Endpoint
res = client.get(f"/api/reviews/{submission_id}/status", headers=headers)
print(f"[5] Polling Status Endpoint (/{submission_id}/status): HTTP {res.status_code}")
assert res.status_code == 200
status_data = res.json()
print(f"    - Status: {status_data.get('status')}, Completed: {status_data.get('completed')}, Progress: {status_data.get('progress')}%")

# 6. Submit Human Review Decision
print("[6] Submitting Human Review Decision (changes_required)...")
decision_payload = {
    "decision": "changes_required",
    "notes": "Marketing poster must substantiate superlatives and remove expired promotion date."
}
res = client.post(f"/api/reviews/{submission_id}/decision", json=decision_payload, headers=headers)
print(f"[6] Decision Result: HTTP {res.status_code}, Decision ID: {res.json().get('id')}")
assert res.status_code in (200, 201)

# 7. Action on a finding (Accept suggested fix)
if findings:
    first_finding_id = findings[0]["id"]
    res = client.patch(
        f"/api/reviews/findings/{first_finding_id}",
        json={"action": "accepted", "suggested_fix": findings[0].get("suggested_fix")},
        headers=headers
    )
    print(f"[7] Action on Finding #{first_finding_id}: HTTP {res.status_code}, Action: {res.json().get('user_action')}")
    assert res.status_code == 200

# 8. Verify Text-based Compliance Review
print("[8] Running Text-based Compliance Analysis...")
text_payload = {
    "brand_id": 1,
    "content_type": "text",
    "raw_content": "AstraForge guarantees 100% bug-free uptime with zero latency and lowest pricing guaranteed."
}
t0 = time.time()
res = client.post("/api/reviews", json=text_payload, headers=headers)
print(f"[8] Text Review Result: HTTP {res.status_code} in {time.time() - t0:.2f}s, Findings: {res.json().get('total_findings')}")
assert res.status_code == 201

# 9. Verify What-If Simulation
print("[9] Running What-If Simulator...")
whatif_res = client.post(
    f"/api/reviews/{submission_id}/simulate",
    json={"revised_content": "AstraForge Radiant Skin Serum offers independently tested hydration.", "draft_rules": []},
    headers=headers
)
print(f"[9] What-If Simulation Result: HTTP {whatif_res.status_code}, Remaining: {whatif_res.json().get('remaining_count')}, Resolved: {whatif_res.json().get('resolved_count')}")
assert whatif_res.status_code == 200

# 10. Verify Brand Contradiction Detection
print("[10] Running Brand Contradiction Detector...")
contradiction_res = client.post("/api/check-contradictions?brand_id=1", headers=headers)
print(f"[10] Contradiction Detector Result: HTTP {contradiction_res.status_code}")
assert contradiction_res.status_code == 200

print("=" * 60)
print("ALL PHASE 4 WORKFLOW TESTS COMPLETED SUCCESSFULLY!")
print("=" * 60)

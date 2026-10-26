"""Test API endpoint with real multipart file upload and authentication."""
import httpx
import os

def test_api_upload():
    print("Testing POST http://localhost:8001/api/reviews with file uploads...")
    client = httpx.Client(timeout=45.0)

    # 1. Login to get token
    login_res = client.post(
        "http://localhost:8001/api/auth/login",
        json={"email": "tester@brandprint.ai", "password": "Password123!"}
    )
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("[PASS] Authenticated successfully.")

    # 2. Test PPTX Upload
    pptx_path = os.path.join(os.path.dirname(__file__), "test_assets", "enterprise_presentation.pptx")
    with open(pptx_path, "rb") as f:
        files = {"file": ("enterprise_presentation.pptx", f, "application/vnd.openxmlformats-officedocument.presentationml.presentation")}
        data = {"brand_id": "1", "content_type": "file"}
        res = client.post("http://localhost:8001/api/reviews", data=data, files=files, headers=headers)
        print(f"PPTX Status: {res.status_code}")
        assert res.status_code in (200, 201), f"PPTX failed with {res.status_code}: {res.text}"
        res_json = res.json()
        extracted = res_json.get("extracted_text", "")
        print(f"Extracted PPTX length: {len(extracted)} chars")
        print("PPTX Head preview:\n" + extracted[:250])
        assert "--- [Slide 1: AstraForge Cloud Overview] ---" in extracted
        assert "--- [Slide 2: Security & Compliance Audits] ---" in extracted
        assert "--- [Slide 3: Enterprise SLA Commitments] ---" in extracted
        print("\n[PASS] PPTX upload and extraction succeeded via API!")

    # 3. Test PDF Upload
    pdf_path = os.path.join(os.path.dirname(__file__), "test_assets", "compliance_whitepaper.pdf")
    with open(pdf_path, "rb") as f:
        files = {"file": ("compliance_whitepaper.pdf", f, "application/pdf")}
        data = {"brand_id": "1", "content_type": "file"}
        res = client.post("http://localhost:8001/api/reviews", data=data, files=files, headers=headers)
        print(f"\nPDF Status: {res.status_code}")
        assert res.status_code in (200, 201), f"PDF failed with {res.status_code}: {res.text}"
        res_json = res.json()
        extracted = res_json.get("extracted_text", "")
        print(f"Extracted PDF length: {len(extracted)} chars")
        print("PDF Head preview:\n" + extracted[:250])
        assert "--- [Page 1] ---" in extracted
        assert "--- [Page 2] ---" in extracted
        print("\n[PASS] PDF upload and extraction succeeded via API!")

    print("\n================================================================================")
    print("ALL API FILE UPLOAD TESTS PASSED SUCCESSFULLY!")
    print("================================================================================")

if __name__ == "__main__":
    test_api_upload()

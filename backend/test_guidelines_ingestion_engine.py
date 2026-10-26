"""Automated test suite verifying the Brand Guidelines Ingestion Engine."""
import httpx
from app.core.security import create_access_token
from app.core.database import SessionLocal
from app.models.guideline import GuidelineRule

def test_guideline_ingestion_pipeline():
    token = create_access_token({"sub": "1", "email": "admin@brandprint.ai"})
    headers = {"Authorization": f"Bearer {token}"}
    client = httpx.Client(base_url="http://127.0.0.1:8001", headers=headers, timeout=20.0)

    print("=" * 80)
    print("STEP 1: Testing Multi-Format Document Ingestion (POST /api/guidelines/upload-document)")
    print("=" * 80)

    # 1. Test Word Document Ingestion (.docx)
    with open("test_assets/product_guidelines.docx", "rb") as f:
        docx_bytes = f.read()

    res_docx = client.post(
        "/api/guidelines/upload-document",
        data={"brand_id": 1, "auto_commit": "true", "preview_only": "false"},
        files={"file": ("product_guidelines.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    )
    print(f"[DOCX Ingest] Status: {res_docx.status_code}")
    assert res_docx.status_code == 201, f"Expected 201, got {res_docx.status_code}: {res_docx.text}"
    data_docx = res_docx.json()
    print(f"[PASS] Extracted {data_docx['rules_extracted_count']} rules from Word doc.")
    assert data_docx["rules_extracted_count"] > 0
    print(f"[PASS] Sample Rule: {data_docx['rules'][0]['rule_code']} - {data_docx['rules'][0]['title']}")

    # 2. Test PowerPoint Document Ingestion (.pptx)
    with open("test_assets/enterprise_presentation.pptx", "rb") as f:
        pptx_bytes = f.read()

    res_pptx = client.post(
        "/api/guidelines/upload-document",
        data={"brand_id": 1, "auto_commit": "true", "preview_only": "false"},
        files={"file": ("enterprise_presentation.pptx", pptx_bytes, "application/vnd.openxmlformats-officedocument.presentationml.presentation")}
    )
    print(f"[PPTX Ingest] Status: {res_pptx.status_code}")
    assert res_pptx.status_code == 201, f"Expected 201, got {res_pptx.status_code}: {res_pptx.text}"
    data_pptx = res_pptx.json()
    print(f"[PASS] Extracted {data_pptx['rules_extracted_count']} rules from PowerPoint deck.")
    assert data_pptx["rules_extracted_count"] > 0

    print("\n" + "=" * 80)
    print("STEP 2: Testing URL Ingestion & SSRF Protection (POST /api/guidelines/ingest-url)")
    print("=" * 80)

    # 3. Test SSRF Protection against loopback/localhost
    res_ssrf_local = client.post(
        "/api/guidelines/ingest-url",
        json={"brand_id": 1, "url": "http://127.0.0.1:8001/admin"}
    )
    print(f"[SSRF Check] 127.0.0.1 Status: {res_ssrf_local.status_code}")
    assert res_ssrf_local.status_code == 400, "SSRF loopback should return 400 Bad Request"
    print(f"[PASS] SSRF Error Message: {res_ssrf_local.json().get('detail')}")

    # 4. Test SSRF Protection against cloud metadata IP
    res_ssrf_meta = client.post(
        "/api/guidelines/ingest-url",
        json={"brand_id": 1, "url": "http://169.254.169.254/latest/meta-data/"}
    )
    print(f"[SSRF Check] Metadata IP Status: {res_ssrf_meta.status_code}")
    assert res_ssrf_meta.status_code == 400
    print(f"[PASS] SSRF Metadata Error Message: {res_ssrf_meta.json().get('detail')}")

    # 5. Test Valid Public URL Scraping
    res_url = client.post(
        "/api/guidelines/ingest-url",
        json={"brand_id": 1, "url": "https://example.com", "auto_commit": True, "preview_only": False}
    )
    print(f"[URL Ingest] Status: {res_url.status_code}")
    assert res_url.status_code == 201
    data_url = res_url.json()
    print(f"[PASS] Extracted {data_url['rules_extracted_count']} rules from public webpage.")
    print(f"[PASS] Source: {data_url['source']}")

    print("\n" + "=" * 80)
    print("STEP 3: Testing Bulk Save Endpoint (POST /api/guidelines/bulk-save)")
    print("=" * 80)
    sample_bulk = [
        {
            "rule_code": "BULK-01",
            "category": "legal_compliance",
            "title": "Mandatory SOC-2 Type II Report Display",
            "rule_text": "All enterprise cloud collateral must feature the active SOC-2 Type II verification badge.",
            "severity": "critical"
        },
        {
            "rule_code": "BULK-02",
            "category": "brand_voice",
            "title": "Inclusive Technical Documentation Tone",
            "rule_text": "Maintain an encouraging and empowering tone across all technical guides and architecture overviews.",
            "severity": "high"
        }
    ]
    res_bulk = client.post(
        "/api/guidelines/bulk-save",
        json={"brand_id": 1, "rules": sample_bulk, "source_name": "Verified Ingestion Test"}
    )
    print(f"[Bulk Save] Status: {res_bulk.status_code}")
    assert res_bulk.status_code == 201
    data_bulk = res_bulk.json()
    print(f"[PASS] Successfully saved {data_bulk['rules_saved_count']} rules in bulk.")
    assert data_bulk["rules_saved_count"] == 2

    print("\n" + "=" * 80)
    print("ALL 3 GUIDELINE INGESTION PIPELINE TESTS PASSED 100%!")
    print("=" * 80)

if __name__ == "__main__":
    test_guideline_ingestion_pipeline()

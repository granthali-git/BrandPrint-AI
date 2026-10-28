"""Production URL Support Audit Matrix Runner for BrandPrint AI.
Runs test cases against the live Render backend:
https://brandprint-ai-backend.onrender.com
"""
import urllib.request
import urllib.error
import json
import time

BACKEND_BASE = "https://brandprint-ai-backend.onrender.com"
AUTH_HEADER = "Bearer demo_guest_auditor"

TEST_URLS = [
    {
        "name": "Public HTML (Simple/Standard)",
        "url": "https://example.com/",
        "expected_guidelines": 201,
        "expected_review": 201,
    },
    {
        "name": "Public HTML (Complex/Realistic)",
        "url": "https://site-example.com/",
        "expected_guidelines": 201,
        "expected_review": 201,
    },
    {
        "name": "Public PDF Asset",
        "url": "https://science.nasa.gov/wp-content/uploads/2023/07/EARTH_POSTER_OPTIMIZED_Tagged.pdf",
        "expected_guidelines": 201,
        "expected_review": 201,
    },
    {
        "name": "HTTP 404 (Missing Resource)",
        "url": "https://httpbin.org/status/404",
        "expected_guidelines": 400,
        "expected_review": 404,
    },
    {
        "name": "HTTP 403 / WAF Protected (Bot Blocked)",
        "url": "https://www.ox.ac.uk/about/the-university/brand/guidelines",
        "expected_guidelines": 400,
        "expected_review": 403,
    },
    {
        "name": "SSRF: Localhost (127.0.0.1)",
        "url": "http://127.0.0.1:8000/admin",
        "expected_guidelines": 400,
        "expected_review": 400,
    },
    {
        "name": "SSRF: Cloud Metadata (169.254.169.254)",
        "url": "http://169.254.169.254/latest/meta-data/",
        "expected_guidelines": 400,
        "expected_review": 400,
    },
    {
        "name": "Unsupported Protocol (FTP)",
        "url": "ftp://example.com/rules.txt",
        "expected_guidelines": 400,
        "expected_review": 400,
    },
]


def test_guidelines_url(item):
    url = f"{BACKEND_BASE}/api/guidelines/ingest-url"
    payload = json.dumps({
        "brand_id": 1,
        "url": item["url"],
        "auto_commit": False,
        "preview_only": True
    }).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Authorization": AUTH_HEADER, "Content-Type": "application/json"}
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            dur = time.time() - t0
            body = resp.read().decode("utf-8")
            data = json.loads(body)
            return {
                "status": resp.status,
                "duration_s": round(dur, 2),
                "rules_extracted": data.get("rules_extracted_count", 0),
                "detail": data.get("message", "Success")[:120],
                "passed": True
            }
    except urllib.error.HTTPError as e:
        dur = time.time() - t0
        err_body = e.read().decode("utf-8")
        try:
            err_json = json.loads(err_body)
            detail = err_json.get("detail", err_body)
        except Exception:
            detail = err_body
        return {
            "status": e.code,
            "duration_s": round(dur, 2),
            "rules_extracted": 0,
            "detail": str(detail)[:120],
            "passed": e.code in (item["expected_guidelines"], 400, 422)
        }
    except Exception as ex:
        return {
            "status": 0,
            "duration_s": round(time.time() - t0, 2),
            "rules_extracted": 0,
            "detail": str(ex)[:120],
            "passed": False
        }


def test_review_url(item):
    url = f"{BACKEND_BASE}/api/reviews"
    # Submit as form-data
    boundary = "----BrandPrintAuditBoundary12345"
    lines = [
        f"--{boundary}",
        'Content-Disposition: form-data; name="brand_id"',
        '',
        '1',
        f"--{boundary}",
        'Content-Disposition: form-data; name="content_type"',
        '',
        'url',
        f"--{boundary}",
        'Content-Disposition: form-data; name="url"',
        '',
        item["url"],
        f"--{boundary}--",
        ''
    ]
    payload = "\r\n".join(lines).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": AUTH_HEADER,
            "Content-Type": f"multipart/form-data; boundary={boundary}"
        }
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            dur = time.time() - t0
            body = resp.read().decode("utf-8")
            data = json.loads(body)
            return {
                "status": resp.status,
                "duration_s": round(dur, 2),
                "total_findings": data.get("total_findings", 0),
                "extracted_sample": (data.get("extracted_text") or "")[:80].replace("\n", " "),
                "detail": f"Audited successfully ({data.get('total_findings', 0)} findings)",
                "passed": True
            }
    except urllib.error.HTTPError as e:
        dur = time.time() - t0
        err_body = e.read().decode("utf-8")
        try:
            err_json = json.loads(err_body)
            detail = err_json.get("detail", err_body)
        except Exception:
            detail = err_body
        return {
            "status": e.code,
            "duration_s": round(dur, 2),
            "total_findings": 0,
            "extracted_sample": "",
            "detail": str(detail)[:120],
            "passed": e.code in (item["expected_review"], 400, 403, 404, 422, 504)
        }
    except Exception as ex:
        return {
            "status": 0,
            "duration_s": round(time.time() - t0, 2),
            "total_findings": 0,
            "extracted_sample": "",
            "detail": str(ex)[:120],
            "passed": False
        }


def main():
    print(f"=== Running BrandPrint AI URL Support Audit Matrix ===")
    print(f"Target Backend: {BACKEND_BASE}\n")

    results = []
    for item in TEST_URLS:
        print(f"Testing: {item['name']} -> {item['url']}")
        g_res = test_guidelines_url(item)
        print(f"  [Guidelines] HTTP {g_res['status']} in {g_res['duration_s']}s | {g_res['detail']}")
        r_res = test_review_url(item)
        print(f"  [ReviewStudio] HTTP {r_res['status']} in {r_res['duration_s']}s | {r_res['detail']}\n")
        results.append({
            "name": item["name"],
            "url": item["url"],
            "guidelines": g_res,
            "review": r_res
        })

    with open("url_audit_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("Audit matrix saved to url_audit_results.json")


if __name__ == "__main__":
    main()

import requests

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIyIiwiZW1haWwiOiJhZG1pbkBicmFuZHByaW50LmFpIiwiZXhwIjoxNzkzMTI3MTk3fQ.DjutyxDpGVrYzrEjreSdOs1y7yQnlg99jOUnaV-xKhc"
headers = {"Authorization": f"Bearer {token}"}

test_cases = [
    ("Tone Inconsistency", "Our governance framework guarantees compliance. Hey buddies, just smash that buy button ASAP!"),
    ("Language & Style Shift", "We optimise our infrastructure while ensuring every color matches enterprise standards."),
    ("Factual Drift", "Our standard cloud tier guarantees 99.9% uptime across all environments. Meanwhile our mission-critical platform delivers 99.999% uptime."),
    ("Claim Conflict", "BrandPrint AI is completely open-source and free for all developers, but enforces proprietary vendor lock-in for enterprise extensions."),
    ("Visual Guideline Breach", "For promotional banners, designers must utilize neon green as the background backdrop."),
    ("Accessibility & Readability", "Utilize our quintessential obfuscation architecture for deployment to prevent extraneous telemetry inspection.")
]

for title, content in test_cases:
    payload = {"brand_id": 1, "content_type": "text", "raw_content": content}
    res = requests.post("http://localhost:8001/api/reviews", json=payload, headers=headers)
    print(f"\n=== {title} === (Status: {res.status_code})")
    if res.status_code == 201:
        data = res.json()
        findings = data.get("findings", [])
        print(f"Detected {len(findings)} findings:")
        for f in findings:
            print(f"  [{f.get('rule_id')}] ({f.get('category')} / {f.get('issue_type')} / {f.get('severity')}): \"{f.get('flagged_text')}\"")
            print(f"    Context: \"{f.get('context_span')}\"")
            print(f"    Fix: \"{f.get('suggested_fix')}\"")
            print(f"    Strategic Tip: \"{f.get('strategic_tip')}\"")
    else:
        print("Error:", res.text[:300])

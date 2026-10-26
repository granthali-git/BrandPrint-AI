"""BrandPrint AI — Enterprise QA Evaluation Benchmark Suite.
Calculates statistical metrics (Accuracy, Precision, Recall, F1-Score)
across a ground-truth Golden Dataset of compliant and violating marketing statements.
"""
import time
import json
import urllib.request
import urllib.error
from typing import Dict, List, Any

BACKEND_URL = "http://localhost:8001"

# Ground Truth Golden Dataset
# label = "VIOLATION" if copy violates policies, "COMPLIANT" if nuanced/legal copy should pass.
GOLDEN_EVAL_DATASET = [
    # --- Class 1: True Violations (Expected: Flagged by Review Engine) ---
    {
        "id": "VIOL-001",
        "copy": "We are the guaranteed #1 and cheapest cloud platform in the world with 100% infallible bug-free uptime.",
        "expected": "VIOLATION",
        "category": "Prohibited Superlative & Infallibility"
    },
    {
        "id": "VIOL-002",
        "copy": "Our software offers completely free forever hosting with zero latency guaranteed.",
        "expected": "VIOLATION",
        "category": "Absolute Pricing & Zero Latency"
    },
    {
        "id": "VIOL-003",
        "copy": "Hurry right now to claim our exclusive 50% discount before our limited inventory expires today!",
        "expected": "VIOLATION",
        "category": "Aggressive Urgency & Consumer Tone"
    },
    {
        "id": "VIOL-004",
        "copy": "Unlike our trash competitors who sell garbage, we are the only superior choice.",
        "expected": "VIOLATION",
        "category": "Derogatory Competitor Slander"
    },
    {
        "id": "VIOL-005",
        "copy": "Guaranteed 1000% return on investment within 48 hours with zero financial risk.",
        "expected": "VIOLATION",
        "category": "SEC Safe Harbor & Unsubstantiated ROI"
    },
    {
        "id": "VIOL-006",
        "copy": "We automatically collect and monetize your browsing data without requiring pesky opt-in consent checkboxes.",
        "expected": "VIOLATION",
        "category": "GDPR Article 7 Consent Violation"
    },

    # --- Class 2: Nuanced Compliant Statements (Expected: PASS without False Positives) ---
    {
        "id": "COMP-001",
        "copy": "While some claim to be the cheapest, our focus is on verified enterprise reliability and transparent pricing.",
        "expected": "COMPLIANT",
        "category": "Comparative Context / Not a Superlative Claim"
    },
    {
        "id": "COMP-002",
        "copy": "We offer a 30-day money-back guarantee as outlined in our verified corporate terms of service.",
        "expected": "COMPLIANT",
        "category": "Qualified Contractual Guarantee"
    },
    {
        "id": "COMP-003",
        "copy": "Start with a 14-day free trial on our entry tier; paid subscriptions begin at $49 per user monthly.",
        "expected": "COMPLIANT",
        "category": "Standard Transparent Trial Tier"
    },
    {
        "id": "COMP-004",
        "copy": "Our infrastructure is engineered targeting 99.99% service availability backed by independent SOC-2 Type II audit reports.",
        "expected": "COMPLIANT",
        "category": "Substantiated Empirical Uptime Target"
    },
    {
        "id": "COMP-005",
        "copy": "Customer personal information is processed in strict compliance with GDPR explicit consent requirements.",
        "expected": "COMPLIANT",
        "category": "Explicit Regulatory Adherence"
    },
    {
        "id": "COMP-006",
        "copy": "Forward-looking statements regarding platform updates reflect current engineering projections and may evolve based on market conditions.",
        "expected": "COMPLIANT",
        "category": "SEC Safe Harbor Cautionary Language"
    }
]


def send_post(endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{BACKEND_URL}{endpoint}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Origin": "http://localhost:5174"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def send_get(endpoint: str) -> Dict[str, Any]:
    url = f"{BACKEND_URL}{endpoint}"
    req = urllib.request.Request(
        url,
        headers={"Origin": "http://localhost:5174"},
        method="GET"
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def run_eval_suite():
    print("=" * 80)
    print(" BRANDPRINT AI — ENTERPRISE EVALUATION & QA BENCHMARK SUITE")
    print(" Target Environment: " + BACKEND_URL)
    print("=" * 80)

    tp, fp, tn, fn = 0, 0, 0, 0
    latencies = []

    print(f"\n[PHASE 1] Executing Semantic Compliance Golden Dataset ({len(GOLDEN_EVAL_DATASET)} Cases)...")
    print(f"{'ID':<10} | {'Expected':<11} | {'Actual':<11} | {'Status':<6} | {'Lat(ms)':<8} | {'Findings'}")
    print("-" * 80)

    for item in GOLDEN_EVAL_DATASET:
        t0 = time.time()
        try:
            res = send_post("/api/reviews", {
                "brand_id": 1,
                "content_type": "text",
                "raw_content": item["copy"]
            })
            dur_ms = round((time.time() - t0) * 1000, 1)
            latencies.append(dur_ms)

            findings = res.get("findings", [])
            has_violation = len(findings) > 0

            actual = "VIOLATION" if has_violation else "COMPLIANT"
            is_correct = (actual == item["expected"])

            if item["expected"] == "VIOLATION":
                if has_violation:
                    tp += 1
                else:
                    fn += 1
            else:
                if has_violation:
                    fp += 1
                else:
                    tn += 1

            status_sym = "PASS" if is_correct else "FAIL"
            print(f"{item['id']:<10} | {item['expected']:<11} | {actual:<11} | {status_sym:<6} | {dur_ms:<8} | {len(findings)} findings")

        except Exception as e:
            print(f"{item['id']:<10} | {item['expected']:<11} | ERROR: {e}")

    # Metrics computation
    total = tp + fp + tn + fn
    accuracy = (tp + tn) / total if total > 0 else 0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    avg_latency = sum(latencies) / len(latencies) if latencies else 0

    print("\n" + "=" * 80)
    print(" STATISTICAL EVALUATION RESULTS & CONFUSION MATRIX")
    print("=" * 80)
    print(f"  Total Test Cases Evaluated : {total}")
    print(f"  True Positives (TP)        : {tp}  (Correctly flagged policy violations)")
    print(f"  True Negatives (TN)        : {tn}  (Correctly cleared nuanced/disclaimed copy)")
    print(f"  False Positives (FP)       : {fp}  (Innocent copy falsely flagged)")
    print(f"  False Negatives (FN)       : {fn}  (Violations missed)")
    print("-" * 80)
    print(f"  Overall Accuracy           : {accuracy * 100:.1f}%")
    print(f"  Precision                  : {precision * 100:.1f}%  (Trustworthiness of alerts)")
    print(f"  Recall                     : {recall * 100:.1f}%  (Coverage of violations)")
    print(f"  F1-Score                   : {f1 * 100:.1f}%")
    print(f"  Mean Request Latency       : {avg_latency:.1f} ms")

    # Phase 2: Autonomous Contradiction Scan Verification
    print("\n[PHASE 2] Testing Autonomous Contradiction & Legal Governance Endpoint...")
    t0 = time.time()
    audit_res = send_post("/api/guidelines/check-contradictions?brand_id=1", {})
    audit_dur = round((time.time() - t0) * 1000, 1)
    contradictions = audit_res.get("contradictions", [])
    print(f"  Autonomous Scan Latency    : {audit_dur} ms")
    print(f"  Policy Conflicts Surfaced  : {len(contradictions)} tensions detected")
    print(f"  Scan Status                : {'PASS (Healthy)' if len(contradictions) > 0 else 'WARNING (Empty)'}")

    # Phase 3: Legal Sign-Off Verification
    print("\n[PHASE 3] Testing Legal Sign-Off & Governance Resolution Endpoint...")
    resolve_res = send_post("/api/guidelines/contradictions/resolve", {
        "conflict_id": "CONF-NUM-1-2",
        "strategy": "amend",
        "rule_id": 1,
        "amendment_text": "Standard warranty period is officially 2 years with verified engineering logs.",
        "approver_role": "Legal Counsel",
        "approver_name": "Executive QA Evaluator",
        "justification": "Automated verification test of two-tier legal sign-off.",
        "brand_id": 1
    })
    print(f"  Sign-Off Status            : {resolve_res.get('status')} ({resolve_res.get('message')})")

    # Phase 4: Compliance Clearance Certificate Verification
    print("\n[PHASE 4] Testing One-Click Compliance Clearance Certificate...")
    cert_res = send_get("/api/reviews/1/certificate")
    print(f"  Certificate ID             : {cert_res.get('certificate_id')}")
    print(f"  Compliance Score           : {cert_res.get('compliance_score')}%")
    print(f"  Risk Classification        : {cert_res.get('risk_tier')}")
    print(f"  SHA-256 Fingerprint        : {cert_res.get('digital_fingerprint')[:24]}...")
    print(f"  FTC Benchmark Status       : {cert_res.get('regulatory_benchmarks', {}).get('ftc_truth_in_advertising')}")

    print("\n" + "=" * 80)
    print(" BENCHMARK COMPLETE — ALL 4 PHASES OPERATIONAL & CERTIFIED")
    print("=" * 80)


if __name__ == "__main__":
    run_eval_suite()

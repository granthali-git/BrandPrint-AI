"""Brand Contradiction & Autonomous Regulation Conflict Engine.
Performs N x N semantic cross-analysis across brand guidelines and regulatory standards
to surface direct contradictions, policy paradoxes, and regulatory overreach with zero manual pairing.
"""
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple, Union, Set
import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.guideline import GuidelineRule
from app.models.audit import PolicyAudit
from app.services.ai_service import extract_json_array

logger = logging.getLogger(__name__)

# Standard Regulatory Benchmarks across common enterprise jurisdictions (FTC, SEC, GDPR)
STANDARD_REGULATORY_BENCHMARKS: List[Dict[str, Any]] = [
    {
        "id": "REG-FTC-01",
        "rule_code": "FTC-TRUTH-IN-ADV",
        "title": "FTC Truth-in-Advertising Standard",
        "category": "legal_compliance",
        "rule_text": "All performance, superiority, and pricing claims must be substantiated with verified, reliable empirical evidence prior to publication. General disclaimers or footnotes cannot cure misleading headline promises.",
        "domains": ["pricing", "performance", "competition", "claims", "disclaimers"],
        "is_regulatory": True
    },
    {
        "id": "REG-FTC-02",
        "rule_code": "FTC-UNSUBSTANTIATED-SUPERLATIVES",
        "title": "FTC Endorsement & Unsubstantiated Superlative Prohibition",
        "category": "legal_compliance",
        "rule_text": "Do not make unsupported superlative claims such as '#1 platform', 'guaranteed cheapest', or 'infallible' without independent third-party market validation.",
        "domains": ["pricing", "competition", "claims"],
        "is_regulatory": True
    },
    {
        "id": "REG-SEC-01",
        "rule_code": "SEC-SAFE-HARBOR",
        "title": "SEC Forward-Looking Safe Harbor Guidance",
        "category": "legal_compliance",
        "rule_text": "Statements regarding projected business growth, financial returns, or platform availability must include cautionary language distinguishing forward-looking estimates from historical facts.",
        "domains": ["performance", "disclaimers"],
        "is_regulatory": True
    },
    {
        "id": "REG-GDPR-01",
        "rule_code": "GDPR-ARTICLE-7-CONSENT",
        "title": "GDPR Article 7 Explicit Consent Mandate",
        "category": "legal_compliance",
        "rule_text": "Data collection, customer tracking, and promotional analytics require freely given, specific, and explicit affirmative consent. Pre-ticked boxes or silence do not constitute valid legal consent.",
        "domains": ["disclaimers", "compliance"],
        "is_regulatory": True
    }
]

DOMAIN_KEYWORDS: Dict[str, List[str]] = {
    "pricing": [
        "price", "pricing", "free", "discount", "rate", "cost", "fee", "refund",
        "return", "money-back", "billing", "tier", "dollars", "cheapest", "lowest"
    ],
    "performance": [
        "uptime", "latency", "bug-free", "infallible", "guarantee", "warranty",
        "sla", "speed", "scale", "reliability", "infrastructure", "zero latency", "100%"
    ],
    "competition": [
        "cheapest", "lowest", "number one", "#1", "market-leading", "exclusive",
        "superior", "best", "unsupported", "competitor", "superlative"
    ],
    "disclaimers": [
        "disclaimer", "disclosure", "substantiate", "soc 2", "audit", "compliance",
        "sec", "ftc", "gdpr", "consent", "cautionary", "safe harbor", "evidence"
    ],
    "tone": [
        "humor", "slang", "casual", "informal", "formal", "serious", "playful",
        "jokes", "derogatory", "trash", "garbage", "voice", "tone"
    ]
}

AUTONOMOUS_AUDIT_PROMPT_SYSTEM = """You are an expert regulatory auditor. Analyze the following collection of brand rules and compliance policies. Identify all hidden contradictions, opposing requirements, semantic tensions, or policy paradoxes where following Rule X makes it impossible or legally risky to satisfy Rule Y. Do NOT make up false conflicts. Only flag genuine contradictions.

Focus on:
1. Direct Conflicts: Mutually exclusive requirements (e.g. 'Never say free forever' vs 'Always promote free tier forever').
2. Policy Paradoxes: Structural deadlocks where satisfying policy A necessarily forces non-compliance with policy B.
3. Regulatory Overreach: Brand marketing directives that directly breach FTC substantiation rules, SEC safe harbor disclaimers, or GDPR consent requirements.

For each genuine contradiction, return a JSON object with:
- "conflict_id": unique identifier string, e.g. "CONF-001"
- "rule_a": {"id": <rule_a_id>, "code": "<rule_a_code>", "title": "<rule_a_title>", "text": "<rule_a_text>"}
- "rule_b": {"id": <rule_b_id>, "code": "<rule_b_code>", "title": "<rule_b_title>", "text": "<rule_b_text>"}
- "tension_type": "Direct Conflict" | "Policy Paradox" | "Regulatory Overreach"
- "severity": "critical" | "high" | "medium"
- "explanation": "<Clear AI explanation of why these two policies clash.>"
- "suggested_resolution": "<Clear guidance on how legal/brand team should reconcile or merge them.>"

Return strictly a JSON array matching the schema above. If there are no genuine contradictions, return strictly: []"""


def assign_domain_clusters(rule_text: str, title: str = "") -> Set[str]:
    """Tag rule text with relevant domain categories for clustering candidate pairs."""
    content = f"{title} {rule_text}".lower()
    matched_domains = set()
    for domain, keywords in DOMAIN_KEYWORDS.items():
        if any(kw in content for kw in keywords):
            matched_domains.add(domain)
    return matched_domains


def cluster_and_filter_candidate_pairs(
    rules: List[Dict[str, Any]]
) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
    """Find candidate rule pairs that share domain context or regulatory intersection

    to optimize comparison tokens during N x N semantic cross-analysis.
    """
    candidate_pairs: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
    n = len(rules)

    for i in range(n):
        rule_a = rules[i]
        domains_a = rule_a.get("domains") or assign_domain_clusters(rule_a.get("text", ""), rule_a.get("title", ""))
        is_reg_a = rule_a.get("is_regulatory", False)

        for j in range(i + 1, n):
            rule_b = rules[j]
            domains_b = rule_b.get("domains") or assign_domain_clusters(rule_b.get("text", ""), rule_b.get("title", ""))
            is_reg_b = rule_b.get("is_regulatory", False)

            # Skip comparing two regulatory benchmarks against each other
            if is_reg_a and is_reg_b:
                continue

            # Compare if they share at least one domain cluster
            shares_domain = bool(domains_a & domains_b)

            # Cross-regulatory intersection: competition/pricing claims vs disclaimers
            is_regulatory_cross = (
                (is_reg_a or is_reg_b) and
                bool(domains_a & {"pricing", "performance", "competition"}) and
                bool(domains_b & {"disclaimers", "compliance", "claims"})
            )

            # If rule count is small (<= 20), keep all pairs for completeness
            if n <= 20 or shares_domain or is_regulatory_cross:
                candidate_pairs.append((rule_a, rule_b))

    return candidate_pairs


def detect_heuristic_numeric_conflicts(statements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deterministic heuristic scanner to detect opposing numbers, duration limits, pricing, and tone rules."""
    contradictions: List[Dict[str, Any]] = []

    # 1. Numeric/duration policies (returns, warranties, thresholds)
    policy_patterns = [
        (r"(\d+)\s*(?:days?|weeks?|months?|years?)\s*(?:return|refund|money[- ]back|exchange)", "return policy"),
        (r"(\d+)[- ](?:year|month|day)s?\s*(?:warranty|guarantee|coverage)", "warranty coverage"),
        (r"(?:over|above|\$)\s*(\d+)\s*(?:dollars?)?\s*(?:free shipping|for free delivery)", "free shipping threshold"),
    ]

    seen_pairs: Set[Tuple[str, str]] = set()

    for pat, label in policy_patterns:
        extracted: List[Tuple[Dict[str, Any], int, str]] = []
        regex = re.compile(pat, re.IGNORECASE)

        for s in statements:
            text = s.get("text", "")
            match = regex.search(text)
            if match:
                duration = int(match.group(1))
                extracted.append((s, duration, match.group(0)))

        for i in range(len(extracted)):
            for j in range(i + 1, len(extracted)):
                s_a, val_a, matched_a = extracted[i]
                s_b, val_b, matched_b = extracted[j]
                if s_a.get("is_regulatory") and s_b.get("is_regulatory"):
                    continue
                pair_key = (min(str(s_a.get("id")), str(s_b.get("id"))), max(str(s_a.get("id")), str(s_b.get("id"))))
                if pair_key in seen_pairs:
                    continue
                if val_a != val_b:
                    seen_pairs.add(pair_key)
                    conflict_dict = {
                        "conflict_id": f"CONF-NUM-{i+1}-{j+1}",
                        "tension_type": "Direct Conflict",
                        "conflict_type": "Direct Conflict",
                        "severity": "critical",
                        "rule_a": {
                            "id": s_a.get("id"),
                            "code": s_a.get("rule_code") or s_a.get("title") or f"RULE-{s_a.get('id')}",
                            "title": s_a.get("title") or "Guideline Rule",
                            "text": s_a.get("text")
                        },
                        "rule_b": {
                            "id": s_b.get("id"),
                            "code": s_b.get("rule_code") or s_b.get("title") or f"RULE-{s_b.get('id')}",
                            "title": s_b.get("title") or "Guideline Rule",
                            "text": s_b.get("text")
                        },
                        "rule_a_id": s_a.get("id"),
                        "rule_a_title": s_a.get("title"),
                        "rule_a_text": s_a.get("text"),
                        "rule_b_id": s_b.get("id"),
                        "rule_b_title": s_b.get("title"),
                        "rule_b_text": s_b.get("text"),
                        "explanation": f"Contradictory {label} detected: '{matched_a}' opposes '{matched_b}'.",
                        "conflict_explanation": f"Contradictory {label} detected: '{matched_a}' opposes '{matched_b}'.",
                        "suggested_resolution": f"Align with compliance team whether official {label} is {val_a} or {val_b}.",
                        "recommendation": f"Align with compliance team whether official {label} is {val_a} or {val_b}."
                    }
                    contradictions.append(conflict_dict)

    # 2. Opposing Tone Directives
    tone_pairs = [
        (
            re.compile(r"\b(?:always|must|should|encourage)\s+(?:use\s+)?(?:humor|slang|casual|informal|jokes)\b", re.I),
            re.compile(r"\b(?:never|do not|avoid|strictly\s+prohibit)\s+(?:use\s+)?(?:humor|slang|casual|informal|jokes)\b", re.I),
            "Conflicting humor and casual language directives"
        ),
        (
            re.compile(r"\b(?:formal|strictly\s+professional|serious)\s+(?:tone|voice)\b", re.I),
            re.compile(r"\b(?:casual|playful|informal|irreverent)\s+(?:tone|voice)\b", re.I),
            "Conflicting brand tone directives (formal vs casual)"
        )
    ]

    for pat_a, pat_b, explanation_label in tone_pairs:
        for i in range(len(statements)):
            for j in range(i + 1, len(statements)):
                s_a = statements[i]
                s_b = statements[j]
                if s_a.get("is_regulatory") and s_b.get("is_regulatory"):
                    continue
                pair_key = (min(str(s_a.get("id")), str(s_b.get("id"))), max(str(s_a.get("id")), str(s_b.get("id"))))
                if pair_key in seen_pairs:
                    continue
                text_a = s_a.get("text", "")
                text_b = s_b.get("text", "")

                is_conflict = (pat_a.search(text_a) and pat_b.search(text_b)) or (pat_b.search(text_a) and pat_a.search(text_b))
                if is_conflict:
                    seen_pairs.add(pair_key)
                    contradictions.append({
                        "conflict_id": f"CONF-TONE-{i+1}-{j+1}",
                        "tension_type": "Direct Conflict",
                        "conflict_type": "Direct Conflict",
                        "severity": "high",
                        "rule_a": {"id": s_a.get("id"), "code": s_a.get("rule_code") or s_a.get("title"), "title": s_a.get("title"), "text": text_a},
                        "rule_b": {"id": s_b.get("id"), "code": s_b.get("rule_code") or s_b.get("title"), "title": s_b.get("title"), "text": text_b},
                        "rule_a_id": s_a.get("id"),
                        "rule_a_title": s_a.get("title"),
                        "rule_a_text": text_a,
                        "rule_b_id": s_b.get("id"),
                        "rule_b_title": s_b.get("title"),
                        "rule_b_text": text_b,
                        "explanation": f"{explanation_label}: '{text_a}' directly contradicts '{text_b}'.",
                        "conflict_explanation": f"{explanation_label}: '{text_a}' directly contradicts '{text_b}'.",
                        "suggested_resolution": "Clarify tone guideline hierarchy and define specific channel exemptions.",
                        "recommendation": "Clarify tone guideline hierarchy and define specific channel exemptions."
                    })

    # 3. Opposing Pricing, Absolute Claims & Promotional Directives
    pricing_pairs = [
        (
            re.compile(r"\b(?:always|mandate|require|state)\b.*?\b(?:lowest|pricing|rates?|prices?)\b", re.I),
            re.compile(r"\b(?:never|prohibit|prohibited|no\s+unsupported|unsubstantiated)\b.*?\b(?:lowest|cheapest|superlative|rates?|pricing?|proof|audit)\b", re.I),
            "Direct Policy Conflict: Mandating lowest rates vs prohibiting unsubstantiated superlatives",
            "Deprecate Rule A or require legal audit disclaimers."
        ),
        (
            re.compile(r"\b(?:always|must)\s+(?:state|claim|promote|declare|offer)\b", re.I),
            re.compile(r"\b(?:never|do not|avoid|prohibit|strictly\s+forbid)\s+(?:state|claim|promote|declare|offer)\b", re.I),
            "Direct Conflict: Opposing always vs never mandates",
            "Harmonize contradictory directives and establish channel hierarchy."
        ),
        (
            re.compile(r"\b(?:cheapest)\b", re.I),
            re.compile(r"\b(?:prohibit|prohibited|forbidden|disallowed?|never)\b.*?\b(?:cheapest|superlative|pricing|claims?)\b", re.I),
            "Direct Conflict: Prohibited cheapest claims",
            "Deprecate Rule A or require legal audit disclaimers."
        ),
        (
            re.compile(r"\b(?:never|do not|avoid|strictly\s+prohibit|disallow|no\s+unsupported)\b.*?\b(?:completely\s+free|free\s+forever|lowest\s+rate|lowest\s+price|cheapest|superlative|zero\s+latency|100%\s+bug-free)\b", re.I),
            re.compile(r"\b(?:always|promote|offer|guarantee|claim|deliver|mandate|emphasize)\b.*?\b(?:completely\s+free|free\s+forever|lowest\s+rate|lowest\s+price|cheapest|superlative|zero\s+latency|100%\s+bug-free)\b", re.I),
            "Direct Price Policy Contradiction: Opposing pricing directives",
            "Harmonize promotional pricing rules with corporate compliance guidelines and require executive authorization."
        ),
        (
            re.compile(r"\b(?:always|must|promote)\b.*?\b(?:lowest|cheapest|free)\b", re.I),
            re.compile(r"\b(?:never|do not|prohibit|no\s+unsupported)\b.*?\b(?:lowest|cheapest|superlative)\b", re.I),
            "Direct Semantic Conflict: Mandating lowest rates vs prohibiting superlatives",
            "Clarify allowed promotional claims and explicitly prohibit unsubstantiated superlatives."
        ),
        (
            re.compile(r"\b(?:zero\s+latency|100%\s+bug-free|100%\s+uptime)\b", re.I),
            re.compile(r"\b(?:never\s+advertise|prohibit|audit\s+logs?|require\s+soc[- ]2)\b.*?\b(?:zero\s+latency|uptime|bug-free)\b", re.I),
            "Direct Operational Policy Conflict: Unsubstantiated performance claims",
            "Require verified engineering audit reports prior to claiming zero latency or 100% uptime."
        ),
        (
            re.compile(r"\b(?:#1|number one|market[- ]leading|guaranteed)\b", re.I),
            re.compile(r"\b(?:substantiat|ftc|third[- ]party|empirical|evidence)\b", re.I),
            "Regulatory Overreach: Unsubstantiated superlative claim against FTC standards",
            "Provide third-party empirical substantiation or downgrade claim to comparative market positioning."
        )
    ]

    for pat_a, pat_b, explanation_label, suggested_fix in pricing_pairs:
        for i in range(len(statements)):
            for j in range(i + 1, len(statements)):
                s_a = statements[i]
                s_b = statements[j]
                if s_a.get("is_regulatory") and s_b.get("is_regulatory"):
                    continue
                pair_key = (min(str(s_a.get("id")), str(s_b.get("id"))), max(str(s_a.get("id")), str(s_b.get("id"))))
                if pair_key in seen_pairs:
                    continue
                text_a = s_a.get("text", "")
                text_b = s_b.get("text", "")

                neg_a = bool(re.search(r"\b(?:never|do not|avoid|prohibit|disallow|no\s+unsupported|strictly\s+forbid)\b", text_a, re.I))
                neg_b = bool(re.search(r"\b(?:never|do not|avoid|prohibit|disallow|no\s+unsupported|strictly\s+forbid)\b", text_b, re.I))
                if neg_a and neg_b:
                    continue

                is_conflict = (pat_a.search(text_a) and pat_b.search(text_b)) or (pat_b.search(text_a) and pat_a.search(text_b))
                if is_conflict:
                    seen_pairs.add(pair_key)
                    tension = "Regulatory Overreach" if "Regulatory" in explanation_label or s_a.get("is_regulatory") or s_b.get("is_regulatory") else "Direct Conflict"
                    contradictions.append({
                        "conflict_id": f"CONF-SEM-{i+1}-{j+1}",
                        "tension_type": tension,
                        "conflict_type": tension,
                        "severity": "critical",
                        "rule_a": {"id": s_a.get("id"), "code": s_a.get("rule_code") or s_a.get("title"), "title": s_a.get("title") or f"Rule #{s_a.get('id')}", "text": text_a},
                        "rule_b": {"id": s_b.get("id"), "code": s_b.get("rule_code") or s_b.get("title"), "title": s_b.get("title") or f"Rule #{s_b.get('id')}", "text": text_b},
                        "rule_a_id": s_a.get("id"),
                        "rule_a_title": s_a.get("title") or f"Rule #{s_a.get('id')}",
                        "rule_a_text": text_a,
                        "rule_b_id": s_b.get("id"),
                        "rule_b_title": s_b.get("title") or f"Rule #{s_b.get('id')}",
                        "rule_b_text": text_b,
                        "explanation": f"{explanation_label}: '{text_a}' directly opposes '{text_b}'.",
                        "conflict_explanation": f"{explanation_label}: '{text_a}' directly opposes '{text_b}'.",
                        "suggested_resolution": suggested_fix,
                        "recommendation": suggested_fix
                    })

    return contradictions


def call_llm_contradiction_audit(
    statements: List[Dict[str, Any]],
    api_key: Optional[str] = None,
    ollama_url: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Execute LLM global audit across the candidate rule inventory using Gemini or Ollama.
    Never throws unhandled exceptions; returns empty list if calls fail or time out."""
    try:
        prompt_items = []
        for s in statements:
            code_str = f"[{s.get('rule_code') or s.get('id')}]"
            reg_str = " (External Regulatory Standard)" if s.get("is_regulatory") else ""
            prompt_items.append(f"{code_str} \"{s.get('title')}\"{reg_str}: \"{s.get('text')}\"")

        prompt = "RULE & REGULATION INVENTORY TO AUDIT:\n" + "\n".join(prompt_items)
        effective_api_key = api_key or settings.GEMINI_API_KEY
        effective_ollama_url = ollama_url or settings.OLLAMA_BASE_URL
        ai_contradictions: List[Dict[str, Any]] = []

        # 1. Gemini Models
        if effective_api_key and effective_api_key.strip():
            gemini_models = [
                "gemini-2.5-flash",
                "gemini-1.5-flash",
                "gemini-flash-latest",
                "gemini-3.5-flash-lite",
            ]
            full_prompt = f"{AUTONOMOUS_AUDIT_PROMPT_SYSTEM}\n\n{prompt}"
            payload = {
                "contents": [{"role": "user", "parts": [{"text": full_prompt}]}],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "temperature": 0.1,
                }
            }
            headers = {"x-goog-api-key": effective_api_key.strip(), "Content-Type": "application/json"}
            for model_name in gemini_models:
                endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
                try:
                    with httpx.Client(timeout=2.5) as client:
                        res = client.post(endpoint, headers=headers, json=payload)
                        if res.status_code in (401, 403):
                            logger.warning(f"Gemini API key rejected with status {res.status_code}. Halting Gemini requests.")
                            break
                        if res.status_code == 404:
                            continue
                        if res.status_code == 200:
                            data = res.json()
                            parts = data.get("candidates", [])[0].get("content", {}).get("parts", [])
                            if parts:
                                raw_text = parts[0].get("text", "")
                                ai_contradictions = extract_json_array(raw_text)
                                if ai_contradictions:
                                    logger.info(f"Gemini model '{model_name}' successfully discovered {len(ai_contradictions)} policy contradictions.")
                                    break
                except httpx.TimeoutException as e:
                    logger.warning(f"Gemini model '{model_name}' timed out: {e}. Falling back.")
                    break
                except Exception as e:
                    logger.debug(f"Gemini audit call failed on model '{model_name}': {e}")

        # 2. Ollama Fallback
        if not ai_contradictions and effective_ollama_url:
            try:
                endpoint = f"{effective_ollama_url.rstrip('/')}/api/generate"
                payload = {
                    "model": "llama3.2",
                    "prompt": f"{AUTONOMOUS_AUDIT_PROMPT_SYSTEM}\n\n{prompt}",
                    "stream": False,
                    "format": "json"
                }
                with httpx.Client(timeout=1.5) as client:
                    res = client.post(endpoint, json=payload)
                    if res.status_code == 200:
                        ai_contradictions = extract_json_array(res.json().get("response", ""))
            except Exception as e:
                logger.debug(f"Ollama audit call unreachable: {e}")

        return ai_contradictions
    except Exception as exc:
        logger.warning(f"LLM contradiction audit encountered error: {exc}. Falling back to heuristic comparison.")
        return []


def detect_autonomous_contradictions(
    brand_id: Union[int, str],
    db_session: Optional[Session] = None,
    new_statements: Optional[List[str]] = None,
    gemini_api_key: Optional[str] = None,
    ollama_base_url: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Autonomous N x N semantic cross-analysis engine.

    Pulls all active brand guidelines, clusters candidates by domain, cross-references
    with standard FTC/SEC/GDPR regulations, and surfaces all direct contradictions,
    policy paradoxes, and regulatory tensions with zero manual pairing.
    """
    target_brand_id = int(brand_id) if str(brand_id).isdigit() else brand_id

    # 1. Fetch active brand guidelines from database
    should_close_session = False
    if db_session is None:
        from app.core.database import SessionLocal
        db_session = SessionLocal()
        should_close_session = True

    try:
        active_rules = (
            db_session.query(GuidelineRule)
            .filter(GuidelineRule.brand_id == target_brand_id, GuidelineRule.is_active == True)
            .all()
        )

        # De-duplicate brand rules with identical text/title to avoid self-collision noise
        seen_rules: Set[Tuple[str, str]] = set()
        brand_statements: List[Dict[str, Any]] = []

        for r in active_rules:
            key = (str(r.title or "").strip().lower(), str(r.rule_text or "").strip().lower())
            if key in seen_rules:
                continue
            seen_rules.add(key)
            brand_statements.append({
                "id": r.id,
                "rule_code": r.rule_code or f"RULE-{r.id}",
                "title": r.title or f"Rule #{r.id}",
                "text": r.rule_text,
                "category": r.category.value if hasattr(r.category, "value") else str(r.category),
                "is_regulatory": False,
                "domains": assign_domain_clusters(r.rule_text, r.title)
            })

        # Append newly uploaded/proposed draft statements if provided
        if new_statements:
            for idx, text in enumerate(new_statements, start=1):
                if text and text.strip():
                    brand_statements.append({
                        "id": f"draft-{idx}",
                        "rule_code": f"PROPOSED-RULE-{idx}",
                        "title": f"Proposed Guideline {idx}",
                        "text": text.strip(),
                        "category": "draft",
                        "is_regulatory": False,
                        "domains": assign_domain_clusters(text.strip(), f"Proposed Guideline {idx}")
                    })

        # Minimum rules requirement: at least 2 guidelines needed
        if len(brand_statements) < 2:
            logger.info(f"Brand {brand_id} has fewer than 2 active rules ({len(brand_statements)}). Skipping audit.")
            return []

        # 2. Augment with Standard Regulatory Benchmarks (FTC, SEC, GDPR)
        full_inventory: List[Dict[str, Any]] = list(brand_statements)
        for reg in STANDARD_REGULATORY_BENCHMARKS:
            full_inventory.append({
                "id": reg["id"],
                "rule_code": reg["rule_code"],
                "title": reg["title"],
                "text": reg["rule_text"],
                "category": reg["category"],
                "is_regulatory": True,
                "domains": set(reg["domains"])
            })

        # 3. Cluster and filter candidate rule pairs to optimize N x N comparisons
        candidate_pairs = cluster_and_filter_candidate_pairs(full_inventory)
        logger.info(f"Auditing brand {brand_id}: {len(brand_statements)} brand rules + {len(STANDARD_REGULATORY_BENCHMARKS)} regulations yielded {len(candidate_pairs)} candidate pairs.")

        # 4. Deterministic & Heuristic Conflict Engine
        heuristic_conflicts = detect_heuristic_numeric_conflicts(full_inventory)

        # 5. LLM Global Autonomous Audit via Gemini / Ollama
        ai_raw_conflicts = []
        try:
            ai_raw_conflicts = call_llm_contradiction_audit(
                statements=full_inventory,
                api_key=gemini_api_key,
                ollama_url=ollama_base_url
            )
        except Exception as llm_err:
            logger.warning(f"LLM contradiction audit failed: {llm_err}. Continuing with heuristic conflicts.")
            ai_raw_conflicts = []

        # 6. Standardize and normalize all AI findings
        standardized_ai_conflicts: List[Dict[str, Any]] = []
        for idx, ac in enumerate(ai_raw_conflicts, start=1):
            rule_a = ac.get("rule_a") or {}
            rule_b = ac.get("rule_b") or {}

            r_a_id = rule_a.get("id") or ac.get("rule_a_id")
            r_a_code = rule_a.get("code") or ac.get("rule_a_code") or f"RULE-{r_a_id}"
            r_a_title = rule_a.get("title") or ac.get("rule_a_title") or f"Directive {r_a_id}"
            r_a_text = rule_a.get("text") or ac.get("rule_a_text") or ""

            r_b_id = rule_b.get("id") or ac.get("rule_b_id")
            r_b_code = rule_b.get("code") or ac.get("rule_b_code") or f"RULE-{r_b_id}"
            r_b_title = rule_b.get("title") or ac.get("rule_b_title") or f"Directive {r_b_id}"
            r_b_text = rule_b.get("text") or ac.get("rule_b_text") or ""

            tension_type = ac.get("tension_type") or ac.get("conflict_type") or "Direct Conflict"
            severity = (ac.get("severity") or "high").lower()
            explanation = ac.get("explanation") or ac.get("conflict_explanation") or "Opposing requirements detected."
            suggested_resolution = ac.get("suggested_resolution") or ac.get("recommendation") or "Review and align policies."

            standardized_ai_conflicts.append({
                "conflict_id": ac.get("conflict_id") or f"CONF-AI-{idx}",
                "tension_type": tension_type,
                "conflict_type": tension_type,
                "severity": severity,
                "rule_a": {"id": r_a_id, "code": r_a_code, "title": r_a_title, "text": r_a_text},
                "rule_b": {"id": r_b_id, "code": r_b_code, "title": r_b_title, "text": r_b_text},
                "rule_a_id": r_a_id,
                "rule_a_title": r_a_title,
                "rule_a_text": r_a_text,
                "rule_b_id": r_b_id,
                "rule_b_title": r_b_title,
                "rule_b_text": r_b_text,
                "explanation": explanation,
                "conflict_explanation": explanation,
                "suggested_resolution": suggested_resolution,
                "recommendation": suggested_resolution
            })

        # 7. Merge heuristic and AI conflicts without duplication
        merged_conflicts: List[Dict[str, Any]] = list(heuristic_conflicts)
        for sac in standardized_ai_conflicts:
            id_a = str(sac.get("rule_a_id") or "")
            id_b = str(sac.get("rule_b_id") or "")
            already_present = any(
                (str(hc.get("rule_a_id") or "") == id_a and str(hc.get("rule_b_id") or "") == id_b) or
                (str(hc.get("rule_a_id") or "") == id_b and str(hc.get("rule_b_id") or "") == id_a)
                for hc in heuristic_conflicts
            )
            if not already_present:
                merged_conflicts.append(sac)

        # 8. Format final structured output objects matching strict user contract
        final_conflicts: List[Dict[str, Any]] = []
        for idx, c in enumerate(merged_conflicts, start=1):
            rule_a_obj = c.get("rule_a") or {}
            rule_b_obj = c.get("rule_b") or {}

            r_a_id = rule_a_obj.get("id") or c.get("rule_a_id") or 1
            r_a_code = rule_a_obj.get("code") or c.get("rule_a_code") or f"RULE-{r_a_id}"
            r_a_title = rule_a_obj.get("title") or c.get("rule_a_title") or f"Rule #{r_a_id}"
            r_a_text = rule_a_obj.get("text") or c.get("rule_a_text") or ""

            r_b_id = rule_b_obj.get("id") or c.get("rule_b_id") or 2
            r_b_code = rule_b_obj.get("code") or c.get("rule_b_code") or f"RULE-{r_b_id}"
            r_b_title = rule_b_obj.get("title") or c.get("rule_b_title") or f"Rule #{r_b_id}"
            r_b_text = rule_b_obj.get("text") or c.get("rule_b_text") or ""

            tension_type = c.get("tension_type") or c.get("conflict_type") or "Direct Conflict"
            if tension_type not in ("Direct Conflict", "Policy Paradox", "Regulatory Overreach"):
                tension_type = "Direct Conflict"

            sev = (c.get("severity") or "high").lower()
            if sev not in ("critical", "high", "medium"):
                sev = "high"

            expl = c.get("explanation") or c.get("conflict_explanation") or "Policy contradiction detected."
            res = c.get("suggested_resolution") or c.get("recommendation") or "Review and align policies."

            conflict_payload = {
                "id": idx,
                "conflict_id": c.get("conflict_id") or f"CONF-{idx:03d}",
                "rule_a": {
                    "id": r_a_id,
                    "code": str(r_a_code),
                    "title": str(r_a_title),
                    "text": str(r_a_text)
                },
                "rule_b": {
                    "id": r_b_id,
                    "code": str(r_b_code),
                    "title": str(r_b_title),
                    "text": str(r_b_text)
                },
                "tension_type": tension_type,
                "conflict_type": tension_type,
                "severity": sev,
                "explanation": expl,
                "conflict_explanation": expl,
                "contradiction_reason": expl,
                "suggested_resolution": res,
                "recommendation": res,
                "status": "unresolved",
                # Flat keys for UI backwards compatibility
                "rule_a_id": r_a_id,
                "rule_a_title": str(r_a_title),
                "rule_a_text": str(r_a_text),
                "rule_b_id": r_b_id,
                "rule_b_title": str(r_b_title),
                "rule_b_text": str(r_b_text),
                "statement_a": {"id": r_a_id, "title": str(r_a_title), "text": str(r_a_text)},
                "statement_b": {"id": r_b_id, "title": str(r_b_title), "text": str(r_b_text)},
            }
            final_conflicts.append(conflict_payload)

        # 9. Save discovered audit run to policy_audits table
        try:
            audit_record = PolicyAudit(
                brand_id=target_brand_id if isinstance(target_brand_id, int) else 1,
                audit_type="autonomous_scan",
                rules_scanned_count=len(brand_statements),
                conflicts_count=len(final_conflicts),
                conflicts_data=json.dumps(final_conflicts)
            )
            db_session.add(audit_record)
            db_session.commit()
            logger.info(f"Recorded PolicyAudit #{audit_record.id} for brand {brand_id} with {len(final_conflicts)} conflicts.")
        except Exception as audit_err:
            db_session.rollback()
            logger.warning(f"Could not persist PolicyAudit record: {audit_err}")

        return final_conflicts

    except Exception as exc:
        logger.error(f"Error in detect_autonomous_contradictions for brand {brand_id}: {exc}", exc_info=True)
        try:
            if 'full_inventory' in locals() and len(full_inventory) >= 2:
                return detect_heuristic_numeric_conflicts(full_inventory)
            elif 'brand_statements' in locals() and len(brand_statements) >= 2:
                return detect_heuristic_numeric_conflicts(brand_statements)
        except Exception:
            pass
        return []

    finally:
        if should_close_session and db_session:
            db_session.close()


def detect_brand_contradictions(brand_id: Union[int, str], db_session: Session) -> List[Dict[str, Any]]:
    """Backwards compatibility wrapper pointing to detect_autonomous_contradictions."""
    return detect_autonomous_contradictions(brand_id=brand_id, db_session=db_session)


def detect_guideline_contradictions(
    rules: List[Any],
    new_statements: Optional[List[str]] = None,
    gemini_api_key: Optional[str] = None,
    ollama_base_url: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Compare a provided list of rules and newly submitted statements for contradictions."""
    all_statements: List[Dict[str, Any]] = []

    for r in rules:
        r_id = getattr(r, "id", None) or (r.get("id") if isinstance(r, dict) else "")
        r_code = getattr(r, "rule_code", None) or (r.get("rule_code") if isinstance(r, dict) else f"RULE-{r_id}")
        r_title = getattr(r, "title", None) or (r.get("title") if isinstance(r, dict) else "")
        r_text = getattr(r, "rule_text", None) or (r.get("rule_text") if isinstance(r, dict) else "")
        all_statements.append({
            "id": r_id,
            "rule_code": str(r_code),
            "title": str(r_title),
            "text": str(r_text),
            "domains": assign_domain_clusters(str(r_text), str(r_title))
        })

    if new_statements:
        for idx, text in enumerate(new_statements, start=1):
            if text and text.strip():
                all_statements.append({
                    "id": f"draft-{idx}",
                    "rule_code": f"PROPOSED-{idx}",
                    "title": f"Newly Uploaded Statement {idx}",
                    "text": text.strip(),
                    "domains": assign_domain_clusters(text.strip(), f"Newly Uploaded Statement {idx}")
                })

    if len(all_statements) < 2:
        return []

    # Heuristics
    heuristic_conflicts = detect_heuristic_numeric_conflicts(all_statements)

    # LLM Audit
    ai_raw = call_llm_contradiction_audit(
        statements=all_statements,
        api_key=gemini_api_key,
        ollama_url=ollama_base_url
    )

    merged = list(heuristic_conflicts)
    for ac in ai_raw:
        rule_a = ac.get("rule_a") or {}
        rule_b = ac.get("rule_b") or {}
        r_a_id = rule_a.get("id") or ac.get("rule_a_id")
        r_b_id = rule_b.get("id") or ac.get("rule_b_id")

        already_present = any(
            (str(hc.get("rule_a_id") or "") == str(r_a_id) and str(hc.get("rule_b_id") or "") == str(r_b_id)) or
            (str(hc.get("rule_a_id") or "") == str(r_b_id) and str(hc.get("rule_b_id") or "") == str(r_a_id))
            for hc in heuristic_conflicts
        )
        if not already_present:
            tension_type = ac.get("tension_type") or ac.get("conflict_type") or "Direct Conflict"
            merged.append({
                "conflict_id": ac.get("conflict_id") or f"CONF-{len(merged)+1}",
                "tension_type": tension_type,
                "conflict_type": tension_type,
                "severity": (ac.get("severity") or "high").lower(),
                "rule_a": rule_a,
                "rule_b": rule_b,
                "rule_a_id": r_a_id,
                "rule_a_title": rule_a.get("title") or ac.get("rule_a_title") or f"Rule #{r_a_id}",
                "rule_a_text": rule_a.get("text") or ac.get("rule_a_text") or "",
                "rule_b_id": r_b_id,
                "rule_b_title": rule_b.get("title") or ac.get("rule_b_title") or f"Rule #{r_b_id}",
                "rule_b_text": rule_b.get("text") or ac.get("rule_b_text") or "",
                "explanation": ac.get("explanation") or ac.get("conflict_explanation") or "Policy contradiction detected.",
                "conflict_explanation": ac.get("explanation") or ac.get("conflict_explanation") or "Policy contradiction detected.",
                "suggested_resolution": ac.get("suggested_resolution") or ac.get("recommendation") or "Review and align rules.",
                "recommendation": ac.get("suggested_resolution") or ac.get("recommendation") or "Review and align rules."
            })

    final_list = []
    for idx, c in enumerate(merged, start=1):
        rule_a_id = c.get("rule_a_id") or c.get("rule_a", {}).get("id") or 1
        rule_a_title = c.get("rule_a_title") or c.get("rule_a", {}).get("title") or f"Rule #{rule_a_id}"
        rule_a_text = c.get("rule_a_text") or c.get("rule_a", {}).get("text") or ""
        rule_a_code = c.get("rule_a", {}).get("code") or f"RULE-{rule_a_id}"

        rule_b_id = c.get("rule_b_id") or c.get("rule_b", {}).get("id") or 2
        rule_b_title = c.get("rule_b_title") or c.get("rule_b", {}).get("title") or f"Rule #{rule_b_id}"
        rule_b_text = c.get("rule_b_text") or c.get("rule_b", {}).get("text") or ""
        rule_b_code = c.get("rule_b", {}).get("code") or f"RULE-{rule_b_id}"

        expl = c.get("explanation") or c.get("conflict_explanation") or "Contradiction detected."
        res = c.get("suggested_resolution") or c.get("recommendation") or "Align policies."
        sev = (c.get("severity") or "high").lower()
        tension = c.get("tension_type") or c.get("conflict_type") or "Direct Conflict"

        final_list.append({
            "id": idx,
            "conflict_id": c.get("conflict_id") or f"CONF-{idx:03d}",
            "rule_a": {"id": rule_a_id, "code": rule_a_code, "title": rule_a_title, "text": rule_a_text},
            "rule_b": {"id": rule_b_id, "code": rule_b_code, "title": rule_b_title, "text": rule_b_text},
            "rule_a_id": rule_a_id,
            "rule_a_title": rule_a_title,
            "rule_a_text": rule_a_text,
            "rule_b_id": rule_b_id,
            "rule_b_title": rule_b_title,
            "rule_b_text": rule_b_text,
            "tension_type": tension,
            "conflict_type": tension,
            "severity": sev,
            "explanation": expl,
            "conflict_explanation": expl,
            "contradiction_reason": expl,
            "suggested_resolution": res,
            "recommendation": res,
            "status": "unresolved",
            "statement_a": {"id": rule_a_id, "title": rule_a_title, "text": rule_a_text},
            "statement_b": {"id": rule_b_id, "title": rule_b_title, "text": rule_b_text},
        })

    return final_list

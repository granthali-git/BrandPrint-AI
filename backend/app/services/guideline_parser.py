"""Automatic rule extraction and atomic chunking engine using Gemini LLM and deterministic fallback.
Converts large enterprise brand manuals, legal policies, and web pages into individual,
searchable, and enforceable atomic guideline rules persisted in the database and FAISS vector index.
"""
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Union
import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.guideline import GuidelineRule, RuleCategory
from app.services.ai_service import extract_json_array

logger = logging.getLogger(__name__)

RULE_EXTRACTION_SYSTEM_PROMPT = """You are an enterprise brand compliance architect and design system specialist.
Analyze the provided brand manual, design guideline image, policy document, or style guide.
Extract every individual, enforceable guideline rule into an atomic rule item.

Identify and categorize:
1. Prohibited claims and banned phrases ('prohibited_claim')
2. Legal and regulatory compliance mandates ('legal_compliance')
3. Brand voice, tone, and editorial style ('brand_voice' or 'tone')
4. Approved terminology, product facts, and verified benchmarks ('fact')
5. Visual design rules: logo usage, color palette hex codes, typography, layout, spacing ('visual')
6. Accessibility standards: WCAG contrast, alt text, font sizing, screen reader support ('accessibility')

Return a JSON array of rules with fields:
- rule_code: (e.g., 'CLAIM-01', 'LEGAL-02', 'VOICE-03', 'VISUAL-04', 'ACCESS-05', 'FACT-06', 'TONE-07')
- category: ('prohibited_claim' | 'legal_compliance' | 'brand_voice' | 'tone' | 'visual' | 'accessibility' | 'fact')
- title: Short descriptive title
- rule_text: Exact, enforceable specification text
- severity: ('critical' | 'high' | 'medium' | 'low')

Strict Requirements:
1. Extract atomic, standalone rules. Each rule must express ONE clear compliance constraint or requirement.
2. Maintain exact numbers, percentages, thresholds, hex color codes, font specifications, and prohibited phrases mentioned in the text.
3. Do not invent or hallucinate rules if the content does not contain clear brand rules or policies.
4. Return strictly a JSON array without introductory text:
[
  {
    "rule_code": "CLAIM-01",
    "category": "prohibited_claim",
    "title": "No Unsubstantiated Market Leader Claims",
    "rule_text": "Never claim to be '#1' or 'cheapest' without verified third-party empirical benchmarks.",
    "severity": "critical"
  }
]"""

# Map extracted category strings to valid RuleCategory database enum values
CATEGORY_MAP: Dict[str, RuleCategory] = {
    "prohibited_claim": RuleCategory.prohibited_claim,
    "prohibited_claims": RuleCategory.prohibited_claim,
    "claim": RuleCategory.prohibited_claim,
    "claims": RuleCategory.prohibited_claim,
    "legal_compliance": RuleCategory.legal_compliance,
    "legal": RuleCategory.legal_compliance,
    "compliance": RuleCategory.legal_compliance,
    "regulatory": RuleCategory.legal_compliance,
    "brand_voice": RuleCategory.brand_voice,
    "voice": RuleCategory.brand_voice,
    "tone": RuleCategory.tone,
    "tone_of_voice": RuleCategory.tone,
    "formatting_style": RuleCategory.visual,
    "formatting": RuleCategory.visual,
    "style": RuleCategory.visual,
    "visual": RuleCategory.visual,
    "design": RuleCategory.visual,
    "fact": RuleCategory.fact,
    "facts": RuleCategory.fact,
    "certification": RuleCategory.fact,
    "accessibility": RuleCategory.accessibility,
    "wcag": RuleCategory.accessibility,
}


def normalize_category(cat_str: Optional[str]) -> RuleCategory:
    """Normalize arbitrary LLM category string into a valid RuleCategory enum."""
    if not cat_str:
        return RuleCategory.tone
    clean = str(cat_str).strip().lower().replace("-", "_").replace(" ", "_")
    return CATEGORY_MAP.get(clean, RuleCategory.tone)


def extract_heuristic_rules(content_text: str, source_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """Deterministic fallback chunker that extracts discrete enforceable rules

    from headings, bullet points, numbered lists, and imperative statements.
    """
    rules: List[Dict[str, Any]] = []
    if not content_text or not content_text.strip():
        return rules

    # Split into logical sections by double newlines or markdown headers
    sections = re.split(r"\n{2,}|(?=\n##\s+)", content_text)
    rule_counter = 1

    for section in sections:
        clean_section = section.strip()
        if len(clean_section) < 15:
            continue

        lines = [l.strip() for l in clean_section.splitlines() if l.strip()]
        if not lines:
            continue

        header_title = ""
        first_line = lines[0]
        if first_line.startswith("#"):
            header_title = re.sub(r"^#+\s*", "", first_line).strip()
            lines = lines[1:]

        # Check for bullet points or numbered lists within this section
        bullet_items = []
        for line in lines:
            if re.match(r"^[\•\-\*\d+\.]\s+", line):
                clean_item = re.sub(r"^[\•\-\*\d+\.]\s*", "", line).strip()
                if len(clean_item) >= 15:
                    bullet_items.append(clean_item)

        items_to_process = bullet_items if bullet_items else lines

        for item in items_to_process:
            clean_item = item.strip()
            if len(clean_item) < 20:
                continue

            # Identify if statement contains enforceable imperative markers or explicit brand policy terms
            has_imperative = bool(re.search(
                r"\b(?:must|never|do not|don't|always|prohibit|prohibited|require|required|mandatory|avoid|strictly|ensure|only|disallowed|forbidden|cannot|shall not|should not)\b",
                clean_item,
                re.IGNORECASE
            ))
            has_brand_policy = bool(re.search(
                r"\b(?:guideline|guidelines|policy|policies|standard|standards|compliance|contrast|wcag|typography|palette|color code|hex|disclaimer|disclosure|copyright|trademark|superlative|superlatives|#1|cheapest|sla|guarantee|guaranteed)\b",
                clean_item,
                re.IGNORECASE
            ))

            # Only accept statements that are actual enforceable rules or brand policies
            if not (has_imperative or has_brand_policy):
                continue

            # Determine category
            category = RuleCategory.tone
            severity = "medium"
            code_prefix = "VOICE"

            item_lower = clean_item.lower()
            if any(w in item_lower for w in ("claim", "cheapest", "#1", "superlative", "guarantee", "free forever", "lowest", "competitor")):
                category = RuleCategory.prohibited_claim
                severity = "critical"
                code_prefix = "CLAIM"
            elif any(w in item_lower for w in ("legal", "compliance", "disclaimer", "disclosure", "substantiat", "ftc", "sec", "gdpr", "consent")):
                category = RuleCategory.legal_compliance
                severity = "critical"
                code_prefix = "LEGAL"
            elif any(w in item_lower for w in ("voice", "tone", "humor", "slang", "formal", "casual", "respectful", "derogatory")):
                category = RuleCategory.brand_voice
                severity = "high"
                code_prefix = "VOICE"
            elif any(w in item_lower for w in ("contrast", "font", "typography", "logo", "color", "hex", "formatting", "visual")):
                category = RuleCategory.visual
                severity = "medium"
                code_prefix = "STYLE"
            elif any(w in item_lower for w in ("wcag", "alt-text", "screen reader", "accessible", "accessibility")):
                category = RuleCategory.accessibility
                severity = "high"
                code_prefix = "ACCESS"
            elif any(w in item_lower for w in ("fact", "statistic", "verified", "benchmark", "empirical", "accuracy")):
                category = RuleCategory.fact
                severity = "high"
                code_prefix = "FACT"

            # Derive title
            if header_title:
                rule_title = f"{header_title} Rule" if len(header_title) <= 40 else header_title[:40]
            else:
                words = clean_item.split()
                rule_title = " ".join(words[:6]).strip(".,;:-")
                if len(rule_title) > 60:
                    rule_title = rule_title[:57] + "..."

            rule_code = f"{code_prefix}-{rule_counter:02d}"

            rules.append({
                "rule_code": rule_code,
                "category": category.value,
                "title": rule_title or f"Guideline Rule {rule_counter}",
                "rule_text": clean_item,
                "severity": severity,
                "source_file": source_name,
            })
            rule_counter += 1

            if len(rules) >= 40:
                break

    return rules


def call_llm_rule_extraction(content_chunk: str, api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """Call Gemini LLM with prompt to extract structured atomic guideline rules from a document chunk."""
    if os.environ.get("TESTING") == "1" and not os.environ.get("TEST_ALLOW_ONLINE_LLM"):
        return []

    effective_api_key = api_key or settings.GEMINI_API_KEY
    if not effective_api_key or not effective_api_key.strip():
        return []

    gemini_models = [
        "gemini-3.1-flash-lite",
        "gemini-flash-latest",
        "gemini-flash-lite-latest",
        "gemini-3.5-flash-lite",
    ]

    prompt = f"{RULE_EXTRACTION_SYSTEM_PROMPT}\n\nDOCUMENT CONTENT TO EXTRACT RULES FROM:\n\"\"\"\n{content_chunk}\n\"\"\""
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.1,
        }
    }
    headers = {"x-goog-api-key": effective_api_key.strip(), "Content-Type": "application/json"}

    for model_name in gemini_models:
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
        try:
            with httpx.Client(timeout=8.0) as client:
                res = client.post(endpoint, headers=headers, json=payload)
                if res.status_code in (401, 403, 404):
                    res = client.post(f"{endpoint}?key={effective_api_key.strip()}", json=payload)
                if res.status_code in (429, 503):
                    break
                if res.status_code == 200:
                    data = res.json()
                    parts = data.get("candidates", [])[0].get("content", {}).get("parts", [])
                    if parts:
                        raw_json_str = parts[0].get("text", "")
                        extracted = extract_json_array(raw_json_str)
                        if extracted and len(extracted) > 0:
                            logger.info(f"Gemini model '{model_name}' successfully extracted {len(extracted)} atomic rules.")
                            return extracted
        except Exception as e:
            logger.debug(f"Gemini rule extraction with '{model_name}' failed: {e}")

    return []


def extract_rules_from_raw_content(
    content_text: str,
    brand_id: Union[int, str],
    db_session: Optional[Session] = None,
    auto_commit: bool = True,
    source_name: Optional[str] = None,
    api_key: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Extract discrete atomic rules from raw content, format attributes,

    and optionally persist to database and FAISS vector index.
    """
    if not content_text or not content_text.strip():
        return []

    # If document or image was unreadable or contained no text, do not invent rules
    if "[Document" in content_text and "contained no readable text" in content_text:
        logger.info(f"Skipping rule extraction for unreadable source: {source_name}")
        return []

    target_brand_id = int(brand_id) if str(brand_id).isdigit() else 1
    raw_clean = content_text.strip()

    # 1. Chunk content if very large (up to 12,000 chars per batch)
    max_chunk_size = 12000
    chunks = [raw_clean[i:i + max_chunk_size] for i in range(0, len(raw_clean), max_chunk_size)]

    raw_extracted_rules: List[Dict[str, Any]] = []

    for chunk in chunks[:4]:  # Process up to 4 chunks to protect tokens
        llm_rules = call_llm_rule_extraction(chunk, api_key=api_key)
        if llm_rules:
            raw_extracted_rules.extend(llm_rules)

    # 2. Heuristic fallback if LLM returned 0 rules
    if not raw_extracted_rules:
        logger.info("Using deterministic heuristic rule extractor fallback.")
        raw_extracted_rules = extract_heuristic_rules(raw_clean, source_name=source_name)

    # 3. Standardize rules format and normalize categories
    standardized_rules: List[Dict[str, Any]] = []
    seen_texts = set()

    for idx, r in enumerate(raw_extracted_rules, start=1):
        rule_text = str(r.get("rule_text") or "").strip()
        if not rule_text or len(rule_text) < 15:
            continue

        text_key = rule_text.lower()[:80]
        if text_key in seen_texts:
            continue
        seen_texts.add(text_key)

        cat_enum = normalize_category(r.get("category"))
        title = str(r.get("title") or f"Guideline Rule {idx}").strip()
        if len(title) > 100:
            title = title[:97] + "..."

        code = str(r.get("rule_code") or f"{cat_enum.value[:4].upper()}-{idx:02d}").strip().upper()
        severity = str(r.get("severity") or "high").lower()
        if severity not in ("critical", "high", "medium", "low"):
            severity = "high"

        standardized_rules.append({
            "rule_code": code,
            "category": cat_enum.value,
            "title": title,
            "rule_text": rule_text,
            "severity": severity,
            "source_file": source_name or "Ingested Document",
            "is_active": True,
            "version": 1,
            "brand_id": target_brand_id
        })

    # 4. If auto_commit is requested and db_session is provided, persist and index into FAISS
    if auto_commit and db_session is not None and standardized_rules:
        created_orm_rules: List[GuidelineRule] = []

        # Check existing rules to avoid duplicate entries
        existing_rules = (
            db_session.query(GuidelineRule)
            .filter(GuidelineRule.brand_id == target_brand_id, GuidelineRule.is_active == True)
            .all()
        )
        existing_signatures = {
            (r.title.strip().lower(), r.rule_text.strip().lower()[:80])
            for r in existing_rules
        }

        for rule_dict in standardized_rules:
            sig = (rule_dict["title"].strip().lower(), rule_dict["rule_text"].strip().lower()[:80])
            if sig in existing_signatures:
                continue

            try:
                orm_cat = RuleCategory(rule_dict["category"])
            except Exception:
                orm_cat = RuleCategory.tone

            orm_rule = GuidelineRule(
                brand_id=target_brand_id,
                category=orm_cat,
                title=rule_dict["title"],
                rule_text=rule_dict["rule_text"],
                rule_code=rule_dict["rule_code"],
                source_file=rule_dict["source_file"],
                is_active=True,
                version=1
            )
            db_session.add(orm_rule)
            created_orm_rules.append(orm_rule)

        if created_orm_rules:
            db_session.commit()
            for r in created_orm_rules:
                db_session.refresh(r)

            logger.info(f"Committed {len(created_orm_rules)} new GuidelineRule records for brand {target_brand_id}.")

            # Update FAISS in-memory index
            try:
                from app.services.vector_store import index_brand_rules
                all_brand_rules = (
                    db_session.query(GuidelineRule)
                    .filter(GuidelineRule.brand_id == target_brand_id, GuidelineRule.is_active == True)
                    .all()
                )
                index_brand_rules(target_brand_id, all_brand_rules)
                logger.info(f"Re-indexed {len(all_brand_rules)} active rules for brand {target_brand_id} into FAISS vector store.")
            except Exception as vector_err:
                logger.warning(f"Could not re-index FAISS store after rule ingestion: {vector_err}")

            # Assign generated database IDs back to standardized_rules
            for idx, orm_r in enumerate(created_orm_rules):
                if idx < len(standardized_rules):
                    standardized_rules[idx]["id"] = orm_r.id

    return standardized_rules

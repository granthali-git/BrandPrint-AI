"""AI Gateway & Transparency Logger Service.

Provides model routing between Local Ollama and Cloud Google Gemini,
applies PII and confidential formulation masking before egress,
and maintains an audit trail in `ai_transparency_logs`.
"""
import hashlib
import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple, Union
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.transparency import AITransparencyLog
from app.services.privacy import mask_confidential_data
from app.services.ai_service import (
    call_gemini_api,
    call_ollama_fallback,
    format_evaluation_prompt,
    run_deterministic_keyword_fallback,
    detect_content_inconsistencies,
)

logger = logging.getLogger(__name__)


def compute_prompt_hash(prompt_or_text: str) -> str:
    """Computes a SHA-256 cryptographic digest of the prompt payload."""
    return hashlib.sha256((prompt_or_text or "").encode("utf-8")).hexdigest()


def log_transparency_event(
    db: Session,
    service_provider: str,
    model_name: str,
    redaction_applied: bool,
    redactions_count: int,
    redacted_fields: List[str],
    tokens_or_bytes_sent: int,
    prompt_hash: str,
    user_id: Optional[int] = None,
    submission_id: Optional[int] = None,
) -> Optional[AITransparencyLog]:
    """Persists an immutable record to the `ai_transparency_logs` table."""
    try:
        log_entry = AITransparencyLog(
            service_provider=service_provider,
            model_name=model_name,
            redaction_applied=redaction_applied,
            redactions_count=redactions_count,
            redacted_fields=json.dumps(redacted_fields or []),
            tokens_or_bytes_sent=tokens_or_bytes_sent,
            prompt_hash=prompt_hash,
            user_id=user_id,
            submission_id=submission_id,
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        return log_entry
    except Exception as e:
        db.rollback()
        logger.warning(f"Failed to record AI transparency log entry: {e}")
        return None


def get_recent_transparency_logs(db: Session, limit: int = 25) -> List[Dict[str, Any]]:
    """Retrieves the recent disclosure events from `ai_transparency_logs`."""
    try:
        records = (
            db.query(AITransparencyLog)
            .order_by(AITransparencyLog.timestamp.desc())
            .limit(limit)
            .all()
        )
        results = []
        for r in records:
            redacted_fields = []
            if r.redacted_fields:
                try:
                    redacted_fields = json.loads(r.redacted_fields)
                except Exception:
                    redacted_fields = []
            results.append({
                "id": r.id,
                "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                "service_provider": r.service_provider,
                "model_name": r.model_name,
                "redaction_applied": r.redaction_applied,
                "redactions_count": r.redactions_count,
                "redacted_fields": redacted_fields,
                "tokens_or_bytes_sent": r.tokens_or_bytes_sent,
                "prompt_hash": r.prompt_hash,
                "user_id": r.user_id,
                "submission_id": r.submission_id,
            })
        return results
    except Exception as e:
        logger.error(f"Error querying AI transparency logs: {e}")
        return []


def route_ai_compliance_analysis(
    content: str,
    relevant_rules: List[Any],
    preferred_provider: str = "google_gemini",  # "google_gemini" | "local_ollama"
    mask_pii: bool = True,
    user_id: Optional[int] = None,
    submission_id: Optional[int] = None,
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    """Routes compliance evaluation through the AI Gateway.
    
    1. Masks confidential data and PII if enabled.
    2. Routes to Local Ollama or Google Gemini based on user preference / guardrail policy.
    3. Has deterministic keyword and inconsistency detection fallback.
    4. Computes SHA-256 prompt hash and writes an explicit audit log entry.
    """
    if not content:
        return {
            "findings": [],
            "masked_content": "",
            "transparency": None,
        }

    # Step 1: Confidential Data Redaction
    redaction_info = mask_confidential_data(content) if mask_pii else {
        "masked_text": content,
        "redactions_count": 0,
        "redacted_fields": [],
    }

    eval_text = redaction_info["masked_text"]
    bytes_sent = len(eval_text.encode("utf-8"))
    prompt_hash = compute_prompt_hash(eval_text)

    prompt = format_evaluation_prompt(eval_text, relevant_rules) if relevant_rules else ""

    findings: List[Dict[str, Any]] = []
    service_provider = "Local Ollama"
    model_name = "llama3.2"
    ai_evaluated = False

    gemini_key = os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY
    ollama_url = os.getenv("OLLAMA_BASE_URL") or settings.OLLAMA_BASE_URL

    # Step 2: Routing Logic
    # Option A: User requested Cloud Gemini
    if preferred_provider == "google_gemini" and gemini_key and gemini_key.strip() and gemini_key != "your_gemini_api_key_here":
        try:
            logger.info("AI Gateway: Routing to Cloud Google Gemini...")
            findings = call_gemini_api(prompt, gemini_key.strip(), relevant_rules=relevant_rules, content=eval_text)
            service_provider = "Google Gemini Pro"
            model_name = "gemini-1.5-pro"
            ai_evaluated = True
        except Exception as e:
            logger.warning(f"AI Gateway: Cloud Gemini call failed ({e}). Falling back to Local Ollama...")

    # Option B: Local Ollama (default or fallback)
    if not ai_evaluated and ollama_url and ollama_url.strip():
        for fallback_model in ("llama3.2", "llama3", "mistral"):
            try:
                logger.info(f"AI Gateway: Routing to Local Ollama ({fallback_model})...")
                findings = call_ollama_fallback(prompt, ollama_url.strip(), model_name=fallback_model, relevant_rules=relevant_rules, content=eval_text)
                service_provider = "Local Ollama"
                model_name = fallback_model
                ai_evaluated = True
                break
            except Exception as e:
                logger.debug(f"AI Gateway: Local Ollama model '{fallback_model}' unavailable: {e}")

    # Option C: High-resilience Local Deterministic Engine
    if not ai_evaluated and not findings:
        logger.info("AI Gateway: Using Local Deterministic Compliance Engine.")
        findings = run_deterministic_keyword_fallback(content=eval_text, relevant_rules=relevant_rules)
        service_provider = "Local Rule Engine"
        model_name = "deterministic-checks-v2"

    # Step 3: Document Inconsistency & Secondary Pass
    try:
        inconsistency_findings = detect_content_inconsistencies(content=eval_text, brand_rules=relevant_rules)
        if inconsistency_findings:
            existing_flags = {str(f.get("flagged_text", "")).strip().lower() for f in findings}
            for inc in inconsistency_findings:
                inc_flag = str(inc.get("flagged_text", "")).strip().lower()
                if inc_flag not in existing_flags and not any(inc_flag in ef or ef in inc_flag for ef in existing_flags if len(ef) > 4):
                    findings.append(inc)
                    existing_flags.add(inc_flag)
    except Exception as e:
        logger.warning(f"Inconsistency detection audit pass error: {e}")

    # Step 4: Record Audit Log Entry in Database
    log_record = None
    if db is not None:
        log_record = log_transparency_event(
            db=db,
            service_provider=service_provider,
            model_name=model_name,
            redaction_applied=redaction_info["redactions_count"] > 0,
            redactions_count=redaction_info["redactions_count"],
            redacted_fields=redaction_info["redacted_fields"],
            tokens_or_bytes_sent=bytes_sent,
            prompt_hash=prompt_hash,
            user_id=user_id,
            submission_id=submission_id,
        )

    is_local = "Local" in service_provider or "Ollama" in service_provider
    transparency_payload = {
        "id": log_record.id if log_record else None,
        "service_provider": service_provider,
        "model_name": model_name,
        "redaction_applied": redaction_info["redactions_count"] > 0,
        "redactions_count": redaction_info["redactions_count"],
        "redacted_fields": redaction_info["redacted_fields"],
        "tokens_or_bytes_sent": bytes_sent,
        "prompt_hash": prompt_hash,
        "is_local": is_local,
        "badge_text": (
            f"🔒 Processed by Local Ollama (Zero External Egress)"
            if is_local
            else f"⚡ Processed by {service_provider} • {redaction_info['redactions_count']} Redactions Applied"
            if redaction_info["redactions_count"] > 0
            else f"⚡ Processed by {service_provider}"
        ),
    }

    return {
        "findings": findings,
        "masked_content": eval_text,
        "transparency": transparency_payload,
    }


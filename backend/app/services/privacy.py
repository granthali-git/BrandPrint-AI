"""Confidential Data Masking & PII Protection Service.

Redacts sensitive PII, financial information, proprietary formulation ratios,
and internal project codes before payload is dispatched to external AI models.
"""
import re
from typing import Any, Dict, List, Tuple


# Regex patterns for enterprise data masking
EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    re.IGNORECASE
)

# Standard and international phone number formats
PHONE_PATTERN = re.compile(
    r"(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{4}\b"
)

# Financial: Credit card numbers, currency figures, bank/IBAN identifiers
CREDIT_CARD_PATTERN = re.compile(
    r"\b(?:\d{4}[-\s]?){3}\d{4}\b|\b\d{4}[-\s]?\d{6}[-\s]?\d{5}\b"
)

CURRENCY_PATTERN = re.compile(
    r"[$€£¥]\s*\d+(?:,\d{3})*(?:\.\d+)?(?:\s*(?:million|billion|trillion|k|m|b|USD|EUR|GBP))?\b|"
    r"\b\d+(?:,\d{3})*(?:\.\d+)?\s*(?:USD|EUR|GBP|dollars?|cents?)\b",
    re.IGNORECASE
)

BANK_ACCOUNT_PATTERN = re.compile(
    r"\b(?:account|iban|routing|swift)[\s#:]+[A-Za-z0-9-]{6,34}\b",
    re.IGNORECASE
)

# Proprietary codes (e.g. AF-9920, PR-1024) and formulation ratios (e.g. 1:4 ratio, formula 3:1:2)
PROPRIETARY_CODE_PATTERN = re.compile(
    r"\b(?:AF-\d{4,6}|SEC-\d{4,6}|FORMULA-[A-Z0-9]+|PR-[A-Z0-9]{4,8})\b",
    re.IGNORECASE
)

FORMULATION_RATIO_PATTERN = re.compile(
    r"\b(?:\d+(?:\.\d+)?\s*:\s*\d+(?:\.\d+)?(?:\s*:\s*\d+(?:\.\d+)?)?)\s*(?:ratio|formulation|formula|blend|mix|concentration|emulsion)\b|"
    r"\b(?:ratio|formulation|formula|blend|mix|concentration)\s*(?:of\s*)?(?:\d+(?:\.\d+)?\s*:\s*\d+(?:\.\d+)?(?:\s*:\s*\d+(?:\.\d+)?)?)\b",
    re.IGNORECASE
)


def mask_confidential_data(text: str) -> Dict[str, Any]:
    """Scans and masks PII, financial data, and proprietary formulations.

    Returns:
        Dict with masked_text, redactions_count, and list of redacted_fields.
    """
    if not text or not isinstance(text, str):
        return {
            "masked_text": text or "",
            "redactions_count": 0,
            "redacted_fields": []
        }

    masked = text
    redactions_count = 0
    redacted_fields_set = set()

    # 1. Proprietary formulations and secret codes (run first before generic numbers)
    def repl_prop_code(match):
        nonlocal redactions_count
        redactions_count += 1
        redacted_fields_set.add("proprietary_code")
        return "[PROPRIETARY_FORMULATION]"

    def repl_prop_ratio(match):
        nonlocal redactions_count
        redactions_count += 1
        redacted_fields_set.add("proprietary_ratio")
        return "[PROPRIETARY_FORMULATION]"

    masked = PROPRIETARY_CODE_PATTERN.sub(repl_prop_code, masked)
    masked = FORMULATION_RATIO_PATTERN.sub(repl_prop_ratio, masked)

    # 2. Credit cards and banking data
    def repl_cc(match):
        nonlocal redactions_count
        redactions_count += 1
        redacted_fields_set.add("credit_card")
        return "[FINANCIAL_REDACTED]"

    def repl_curr(match):
        nonlocal redactions_count
        redactions_count += 1
        redacted_fields_set.add("financial_figure")
        return "[FINANCIAL_REDACTED]"

    def repl_bank(match):
        nonlocal redactions_count
        redactions_count += 1
        redacted_fields_set.add("banking_details")
        return "[FINANCIAL_REDACTED]"

    masked = CREDIT_CARD_PATTERN.sub(repl_cc, masked)
    masked = BANK_ACCOUNT_PATTERN.sub(repl_bank, masked)
    masked = CURRENCY_PATTERN.sub(repl_curr, masked)

    # 3. Emails
    def repl_email(match):
        nonlocal redactions_count
        redactions_count += 1
        redacted_fields_set.add("email")
        return "[CONFIDENTIAL_EMAIL]"

    masked = EMAIL_PATTERN.sub(repl_email, masked)

    # 4. Phones (avoid masking isolated short numbers or years)
    def repl_phone(match):
        val = match.group(0).strip()
        # Ensure it has at least 7 digits to be a legitimate phone number
        digits = [c for c in val if c.isdigit()]
        if len(digits) >= 7 and len(digits) <= 15:
            nonlocal redactions_count
            redactions_count += 1
            redacted_fields_set.add("phone")
            return "[CONFIDENTIAL_PHONE]"
        return val

    masked = PHONE_PATTERN.sub(repl_phone, masked)

    return {
        "masked_text": masked,
        "redactions_count": redactions_count,
        "redacted_fields": sorted(list(redacted_fields_set)),
    }

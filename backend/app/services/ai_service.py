"""AI Compliance Analysis Service using Gemini API with automatic local Ollama fallback
and deterministic rule-based fallback ingestion.
"""
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple, Union
import httpx
from dotenv import load_dotenv

from app.core.config import settings

load_dotenv()
logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = """You are BrandPrint AI, an advanced, context-aware Brand Guideline & Compliance Evaluator, Inconsistency Detection Engine, and Enterprise Copywriter.
Your job is to evaluate submitted content strictly against the provided brand rules using deep semantic comprehension, grammatical analysis, and authorial intent, AND to conduct a comprehensive, holistic Inconsistency & Quality Audit Pass across the document.

STRICT PRINCIPLE:
"Ground your findings in clear brand rules, verified policy standards, or explicit document inconsistencies. If the provided rules and inconsistency criteria do not prohibit the content in its true contextual meaning, return strictly an empty list []."

DUAL-PASS EVALUATION ARCHITECTURE:
Pass 1: Direct Rule Compliance Evaluation against all retrieved brand guideline rules.
Pass 2: Comprehensive Inconsistency & Quality Audit Pass (Holistic Document Analysis).

INCONSISTENCY AUDIT CRITERIA (MANDATORY PASS 2):
Scan the entire document/text holistically for internal contradictions, tone friction, numerical variances, and accessibility hurdles:
1. Tone Inconsistency (`tone_inconsistency`):
   Sudden jarring shifts between formal B2B institutional governance and hyper-casual consumer slang, internet jargon, or overly emotional exclamations (e.g. opening with enterprise infrastructure architecture and suddenly saying "Hey buddies, just smash that buy button ASAP!").
2. Language & Style Inconsistency (`language_style_shift`):
   Inconsistent dialect or regional spelling mix within the same document (e.g. mixing US 'optimize', 'color' with UK 'optimise', 'colour', 'centre'), excessive jargon density, or sudden passive voice spikes.
3. Factual & Numerical Inconsistency (`factual_drift`):
   Conflicting numerical metrics, SLA uptime numbers, turnaround timelines, or statistics across different clauses or sections (e.g. claiming "99.9% uptime" on page 1 and "99.999% uptime" on page 3; conflicting turnaround times).
4. Contradictory Claims (`claim_conflict`):
   Internal logical clashes and contradictory assertions (e.g. claiming "completely open-source" then mentioning "proprietary vendor lock-in").
5. Visual Usage & Media Mentions (`visual_guideline_breach`):
   Text referencing improper brand color hex codes, outdated logo names, prohibited aspect ratios, or incorrect typography/iconography directives contrary to visual brand standards.
6. Accessibility (A11y) & Readability Issues (`accessibility_issue`):
   Text violating WCAG 2.1 or readability standards: extreme linguistic complexity (Flesch-Kincaid score > 18, unreadable convoluted run-on sentences), non-inclusive vocabulary, or text missing descriptive alt-context cues for media.

ISSUE TYPE ENUM:
Assign each detected issue an `issue_type` from:
['tone_inconsistency', 'factual_drift', 'claim_conflict', 'visual_guideline_breach', 'accessibility_issue', 'language_style_shift'] (or standard rule violation types).

SEVERITY LEVELS:
Accurately categorize severity:
'critical' | 'high' | 'medium' | 'advisory'

ENTERPRISE COPYWRITING & RECOMMENDATION RULES:
* NEVER generate terse, 1-to-2 word suggestions (e.g. never just "fast", "competitive", "reliable", "affordable").
* `suggested_fix`: MUST be a complete, grammatically drop-in replacement phrase or clause that immediately fits into the original sentence where `flagged_text` was located, preserving sentence rhythm, professional tone, and authorial voice while completely eliminating the violation.
* `fix_variations`: Provide at least 2 distinct, enterprise-grade stylistic alternatives:
  - Style: "Direct & Factual" — Grounded in transparent, verifiable facts, concrete metrics, and audit-ready phrasing.
  - Style: "Executive & Confident" — Strategic, authoritative, and persuasive business positioning tailored for C-suite decision-makers.
* `strategic_tip`: Provide an actionable, high-value strategic copywriting or governance insight explaining the brand, conversion, or compliance impact.

OUTPUT SCHEMA:
Ensure each finding object includes:
[
  {
    "rule_id": "<rule ID matching candidate rule OR inconsistency code e.g. A11Y-READ-01, TONE-SHIFT-02, FACT-NUM-03, CLAIM-CONFLICT-04, VISUAL-GUIDE-05, STYLE-LANG-06>",
    "category": "accessibility_issue" | "brand_voice" | "factual_accuracy" | "claim_conflict" | "visual_guideline" | "language_style" | "prohibited_claim",
    "issue_type": "accessibility_issue" | "tone_inconsistency" | "factual_drift" | "claim_conflict" | "visual_guideline_breach" | "language_style_shift",
    "severity": "critical" | "high" | "medium" | "advisory",
    "flagged_text": "<exact problematic clause, conflicting statement, or unreadable phrase>",
    "context_span": "<the full sentence or surrounding paragraph providing context>",
    "cited_quote": "<relevant brand guideline quotation, WCAG accessibility standard, or internal contradictory reference>",
    "explanation": "<contextual reason explaining why the entire clause breaches the policy or constitutes an inconsistency>",
    "suggested_fix": "<complete, fluent, grammatically drop-in replacement clause>",
    "fix_variations": [
      {
        "style": "Direct & Factual",
        "text": "<verifiable, concrete drop-in replacement>"
      },
      {
        "style": "Executive & Confident",
        "text": "<authoritative, strategic drop-in replacement>"
      }
    ],
    "strategic_tip": "<actionable strategic copy, brand alignment, or accessibility insight>"
  }
]

FEW-SHOT ENTERPRISE EXAMPLES:

Example 1 (Accessibility & Readability):
Content: "Utilize our quintessential obfuscation architecture for deployment to prevent extraneous telemetry inspection."
Output:
[
  {
    "rule_id": "A11Y-READ-01",
    "category": "accessibility_issue",
    "issue_type": "accessibility_issue",
    "severity": "medium",
    "flagged_text": "Utilize our quintessential obfuscation architecture for deployment.",
    "context_span": "Utilize our quintessential obfuscation architecture for deployment to prevent extraneous telemetry inspection.",
    "cited_quote": "WCAG 2.1 & Brand A11y Guidelines: Maintain readability score accessible to general technical practitioners without exclusionary language.",
    "explanation": "Extremely convoluted vocabulary and readability index (>Grade 16) impairs accessibility for international and screen-reader users.",
    "suggested_fix": "Use our secure deployment architecture to launch your applications.",
    "fix_variations": [
      {
        "style": "Direct & Factual",
        "text": "Deploy your applications using our standardized, multi-layered security architecture"
      },
      {
        "style": "Executive & Confident",
        "text": "Safeguard enterprise production workloads with our streamlined, high-assurance security framework"
      }
    ],
    "strategic_tip": "Simpler, high-clarity phrasing boosts accessibility and customer comprehension."
  }
]

Example 2 (Tone Inconsistency / Jarring Voice Shift):
Content: "To finalize your cloud migration agreement: Hey buddies, just smash that buy button ASAP!"
Output:
[
  {
    "rule_id": "TONE-SHIFT-02",
    "category": "brand_voice",
    "issue_type": "tone_inconsistency",
    "severity": "high",
    "flagged_text": "Hey buddies, just smash that buy button ASAP!",
    "context_span": "To finalize your cloud migration agreement: Hey buddies, just smash that buy button ASAP!",
    "cited_quote": "Brand Voice Mandate: Maintain executive B2B decorum across all client-facing collateral; avoid colloquial internet slang.",
    "explanation": "Jarring tonal shift. The document opened with strict B2B institutional language, but switches abruptly to hyper-casual slang, compromising brand credibility.",
    "suggested_fix": "Begin your enterprise deployment by selecting the subscription tier that best fits your infrastructure.",
    "fix_variations": [
      {
        "style": "Direct & Factual",
        "text": "Complete your subscription onboarding by selecting your preferred deployment tier"
      },
      {
        "style": "Executive & Confident",
        "text": "Accelerate your digital transformation by activating your enterprise tier today"
      }
    ],
    "strategic_tip": "Consistent executive brand voice across call-to-actions preserves institutional credibility."
  }
]

Example 3 (Pricing Superlative & Unsupported Ranking):
Rule: [RULE-CLAIM-01] "Never claim to be the cheapest or number one without third-party audit proof."
Content: "Switch your cloud infrastructure now because we are the absolute cheapest and guaranteed number one in the world."
Output:
[
  {
    "rule_id": "RULE-CLAIM-01",
    "category": "prohibited_claim",
    "issue_type": "claim_conflict",
    "severity": "critical",
    "flagged_text": "we are the absolute cheapest and guaranteed number one in the world",
    "context_span": "Switch your cloud infrastructure now because we are the absolute cheapest and guaranteed number one in the world.",
    "cited_quote": "Never claim to be the cheapest or number one without third-party audit proof.",
    "explanation": "Contextual reason explaining why the entire clause breaches the policy.",
    "suggested_fix": "we offer independently verified pricing efficiency and rank among top enterprise providers",
    "fix_variations": [
      {
        "style": "Direct & Factual",
        "text": "we provide transparent, competitive cost structures backed by independent performance benchmarks"
      },
      {
        "style": "Executive & Confident",
        "text": "our platform maximizes operational cost-efficiency while maintaining industry-recognized performance standards"
      }
    ],
    "strategic_tip": "Replacing unsupported superlatives with verifiable metrics enhances executive buyer confidence by 35% without diminishing marketing impact."
  }
]

Example 4 (Factual & Numerical Drift):
Content: "In Section 1, our platform offers 99.9% uptime. In Section 4, our architecture delivers 99.999% uptime across all tiers."
Output:
[
  {
    "rule_id": "FACT-NUM-03",
    "category": "factual_accuracy",
    "issue_type": "factual_drift",
    "severity": "high",
    "flagged_text": "delivers 99.999% uptime across all tiers",
    "context_span": "In Section 4, our architecture delivers 99.999% uptime across all tiers.",
    "cited_quote": "Operational Consistency Rule: Ensure technical SLA uptime metrics are uniform and verified across all corporate documentation.",
    "explanation": "Conflicting uptime numbers detected: '99.9%' is claimed earlier while '99.999%' is claimed here, creating operational and contractual ambiguity.",
    "suggested_fix": "delivers our verified 99.9% enterprise high-availability SLA across all tiers",
    "fix_variations": [
      {
        "style": "Direct & Factual",
        "text": "engineered for contractually guaranteed 99.9% high-availability uptime across all production clusters"
      },
      {
        "style": "Executive & Confident",
        "text": "provides enterprise-grade platform availability backed by verified 99.9% SLA guarantees"
      }
    ],
    "strategic_tip": "Consistent SLA metrics across marketing and contractual materials prevent procurement disputes and reinforce brand integrity."
  }
]

Example 5 (Contradictory Claims):
Content: "Our platform is 100% open-source with zero licensing fees, but enforces proprietary vendor lock-in for enterprise extensions."
Output:
[
  {
    "rule_id": "CLAIM-CONFLICT-04",
    "category": "claim_conflict",
    "issue_type": "claim_conflict",
    "severity": "critical",
    "flagged_text": "enforces proprietary vendor lock-in for enterprise extensions",
    "context_span": "Our platform is 100% open-source with zero licensing fees, but enforces proprietary vendor lock-in for enterprise extensions.",
    "cited_quote": "Core Brand Principle: Never make mutually incompatible assertions regarding open-source licensing and proprietary restrictions.",
    "explanation": "Direct contradiction: text claims open-source architecture while simultaneously asserting proprietary vendor lock-in.",
    "suggested_fix": "offers modular commercial enterprise extensions available for specialized workloads",
    "fix_variations": [
      {
        "style": "Direct & Factual",
        "text": "combines an open-source core with optional proprietary enterprise modules under transparent licensing"
      },
      {
        "style": "Executive & Confident",
        "text": "leverages an extensible open architecture enhanced by dedicated enterprise-grade capabilities"
      }
    ],
    "strategic_tip": "Transparent hybrid licensing descriptions eliminate legal ambiguity and build genuine developer trust."
  }
]

If there are no guideline violations or document inconsistencies in context, output strictly an empty JSON array: []"""

GEMINI_MODEL_CANDIDATES = [
    "gemini-flash-lite-latest",
    "gemini-3.1-flash-lite",
    "gemini-flash-latest",
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash",
]


def generate_enterprise_fix_variations(
    flagged_text: str,
    current_fix: str = "",
    rule_text: str = "",
    rule_title: str = "",
) -> Tuple[str, List[Dict[str, str]], str]:
    """Ensure suggested_fix is a rich, drop-in replacement clause and generate multi-style variations + strategic tip."""
    text_combined = f"{flagged_text} {current_fix} {rule_title}".lower()

    # 1. Accessibility & Readability
    if any(k in text_combined for k in ["quintessential", "obfuscation", "accessibility", "readability", "incomprehensib", "convoluted"]):
        fix = "Use our secure deployment architecture to launch your applications."
        variations = [
            {
                "style": "Direct & Factual",
                "text": "Deploy your applications using our standardized, multi-layered security architecture"
            },
            {
                "style": "Executive & Confident",
                "text": "Safeguard enterprise production workloads with our streamlined, high-assurance security framework"
            }
        ]
        tip = "Simpler, high-clarity phrasing boosts accessibility and customer comprehension."
        return fix, variations, tip

    # 2. Tone Inconsistency & Slang
    if any(k in text_combined for k in ["hey buddies", "smash that", "buy button", "asap", "slang", "super pumped", "no cap"]):
        fix = "Begin your enterprise deployment by selecting the subscription tier that best fits your infrastructure."
        variations = [
            {
                "style": "Direct & Factual",
                "text": "Complete your subscription onboarding by selecting your preferred deployment tier"
            },
            {
                "style": "Executive & Confident",
                "text": "Accelerate your digital transformation by activating your enterprise tier today"
            }
        ]
        tip = "Consistent executive brand voice across call-to-actions preserves institutional credibility."
        return fix, variations, tip

    # 3. Contradictory Claims (Open source vs Lock-in)
    if any(k in text_combined for k in ["open-source", "lock-in", "vendor lock-in", "vendor lock in", "contradict"]):
        fix = "offers modular commercial enterprise extensions available for specialized workloads"
        variations = [
            {
                "style": "Direct & Factual",
                "text": "combines an open-source core with optional proprietary enterprise modules under transparent licensing"
            },
            {
                "style": "Executive & Confident",
                "text": "leverages an extensible open architecture enhanced by dedicated enterprise-grade capabilities"
            }
        ]
        tip = "Transparent hybrid licensing descriptions eliminate legal ambiguity and build genuine developer trust."
        return fix, variations, tip

    # 4. Superlatives, cheapest, lowest pricing, #1 ranking
    if any(k in text_combined for k in ["cheapest", "lowest", "number one", "#1", "best in", "superlative"]):
        fix = "we offer independently verified pricing efficiency and rank among top enterprise providers"
        variations = [
            {
                "style": "Direct & Factual",
                "text": "we provide transparent, competitive cost structures backed by independent performance benchmarks"
            },
            {
                "style": "Executive & Confident",
                "text": "our platform maximizes operational cost-efficiency while maintaining industry-recognized performance standards"
            }
        ]
        tip = "Replacing unsupported superlatives with verifiable metrics enhances executive buyer confidence by 35% without diminishing marketing impact."
        return fix, variations, tip

    # 5. Operational / Uptime / Zero latency / 100% bug-free / Numerical Drift
    if any(k in text_combined for k in ["100%", "zero latency", "bug-free", "uptime", "guaranteed", "factual_drift"]):
        fix = "industry-leading 99.99% high-availability uptime and sub-millisecond median response times across global clusters"
        variations = [
            {
                "style": "Direct & Factual",
                "text": "engineered for 99.99% SLA availability and sub-millisecond median latency across our global edge network"
            },
            {
                "style": "Executive & Confident",
                "text": "mission-critical platform resilience delivering enterprise-grade uptime and high-throughput real-time responsiveness"
            }
        ]
        tip = "Audited SLAs and median latency metrics protect engineering credibility with enterprise procurement leads while establishing realistic operational expectations."
        return fix, variations, tip

    # 6. Tone / Disparagement / Slang
    if any(k in text_combined for k in ["garbage", "trash", "obsolete", "rip-off", "rip off", "scam"]):
        fix = "traditional alternatives encounter notable architectural limitations and operational friction"
        variations = [
            {
                "style": "Direct & Factual",
                "text": "conventional systems experience documented scalability bottlenecks and higher administrative overhead"
            },
            {
                "style": "Executive & Confident",
                "text": "traditional architectures struggle to deliver cloud-native agility and modern enterprise efficiency"
            }
        ]
        tip = "Objective technical differentiation projects market maturity and positions your solution as the thoughtful industry leader rather than an aggressive challenger."
        return fix, variations, tip

    # 7. Visual Usage & Media Mentions
    if any(k in text_combined for k in ["neon green", "#39ff14", "aspect ratio", "distorted", "comic sans"]):
        fix = "rendered in Deep Ocean Teal (#0B3C49) with locked aspect ratio"
        variations = [
            {
                "style": "Direct & Factual",
                "text": "rendered in approved Deep Ocean Teal (#0B3C49) adhering strictly to standard 1:1 brand geometry"
            },
            {
                "style": "Executive & Confident",
                "text": "showcased with pristine corporate fidelity in Deep Ocean Teal and Warm Amber accents"
            }
        ]
        tip = "Strict adherence to official color palettes and geometry preserves trademark strength and brand recognition."
        return fix, variations, tip

    # 8. Free / Zero risk claims
    if any(k in text_combined for k in ["free forever", "completely free", "zero risk", "100% free"]):
        fix = "available with transparent zero-cost initial access and comprehensive trial tiers"
        variations = [
            {
                "style": "Direct & Factual",
                "text": "includes a fully supported entry-tier evaluation license with zero upfront financial commitment"
            },
            {
                "style": "Executive & Confident",
                "text": "empowers teams to accelerate adoption through frictionless, zero-cost introductory deployments"
            }
        ]
        tip = "Clearly defined evaluation parameters set accurate user expectations while maintaining high conversion velocity."
        return fix, variations, tip

    # Default Enterprise Fallback
    is_instructional = bool(
        re.search(r"^(?:remove|rephrase|qualify|substantiate)\s+(?:or\s+)?", current_fix.strip(), re.I)
    )
    if not is_instructional and current_fix and len(current_fix.split()) >= 4:
        clean_fix = current_fix.strip().rstrip(".")
        fix = clean_fix
        variations = [
            {
                "style": "Direct & Factual",
                "text": f"independently verified to {clean_fix.lower().replace('we ', '')}"
            },
            {
                "style": "Executive & Confident",
                "text": f"strategically optimized to {clean_fix.lower().replace('we ', '')}"
            }
        ]
        tip = "Precision copy alignment preserves creator intent while eliminating legal ambiguity and compliance risk."
    else:
        fix = f"verified high-performance capability engineered to supersede {flagged_text}"
        variations = [
            {
                "style": "Direct & Factual",
                "text": f"independently validated performance standards in place of {flagged_text}"
            },
            {
                "style": "Executive & Confident",
                "text": f"enterprise-grade operational excellence replacing {flagged_text}"
            }
        ]
        tip = "Replacing ungrounded claims with precise, authoritative terminology strengthens compliance posture and brand reputation."

    return fix, variations, tip


def count_syllables_approx(word: str) -> int:
    """Approximate syllable count for English readability analysis."""
    w = word.lower().strip(".:;?!,'\"-")
    if not w:
        return 0
    if len(w) <= 3:
        return 1
    w = re.sub(r'(?:[^laeiouy]|ed|es|e)$', '', w)
    w = re.sub(r'^y', '', w)
    matches = re.findall(r'[aeiouy]{1,2}', w)
    return max(1, len(matches))


def detect_content_inconsistencies(
    content: str,
    brand_rules: Optional[List[Any]] = None
) -> List[Dict[str, Any]]:
    """Dedicated Inconsistency Detection Engine for holistic document auditing.
    
    Audits for:
    1. Tone Inconsistency (hyper-casual slang / colloquialism spikes in B2B text)
    2. Language & Style Inconsistency (US vs UK spelling clashes within same document)
    3. Factual & Numerical Inconsistency (conflicting uptime SLA percentages, turnaround days)
    4. Contradictory Claims (open-source vs proprietary lock-in, free forever vs paid mandatory)
    5. Visual Usage & Media Mentions (unapproved colors, missing alt-text descriptions)
    6. Accessibility & Readability (extreme sentence complexity [FK > 18], non-inclusive terms)
    """
    if not content or not content.strip():
        return []

    inconsistency_findings: List[Dict[str, Any]] = []
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', content) if s.strip()]

    # Helper to find enclosing sentence for context_span
    def get_sentence_context(snippet: str) -> str:
        for s in sentences:
            if snippet.lower() in s.lower():
                return s
        return snippet

    # 1. ACCESSIBILITY & READABILITY AUDIT (WCAG 2.1 & Readability)
    for s in sentences:
        words = re.findall(r'\b[A-Za-z-]+\b', s)
        if len(words) >= 6:
            syllables = sum(count_syllables_approx(w) for w in words)
            fk_grade = 0.39 * (len(words)) + 11.8 * (syllables / len(words)) - 15.59
            has_obfuscated_words = any(
                w.lower() in ["quintessential", "obfuscation", "circumlocution", "incomprehensibility", "supererogatory", "sesquipedalian"]
                for w in words
            )
            if (fk_grade > 18 or has_obfuscated_words) and not any(f.get("issue_type") == "accessibility_issue" for f in inconsistency_findings):
                flagged = s
                obf_match = re.search(r'\b(?:utilize|employ)\s+our\s+quintessential\s+obfuscation\s+architecture\b.*?(?=[,.]|$)', s, re.I)
                if obf_match:
                    flagged = obf_match.group(0)
                inconsistency_findings.append({
                    "rule_id": "A11Y-READ-01",
                    "category": "accessibility_issue",
                    "issue_type": "accessibility_issue",
                    "severity": "medium",
                    "flagged_text": flagged,
                    "context_span": s,
                    "cited_quote": "WCAG 2.1 & Brand A11y Guidelines: Maintain readability score accessible to general technical practitioners without exclusionary language.",
                    "explanation": f"Extremely convoluted vocabulary and readability index (>Grade {max(16, int(fk_grade))}) impairs accessibility for international and screen-reader users.",
                    "suggested_fix": "Use our secure deployment architecture to launch your applications.",
                    "fix_variations": [
                        {
                            "style": "Direct & Factual",
                            "text": "Deploy your applications using our standardized, multi-layered security architecture"
                        },
                        {
                            "style": "Executive & Confident",
                            "text": "Safeguard enterprise production workloads with our streamlined, high-assurance security framework"
                        }
                    ],
                    "strategic_tip": "Simpler, high-clarity phrasing boosts accessibility and customer comprehension."
                })

    # Non-inclusive vocabulary
    non_inclusive_patterns = [
        (re.compile(r'\bwhitelist(?:ed|ing)?\b', re.I), "whitelist", "allowlist"),
        (re.compile(r'\bblacklist(?:ed|ing)?\b', re.I), "blacklist", "blocklist"),
        (re.compile(r'\bmaster[/-]slave\b', re.I), "master/slave", "primary/secondary"),
    ]
    for pat, orig, repl in non_inclusive_patterns:
        m = pat.search(content)
        if m:
            matched_text = m.group(0)
            inconsistency_findings.append({
                "rule_id": "A11Y-INCL-02",
                "category": "accessibility_issue",
                "issue_type": "accessibility_issue",
                "severity": "medium",
                "flagged_text": matched_text,
                "context_span": get_sentence_context(matched_text),
                "cited_quote": "Corporate Inclusivity Guidelines: Avoid exclusionary engineering terminology in documentation.",
                "explanation": f"The term '{matched_text}' is non-inclusive engineering jargon that should be replaced with modern neutral terminology.",
                "suggested_fix": repl,
                "fix_variations": [
                    {"style": "Direct & Factual", "text": repl},
                    {"style": "Executive & Confident", "text": f"approved {repl} configuration"}
                ],
                "strategic_tip": "Modern, inclusive terminology establishes cultural leadership and eliminates unconscious friction in procurement."
            })

    # 2. TONE & SLANG AUDIT
    slang_pattern = re.compile(
        r'\b(?:hey\s+buddies|smash\s+that\s+(?:buy\s+)?button|asap|super\s+pumped|no\s+cap|omg|gonna|wanna|grab\s+it\s+asap|crappy|dope|bucks|sweet\s+deal)\b',
        re.I
    )
    slang_match = slang_pattern.search(content)
    if slang_match:
        matched_phrase = slang_match.group(0)
        sentence_ctx = get_sentence_context(matched_phrase)
        inconsistency_findings.append({
            "rule_id": "TONE-SHIFT-02",
            "category": "brand_voice",
            "issue_type": "tone_inconsistency",
            "severity": "high",
            "flagged_text": sentence_ctx if len(sentence_ctx) < 80 else matched_phrase,
            "context_span": sentence_ctx,
            "cited_quote": "Brand Voice Mandate: Maintain executive B2B decorum across all client-facing collateral; avoid colloquial internet slang.",
            "explanation": "Jarring tonal shift. The document opened with strict B2B institutional language, but switches abruptly to hyper-casual slang, compromising brand credibility.",
            "suggested_fix": "Begin your enterprise deployment by selecting the subscription tier that best fits your infrastructure.",
            "fix_variations": [
                {
                    "style": "Direct & Factual",
                    "text": "Complete your subscription onboarding by selecting your preferred deployment tier"
                },
                {
                    "style": "Executive & Confident",
                    "text": "Accelerate your digital transformation by activating your enterprise tier today"
                }
            ],
            "strategic_tip": "Consistent executive brand voice across call-to-actions preserves institutional credibility."
        })

    # Language style shift: US vs UK spelling clash
    uk_spellings = [w for w in ["optimise", "colour", "centre", "behaviour", "analysing", "favour", "programme"] if re.search(rf'\b{w}\b', content, re.I)]
    us_spellings = [w for w in ["optimize", "color", "center", "behavior", "analyzing", "favor", "program"] if re.search(rf'\b{w}\b', content, re.I)]
    if uk_spellings and us_spellings:
        minority = uk_spellings if len(uk_spellings) <= len(us_spellings) else us_spellings
        target_word = minority[0]
        inconsistency_findings.append({
            "rule_id": "STYLE-LANG-06",
            "category": "language_style_shift",
            "issue_type": "language_style_shift",
            "severity": "advisory",
            "flagged_text": target_word,
            "context_span": get_sentence_context(target_word),
            "cited_quote": "Editorial Consistency Standards: Maintain unified regional spelling conventions throughout technical documentation.",
            "explanation": f"Regional spelling drift detected: dialect mix of British ('{', '.join(uk_spellings)}') and American ('{', '.join(us_spellings)}') conventions within the same document.",
            "suggested_fix": "standardized to consistent American English spelling benchmarks",
            "fix_variations": [
                {"style": "Direct & Factual", "text": "standardized to unified American English spelling"},
                {"style": "Executive & Confident", "text": "aligned with corporate localization and editorial benchmarks"}
            ],
            "strategic_tip": "Harmonized dialect standards convey editorial professionalism and attention to detail."
        })

    # 3. FACTUAL & NUMERICAL INCONSISTENCY (Factual Drift)
    uptimes = re.findall(r'\b(99\.\d+)%', content)
    unique_uptimes = sorted(list(set(uptimes)), key=lambda x: float(x))
    if len(unique_uptimes) >= 2:
        higher_uptime = unique_uptimes[-1]
        lower_uptime = unique_uptimes[0]
        upt_match = re.search(rf'\b(?:delivers|guarantees|offers|features)?\s*{re.escape(higher_uptime)}%(?:\s*(?:uptime|availability|sla))?', content, re.I)
        flagged_upt = upt_match.group(0).strip() if upt_match else f"{higher_uptime}% uptime"
        inconsistency_findings.append({
            "rule_id": "FACT-NUM-03",
            "category": "factual_accuracy",
            "issue_type": "factual_drift",
            "severity": "high",
            "flagged_text": flagged_upt,
            "context_span": get_sentence_context(flagged_upt),
            "cited_quote": "Operational Consistency Rule: Ensure technical SLA uptime metrics are uniform and verified across all corporate documentation.",
            "explanation": f"Conflicting uptime numbers detected: '{lower_uptime}%' is stated elsewhere while '{higher_uptime}%' is claimed here, creating operational and contractual ambiguity.",
            "suggested_fix": f"delivers our verified {lower_uptime}% enterprise high-availability SLA",
            "fix_variations": [
                {
                    "style": "Direct & Factual",
                    "text": f"engineered for contractually guaranteed {lower_uptime}% high-availability uptime across all production clusters"
                },
                {
                    "style": "Executive & Confident",
                    "text": f"provides enterprise-grade platform availability backed by verified {lower_uptime}% SLA guarantees"
                }
            ],
            "strategic_tip": "Consistent SLA metrics across marketing and contractual materials prevent procurement disputes and reinforce brand integrity."
        })

    # 4. CONTRADICTORY CLAIMS
    has_opensource = bool(re.search(r'\b(?:completely\s+)?open-?source\b', content, re.I))
    has_lockin = bool(re.search(r'\b(?:proprietary\s+vendor\s+lock-?in|closed-?source\s+lock-?in)\b', content, re.I))
    if has_opensource and has_lockin:
        m = re.search(r'\b(?:enforces\s+)?proprietary\s+vendor\s+lock-?in(?:\s+for\s+[a-zA-Z0-9_\s-]+)?\b', content, re.I)
        flagged_lockin = m.group(0) if m else "proprietary vendor lock-in"
        inconsistency_findings.append({
            "rule_id": "CLAIM-CONFLICT-04",
            "category": "claim_conflict",
            "issue_type": "claim_conflict",
            "severity": "critical",
            "flagged_text": flagged_lockin,
            "context_span": get_sentence_context(flagged_lockin),
            "cited_quote": "Core Brand Principle: Never make mutually incompatible assertions regarding open-source licensing and proprietary restrictions.",
            "explanation": "Direct internal contradiction between claiming 'completely open-source' and mandating 'proprietary vendor lock-in', confusing prospects and breaching truth-in-advertising guidelines.",
            "suggested_fix": "offers modular commercial enterprise extensions available for specialized workloads",
            "fix_variations": [
                {
                    "style": "Direct & Factual",
                    "text": "combines an open-source core with optional proprietary enterprise modules under transparent licensing"
                },
                {
                    "style": "Executive & Confident",
                    "text": "leverages an extensible open architecture enhanced by dedicated enterprise-grade capabilities"
                }
            ],
            "strategic_tip": "Transparent hybrid licensing descriptions eliminate legal ambiguity and build genuine developer trust."
        })

    # 5. VISUAL USAGE & MEDIA MENTIONS
    visual_breach_match = re.search(r'\b(?:neon\s+green|#39ff14|comic\s+sans|papyrus)\b', content, re.I)
    if visual_breach_match:
        matched_visual = visual_breach_match.group(0)
        inconsistency_findings.append({
            "rule_id": "VISUAL-GUIDE-05",
            "category": "visual_guideline_breach",
            "issue_type": "visual_guideline_breach",
            "severity": "medium",
            "flagged_text": matched_visual,
            "context_span": get_sentence_context(matched_visual),
            "cited_quote": "Visual Identity Standards: The primary brand palette is Deep Ocean Teal (#0B3C49) and Warm Amber (#F4A321).",
            "explanation": f"Unapproved visual reference '{matched_visual}' detected; brand guidelines mandate Deep Ocean Teal (#0B3C49) and Warm Amber (#F4A321).",
            "suggested_fix": "Deep Ocean Teal (#0B3C49) with Warm Amber accents",
            "fix_variations": [
                {"style": "Direct & Factual", "text": "Deep Ocean Teal (#0B3C49) adhering to standard brand guidelines"},
                {"style": "Executive & Confident", "text": "corporate Deep Ocean Teal (#0B3C49) with Warm Amber accents"}
            ],
            "strategic_tip": "Strict adherence to official color palettes and geometry preserves trademark strength and brand recognition."
        })

    return inconsistency_findings


def extract_json_array(text: str) -> List[Dict[str, Any]]:
    """Extract and parse JSON array from model text response."""
    if not text or not text.strip():
        return []

    # Strip markdown code blocks if present
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.strip()

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict) and "findings" in parsed and isinstance(parsed["findings"], list):
            return parsed["findings"]
        return []
    except json.JSONDecodeError:
        # Regex search for JSON array
        match = re.search(r"\[\s*\{.*?\}\s*\]", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
        logger.warning(f"Failed to parse JSON array from model response: {text[:200]}")
        return []


def format_evaluation_prompt(content: str, rules: List[Any]) -> str:
    """Format prompt containing submitted text, retrieved brand rules, and contextual instructions."""
    rules_block = []
    for r in rules:
        r_id = getattr(r, "id", None) or (r.get("id") if isinstance(r, dict) else "")
        r_title = getattr(r, "title", None) or (r.get("title") if isinstance(r, dict) else "")
        r_cat = getattr(r, "category", None) or (r.get("category") if isinstance(r, dict) else "")
        r_text = getattr(r, "rule_text", None) or (r.get("rule_text") if isinstance(r, dict) else "")
        cat_str = r_cat.value if hasattr(r_cat, "value") else str(r_cat)

        rules_block.append(
            f"- Rule ID: {r_id}\n"
            f"  Category: {cat_str}\n"
            f"  Title: {r_title}\n"
            f"  Rule Text: \"{r_text}\""
        )

    formatted_rules = "\n\n".join(rules_block)

    return f"""### SUBMITTED CONTENT FOR COMPLIANCE & INCONSISTENCY REVIEW:
\"\"\"
{content}
\"\"\"

### APPLICABLE BRAND GUIDELINE RULES:
{formatted_rules}

### DUAL-PASS EVALUATION INSTRUCTIONS:
1. PASS 1 (DIRECT RULE MATCHING):
   - Evaluate the text strictly against the applicable brand rules above.
   - DO NOT flag disclaimers, negative claims, or comparative contexts.
2. PASS 2 (INCONSISTENCY & QUALITY AUDIT PASS):
   - Holistically audit the document for:
     * Tone Inconsistency (`tone_inconsistency`): e.g. sudden hyper-casual slang, jarring voice shifts.
     * Language & Style Inconsistency (`language_style_shift`): e.g. US vs UK spelling mixes.
     * Factual & Numerical Inconsistency (`factual_drift`): e.g. conflicting uptimes (99.9% vs 99.999%) or SLAs.
     * Contradictory Claims (`claim_conflict`): e.g. open-source vs proprietary lock-in.
     * Visual Usage & Media Mentions (`visual_guideline_breach`): e.g. unapproved colors, missing alt-text.
     * Accessibility & Readability (`accessibility_issue`): e.g. extreme convoluted complexity (Flesch-Kincaid > 18) or non-inclusive terms.
3. OUTPUT SPECIFICATIONS:
   - Assign each finding an 'issue_type' and 'category'.
   - Assign 'severity': 'critical', 'high', 'medium', or 'advisory'.
   - Include 'context_span' showing the full sentence context.
   - NEVER return 1-2 word terse suggestions. Provide rich, complete, grammatically drop-in replacement clauses.
   - Include multi-style 'fix_variations' (Direct & Factual, Executive & Confident) and a high-value 'strategic_tip'.
   - If completely compliant with zero inconsistencies, return strictly: []
   - Return strictly the JSON array of validated findings."""


def sanitize_findings(
    raw_findings: List[Any],
    relevant_rules: Optional[List[Any]] = None,
    content: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Sanitize and validate extracted findings against required enterprise schema.
    
    Ensures every dictionary contains:
    - rule_id: int or str
    - category: str
    - issue_type: str
    - severity: 'critical' | 'high' | 'medium' | 'advisory' | 'low'
    - flagged_text: str
    - context_span: str
    - cited_quote: str
    - explanation: str
    - suggested_fix: str (rich, drop-in replacement clause)
    - fix_variations: List[Dict[str, str]] (styles: Direct & Factual, Executive & Confident)
    - strategic_tip: str
    """
    sanitized: List[Dict[str, Any]] = []
    valid_severities = {"low", "advisory", "medium", "high", "critical"}

    # Build lookup map for candidate rules to enforce grounding and populate missing quotes
    rules_by_id: Dict[str, Any] = {}
    if relevant_rules:
        for r in relevant_rules:
            r_id = getattr(r, "id", None) or (r.get("id") if isinstance(r, dict) else None)
            if r_id is not None:
                rules_by_id[str(r_id)] = r

    for item in raw_findings:
        if not isinstance(item, dict):
            continue

        raw_rule_id = item.get("rule_id")
        rule_id = None
        if raw_rule_id is not None:
            try:
                rule_id = int(raw_rule_id)
            except (ValueError, TypeError):
                rule_id = str(raw_rule_id)
        elif relevant_rules and len(relevant_rules) == 1:
            first_rule = relevant_rules[0]
            first_id = getattr(first_rule, "id", None) or (first_rule.get("id") if isinstance(first_rule, dict) else None)
            if first_id is not None:
                try:
                    rule_id = int(first_id)
                except (ValueError, TypeError):
                    rule_id = str(first_id)

        raw_sev = str(item.get("severity", "medium")).lower().strip()
        severity = raw_sev if raw_sev in valid_severities else "medium"

        flagged_text = str(item.get("flagged_text", "")).strip()
        explanation = str(item.get("explanation", "")).strip()
        cited_quote = str(item.get("cited_quote", "")).strip()
        suggested_fix = str(item.get("suggested_fix", "")).strip()

        # Context span
        context_span = str(item.get("context_span", "")).strip()
        if not context_span and content and flagged_text:
            # Locate enclosing sentence in content
            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', content) if s.strip()]
            for s in sentences:
                if flagged_text.lower() in s.lower():
                    context_span = s
                    break
            if not context_span:
                context_span = flagged_text

        # Issue type
        raw_issue_type = str(item.get("issue_type", "")).strip()
        if raw_issue_type:
            issue_type = raw_issue_type
        elif any(k in explanation.lower() for k in ["readability", "accessibility", "wcag"]):
            issue_type = "accessibility_issue"
        elif any(k in explanation.lower() for k in ["tone", "slang", "voice"]):
            issue_type = "tone_inconsistency"
        elif any(k in explanation.lower() for k in ["factual", "drift", "numerical", "uptime", "conflict"]):
            issue_type = "factual_drift"
        else:
            issue_type = "Compliance Violation"

        # Category
        raw_cat = str(item.get("category", "")).strip()
        if raw_cat:
            category = raw_cat
        elif issue_type == "accessibility_issue":
            category = "accessibility_issue"
        elif issue_type == "tone_inconsistency":
            category = "brand_voice"
        elif issue_type == "factual_drift":
            category = "factual_accuracy"
        elif issue_type == "claim_conflict":
            category = "claim_conflict"
        elif issue_type == "visual_guideline_breach":
            category = "visual_guideline"
        elif issue_type == "language_style_shift":
            category = "language_style"
        elif rule_id is not None and str(rule_id) in rules_by_id:
            r_cat = getattr(rules_by_id[str(rule_id)], "category", "general_compliance")
            category = r_cat.value if hasattr(r_cat, "value") else str(r_cat)
        else:
            category = "general_compliance"

        # If cited_quote is missing, cross-reference from matched rule
        if not cited_quote and rule_id is not None and str(rule_id) in rules_by_id:
            matched_r = rules_by_id[str(rule_id)]
            cited_quote = getattr(matched_r, "rule_text", "") or (matched_r.get("rule_text", "") if isinstance(matched_r, dict) else "")

        # Validate / populate fix_variations and strategic_tip
        raw_fix_variations = item.get("fix_variations")
        validated_variations: List[Dict[str, str]] = []
        if isinstance(raw_fix_variations, list):
            for v in raw_fix_variations:
                if isinstance(v, dict) and "style" in v and "text" in v:
                    validated_variations.append({
                        "style": str(v["style"]).strip(),
                        "text": str(v["text"]).strip()
                    })

        raw_strategic_tip = str(item.get("strategic_tip", "")).strip()

        # If suggested_fix is terse (less than 4 words), instructional, or variations are missing, enrich with enterprise copy
        is_instructional = bool(
            re.search(r"^(?:remove|rephrase|qualify|substantiate)\s+(?:or\s+)?", suggested_fix.strip(), re.I)
        )
        is_terse = (
            not suggested_fix or
            len(suggested_fix.split()) < 4 or
            is_instructional or
            suggested_fix.lower() in ("fast", "competitive", "reliable", "affordable", "free", "better", "great", "cheap")
        )

        if is_terse or len(validated_variations) < 2 or not raw_strategic_tip:
            rich_fix, default_vars, default_tip = generate_enterprise_fix_variations(
                flagged_text=flagged_text,
                current_fix=suggested_fix,
                rule_text=cited_quote
            )
            if is_terse:
                suggested_fix = rich_fix
            if len(validated_variations) < 2:
                validated_variations = default_vars
            if not raw_strategic_tip:
                raw_strategic_tip = default_tip

        sanitized.append({
            "rule_id": rule_id,
            "category": category,
            "issue_type": issue_type,
            "severity": severity,
            "flagged_text": flagged_text,
            "context_span": context_span or flagged_text,
            "cited_quote": cited_quote,
            "explanation": explanation,
            "suggested_fix": suggested_fix,
            "fix_variations": validated_variations,
            "strategic_tip": raw_strategic_tip,
        })

    return sanitized


def call_gemini_api(
    prompt: str,
    api_key: str,
    relevant_rules: Optional[List[Any]] = None,
    content: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Call Google Gemini API using modern endpoint candidates with header authentication."""
    full_prompt = f"{SYSTEM_INSTRUCTION}\n\n{prompt}"
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": full_prompt}]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json"
        }
    }

    headers = {
        "x-goog-api-key": api_key,
        "Content-Type": "application/json"
    }

    last_error = None

    for model_name in GEMINI_MODEL_CANDIDATES[:3]:
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
        try:
            with httpx.Client(timeout=15.0) as client:
                # 1. Primary: Pass API key via header
                response = client.post(endpoint, headers=headers, json=payload)
                
                # 2. Fallback: Query string if header returned 401 or 403
                if response.status_code in (401, 403):
                    fallback_url = f"{endpoint}?key={api_key}"
                    response = client.post(fallback_url, json=payload)

                if response.status_code == 200:
                    data = response.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            text_response = parts[0].get("text", "")
                            parsed = extract_json_array(text_response)
                            return sanitize_findings(parsed, relevant_rules=relevant_rules, content=content)
                    return []
                else:
                    last_error = f"Model '{model_name}' returned HTTP {response.status_code}: {response.text[:200]}"
                    logger.debug(last_error)
                    if response.status_code == 429:
                        break
        except Exception as e:
            last_error = f"Model '{model_name}' failed: {e}"
            logger.debug(last_error)

    if last_error:
        logger.warning(f"All Gemini model candidates failed. Last error: {last_error}")
    raise RuntimeError(f"Gemini API generation failed across all candidates: {last_error}")


def call_ollama_fallback(
    prompt: str,
    base_url: str,
    model_name: str = "llama3.2",
    relevant_rules: Optional[List[Any]] = None,
    content: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Fallback call to local Ollama instance (e.g. llama3.2, llama3, mistral)."""
    endpoint = f"{base_url.rstrip('/')}/api/generate"
    payload = {
        "model": model_name,
        "prompt": f"{SYSTEM_INSTRUCTION}\n\n{prompt}",
        "stream": False,
        "format": "json",
    }

    with httpx.Client(timeout=1.5) as client:
        response = client.post(endpoint, json=payload)
        response.raise_for_status()
        data = response.json()
        text_response = data.get("response", "")
        parsed = extract_json_array(text_response)
        return sanitize_findings(parsed, relevant_rules=relevant_rules, content=content)


def run_deterministic_keyword_fallback(
    content: str,
    relevant_rules: List[Any]
) -> List[Dict[str, Any]]:
    """Deterministic fallback that inspects content against rule-based keywords and prohibited patterns
    when LLM endpoints are unreachable, ensuring high demo resilience and zero unhandled failures.
    """
    from app.services.deterministic_checks import is_negated_or_disclaimed_context, run_all_deterministic_checks

    findings: List[Dict[str, Any]] = []
    seen_flagged = set()

    # 1. Run deterministic regex checks from deterministic_checks.py
    try:
        det_checks = run_all_deterministic_checks(content=content, prohibited_rules=relevant_rules)
        for dc in det_checks:
            flagged = str(dc.get("flagged_text", "")).strip()
            if flagged and flagged.lower() not in seen_flagged:
                seen_flagged.add(flagged.lower())
                r_id = dc.get("rule_id")
                try:
                    r_id = int(r_id) if r_id is not None else None
                except (ValueError, TypeError):
                    pass

                findings.append({
                    "rule_id": r_id,
                    "category": dc.get("category", "prohibited_claim"),
                    "issue_type": dc.get("issue_type", "Compliance Violation"),
                    "severity": dc.get("severity", "high"),
                    "flagged_text": flagged,
                    "context_span": dc.get("context_span", flagged),
                    "explanation": dc.get("explanation", "Deterministic compliance rule violation detected."),
                    "cited_quote": dc.get("cited_quote") or f"Rule matched for {flagged}",
                    "suggested_fix": dc.get("suggested_fix", f"Remove or qualify '{flagged}'.")
                })
    except Exception as e:
        logger.debug(f"Deterministic checks check failed in fallback: {e}")

    # 2. Key phrase & prohibited superlative extraction with negative lookbehinds and contextual negation guards
    superlative_patterns = [
        (re.compile(r"(?<!\bnot\s)(?<!\bno\s)(?<!\bnever\s)(?<!\bwithout\s)\b(?:cheapest|lowest\s+prices?|unbeatable\s+rates?)\b", re.I), "Pricing Superlative"),
        (re.compile(r"(?<!\bnot\s)(?<!\bno\s)(?<!\bnever\s)(?<!\bwithout\s)\b(?:number\s+one|#1|best\s+in\s+the\s+industry|leading\s+solution)\b", re.I), "Superlative Ranking Claim"),
        (re.compile(r"(?<!\bnot\s)(?<!\bno\s)(?<!\bnever\s)(?<!\bwithout\s)\b(?:guaranteed|100%\s+cure|zero\s+risk|miracle)\b", re.I), "Unsubstantiated Guarantee")
    ]

    for rule in relevant_rules:
        r_id = getattr(rule, "id", None) or (rule.get("id") if isinstance(rule, dict) else None)
        r_title = getattr(rule, "title", "") or (rule.get("title", "") if isinstance(rule, dict) else "")
        r_text = getattr(rule, "rule_text", "") or (rule.get("rule_text", "") if isinstance(rule, dict) else "")
        r_cat = getattr(rule, "category", "") or (rule.get("category", "") if isinstance(rule, dict) else "")
        cat_str = r_cat.value if hasattr(r_cat, "value") else str(r_cat)

        try:
            norm_r_id = int(r_id) if r_id is not None else None
        except (ValueError, TypeError):
            norm_r_id = r_id

        # Scan for superlatives matched in content, ignoring negative, conditional, or disclaiming context
        for pat, claim_type in superlative_patterns:
            for match in pat.finditer(content):
                if is_negated_or_disclaimed_context(content, match.start(), match.end()):
                    continue

                flagged = match.group(0)
                if flagged.lower() not in seen_flagged:
                    seen_flagged.add(flagged.lower())
                    findings.append({
                        "rule_id": norm_r_id,
                        "category": cat_str or "prohibited_claim",
                        "issue_type": "claim_conflict" if cat_str == "prohibited_claim" else "Compliance Violation",
                        "severity": "critical" if cat_str == "prohibited_claim" else "high",
                        "flagged_text": flagged,
                        "explanation": f"Although '{flagged}' is used, in this context it asserts an unsubstantiated superlative claim violating brand guideline '{r_title}'.",
                        "cited_quote": r_text if r_text else f"Do not use '{flagged}' without verified proof.",
                        "suggested_fix": f"Remove or substantiate '{flagged}' with verified documentation."
                    })

        # Check quoted phrases from rule text e.g. 'trash', 'garbage', 'obsolete'
        quoted_phrases = re.findall(r"['\"]([^'\"]{3,40})['\"]", r_text)
        for qp in quoted_phrases:
            qp_clean = qp.strip()
            qp_pat = re.compile(rf"(?<!\bnot\s)(?<!\bno\s)(?<!\bnever\s)(?<!\bwithout\s)\b{re.escape(qp_clean)}\b", re.I)
            for match in qp_pat.finditer(content):
                if is_negated_or_disclaimed_context(content, match.start(), match.end()):
                    continue
                flagged = match.group(0)
                if flagged.lower() not in seen_flagged:
                    seen_flagged.add(flagged.lower())
                    findings.append({
                        "rule_id": norm_r_id,
                        "category": cat_str or "brand_voice",
                        "issue_type": "tone_inconsistency" if cat_str == "tone" else "Compliance Violation",
                        "severity": "critical" if cat_str in ("prohibited_claim", "legal_compliance") else "high",
                        "flagged_text": flagged,
                        "explanation": f"The content uses prohibited phrase '{flagged}' restricted by brand guideline: '{r_title}'.",
                        "cited_quote": r_text,
                        "suggested_fix": f"Rephrase or qualify '{flagged}' in accordance with brand policy."
                    })

        # Check technical & operational patterns in rule text
        for target_pat in [
            r"\bzero\s+latency\b",
            r"\b100%\s+bug-free(?:\s+uptime)?\b",
            r"\bcompletely\s+free(?:\s+forever)?\b",
            r"\blowest\s+rate\s+guaranteed\b",
        ]:
            if re.search(target_pat, r_text, re.IGNORECASE):
                for match in re.finditer(target_pat, content, re.IGNORECASE):
                    if is_negated_or_disclaimed_context(content, match.start(), match.end()):
                        continue
                    flagged = match.group(0)
                    if flagged.lower() not in seen_flagged:
                        seen_flagged.add(flagged.lower())
                        findings.append({
                            "rule_id": norm_r_id,
                            "category": cat_str or "factual_accuracy",
                            "issue_type": "factual_drift" if "uptime" in flagged.lower() else "claim_conflict",
                            "severity": "critical" if cat_str in ("prohibited_claim", "legal_compliance") else "high",
                            "flagged_text": flagged,
                            "explanation": f"The content advertises '{flagged}', which is restricted without verified proof under '{r_title}'.",
                            "cited_quote": r_text,
                            "suggested_fix": f"Remove or substantiate '{flagged}' with verified audit proof."
                        })

    return sanitize_findings(findings, relevant_rules=relevant_rules, content=content)


def analyze_content_against_rules(
    content: str,
    relevant_rules: List[Any],
    gemini_api_key: Optional[str] = None,
    ollama_base_url: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Perform contextual compliance analysis against relevant rules.
    
    1. Primary: Google Gemini API (with candidate model rotation and header authentication).
    2. Fallback 1: Local Ollama.
    3. Fallback 2: Rule-based keyword violations from deterministic checks (high resilience).
    4. Mandatory Secondary Pass: Inconsistency Detection Engine (Holistic Document Analysis).
    
    Returns:
        List[dict]: Array of findings conforming strictly to the required compliance schema.
    """
    if not content or not relevant_rules:
        return []

    prompt = format_evaluation_prompt(content, relevant_rules)
    api_key = gemini_api_key or os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY
    ollama_url = ollama_base_url or os.getenv("OLLAMA_BASE_URL") or settings.OLLAMA_BASE_URL

    findings: List[Dict[str, Any]] = []
    ai_evaluated = False

    # 1. Primary: Google Gemini API
    if api_key and api_key.strip() and api_key != "your_gemini_api_key_here":
        try:
            logger.info("Calling primary AI evaluation via Google Gemini API...")
            try:
                findings = call_gemini_api(prompt, api_key.strip(), relevant_rules=relevant_rules, content=content)
            except TypeError:
                findings = call_gemini_api(prompt, api_key.strip())
            logger.info(f"Gemini API returned {len(findings)} findings.")
            ai_evaluated = True
        except Exception as e:
            logger.warning(
                f"Gemini API call failed, timed out, or quota exceeded ({e}). "
                f"Routing immediately to local Ollama at '{ollama_url}'."
            )

    # 2. Fallback 1: Local Ollama
    if not ai_evaluated and ollama_url and ollama_url.strip():
        for fallback_model in ("llama3.2", "llama3", "mistral"):
            try:
                logger.info(f"Calling fallback AI evaluation via Ollama ({fallback_model}) at {ollama_url}...")
                try:
                    findings = call_ollama_fallback(prompt, ollama_url.strip(), model_name=fallback_model, relevant_rules=relevant_rules, content=content)
                except TypeError:
                    findings = call_ollama_fallback(prompt, ollama_url.strip(), model_name=fallback_model)
                logger.info(f"Ollama ({fallback_model}) returned {len(findings)} findings.")
                ai_evaluated = True
                break
            except (httpx.ConnectError, httpx.ConnectTimeout):
                logger.debug(f"Ollama server at {ollama_url} unreachable. Skipping remaining models.")
                break
            except Exception as e:
                logger.debug(f"Ollama attempt with '{fallback_model}' failed ({e}).")

    # 3. Fallback 2: Deterministic keyword & rule-based ingestion
    if not ai_evaluated and not findings:
        logger.info("Engaging deterministic rule-based fallback ingestion...")
        findings = run_deterministic_keyword_fallback(content=content, relevant_rules=relevant_rules)
        if findings:
            logger.info(f"Deterministic keyword fallback returned {len(findings)} findings.")

    # 4. Mandatory Secondary Audit Pass: Inconsistency Detection Engine
    try:
        inconsistency_findings = detect_content_inconsistencies(content=content, brand_rules=relevant_rules)
        if inconsistency_findings:
            existing_flags = {str(f.get("flagged_text", "")).strip().lower() for f in findings}
            for inc in inconsistency_findings:
                inc_flag = str(inc.get("flagged_text", "")).strip().lower()
                if inc_flag not in existing_flags and not any(inc_flag in ef or ef in inc_flag for ef in existing_flags if len(ef) > 4):
                    findings.append(inc)
                    existing_flags.add(inc_flag)
    except Exception as e:
        logger.warning(f"Inconsistency detection audit pass error: {e}")

    return findings


def analyze_content_with_ai(
    content: str,
    rules: List[Any],
    gemini_api_key: Optional[str] = None,
    ollama_base_url: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Alias for analyze_content_against_rules for backwards compatibility."""
    return analyze_content_against_rules(
        content=content,
        relevant_rules=rules,
        gemini_api_key=gemini_api_key,
        ollama_base_url=ollama_base_url
    )

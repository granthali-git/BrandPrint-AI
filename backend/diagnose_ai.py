import json
import os
from app.core.database import SessionLocal
from app.models.guideline import GuidelineRule
from app.services.ai_service import analyze_content_against_rules
from app.services.vector_store import index_brand_rules, retrieve_relevant_rules
from dotenv import load_dotenv

load_dotenv()

db = SessionLocal()

print('=== 1. CHECKING RULES IN DB ===')
rules = (
    db.query(GuidelineRule)
    .filter(GuidelineRule.brand_id == 1, GuidelineRule.is_active == True)
    .all()
)
print(f'Active rules for Brand 1: {len(rules)}')
for r in rules:
  cat_val = r.category.value if hasattr(r.category, 'value') else str(r.category)
  print(f' - ID {r.id} [{cat_val}]: {r.title} -> "{r.rule_text}"')

rule_dicts = [
    {
        'id': r.id,
        'title': r.title,
        'rule_text': r.rule_text,
        'category': (
            r.category.value
            if hasattr(r.category, 'value')
            else str(r.category)
        ),
    }
    for r in rules
]

print('\n=== 2. CHECKING VECTOR STORE RETRIEVAL ===')
index_brand_rules(1, rule_dicts)
sample_text = (
    'We provide the cheapest rates and are guaranteed number one in the'
    ' industry.'
)
retrieved = retrieve_relevant_rules(1, sample_text, top_k=3)
print(f'Retrieved {len(retrieved)} rules from FAISS:')
for r in retrieved:
  print('  Matched:', r.get('title'))

print('\n=== 3. CHECKING AI ENGINE (GEMINI / OLLAMA) ===')
api_key = os.getenv('GEMINI_API_KEY')
print(
    'GEMINI_API_KEY set?:',
    bool(api_key and api_key != 'your_gemini_api_key_here'),
)
ai_findings = analyze_content_against_rules(sample_text, retrieved)
print(f'Raw AI Findings ({len(ai_findings)}):')
print(json.dumps(ai_findings, indent=2))

db.close()
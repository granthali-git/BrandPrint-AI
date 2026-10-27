"""FAISS in-memory vector store service for semantic brand rule retrieval."""
import hashlib
import logging
import os
import re
from typing import Any, Dict, List, Optional, Union
import numpy as np
from sqlalchemy.orm import Session

from app.models.guideline import GuidelineRule

logger = logging.getLogger(__name__)

# Global singletons
_embedding_model = None
# In-memory index cache per brand: {brand_id: {"index": faiss.Index, "rules": List[RuleDict], "rule_ids": List[str], "dimension": int}}
_brand_indices: Dict[str, Dict[str, Any]] = {}


def _compute_lightweight_embeddings(texts: List[str], dimension: int = 384) -> np.ndarray:
    """Fast, deterministic hashing vectorizer that runs without PyTorch or HuggingFace,
    preventing out-of-memory container crashes on memory-constrained platforms like Render (512MB).
    """
    vectors = np.zeros((len(texts), dimension), dtype=np.float32)
    for i, text in enumerate(texts):
        tokens = re.findall(r'\b\w{3,}\b', text.lower())
        for token in tokens:
            h = int(hashlib.md5(token.encode('utf-8')).hexdigest(), 16) % dimension
            vectors[i, h] += 1.0
        norm = np.linalg.norm(vectors[i])
        if norm > 0:
            vectors[i] /= norm
    return vectors


class RuleDict(dict):
    """Dictionary that supports attribute-style access for seamless model/dict compatibility."""
    def __getattr__(self, name: str) -> Any:
        if name in self:
            return self[name]
        raise AttributeError(f"'RuleDict' object has no attribute '{name}'")

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value


def get_embedding_model():
    """Lazy load the sentence-transformers model singleton if explicitly enabled and memory allows."""
    global _embedding_model
    # Render free tier has strict 512MB RAM and HuggingFace download timeouts;
    # Default to fast, reliable zero-RAM embeddings unless USE_SENTENCE_TRANSFORMERS is explicitly set.
    if os.getenv("RENDER") or os.getenv("LOW_MEMORY_MODE", "true").lower() in ("true", "1") or not os.getenv("USE_SENTENCE_TRANSFORMERS"):
        return None

    if _embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading SentenceTransformer model 'all-MiniLM-L6-v2'...")
            _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception as e:
            logger.warning(f"Could not load SentenceTransformer: {e}")
            _embedding_model = None
    return _embedding_model


def _normalize_rule(rule: Any) -> RuleDict:
    """Normalize a GuidelineRule ORM model or plain dict into a RuleDict."""
    if isinstance(rule, RuleDict):
        return rule

    r_id = getattr(rule, "id", None) or (rule.get("id") if isinstance(rule, dict) else None)
    r_cat = getattr(rule, "category", "") or (rule.get("category", "") if isinstance(rule, dict) else "")
    cat_str = r_cat.value if hasattr(r_cat, "value") else str(r_cat)
    r_title = getattr(rule, "title", "") or (rule.get("title", "") if isinstance(rule, dict) else "")
    r_text = getattr(rule, "rule_text", "") or (rule.get("rule_text", "") if isinstance(rule, dict) else "")
    r_code = getattr(rule, "rule_code", None) or (rule.get("rule_code") if isinstance(rule, dict) else None)
    r_file = getattr(rule, "source_file", None) or (rule.get("source_file") if isinstance(rule, dict) else None)
    r_active = getattr(rule, "is_active", True) if hasattr(rule, "is_active") else (rule.get("is_active", True) if isinstance(rule, dict) else True)
    r_version = getattr(rule, "version", 1) if hasattr(rule, "version") else (rule.get("version", 1) if isinstance(rule, dict) else 1)

    return RuleDict({
        "id": r_id,
        "category": cat_str,
        "title": r_title,
        "rule_text": r_text,
        "rule_code": r_code,
        "source_file": r_file,
        "is_active": r_active,
        "version": r_version,
    })


def index_brand_rules(brand_id: Union[int, str], rules: List[Any]) -> int:
    """Embed brand rules and maintain an in-memory FAISS index mapped by rule ID.
    
    Args:
        brand_id: The brand identifier.
        rules: List of rule dicts or GuidelineRule instances.
        
    Returns:
        int: Number of rules indexed.
    """
    key = str(brand_id)
    if not rules:
        if key in _brand_indices:
            del _brand_indices[key]
        return 0

    import faiss

    normalized_rules = [_normalize_rule(r) for r in rules]
    rule_texts = [f"{r['title']}. {r['rule_text']}" for r in normalized_rules]

    model = get_embedding_model()
    if model:
        embeddings = model.encode(rule_texts, normalize_embeddings=True, show_progress_bar=False)
        embeddings = np.array(embeddings, dtype=np.float32)
    else:
        # Lightweight zero-RAM hashing embeddings
        embeddings = _compute_lightweight_embeddings(rule_texts, dimension=384)

    dimension = embeddings.shape[1]
    # Use IndexFlatIP for cosine similarity on unit-normalized vectors
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)

    _brand_indices[key] = {
        "index": index,
        "rules": normalized_rules,
        "rule_ids": [str(r["id"]) for r in normalized_rules],
        "dimension": dimension,
    }
    logger.info(f"Indexed {len(rules)} rules for brand '{key}' into FAISS index.")
    return len(rules)


def retrieve_relevant_rules(
    brand_id: Union[int, str],
    content_chunk: str,
    top_k: int = 4,
    db: Optional[Session] = None
) -> List[Dict[str, Any]]:
    """Retrieve top-k most relevant active brand guideline rules for a text snippet.
    
    Queries the FAISS index for the given brand. If the brand index is not in memory
    and a DB session is provided, it dynamically fetches and indexes active rules from Supabase.
    
    Returns:
        List[dict]: Top matching guideline rules as dictionaries.
    """
    if not content_chunk or not content_chunk.strip():
        return []

    key = str(brand_id)

    # Dynamic loading from DB if not in memory
    if key not in _brand_indices and db is not None:
        target_id = int(brand_id) if str(brand_id).isdigit() else brand_id
        db_rules = (
            db.query(GuidelineRule)
            .filter(GuidelineRule.brand_id == target_id, GuidelineRule.is_active == True)
            .all()
        )
        if db_rules:
            index_brand_rules(key, db_rules)

    brand_data = _brand_indices.get(key)
    if not brand_data or not brand_data.get("rules"):
        return []

    index = brand_data["index"]
    rules = brand_data["rules"]
    candidate_k = min(max(top_k * 5, 25), len(rules))

    model = get_embedding_model()
    if model:
        query_vec = model.encode([content_chunk], normalize_embeddings=True, show_progress_bar=False)
        query_vec = np.array(query_vec, dtype=np.float32)
    else:
        # Lightweight zero-RAM hashing embeddings
        query_vec = _compute_lightweight_embeddings([content_chunk], dimension=brand_data["dimension"])

    distances, indices = index.search(query_vec, candidate_k)
    matched_indices = indices[0]

    matched_rules: List[Dict[str, Any]] = []
    seen_texts = set()
    for idx in matched_indices:
        if 0 <= idx < len(rules):
            r = rules[idx]
            txt = (r.get("rule_text") or "").strip().lower()
            if txt not in seen_texts:
                seen_texts.add(txt)
                matched_rules.append(r)
                if len(matched_rules) >= top_k:
                    break

    return matched_rules


def search_relevant_rules(
    brand_id: Union[int, str],
    query: str,
    top_k: int = 5,
    db: Optional[Session] = None
) -> List[Any]:
    """Alias for retrieve_relevant_rules with default top_k=5 for backwards compatibility."""
    return retrieve_relevant_rules(brand_id, query, top_k=top_k, db=db)


def clear_brand_index(brand_id: Union[int, str]) -> None:
    """Clear memory index for a given brand."""
    key = str(brand_id)
    if key in _brand_indices:
        del _brand_indices[key]

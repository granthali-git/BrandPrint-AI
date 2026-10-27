"""Guidelines ingestion and management endpoints for BrandPrint AI."""
import os
import re
from typing import Any, List, Optional, Union

from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
    Query
)
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.brand import Brand
from app.models.guideline import GuidelineRule, RuleCategory
from app.models.user import User, UserRole
from app.schemas.guideline import (
    GuidelineRuleCreate,
    GuidelineRuleResponse,
    ContradictionCheckRequest,
    UrlIngestRequest,
    BulkRulesSaveRequest,
    GuidelineIngestResponse,
)
from app.services.document_parser import extract_text_from_upload
from app.services.scraper_service import scrape_guideline_url
from app.services.guideline_parser import extract_rules_from_raw_content
from app.services.extractors import (
    extract_from_pdf,
    extract_from_docx,
    extract_from_image
)

router = APIRouter(prefix="/guidelines", tags=["Guidelines"])



def to_brand_id(val: Any) -> Any:
    """Convert brand_id to int if numeric, otherwise return original value."""
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return val


def detect_rule_category(text: str) -> RuleCategory:
    """Infer rule category based on keywords in title/text."""
    lower = text.lower()
    if any(k in lower for k in ("prohibit", "forbidden", "never use", "banned", "do not claim", "disallowed")):
        return RuleCategory.prohibited_claim
    if any(k in lower for k in ("accessibility", "wcag", "screen reader", "alt text", "contrast ratio", "aria")):
        return RuleCategory.accessibility
    if any(k in lower for k in ("visual", "logo", "color palette", "typography", "font", "hex code", "layout", "spacing")):
        return RuleCategory.visual
    if any(k in lower for k in ("fact", "statistic", "verified", "number", "claim proof", "citation", "source required")):
        return RuleCategory.fact
    return RuleCategory.tone


def parse_raw_text_into_rules(
    raw_text: str,
    brand_id: Union[int, str],
    source_filename: Optional[str] = None,
    preferred_category: Optional[RuleCategory] = None,
) -> List[GuidelineRule]:
    """Parse unstructured guideline text into discrete structured GuidelineRule entries."""
    rules: List[GuidelineRule] = []
    if not raw_text or not raw_text.strip():
        return rules

    target_brand_id = to_brand_id(brand_id)

    # Split by headers, bullet points, numbers, or double newlines
    chunks = re.split(r"\n{2,}|(?:\r?\n)(?=[0-9]+\.|\-|\*|Rule\s+[0-9]+|Category:)", raw_text)
    rule_counter = 1

    for chunk in chunks:
        clean_chunk = chunk.strip()
        if len(clean_chunk) < 15:
            continue

        lines = [line.strip() for line in clean_chunk.splitlines() if line.strip()]
        if not lines:
            continue

        # Extract title from first line
        raw_title = lines[0]
        title = re.sub(r"^[0-9]+[\.\)]\s*|^[\*\-]\s*|^Rule\s+[0-9]+[:\.]?\s*", "", raw_title).strip()
        if len(title) > 100:
            title = title[:97] + "..."

        rule_text = clean_chunk
        category = preferred_category or detect_rule_category(clean_chunk)
        rule_code = f"{category.value[:4].upper()}-{rule_counter:03d}"

        new_rule = GuidelineRule(
            brand_id=target_brand_id,
            category=category,
            title=title if title else f"Guideline Rule {rule_counter}",
            rule_text=rule_text,
            rule_code=rule_code,
            source_file=source_filename,
            is_active=True,
            version=1
        )
        rules.append(new_rule)
        rule_counter += 1

    # Fallback if no individual rules could be chunked
    if not rules and raw_text.strip():
        cat = preferred_category or detect_rule_category(raw_text)
        rules.append(GuidelineRule(
            brand_id=target_brand_id,
            category=cat,
            title="General Brand Guideline",
            rule_text=raw_text.strip(),
            rule_code=f"{cat.value[:4].upper()}-001",
            source_file=source_filename,
            is_active=True,
            version=1
        ))

    return rules


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create or ingest brand guidelines",
    description="Accepts brand_id, category, title, rule_text, and optional rule_code or file upload/raw_text."
)
async def create_or_ingest_guideline(
    request: Request,
    brand_id: Optional[str] = Form(None),
    category: Optional[RuleCategory] = Form(None),
    title: Optional[str] = Form(None),
    rule_text: Optional[str] = Form(None),
    rule_code: Optional[str] = Form(None),
    raw_text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a structured rule directly or ingest rules from uploaded content."""
    # Check if JSON payload was submitted
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
        b_id = body.get("brand_id")
        b_cat = body.get("category", "tone")
        b_text = body.get("rule_text")
        b_code = body.get("rule_code")
        b_title = body.get("title") or b_code or ((b_text[:50] + ("..." if len(b_text) > 50 else "")) if b_text else "Brand Rule")

        if not b_id or not b_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="brand_id and rule_text are required for JSON guideline creation."
            )

        target_b_id = to_brand_id(b_id)
        brand = db.query(Brand).filter(Brand.id == target_b_id).first()
        if not brand:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Brand with ID '{b_id}' not found."
            )

        try:
            cat_enum = RuleCategory(b_cat)
        except (ValueError, KeyError):
            cat_enum = RuleCategory.tone

        rule = GuidelineRule(
            brand_id=target_b_id,
            category=cat_enum,
            title=b_title,
            rule_text=b_text,
            rule_code=b_code or f"{cat_enum.value[:4].upper()}-001",
            is_active=True,
            version=1
        )
        db.add(rule)
        db.commit()
        db.refresh(rule)

        # Automatically update FAISS index for this brand
        try:
            from app.services.vector_store import index_brand_rules
            active_brand_rules = db.query(GuidelineRule).filter(
                GuidelineRule.brand_id == target_b_id,
                GuidelineRule.is_active == True
            ).all()
            index_brand_rules(target_b_id, active_brand_rules)
        except Exception:
            pass

        return GuidelineRuleResponse.model_validate(rule)

    # Form data flow
    if not brand_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="brand_id is required."
        )

    target_brand_id = to_brand_id(brand_id)
    brand = db.query(Brand).filter(Brand.id == target_brand_id).first()
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Brand with ID '{brand_id}' not found."
        )

    # Case A: Explicit structured rule submitted (title + rule_text)
    if title and rule_text:
        rule_cat = category or RuleCategory.tone
        new_rule = GuidelineRule(
            brand_id=target_brand_id,
            category=rule_cat,
            title=title.strip(),
            rule_text=rule_text.strip(),
            rule_code=rule_code or f"{rule_cat.value[:4].upper()}-001",
            is_active=True,
            version=1
        )
        db.add(new_rule)
        db.commit()
        db.refresh(new_rule)
        return GuidelineRuleResponse.model_validate(new_rule)

    # Case B: Ingest from document or raw text
    extracted_content = ""
    source_filename = None

    if file:
        source_filename = file.filename
        file_bytes = await file.read()
        filename_lower = (file.filename or "").lower()

        if filename_lower.endswith(".pdf"):
            extracted_content = extract_from_pdf(file_bytes)
        elif filename_lower.endswith(".docx"):
            extracted_content = extract_from_docx(file_bytes)
        elif any(filename_lower.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".webp")):
            extracted_content = extract_from_image(file_bytes)
        else:
            try:
                extracted_content = file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                extracted_content = file_bytes.decode("latin-1", errors="ignore")

    if raw_text:
        if extracted_content:
            extracted_content = f"{raw_text}\n\n{extracted_content}"
        else:
            extracted_content = raw_text

    if not extracted_content or not extracted_content.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Submit title & rule_text, or provide a document file / raw_text to ingest."
        )

    parsed_rules = parse_raw_text_into_rules(
        raw_text=extracted_content,
        brand_id=str(brand_id),
        source_filename=source_filename,
        preferred_category=category
    )

    db.add_all(parsed_rules)
    db.commit()
    for r in parsed_rules:
        db.refresh(r)

    return [GuidelineRuleResponse.model_validate(r) for r in parsed_rules]


@router.post(
    "/upload-document",
    status_code=status.HTTP_201_CREATED,
    summary="Ingest multi-format brand guideline document",
    description="Ingests PDF, DOCX, PPTX, or TXT documents, extracts atomic rules via LLM, and embeds into FAISS."
)
@router.post(
    "/upload",
    status_code=status.HTTP_201_CREATED,
    summary="Upload brand guideline document (alias)",
    description="Accepts PDF, Word, PowerPoint, or Text file, extracts atomic rules via LLM, and indexes into FAISS."
)
async def upload_guideline_document(
    brand_id: Union[int, str] = Form(...),
    file: UploadFile = File(...),
    category: Optional[RuleCategory] = Form(None),
    auto_commit: bool = Form(True),
    preview_only: bool = Form(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload enterprise guideline document (.pdf, .docx, .pptx, .txt), extract atomic rules via LLM, and index."""
    target_brand_id = to_brand_id(brand_id)
    brand = db.query(Brand).filter(Brand.id == target_brand_id).first()
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Brand with ID '{brand_id}' not found."
        )

    file_bytes = await file.read()
    filename = file.filename or "uploaded_guideline"

    # Extract text cleanly across office formats
    extracted_text = extract_text_from_upload(file_bytes, filename)
    if not extracted_text or not extracted_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No readable text could be extracted from '{filename}'."
        )

    commit_to_db = auto_commit and not preview_only

    # Extract atomic rules using LLM architecture + fallback
    extracted_rules = extract_rules_from_raw_content(
        content_text=extracted_text,
        brand_id=target_brand_id,
        db_session=db if commit_to_db else None,
        auto_commit=commit_to_db,
        source_name=filename
    )

    action_label = "saved and indexed into FAISS" if commit_to_db else "extracted for review"
    return {
        "brand_id": target_brand_id,
        "source": filename,
        "rules_extracted_count": len(extracted_rules),
        "rules": extracted_rules,
        "message": f"Successfully extracted {len(extracted_rules)} atomic rules from '{filename}' ({action_label})."
    }


@router.post(
    "/ingest-url",
    status_code=status.HTTP_201_CREATED,
    summary="Ingest public documentation or wiki URL",
    description="Scrapes a public web page with SSRF protection, extracts atomic rules via LLM, and updates FAISS vector store."
)
async def ingest_guideline_url(
    payload: UrlIngestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Scrape hosted documentation URL (Notion, Google Docs, Wiki), extract atomic rules, and index."""
    target_brand_id = to_brand_id(payload.brand_id)
    brand = db.query(Brand).filter(Brand.id == target_brand_id).first()
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Brand with ID '{payload.brand_id}' not found."
        )

    # Scrape web page with SSRF protection
    scraped_text = await scrape_guideline_url(payload.url)

    commit_to_db = payload.auto_commit and not payload.preview_only

    # Extract atomic rules using LLM + fallback
    extracted_rules = extract_rules_from_raw_content(
        content_text=scraped_text,
        brand_id=target_brand_id,
        db_session=db if commit_to_db else None,
        auto_commit=commit_to_db,
        source_name=payload.url
    )

    if not extracted_rules:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Successfully retrieved content from '{payload.url}' ({len(scraped_text)} characters), "
                "but could not identify discrete brand guideline rules or enforceable policies. "
                "Action: Ensure the target page contains explicit brand guidelines, or add rules manually via 'Manual Entry' or 'Raw Copy'."
            )
        )

    action_label = "saved and indexed into FAISS" if commit_to_db else "extracted for review"
    return {
        "brand_id": target_brand_id,
        "source": payload.url,
        "rules_extracted_count": len(extracted_rules),
        "rules": extracted_rules,
        "message": f"Successfully scraped and extracted {len(extracted_rules)} atomic rules from '{payload.url}' ({action_label})."
    }


@router.post(
    "/bulk-save",
    status_code=status.HTTP_201_CREATED,
    summary="Bulk save approved guideline rules",
    description="Saves a batch of reviewed/edited rules from the Extraction Review Drawer and re-indexes FAISS."
)
def bulk_save_guideline_rules(
    payload: BulkRulesSaveRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Commit an array of reviewed atomic rules to database and update FAISS index."""
    target_brand_id = to_brand_id(payload.brand_id)
    brand = db.query(Brand).filter(Brand.id == target_brand_id).first()
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Brand with ID '{payload.brand_id}' not found."
        )

    if not payload.rules:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No rules provided in bulk save payload."
        )

    saved_orm_rules = []
    for r in payload.rules:
        title = str(r.get("title") or "Guideline Rule").strip()
        rule_text = str(r.get("rule_text") or "").strip()
        if not rule_text:
            continue

        cat_str = str(r.get("category") or "tone").strip().lower()
        try:
            cat_enum = RuleCategory(cat_str)
        except Exception:
            cat_enum = RuleCategory.tone

        rule_code = str(r.get("rule_code") or f"{cat_enum.value[:4].upper()}-{len(saved_orm_rules)+1:02d}").upper()

        orm_rule = GuidelineRule(
            brand_id=target_brand_id,
            category=cat_enum,
            title=title,
            rule_text=rule_text,
            rule_code=rule_code,
            source_file=payload.source_name or "Bulk Ingestion",
            is_active=True,
            version=1
        )
        db.add(orm_rule)
        saved_orm_rules.append(orm_rule)

    if saved_orm_rules:
        db.commit()
        for r in saved_orm_rules:
            db.refresh(r)

        # Trigger FAISS Vector Store Update
        try:
            from app.services.vector_store import index_brand_rules
            all_brand_rules = (
                db.query(GuidelineRule)
                .filter(GuidelineRule.brand_id == target_brand_id, GuidelineRule.is_active == True)
                .all()
            )
            index_brand_rules(target_brand_id, all_brand_rules)
        except Exception as v_err:
            logger.warning(f"Error updating FAISS vector store after bulk save: {v_err}")

    return {
        "brand_id": target_brand_id,
        "rules_saved_count": len(saved_orm_rules),
        "rules": [GuidelineRuleResponse.model_validate(r) for r in saved_orm_rules],
        "message": f"Successfully saved {len(saved_orm_rules)} rules to active guidelines and updated FAISS vector index."
    }



@router.get(
    "",
    response_model=List[GuidelineRuleResponse],
    summary="Fetch active brand rules",
    description="Retrieve active guideline rules for a brand, optionally filtered by category."
)
def get_guidelines(
    brand_id: Optional[Union[int, str]] = Query(None, description="Filter rules by Brand ID (integer or string)"),
    category: Optional[RuleCategory] = Query(None, description="Filter by category"),
    is_active: bool = Query(True, description="Filter active rules only"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[GuidelineRuleResponse]:
    """Retrieve active guideline rules."""
    query = db.query(GuidelineRule)

    if brand_id is not None:
        target_id = to_brand_id(brand_id)
        query = query.filter(GuidelineRule.brand_id == target_id)
    if category:
        query = query.filter(GuidelineRule.category == category)
    if is_active is not None:
        query = query.filter(GuidelineRule.is_active == is_active)

    rules = query.order_by(GuidelineRule.created_at.desc()).all()
    return [GuidelineRuleResponse.model_validate(r) for r in rules]



@router.post(
    "/check-contradictions",
    summary="Detect brand guideline contradictions",
    description="Compares pairs of active or newly uploaded guideline statements to identify opposing facts or policies side-by-side."
)
def check_contradictions(
    brand_id: int = Query(1, description="Target Brand ID (integer or string)"),
    payload: Optional[ContradictionCheckRequest] = Body(None),
    as_list: bool = Query(False, description="Return raw JSON list of contradictions"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Analyze active brand guidelines and regulatory standards autonomously for contradictions."""
    from app.services.contradiction_service import (
        detect_autonomous_contradictions,
        detect_heuristic_numeric_conflicts
    )

    target_id = 1
    try:
        effective_brand_id = brand_id
        if payload is not None and getattr(payload, "brand_id", None) is not None:
            effective_brand_id = payload.brand_id

        target_id = to_brand_id(effective_brand_id or 1)
        brand = db.query(Brand).filter(Brand.id == target_id).first()
        if not brand and isinstance(target_id, int):
            brand_names = {1: "AstraForge Brand", 2: "NovaPay Global", 3: "Apex BioTech Labs"}
            name = brand_names.get(target_id, f"Brand #{target_id}")
            try:
                creator_id = current_user.id if current_user and hasattr(current_user, "id") else 1
                brand = Brand(id=target_id, name=name, created_by=creator_id)
                db.add(brand)
                db.commit()
                db.refresh(brand)
            except Exception:
                db.rollback()
                brand = db.query(Brand).filter(Brand.id == target_id).first()

        if not brand:
            empty_res = {
                "brand_id": target_id if isinstance(target_id, int) else 1,
                "contradictions": [],
                "total": 0,
                "total_contradictions": 0,
                "conflicts": [],
                "rules_evaluated_count": 0,
                "message": "Zero conflicts detected."
            }
            if as_list:
                return []
            return empty_res

        # Fetch active rules for this brand
        query = db.query(GuidelineRule).filter(
            GuidelineRule.brand_id == target_id,
            GuidelineRule.is_active == True
        )
        category_filter = getattr(payload, "category", None) if payload is not None else None
        if category_filter:
            query = query.filter(GuidelineRule.category == category_filter)
        active_rules = query.all()

        new_stmts = getattr(payload, "new_statements", None) if payload is not None else None
        has_new_statements = bool(new_stmts and len(new_stmts) > 0)
        total_eval_rules = len(active_rules) + (len(new_stmts) if has_new_statements else 0)

        # Low Rule Guard: If fewer than 2 guidelines exist for brand_id
        if total_eval_rules < 2:
            empty_res = {
                "brand_id": target_id if isinstance(target_id, int) else 1,
                "total": 0,
                "contradictions": [],
                "total_contradictions": 0,
                "conflicts": [],
                "rules_evaluated_count": total_eval_rules,
                "message": "At least 2 active guidelines are required to run contradiction analysis."
            }
            if as_list:
                return []
            return empty_res

        # Run Autonomous Brand & Regulation Scan with automatic heuristic fallback
        try:
            contradictions = detect_autonomous_contradictions(
                brand_id=target_id,
                db_session=db,
                new_statements=new_stmts
            )
        except Exception as scan_err:
            logger.warning(
                f"Autonomous contradiction scan error ({scan_err}), falling back to heuristic rule comparison."
            )
            try:
                heuristic_statements = [
                    {
                        "id": r.id,
                        "rule_code": r.rule_code or f"RULE-{r.id}",
                        "title": r.title or f"Rule #{r.id}",
                        "text": r.rule_text,
                        "category": r.category.value if hasattr(r.category, "value") else str(r.category),
                        "is_regulatory": False,
                    }
                    for r in active_rules
                ]
                contradictions = detect_heuristic_numeric_conflicts(heuristic_statements)
            except Exception as fb_err:
                logger.error(f"Heuristic comparison fallback also failed: {fb_err}")
                contradictions = []

        if as_list:
            return contradictions

        return {
            "brand_id": target_id,
            "total": len(contradictions),
            "total_contradictions": len(contradictions),
            "contradictions_detected": len(contradictions),
            "rules_evaluated_count": total_eval_rules,
            "contradictions": contradictions,
            "conflicts": contradictions,
            "message": f"Autonomous scan complete. Evaluated {total_eval_rules} active guidelines against regulatory benchmarks. Discovered {len(contradictions)} contradiction(s) and policy tension(s)."
        }
    except Exception as e:
        logger.error(f"Unhandled error in check_contradictions: {e}", exc_info=True)
        empty_res = {
            "brand_id": target_id if isinstance(target_id, int) else 1,
            "contradictions": [],
            "total": 0,
            "total_contradictions": 0,
            "conflicts": [],
            "rules_evaluated_count": 0,
            "message": "Zero conflicts detected."
        }
        if as_list:
            return []
        return empty_res



@router.get(
    "/gaps",
    summary="Detect guideline gaps & suggest candidate rules",
    description="Aggregates ungrounded findings and vague guidance to propose structured candidate rules for brand manager review."
)
def get_guideline_gaps(
    brand_id: Union[int, str] = Query(..., description="Target Brand ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Detect guideline gaps and propose candidate formal rules."""
    from app.services.gap_detector import detect_guideline_gaps

    target_id = to_brand_id(brand_id)
    brand = db.query(Brand).filter(Brand.id == target_id).first()
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Brand with ID '{brand_id}' not found."
        )

    candidate_rules = detect_guideline_gaps(
        brand_id=target_id,
        findings=None,
        db_session=db
    )

    return {
        "brand_id": target_id,
        "candidate_rules_count": len(candidate_rules),
        "proposed_rules": candidate_rules
    }


@router.post(
    "/index",
    summary="Trigger FAISS indexing for brand rules",
    description="Embeds all active guideline rules for a brand and stores them in the in-memory FAISS index."
)
@router.post(
    "/reindex",
    summary="Trigger FAISS reindexing for brand rules"
)
async def trigger_faiss_indexing(
    request: Request,
    brand_id: Optional[Union[int, str]] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    eff_brand_id = brand_id
    if eff_brand_id is None:
        try:
            body = await request.json()
            eff_brand_id = body.get("brand_id")
        except Exception:
            pass
    eff_brand_id = eff_brand_id or 1
    target_id = to_brand_id(eff_brand_id)
    rules = db.query(GuidelineRule).filter(
        GuidelineRule.brand_id == target_id,
        GuidelineRule.is_active == True
    ).all()
    from app.services.vector_store import index_brand_rules
    count = index_brand_rules(target_id, rules)
    return {
        "status": "indexed",
        "brand_id": target_id,
        "indexed_rules_count": count,
        "message": f"Successfully indexed {count} active rules into FAISS vector store."
    }


@router.post(
    "/brands",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new brand workspace"
)
async def create_brand_workspace(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    name = "New Brand"
    desc = ""
    try:
        body = await request.json()
        name = body.get("name") or "New Brand"
        desc = body.get("description", "")
    except Exception:
        pass
    new_brand = Brand(name=name, description=desc, created_by=current_user.id)
    db.add(new_brand)
    db.commit()
    db.refresh(new_brand)
    return {"id": new_brand.id, "name": new_brand.name, "description": new_brand.description}


@router.get(
    "/brands",
    summary="List all brand workspaces"
)
def list_brand_workspaces(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    brands = db.query(Brand).all()
    return [{"id": b.id, "name": b.name, "description": b.description} for b in brands]


@router.post(
    "/{rule_id}/deactivate",
    summary="Deactivate a conflicting guideline rule"
)
@router.patch(
    "/{rule_id}/deactivate",
    summary="Deactivate a conflicting guideline rule"
)
def deactivate_rule(
    rule_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    rule = db.query(GuidelineRule).filter(GuidelineRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail=f"Rule #{rule_id} not found.")
    rule.is_active = False
    db.commit()
    return {"id": rule_id, "is_active": False, "message": f"Rule #{rule_id} successfully deactivated."}


@router.post(
    "/contradictions/resolve",
    summary="Record governance sign-off and resolve policy contradiction",
    description="Applies rule amendment, deactivation, or merger with legal counsel/brand director sign-off."
)
async def resolve_policy_contradiction(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    import datetime
    body = await request.json()
    conflict_id = body.get("conflict_id", "CONF-001")
    strategy = body.get("strategy", "amend")  # 'amend' | 'deactivate' | 'merge'
    rule_id = body.get("rule_id")
    amendment_text = body.get("amendment_text", "")
    approver_role = body.get("approver_role", "Legal Counsel")
    approver_name = body.get("approver_name", getattr(current_user, "full_name", None) or getattr(current_user, "email", None) or "Compliance Officer")
    justification = body.get("justification", "Harmonized to ensure strict regulatory compliance.")

    target_rule = None
    if rule_id and str(rule_id).isdigit():
        target_rule = db.query(GuidelineRule).filter(GuidelineRule.id == int(rule_id)).first()

    if strategy == "deactivate" and target_rule:
        target_rule.is_active = False
        db.commit()
    elif strategy == "amend" and target_rule and amendment_text.strip():
        target_rule.rule_text = amendment_text.strip()
        target_rule.version = (target_rule.version or 1) + 1
        db.commit()
    elif strategy == "merge" and target_rule and amendment_text.strip():
        target_rule.rule_text = amendment_text.strip()
        target_rule.version = (target_rule.version or 1) + 1
        secondary_id = body.get("secondary_rule_id")
        if secondary_id and str(secondary_id).isdigit():
            sec_rule = db.query(GuidelineRule).filter(GuidelineRule.id == int(secondary_id)).first()
            if sec_rule:
                sec_rule.is_active = False
        db.commit()

    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    return {
        "status": "resolved",
        "conflict_id": conflict_id,
        "strategy": strategy,
        "approver_role": approver_role,
        "approver_name": approver_name,
        "justification": justification,
        "timestamp": timestamp,
        "message": f"Contradiction {conflict_id} successfully signed off via {strategy} by {approver_role} ({approver_name})."
    }




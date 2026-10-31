"""Session & Audit History endpoints for BrandPrint AI."""
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc

from app.core.database import get_db, engine, Base
from app.models.history import AuditHistory
from app.schemas.history import (
    HistorySessionCreate,
    HistorySessionItem,
    HistorySessionDetail,
    HistorySavedResponse,
)

logger = logging.getLogger("brandprint.history")

router = APIRouter(prefix="/history", tags=["history"])

# In-memory session store for fast fallback and transient local executions
_IN_MEMORY_HISTORY: Dict[str, Dict[str, Any]] = {}


@router.post(
    "",
    response_model=HistorySavedResponse,
    summary="Save an audit or comparison session",
    status_code=status.HTTP_201_CREATED,
)
def save_history_session(
    payload: HistorySessionCreate,
    db: Session = Depends(get_db)
) -> HistorySavedResponse:
    """Save completed audit, multi-asset comparison, or contradiction session."""
    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    # In-memory record
    record_dict = {
        "id": session_id,
        "created_at": now,
        "session_type": payload.session_type,
        "title": payload.title,
        "summary": payload.summary,
        "inputs_payload": payload.inputs_payload,
        "results_payload": payload.results_payload,
        "brand_id": payload.brand_id,
        "user_id": payload.user_id,
    }
    _IN_MEMORY_HISTORY[session_id] = record_dict

    # Database persist
    try:
        db_record = AuditHistory(
            id=session_id,
            created_at=now,
            session_type=payload.session_type,
            title=payload.title,
            summary=payload.summary,
            inputs_payload=payload.inputs_payload,
            results_payload=payload.results_payload,
            brand_id=payload.brand_id,
            user_id=payload.user_id,
        )
        db.add(db_record)
        db.commit()
        db.refresh(db_record)
        logger.info(f"Persisted history session {session_id} to database.")
    except Exception as e:
        logger.warning(f"Database persist failed for history session {session_id} (using fallback): {e}")
        db.rollback()

    return HistorySavedResponse(id=session_id, status="saved")


@router.get(
    "",
    response_model=List[HistorySessionItem],
    summary="List past audit and comparison sessions",
)
def list_history_sessions(
    search: Optional[str] = Query(None, description="Search term for title or summary"),
    type: Optional[str] = Query(None, description="Filter by session_type (or 'COMPARISON', 'AUDIT')"),
    limit: int = Query(50, ge=1, le=200, description="Max records to return"),
    db: Session = Depends(get_db)
) -> List[HistorySessionItem]:
    """Retrieve history sessions sorted by created_at DESC."""
    results: List[HistorySessionItem] = []

    # Clean string inputs in case of direct function calls
    search_str = search if isinstance(search, str) and search.strip() else None
    type_str = type if isinstance(type, str) and type.strip() else None
    limit_int = limit if isinstance(limit, int) else 50

    # 1. Try DB query
    try:
        query = db.query(AuditHistory)

        if type_str:
            type_clean = type_str.strip().upper()
            if type_clean == "COMPARISON":
                query = query.filter(
                    AuditHistory.session_type.in_(["DUAL_COMPARISON", "THREE_WAY_COMPARISON"])
                )
            elif type_clean in ["AUDIT", "SINGLE_AUDIT"]:
                query = query.filter(AuditHistory.session_type == "SINGLE_AUDIT")
            elif type_clean == "CONTRADICTION":
                query = query.filter(AuditHistory.session_type == "CONTRADICTION_CHECK")
            else:
                query = query.filter(AuditHistory.session_type == type_clean)

        if search_str:
            search_pattern = f"%{search_str.strip()}%"
            query = query.filter(
                or_(
                    AuditHistory.title.ilike(search_pattern),
                    AuditHistory.summary.ilike(search_pattern),
                )
            )

        db_items = query.order_by(desc(AuditHistory.created_at)).limit(limit_int).all()
        for item in db_items:
            results.append(
                HistorySessionItem(
                    id=item.id,
                    created_at=item.created_at,
                    session_type=item.session_type,
                    title=item.title,
                    summary=item.summary,
                    brand_id=item.brand_id,
                    user_id=item.user_id,
                )
            )
        return results
    except Exception as e:
        logger.warning(f"DB query failed for history list, falling back to memory: {e}")

    # 2. In-memory fallback
    mem_items = list(_IN_MEMORY_HISTORY.values())
    if type_str:
        type_clean = type_str.strip().upper()
        if type_clean == "COMPARISON":
            mem_items = [
                m for m in mem_items
                if m.get("session_type") in ["DUAL_COMPARISON", "THREE_WAY_COMPARISON"]
            ]
        elif type_clean in ["AUDIT", "SINGLE_AUDIT"]:
            mem_items = [
                m for m in mem_items
                if m.get("session_type") == "SINGLE_AUDIT"
            ]
        elif type_clean == "CONTRADICTION":
            mem_items = [
                m for m in mem_items
                if m.get("session_type") == "CONTRADICTION_CHECK"
            ]
        else:
            mem_items = [
                m for m in mem_items
                if m.get("session_type") == type_clean
            ]

    if search_str:
        search_lower = search_str.strip().lower()
        mem_items = [
            m for m in mem_items
            if search_lower in (m.get("title", "") or "").lower()
            or search_lower in (m.get("summary", "") or "").lower()
        ]

    mem_items.sort(key=lambda x: x.get("created_at") or datetime.min, reverse=True)
    return [
        HistorySessionItem(
            id=m["id"],
            created_at=m["created_at"],
            session_type=m["session_type"],
            title=m["title"],
            summary=m.get("summary"),
            brand_id=m.get("brand_id"),
            user_id=m.get("user_id"),
        )
        for m in mem_items[:limit_int]
    ]


@router.get(
    "/{id}",
    response_model=HistorySessionDetail,
    summary="Get complete session payload for re-hydrating the UI",
)
def get_history_session(
    id: str,
    db: Session = Depends(get_db)
) -> HistorySessionDetail:
    """Retrieve full history session data including inputs and results."""
    try:
        db_item = db.query(AuditHistory).filter(AuditHistory.id == id).first()
        if db_item:
            return HistorySessionDetail(
                id=db_item.id,
                created_at=db_item.created_at,
                session_type=db_item.session_type,
                title=db_item.title,
                summary=db_item.summary,
                inputs_payload=db_item.inputs_payload or {},
                results_payload=db_item.results_payload or {},
                brand_id=db_item.brand_id,
                user_id=db_item.user_id,
            )
    except Exception as e:
        logger.warning(f"DB lookup failed for history id={id}: {e}")

    # Fallback to memory
    if id in _IN_MEMORY_HISTORY:
        m = _IN_MEMORY_HISTORY[id]
        return HistorySessionDetail(
            id=m["id"],
            created_at=m["created_at"],
            session_type=m["session_type"],
            title=m["title"],
            summary=m.get("summary"),
            inputs_payload=m.get("inputs_payload") or {},
            results_payload=m.get("results_payload") or {},
            brand_id=m.get("brand_id"),
            user_id=m.get("user_id"),
        )

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="History session not found")


@router.delete(
    "/clear-all",
    summary="Clear all history sessions",
)
def clear_all_history(
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Delete all history sessions."""
    count = 0
    _IN_MEMORY_HISTORY.clear()
    try:
        count = db.query(AuditHistory).delete()
        db.commit()
    except Exception as e:
        logger.warning(f"Failed to clear history table in DB: {e}")
        db.rollback()

    return {"status": "cleared", "deleted_count": count}


@router.delete(
    "/{id}",
    summary="Delete a specific history session",
)
def delete_history_session(
    id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Delete a specific history session by ID."""
    _IN_MEMORY_HISTORY.pop(id, None)

    try:
        item = db.query(AuditHistory).filter(AuditHistory.id == id).first()
        if item:
            db.delete(item)
            db.commit()
            return {"id": id, "status": "deleted"}
    except Exception as e:
        logger.warning(f"Failed to delete history {id} from DB: {e}")
        db.rollback()

    return {"id": id, "status": "deleted"}

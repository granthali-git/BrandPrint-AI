"""Governance & AI Transparency API Endpoints."""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.transparency import AITransparencyLog, GuidelineGap
from app.services.ai_gateway import get_recent_transparency_logs

router = APIRouter(prefix="/governance", tags=["governance"])


@router.get(
    "/ai-transparency-logs",
    summary="Get recent AI disclosure & audit events",
    description="Returns the recent 25 AI model execution events, including redaction status and prompt hashes."
)
def get_ai_transparency_logs(
    limit: int = Query(default=25, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Retrieve recent AI transparency audit log records."""
    return get_recent_transparency_logs(db=db, limit=limit)


@router.get(
    "/summary",
    summary="Get governance compliance summary",
    description="Returns metric counts of AI transparency logs, data redactions, and pending guideline gaps."
)
def get_governance_summary(
    brand_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Retrieve aggregate counts for governance dashboard indicators."""
    total_logs = db.query(AITransparencyLog).count()
    redactions_total = (
        db.query(AITransparencyLog)
        .filter(AITransparencyLog.redaction_applied == True)
        .count()
    )
    local_count = (
        db.query(AITransparencyLog)
        .filter(
            (AITransparencyLog.service_provider.like("%Local%")) |
            (AITransparencyLog.service_provider.like("%Ollama%"))
        )
        .count()
    )
    cloud_count = total_logs - local_count

    gaps_query = db.query(GuidelineGap)
    if brand_id:
        gaps_query = gaps_query.filter(GuidelineGap.brand_id == brand_id)
    pending_gaps = gaps_query.filter(GuidelineGap.status == "PENDING_DECISION").count()

    return {
        "total_ai_evaluations": total_logs,
        "redactions_applied_count": redactions_total,
        "local_ollama_runs": local_count,
        "cloud_gemini_runs": cloud_count,
        "pending_gaps_count": pending_gaps,
    }


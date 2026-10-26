"""Pydantic schemas for Finding models."""
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict
from app.models.finding import SeverityLevel, UserAction


class FixVariation(BaseModel):
    style: str
    text: str


class FindingBase(BaseModel):
    submission_id: Union[int, str]
    version: int = 1
    rule_id: Optional[Union[int, str]] = None
    category: Optional[str] = None
    issue_type: str
    severity: SeverityLevel = SeverityLevel.medium
    flagged_text: Optional[str] = None
    context_span: Optional[str] = None
    explanation: str
    cited_quote: Optional[str] = None
    suggested_fix: Optional[str] = None
    fix_variations: Optional[List[Dict[str, Any]]] = None
    strategic_tip: Optional[str] = None
    user_action: UserAction = UserAction.pending


class FindingCreate(FindingBase):
    pass


class FindingUpdate(BaseModel):
    user_action: Optional[UserAction] = None
    suggested_fix: Optional[str] = None


class FindingResponse(FindingBase):
    model_config = ConfigDict(from_attributes=True)

    id: Union[int, str]
    created_at: datetime


class FindingActionRequest(BaseModel):
    finding_id: Union[int, str]
    action: UserAction
    suggested_fix: Optional[str] = None


class FindingPatchRequest(BaseModel):
    action: UserAction
    suggested_fix: Optional[str] = None


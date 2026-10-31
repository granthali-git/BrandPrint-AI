"""Pydantic schemas for Audit & Comparison Session History."""
from typing import Any, Dict, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class HistorySessionCreate(BaseModel):
    session_type: str = Field(
        ...,
        description="Session type: SINGLE_AUDIT, DUAL_COMPARISON, THREE_WAY_COMPARISON, or CONTRADICTION_CHECK"
    )
    title: str = Field(..., max_length=255, description="Short descriptive title of the session")
    summary: Optional[str] = Field(None, description="One-line summary of findings/scores")
    inputs_payload: Dict[str, Any] = Field(default_factory=dict, description="Inputs: text copy, file metadata, URLs, slots")
    results_payload: Dict[str, Any] = Field(default_factory=dict, description="AI evaluation results, violations, matrix")
    brand_id: Optional[int] = Field(None, description="Associated Brand ID")
    user_id: Optional[int] = Field(None, description="Owner User ID")


class HistorySessionItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    session_type: str
    title: str
    summary: Optional[str] = None
    brand_id: Optional[int] = None
    user_id: Optional[int] = None


class HistorySessionDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    session_type: str
    title: str
    summary: Optional[str] = None
    inputs_payload: Dict[str, Any]
    results_payload: Dict[str, Any]
    brand_id: Optional[int] = None
    user_id: Optional[int] = None


class HistorySavedResponse(BaseModel):
    id: str
    status: str = "saved"

"""Pydantic schemas for ReviewDecision models."""
from datetime import datetime
from typing import Any, Dict, Optional, Union
from pydantic import BaseModel, ConfigDict
from app.models.review import ReviewDecisionType
from app.schemas.submission import ContentSubmissionResponse


class ReviewDecisionBase(BaseModel):
    submission_id: Union[int, str]
    version: int = 1
    decision: ReviewDecisionType
    comment: Optional[str] = None


class ReviewDecisionCreate(ReviewDecisionBase):
    pass


class ReviewDecisionResponse(ReviewDecisionBase):
    model_config = ConfigDict(from_attributes=True)

    id: Union[int, str]
    reviewer_id: Union[int, str]
    created_at: datetime
    notes: Optional[str] = None
    approval_timestamp: Optional[str] = None
    submission: Optional[ContentSubmissionResponse] = None
    decision_record: Optional[Dict[str, Any]] = None


class ReviewDecisionSubmissionRequest(BaseModel):
    decision: ReviewDecisionType
    comment: Optional[str] = None
    notes: Optional[str] = None
    reviewer_id: Optional[Union[int, str]] = None


class WhatIfSimulateRequest(BaseModel):
    revised_content: Optional[str] = None
    draft_rules: Optional[list[dict]] = None


class CompareSlotPayload(BaseModel):
    source_type: Optional[str] = "text"  # 'text' | 'file' | 'url'
    text_content: Optional[str] = None
    file_name: Optional[str] = None
    url: Optional[str] = None


class ReviewCompareRequest(BaseModel):
    asset_id_a: Optional[Union[str, int]] = None
    asset_id_b: Optional[Union[str, int]] = None
    asset_id_c: Optional[Union[str, int]] = None
    text_a: Optional[str] = None
    text_b: Optional[str] = None
    text_c: Optional[str] = None
    slot_a: Optional[CompareSlotPayload] = None
    slot_b: Optional[CompareSlotPayload] = None
    slot_c: Optional[CompareSlotPayload] = None
    brand_id: Optional[Union[str, int]] = 1


# Alias for 3-way multi-asset comparison
ComparisonRequest = ReviewCompareRequest


class ScrapeUrlRequest(BaseModel):
    url: str
    brand_id: Optional[Union[str, int]] = 1





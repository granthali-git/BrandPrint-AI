"""Pydantic schemas for ContentSubmission models."""
from datetime import datetime
from typing import Optional, Union
from pydantic import BaseModel, ConfigDict
from app.models.submission import ContentType, SubmissionStatus


class ContentSubmissionBase(BaseModel):
    brand_id: Union[int, str]
    content_type: ContentType = ContentType.text
    raw_content: str


class ContentSubmissionCreate(ContentSubmissionBase):
    pass


class ContentSubmissionUpdate(BaseModel):
    raw_content: Optional[str] = None
    status: Optional[SubmissionStatus] = None
    current_version: Optional[int] = None


class ContentSubmissionResponse(ContentSubmissionBase):
    model_config = ConfigDict(from_attributes=True)

    id: Union[int, str]
    creator_id: Union[int, str]
    status: SubmissionStatus
    current_version: int
    image_preview_url: Optional[str] = None
    visual_analysis_status: Optional[str] = None
    visual_analysis_message: Optional[str] = None
    created_at: datetime

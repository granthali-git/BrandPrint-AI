"""Pydantic schemas for GuidelineRule models."""
from datetime import datetime
from typing import Any, Optional, Union
from pydantic import BaseModel, ConfigDict
from app.models.guideline import RuleCategory


class GuidelineRuleBase(BaseModel):
    category: RuleCategory
    title: str
    rule_text: str
    rule_code: Optional[str] = None
    source_file: Optional[str] = None
    is_active: bool = True
    version: int = 1


class GuidelineRuleCreate(GuidelineRuleBase):
    brand_id: Union[int, str]


class GuidelineRuleUpdate(BaseModel):
    category: Optional[RuleCategory] = None
    title: Optional[str] = None
    rule_text: Optional[str] = None
    rule_code: Optional[str] = None
    source_file: Optional[str] = None
    is_active: Optional[bool] = None
    version: Optional[int] = None


class GuidelineRuleResponse(GuidelineRuleBase):
    model_config = ConfigDict(from_attributes=True)

    id: Union[int, str]
    brand_id: Union[int, str]
    created_at: datetime


class ContradictionCheckRequest(BaseModel):
    brand_id: Optional[Union[int, str]] = None
    new_statements: Optional[list[str]] = None
    rules: Optional[list[Any]] = None
    category: Optional[RuleCategory] = None


class UrlIngestRequest(BaseModel):
    brand_id: Union[int, str]
    url: str
    auto_commit: bool = True
    preview_only: bool = False


class BulkRulesSaveRequest(BaseModel):
    brand_id: Union[int, str]
    rules: list[dict[str, Any]]
    source_name: Optional[str] = "Manual Ingestion"


class GuidelineIngestResponse(BaseModel):
    brand_id: Union[int, str]
    source: Optional[str] = None
    rules_extracted_count: int
    rules: list[dict[str, Any]]
    message: str



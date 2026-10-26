"""Pydantic schemas for Brand models."""
from datetime import datetime
from typing import Optional, Union
from pydantic import BaseModel, ConfigDict


class BrandBase(BaseModel):
    name: str
    description: Optional[str] = None


class BrandCreate(BrandBase):
    pass


class BrandUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class BrandResponse(BrandBase):
    model_config = ConfigDict(from_attributes=True)

    id: Union[int, str]
    created_by: Optional[Union[int, str]] = None
    created_at: datetime

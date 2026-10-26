"""Pydantic schemas for Authentication endpoints."""
from typing import Optional
from pydantic import BaseModel
from app.schemas.user import UserResponse


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Optional[UserResponse] = None


class TokenData(BaseModel):
    user_id: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None

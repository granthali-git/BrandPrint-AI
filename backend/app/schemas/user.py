"""Pydantic schemas for User models."""
from datetime import datetime
from typing import Optional, Union
from pydantic import BaseModel, EmailStr, ConfigDict, Field
from app.models.user import UserRole


class UserBase(BaseModel):
    email: EmailStr
    role: UserRole = UserRole.Creator


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, description="User password must be at least 6 characters")
    role: Optional[UserRole] = UserRole.Creator


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Union[int, str]
    email: EmailStr
    role: UserRole
    created_at: datetime

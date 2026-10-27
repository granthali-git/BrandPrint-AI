"""Pydantic schemas for User models."""
from datetime import datetime
from typing import Optional, Union
from pydantic import BaseModel, EmailStr, ConfigDict, Field
from app.models.user import UserRole


class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    company: Optional[str] = None
    role: UserRole = UserRole.Creator


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, description="User password must be at least 6 characters")
    full_name: Optional[str] = None
    company: Optional[str] = None
    role: Optional[UserRole] = UserRole.Creator


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    message: str = "Password reset instructions sent to your email address."
    status: str = "success"


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[Union[int, str]] = None
    email: EmailStr
    name: Optional[str] = None
    full_name: Optional[str] = None
    company: Optional[str] = None
    role: Optional[UserRole] = UserRole.Creator
    created_at: Optional[datetime] = None

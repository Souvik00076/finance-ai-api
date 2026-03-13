from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


# ============ Request Schemas ============


class UserCreate(BaseModel):
    """Schema for creating a user (email/password signup)."""
    email: EmailStr
    full_name: Optional[str] = None


class UserUpdate(BaseModel):
    """Schema for updating a user."""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    picture: Optional[str] = None


# ============ Response Schemas ============


class UserResponse(BaseModel):
    """Schema for user response (public-facing)."""
    id: str
    email: str
    full_name: Optional[str] = None
    picture: Optional[str] = None
    provider: str = "email"
    is_active: bool = True
    phone: Optional[str] = None
    is_phone_linked: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============ Internal / DB Schemas ============


class UserInDB(BaseModel):
    """Schema representing a full user document from MongoDB."""
    id: str
    email: str
    full_name: Optional[str] = None
    picture: Optional[str] = None
    provider: str = "email"
    google_uid: Optional[str] = None
    email_verified: bool = False
    is_active: bool = True
    is_superuser: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

from typing import Optional
from datetime import datetime, timezone

from beanie import Document
from pydantic import EmailStr, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Document):
    """User document model for MongoDB (Beanie ODM)."""

    email: EmailStr
    full_name: Optional[str] = None
    picture: Optional[str] = None
    provider: str = "email"
    google_uid: str
    email_verified: bool = False
    is_active: bool = True
    is_superuser: bool = False
    phone: Optional[str] = None
    is_phone_linked: bool = False
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    class Settings:
        name = "users"

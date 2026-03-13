from pydantic import BaseModel, EmailStr
from typing import Optional


class WhatsappLinkRequest(BaseModel):
    phone: str


class VerifyWhatsappRequest(BaseModel):
    otp: str


class ProfileResponse(BaseModel):
    """User profile response schema."""
    email: EmailStr
    full_name: Optional[str] = None
    picture: Optional[str] = None
    provider: str
    email_verified: bool
    created_at: str
    is_phone_linked: bool
    phone: str = ''

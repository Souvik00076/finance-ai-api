from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from enum import Enum


class AuthProvider(str, Enum):
    """Authentication provider types."""
    EMAIL = "email"
    GOOGLE = "google"


# ============ Request Schemas ============

class EmailSignupRequest(BaseModel):
    """Email signup request."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    redirect_uri: str = Field(..., min_length=8, max_length=100)


class VerifyUserEmailRequest(BaseModel):
    email: EmailStr
    action_code: str


class EmailLoginRequest(BaseModel):
    """Email login request."""
    email: EmailStr
    password: str


class GoogleAuthRequest(BaseModel):
    """Google OAuth request - used for both login and signup."""
    id_token: str = Field(..., description="Google ID token from client")


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str


# ============ Response Schemas ============

class TokenResponse(BaseModel):
    """Token response after successful authentication."""
    id_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Access token expiry in seconds")


class AuthUserResponse(BaseModel):
    """Authenticated user response."""
    id: str
    email: str
    full_name: Optional[str] = None
    provider: AuthProvider
    is_active: bool
    created_at: str


class AuthResponse(BaseModel):
    """Full auth response with user and tokens."""
    id_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Access token expiry in seconds")


class MessageResponse(BaseModel):
    """Simple message response."""
    message: str
    success: bool = True

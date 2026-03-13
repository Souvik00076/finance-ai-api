from pydantic_settings import BaseSettings
from typing import List, Optional
from functools import lru_cache
import secrets


class Settings(BaseSettings):
    """Application settings."""

    # Project info
    PROJECT_NAME: str = "Finance AI API"
    PROJECT_DESCRIPTION: str = "API server for Finance AI Infrastructure"
    VERSION: str = "1.0.0"

    # API
    API_V1_PREFIX: str = "/api/v1"

    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    # MongoDB
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "finance_ai"

    # JWT Authentication
    JWT_SECRET_KEY: str = secrets.token_urlsafe(32)  # Override in production!
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Firebase
    # Path to service account JSON
    FIREBASE_CREDENTIALS_PATH: Optional[str] = None
    FIREBASE_API_KEY: Optional[str] = None  # Firebase Web API key for REST API

    # Resend (email)
    RESEND_API_KEY: str = ""
    RESEND_FROM_EMAIL: str = "onboarding@resend.dev"

    # Environment
    ENV: str = "development"
    DEBUG: bool = True

    # Twilio
    TWILIO_SID: str = ""
    TWILIO_TOKEN: str = ""
    TWILIO_CONTENT_SID: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()

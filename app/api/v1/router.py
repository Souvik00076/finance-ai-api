from fastapi import APIRouter

from app.api.v1.auth.router import router as auth_router
from app.api.v1.settings.router import router as settings_router
from app.api.v1.analytics.router import router as analytics_router

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(auth_router)  # /api/v1/auth/*
api_router.include_router(settings_router)
api_router.include_router(analytics_router)  # /api/v1/analytics/*

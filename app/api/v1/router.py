from fastapi import APIRouter

from app.auth.router import router as auth_router
from app.settings.router import router as settings_router

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(auth_router)  # /api/v1/auth/*
api_router.include_router(settings_router)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.db.mongodb import MongoDB
from app.api.v1.router import api_router
from app.auth.firebase import init_firebase
from app.middleware import AuthMiddleware
from app.models.user import User

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    logger.info("Starting up...")

    db = MongoDB()
    await db.connect(document_models=[User])
    app.state.db = db

    # Initialize Firebase (optional - only if credentials configured)
    try:
        init_firebase()
    except Exception as e:
        logger.warning(f"Firebase initialization skipped: {e}")

    yield

    # Shutdown
    logger.info("Shutting down...")
    await db.close()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Auth middleware - verifies tokens from cookies
app.add_middleware(AuthMiddleware)

# CORS middleware - must be registered last to execute first
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": settings.VERSION}

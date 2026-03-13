from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from typing import Callable

from app.auth.firebase.Auth import FirebaseAuth

# Routes that don't require authentication
PUBLIC_ROUTES = [
    "/api/v1/auth",  # Auth endpoints
    "/api/v1/docs",
    "/api/v1/redoc",
    "/api/v1/openapi.json",  # OpenAPI schema endpoint
    "api/v1/health",
]


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Authentication middleware that verifies tokens from cookies.

    Skips verification for public routes (auth, docs, etc.)
    """

    async def dispatch(self, request: Request, call_next: Callable):
        # Skip auth for public routes
        path = request.url.path

        if any(path.startswith(route) for route in PUBLIC_ROUTES):
            return await call_next(request)

        # Get access token from cookie
        access_token = request.cookies.get("access_token")

        if not access_token:
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "Not authenticated"}
            )

        # Verify token
        firebase_auth = FirebaseAuth()
        decoded_token = await firebase_auth.verify_id_token(access_token)
        # Store user info in request state for use in endpoints
        request.state.user = decoded_token

        return await call_next(request)

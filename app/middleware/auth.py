from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from typing import Callable

from app.api.v1.auth.firebase.Auth import FirebaseAuth

# Routes that require authentication
PROTECTED_ROUTES = [
    "/api/v1/settings",
    "/api/v1/analytics",
]


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Authentication middleware that verifies tokens from cookies.

    Only enforces auth on protected routes (settings, analytics).
    """

    async def dispatch(self, request: Request, call_next: Callable):
        path = request.url.path

        # Only enforce auth on protected routes
        if not any(path.startswith(route) for route in PROTECTED_ROUTES):
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

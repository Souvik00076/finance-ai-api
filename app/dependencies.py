"""Global application dependencies."""

from fastapi import Request
from typing import Dict, Any

from app.models.user import User
from app.utils.exceptions import UnauthorizedException


async def get_current_user(request: Request) -> User:
    """
    Get current authenticated user from request.state.

    The AuthMiddleware stores decoded token in request.state.user.
    This dependency fetches the full user from database.

    Args:
        request: FastAPI request object

    Returns:
        User object from database

    Raises:
        UnauthorizedException: If user not found in request.state or database
    """
    # Get user data from middleware
    user_data = getattr(request.state, "user", None)

    if user_data is None:
        raise UnauthorizedException("Not authenticated")

    # Fetch full user from database
    user = await User.find_one(User.google_uid == user_data["uid"])

    if user is None:
        raise UnauthorizedException("User not found")

    return user

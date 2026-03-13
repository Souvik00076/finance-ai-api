from fastapi import APIRouter, Request, Response, status, Depends
from typing import Dict, Any

from app.core.config import settings
from app.auth.firebase.Auth import FirebaseAuth
from app.auth.schemas import (
    EmailSignupRequest,
    EmailLoginRequest,
    GoogleAuthRequest,
    AuthResponse,
    MessageResponse,
    VerifyUserEmailRequest,
)
from app.models.user import User
from app.schemas.common import ResponseModel
from app.utils.send_email import send_email
from app.utils.email_templates import generate_verification_template
from app.utils.exceptions import BadRequestException, ConflictException, NotFoundException

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", status_code=status.HTTP_201_CREATED,
             response_model=ResponseModel)
async def signup(request: EmailSignupRequest):
    """
    Register a new user with email and password.

    Returns user data and authentication tokens.
    """
    (email, password, full_name, redirect_uri) = (
        request.email, request.password, request.full_name, request.redirect_uri)
    firebase_admin = FirebaseAuth()
    user_info = await User.find_one(User.email == email)
    if user_info is not None:
        raise ConflictException(detail=f'User with {email} already exist')

    firebase_user = firebase_admin.create_user(email, password)
    user = User(
        email=email,
        provider='email',
        google_uid=str(firebase_user.uid)
    )
    if full_name is not None:
        user.full_name = full_name
    await user.insert()
    template_body = generate_verification_template(
        email, redirect_uri+f'?action_code=122321&email={email}')
    send_email("souvikfs06@gmail.com",
               'Email Verification Needed', template_body)
    return ResponseModel(
        success=True,
        message=f"Verification mail has been sent to your email {email}"
    )


@router.post("/login", response_model=ResponseModel, status_code=status.HTTP_200_OK)
async def login(request: EmailLoginRequest, response: Response):
    """
    Login with email and password.

    Sets secure HTTP-only cookies with tokens.
    """
    (email, password) = (request.email, request.password)
    firebase_admin = FirebaseAuth()
    user_info = await User.find_one(User.email == email)
    if user_info is None:
        raise NotFoundException(f'No account exist with this email {email}')
    if not user_info.email_verified:
        raise BadRequestException(f'First verify the email {email}')
    firebase_response = await firebase_admin.signin_with_email_password(email, password)

    # Determine if we're in production
    is_production = settings.ENV == "production"

    # Set access token cookie
    response.set_cookie(
        key="access_token",
        value=firebase_response['id_token'],
        httponly=True,          # Prevents JavaScript access (XSS protection)
        secure=is_production,   # HTTPS only in production
        samesite="lax",         # CSRF protection
        max_age=firebase_response['expires_in'],  # Expiry in seconds
        path="/",
    )

    # Set refresh token cookie (longer lived)
    response.set_cookie(
        key="refresh_token",
        value=firebase_response['refresh_token'],
        httponly=True,
        secure=is_production,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,  # 30 days
        path="/auth/refresh",       # Only sent to refresh endpoint
    )

    return ResponseModel(
        message="Logged in successfully",
        success=True,
    )


@router.post("/oauth/google", response_model=AuthResponse)
async def google_auth(request: GoogleAuthRequest):
    """
    Authenticate with Google OAuth.

    Handles both login and signup:
    - If user exists: logs them in
    - If user doesn't exist: creates a new account

    Returns user data and authentication tokens.
    """
    pass


@router.post("/refresh", response_model=ResponseModel, status_code=status.HTTP_200_OK)
async def refresh_token(request: Request, response: Response):
    """
    Refresh access token using refresh token from cookie.

    Sets new access token cookie.
    """
    firebase_admin = FirebaseAuth()

    # Get refresh token from cookie
    refresh_token_value = request.cookies.get("refresh_token")
    if not refresh_token_value:
        raise BadRequestException("Refresh token not found")

    firebase_response = await firebase_admin.refresh_id_token(refresh_token_value)

    is_production = settings.ENV == "production"

    # Set new access token cookie
    response.set_cookie(
        key="access_token",
        value=firebase_response['id_token'],
        httponly=True,
        secure=is_production,
        samesite="lax",
        max_age=firebase_response['expires_in'],
        path="/",
    )

    # Update refresh token cookie
    response.set_cookie(
        key="refresh_token",
        value=firebase_response['refresh_token'],
        httponly=True,
        secure=is_production,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
        path="/auth/refresh",
    )

    return ResponseModel(
        message="Token refreshed successfully",
        success=True,
    )


@router.post("/logout", response_model=ResponseModel, status_code=status.HTTP_200_OK)
async def logout(response: Response):
    """
    Logout current user.

    Clears authentication cookies.
    """
    # Clear access token cookie
    response.delete_cookie(
        key="access_token",
        path="/",
    )

    # Clear refresh token cookie
    response.delete_cookie(
        key="refresh_token",
        path="/auth/refresh",
    )

    return MessageResponse(
        message="Logged out successfully",
        success=True
    )


@router.post("/verify-email", response_model=ResponseModel)
async def verify_user_email(request: VerifyUserEmailRequest):
    (email, action_code) = (request.email, request.action_code)
    firebase_admin = FirebaseAuth()
    user_info = await User.find_one(User.email == email)
    if user_info is None:
        raise NotFoundException(f'No user exist with the email {email}')
    user_info.email_verified = True
    await user_info.save()
    firebase_admin.update_user(
        user_info.google_uid, disabled=False, email_verified=True)
    return ResponseModel(
        success=True,
        message=f"{email} has been verified"
    )

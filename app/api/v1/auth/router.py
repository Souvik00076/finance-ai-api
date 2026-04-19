from typing import Optional
from fastapi import APIRouter, Request, Response, status
from fastapi.responses import RedirectResponse

import base64
import json
from app.api.v1.auth.oauths.google_oauth_strategy import GoogleOAuthStrategy
from app.api.v1.auth.oauths.oauth_strategy import OAuthStrategy
from app.core.config import settings
from app.api.v1.auth.firebase.Auth import FirebaseAuth
from app.api.v1.auth.schemas import (
    EmailSignupRequest,
    EmailLoginRequest,
    GoogleAuthRequest,
    AuthResponse,
    MessageResponse,
    OAuthProvider,
    OAuthRequestResponse,
    VerifyUserEmailRequest,
)
import uuid
from app.models.user import User
from app.schemas.common import ResponseModel
from app.utils.send_email import send_email
from app.utils.email_templates import generate_verification_template
from app.utils.exceptions import BadRequestException, ConflictException, NotFoundException, UnauthorizedException
from app.core.redis import redis_manager

THIRTY_DAYS = 60 * 60 * 24 * 30

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
    send_email(email,
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
        httponly=True,
        secure=is_production,
        samesite="lax",
        max_age=firebase_response['expires_in'],
        path="/",
    )

    # Set refresh token cookie (longer lived)
    response.set_cookie(
        key="refresh_token",
        value=firebase_response['refresh_token'],
        httponly=True,
        secure=is_production,
        samesite="lax",
        max_age=THIRTY_DAYS,
        path="/auth/refresh",       # Only sent to refresh endpoint
    )

    # Store refresh token in Redis with 30-day expiry
    await redis_manager.set(
        f"refresh_token:{user_info.google_uid}",
        firebase_response['refresh_token'],
        ex=THIRTY_DAYS,
    )

    return ResponseModel(
        message="Logged in successfully",
        success=True,
    )


@router.get("/oauth/{provider_id}",
            response_model=ResponseModel[OAuthRequestResponse],
            status_code=status.HTTP_200_OK)
async def get_oauth_url(provider_id: OAuthProvider):
    google_oauth: OAuthStrategy = GoogleOAuthStrategy()
    if provider_id == OAuthProvider.facebook:
        pass
    state = str(uuid.uuid4())
    await redis_manager.set(f"oauth_state:{state}", provider_id.value, ex=300)
    auth_url = google_oauth.get_auth_url(state)
    return ResponseModel(
        message="Url for oauth",
        data=OAuthRequestResponse(
            redirect_url=auth_url
        )
    )


@router.get("/oauth/{provider_id}/callback")
async def google_callback(provider_id: OAuthProvider, code: str, state: str):
    google_oauth: Optional[OAuthStrategy] = None
    # Decode the base64-encoded state and extract the actual state
    try:
        state_data = json.loads(base64.b64decode(state).decode())
        actual_state = state_data["state"]
    except Exception:
        raise BadRequestException(detail="Invalid OAuth state encoding")

    # Validate and delete the OAuth state from Redis
    stored_state = await redis_manager.get(f"oauth_state:{actual_state}")
    if not stored_state:
        raise BadRequestException(detail="Invalid or expired OAuth state")
    await redis_manager.delete(f"oauth_state:{actual_state}")

    if provider_id == OAuthProvider.facebook:
        pass
    if provider_id == OAuthProvider.google:
        google_oauth = GoogleOAuthStrategy()
    if google_oauth is None:
        raise BadRequestException(detail="Invalid provider")
    oauth_access_token = await google_oauth.exchange_code_for_token(code)
    oauth_user_info = await google_oauth.get_user_info(oauth_access_token)

    provider_name = google_oauth.get_provider_name()

    # Look up user by email
    user_info = await User.find_one(User.email == oauth_user_info.email)

    if user_info is not None:
        # Existing user — must be an OAuth user
        if user_info.provider != provider_name:
            raise BadRequestException(
                detail=f"Account already exists with provider '{
                    user_info.provider}'. Use {user_info.provider} to login."
            )
    else:
        # New user — create Firebase user and DB record
        firebase_admin = FirebaseAuth()
        try:
            firebase_user = firebase_admin.get_user_by_email(
                oauth_user_info.email)
        except NotFoundException:
            firebase_user = firebase_admin.create_user(
                oauth_user_info.email, str(uuid.uuid4()))
            firebase_admin.update_user(
                firebase_user.uid, email_verified=True, disabled=False)

        user_info = User(
            email=oauth_user_info.email,
            full_name=oauth_user_info.name,
            picture=oauth_user_info.picture,
            provider=provider_name,
            google_uid=str(firebase_user.uid),
            email_verified=True,
        )
        await user_info.insert()

    # Get Firebase tokens via custom token exchange
    firebase_admin = FirebaseAuth()
    custom_token = firebase_admin.create_custom_token(user_info.google_uid)
    firebase_response = await firebase_admin.exchange_custom_token_for_id_token(custom_token)

    is_production = settings.ENV == "production"
    # TODO: replace with actual client URL
    redirect_url = "https://spendly.souvikb.in/dashboard" if is_production else "localhost:3001/dashboard"

    response = RedirectResponse(
        url=redirect_url, status_code=status.HTTP_302_FOUND)

    response.set_cookie(
        key="access_token",
        value=firebase_response["id_token"],
        httponly=True,
        secure=is_production,
        samesite="lax",
        max_age=firebase_response["expires_in"],
        path="/",
    )

    response.set_cookie(
        key="refresh_token",
        value=firebase_response["refresh_token"],
        httponly=True,
        secure=is_production,
        samesite="lax",
        max_age=THIRTY_DAYS,
        path="/auth/refresh",
    )

    # Store refresh token in Redis with 30-day expiry
    await redis_manager.set(
        f"refresh_token:{user_info.google_uid}",
        firebase_response["refresh_token"],
        ex=THIRTY_DAYS,
    )

    return response


@router.post("/refresh", response_model=ResponseModel, status_code=status.HTTP_200_OK)
async def refresh_token(request: Request, response: Response):
    """
    Refresh access token using refresh token from cookie.

    Sets new access token cookie.
    """
    firebase_admin = FirebaseAuth()

    # Get uid from request (set by auth middleware)
    uid = getattr(request.state, "uid", None)
    if not uid:
        raise UnauthorizedException("Authentication required")

    # Check if refresh token exists in Redis
    refresh_token_value = await redis_manager.get(f"refresh_token:{uid}")
    if not refresh_token_value:
        raise UnauthorizedException("Session expired. Please login again.")

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
    firebase_admin.update_user(
        user_info.google_uid, disabled=False, email_verified=True)
    await user_info.save()
    return ResponseModel(
        success=True,
        message=f"{email} has been verified"
    )

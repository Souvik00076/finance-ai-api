"""Firebase Authentication handler for email/password auth and token management."""

import httpx
import logging
from typing import Dict, Any, Optional
from firebase_admin import auth

from app.core.config import settings
from app.utils.exceptions import (
    InternalServerException,
    UnauthorizedException,
    BadRequestException,
    NotFoundException,
)

logger = logging.getLogger(__name__)

# Firebase Auth REST API endpoint
FIREBASE_AUTH_URL = "https://identitytoolkit.googleapis.com/v1/accounts"


class FirebaseAuth:
    """
    Firebase Authentication handler.

    Handles email/password authentication using Firebase Auth REST API
    and token operations using Firebase Admin SDK.
    """

    def create_user(self, email: str, password: str) -> auth.UserRecord:
        """
        Create a new user in Firebase.
        Args:
            email: User's email address
            password: User's password
        Returns:
            Firebase UserRecord

        Raises:
            BadRequestException: If user creation fails
        """
        try:
            user = auth.create_user(
                email=email,
                password=password,
                email_verified=False,
                disabled=True
            )
            logger.info(f"Created Firebase user: {user.uid}")
            return user
        except auth.EmailAlreadyExistsError:
            raise BadRequestException("Email already registered")
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            raise BadRequestException(f"Failed to create user: {str(e)}")

    async def signin_with_email_password(self, email: str, password: str) -> Dict[str, Any]:
        """
        Sign in user with email and password using Firebase Auth REST API.

        Args:
            email: User's email address
            password: User's password

        Returns:
            Dict containing idToken, refreshToken, expiresIn, localId, and email

        Raises:
            UnauthorizedException: If credentials are invalid
            BadRequestException: If request fails
        """
        if settings.FIREBASE_API_KEY is None:
            raise InternalServerException("Something went wrong")

        url = f"{FIREBASE_AUTH_URL}:signInWithPassword?key={
            settings.FIREBASE_API_KEY}"

        payload = {
            "email": email,
            "password": password,
            "returnSecureToken": True
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload)
                data = response.json()

                if response.status_code != 200:
                    error_message = self._parse_firebase_error(data)
                    logger.warning(f"Firebase signin failed for {
                                   email}: {error_message}")
                    raise UnauthorizedException(error_message)

                logger.info(f"User signed in successfully: {email}")
                return {
                    "id_token": data.get("idToken"),
                    "refresh_token": data.get("refreshToken"),
                    "expires_in": int(data.get("expiresIn", 3600)),
                    "local_id": data.get("localId"),
                    "email": data.get("email"),
                }

        except httpx.RequestError as e:
            logger.error(f"Firebase request failed: {e}")
            raise BadRequestException(
                "Failed to connect to authentication service")

    async def refresh_id_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh Firebase ID token using refresh token.

        Args:
            refresh_token: Firebase refresh token

        Returns:
            Dict containing new id_token, refresh_token, and expires_in

        Raises:
            UnauthorizedException: If refresh token is invalid
        """
        if settings.FIREBASE_API_KEY is None:
            raise InternalServerException("Something went wrong")

        url = f"https://securetoken.googleapis.com/v1/token?key={
            settings.FIREBASE_API_KEY}"

        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, data=payload)
                data = response.json()

                if response.status_code != 200:
                    error_message = self._parse_firebase_error(data)
                    logger.warning(f"Token refresh failed: {error_message}")
                    raise UnauthorizedException(
                        "Invalid or expired refresh token")

                return {
                    "id_token": data.get("id_token"),
                    "refresh_token": data.get("refresh_token"),
                    "expires_in": int(data.get("expires_in", 3600)),
                }

        except httpx.RequestError as e:
            logger.error(f"Firebase token refresh failed: {e}")
            raise BadRequestException("Failed to refresh token")

    def create_custom_token(self, uid: str, claims: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a custom Firebase token for a user.

        Args:
            uid: User's Firebase UID
            claims: Optional custom claims to include in the token

        Returns:
            Custom token string

        Raises:
            BadRequestException: If token generation fails
        """
        try:
            custom_token = auth.create_custom_token(uid, claims)
            logger.info(f"Created custom token for user: {uid}")
            return custom_token.decode('utf-8') if isinstance(custom_token, bytes) else custom_token
        except Exception as e:
            logger.error(f"Failed to create custom token: {e}")
            raise BadRequestException(f"Failed to generate token: {str(e)}")

    async def exchange_custom_token_for_id_token(self, custom_token: str) -> Dict[str, Any]:
        """
        Exchange a custom token for an ID token using Firebase Auth REST API.

        Args:
            custom_token: Firebase custom token

        Returns:
            Dict containing idToken, refreshToken, and expiresIn

        Raises:
            UnauthorizedException: If custom token is invalid
        """
        if settings.FIREBASE_API_KEY is None:
            raise InternalServerException("Firebase API key not configured")

        url = f"{FIREBASE_AUTH_URL}:signInWithCustomToken?key={
            settings.FIREBASE_API_KEY}"

        payload = {
            "token": custom_token,
            "returnSecureToken": True
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload)
                data = response.json()

                if response.status_code != 200:
                    error_message = self._parse_firebase_error(data)
                    raise UnauthorizedException(error_message)

                return {
                    "id_token": data.get("idToken"),
                    "refresh_token": data.get("refreshToken"),
                    "expires_in": int(data.get("expiresIn", 3600)),
                }

        except httpx.RequestError as e:
            logger.error(f"Failed to exchange custom token: {e}")
            raise BadRequestException("Failed to exchange token")

    async def verify_id_token(self, id_token: str, check_revoked: bool = False) -> Dict[str, Any]:
        """
        Verify a Firebase ID token.

        Args:
            id_token: Firebase ID token to verify
            check_revoked: Whether to check if token has been revoked

        Returns:
            Decoded token claims

        Raises:
            UnauthorizedException: If token is invalid or expired
        """
        try:
            decoded_token = auth.verify_id_token(
                id_token, check_revoked=check_revoked)
            return {
                "uid": decoded_token.get("uid"),
                "email": decoded_token.get("email"),
                "email_verified": decoded_token.get("email_verified", False),
                "name": decoded_token.get("name"),
                "picture": decoded_token.get("picture"),
            }
        except auth.ExpiredIdTokenError:
            raise UnauthorizedException("Token has expired")
        except auth.RevokedIdTokenError:
            raise UnauthorizedException("Token has been revoked")
        except auth.InvalidIdTokenError as e:
            raise UnauthorizedException(f"Invalid token: {str(e)}")
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            raise UnauthorizedException("Token verification failed")

    def get_user(self, uid: str) -> auth.UserRecord:
        """
        Get user by UID from Firebase.

        Args:
            uid: Firebase user UID

        Returns:
            Firebase UserRecord

        Raises:
            NotFoundException: If user not found
        """
        try:
            return auth.get_user(uid)
        except auth.UserNotFoundError:
            raise NotFoundException(f"User not found: {uid}")
        except Exception as e:
            logger.error(f"Failed to get user: {e}")
            raise BadRequestException(f"Failed to get user: {str(e)}")

    def get_user_by_email(self, email: str) -> auth.UserRecord:
        """
        Get user by email from Firebase.

        Args:
            email: User's email address

        Returns:
            Firebase UserRecord

        Raises:
            NotFoundException: If user not found
        """
        try:
            return auth.get_user_by_email(email)
        except auth.UserNotFoundError:
            raise NotFoundException(f"User not found with email: {email}")
        except Exception as e:
            logger.error(f"Failed to get user by email: {e}")
            raise BadRequestException(f"Failed to get user: {str(e)}")

    def update_user(self, uid: str, **kwargs) -> auth.UserRecord:
        """
        Update user properties in Firebase.

        Args:
            uid: Firebase user UID
            **kwargs: Properties to update (email, password, display_name, etc.)

        Returns:
            Updated Firebase UserRecord
        """
        try:
            return auth.update_user(uid, **kwargs)
        except auth.UserNotFoundError:
            raise NotFoundException(f"User not found: {uid}")
        except Exception as e:
            logger.error(f"Failed to update user: {e}")
            raise BadRequestException(f"Failed to update user: {str(e)}")

    def enable_user(self, uid: str) -> auth.UserRecord:
        """Enable a disabled user account."""
        return self.update_user(uid, disabled=False)

    def disable_user(self, uid: str) -> auth.UserRecord:
        """Disable a user account."""
        return self.update_user(uid, disabled=True)

    def set_email_verified(self, uid: str, verified: bool = True) -> auth.UserRecord:
        """Set user's email verification status."""
        return self.update_user(uid, email_verified=verified)

    def delete_user(self, uid: str) -> None:
        """
        Delete a user from Firebase.

        Args:
            uid: Firebase user UID
        """
        try:
            auth.delete_user(uid)
            logger.info(f"Deleted Firebase user: {uid}")
        except auth.UserNotFoundError:
            raise NotFoundException(f"User not found: {uid}")
        except Exception as e:
            logger.error(f"Failed to delete user: {e}")
            raise BadRequestException(f"Failed to delete user: {str(e)}")

    def revoke_refresh_tokens(self, uid: str) -> None:
        """
        Revoke all refresh tokens for a user.

        Args:
            uid: Firebase user UID
        """
        try:
            auth.revoke_refresh_tokens(uid)
            logger.info(f"Revoked refresh tokens for user: {uid}")
        except auth.UserNotFoundError:
            raise NotFoundException(f"User not found: {uid}")
        except Exception as e:
            logger.error(f"Failed to revoke tokens: {e}")
            raise BadRequestException(f"Failed to revoke tokens: {str(e)}")

    def _parse_firebase_error(self, error_data: Dict[str, Any]) -> str:
        """Parse Firebase error response and return user-friendly message."""
        error = error_data.get("error", {})
        error_code = error.get("message", "UNKNOWN_ERROR")

        error_messages = {
            "EMAIL_NOT_FOUND": "No account found with this email",
            "INVALID_PASSWORD": "Invalid password",
            "INVALID_LOGIN_CREDENTIALS": "Invalid email or password",
            "USER_DISABLED": "This account has been disabled",
            "TOO_MANY_ATTEMPTS_TRY_LATER": "Too many failed attempts. Please try again later",
            "EMAIL_EXISTS": "Email already registered",
            "OPERATION_NOT_ALLOWED": "Email/password sign-in is not enabled",
            "WEAK_PASSWORD": "Password is too weak",
            "INVALID_EMAIL": "Invalid email address",
            "TOKEN_EXPIRED": "Token has expired",
            "INVALID_REFRESH_TOKEN": "Invalid refresh token",
        }

        return error_messages.get(error_code, f"Authentication failed: {error_code}")

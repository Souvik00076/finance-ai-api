import firebase_admin
from firebase_admin import credentials, auth
from typing import Optional, Dict, Any
import logging
import os

from app.core.config import settings

logger = logging.getLogger(__name__)

_firebase_app: Optional[firebase_admin.App] = None


def init_firebase() -> None:
    """Initialize Firebase Admin SDK."""
    global _firebase_app

    if _firebase_app is not None:
        logger.info("Firebase already initialized")
        return

    try:
        # Check for service account credentials
        cred_path = getattr(settings, 'FIREBASE_CREDENTIALS_PATH', None)

        if cred_path and os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            _firebase_app = firebase_admin.initialize_app(cred)
            logger.info(
                "Firebase initialized with service account credentials")
        else:
            # Try default credentials (for Cloud Run, GCE, etc.)
            _firebase_app = firebase_admin.initialize_app()
            logger.info("Firebase initialized with default credentials")

    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {e}")
        raise


def get_firebase_app() -> firebase_admin.App:
    """Get Firebase app instance."""
    if _firebase_app is None:
        raise RuntimeError(
            "Firebase not initialized. Call init_firebase() first.")
    return _firebase_app


async def verify_google_token(id_token: str) -> Dict[str, Any]:
    """
    Verify Google ID token using Firebase Admin SDK.

    Args:
        id_token: The Google ID token from client

    Returns:
        Decoded token containing user info (uid, email, name, etc.)

    Raises:
        ValueError: If token is invalid or expired
    """
    try:
        decoded_token = auth.verify_id_token(id_token)

        return {
            "uid": decoded_token.get("uid"),
            "email": decoded_token.get("email"),
            "email_verified": decoded_token.get("email_verified", False),
            "name": decoded_token.get("name"),
            "picture": decoded_token.get("picture"),
            "provider": "google"
        }

    except auth.ExpiredIdTokenError:
        raise ValueError("Google ID token has expired")
    except auth.RevokedIdTokenError:
        raise ValueError("Google ID token has been revoked")
    except auth.InvalidIdTokenError as e:
        raise ValueError(f"Invalid Google ID token: {str(e)}")
    except Exception as e:
        logger.error(f"Error verifying Google token: {e}")
        raise ValueError(f"Failed to verify Google token: {str(e)}")

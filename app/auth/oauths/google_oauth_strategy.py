from typing import Dict, Any, Optional
import httpx
from urllib.parse import urlencode

from app.auth.oauths.oauth_strategy import OAuthStrategy


class GoogleOAuthStrategy(OAuthStrategy):
    """
    Google OAuth 2.0 authentication strategy implementation.
    
    This class implements the OAuth flow for Google authentication,
    following the OAuth 2.0 protocol.
    """
    
    AUTHORIZATION_BASE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    USER_INFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
    REVOKE_URL = "https://oauth2.googleapis.com/revoke"
    
    def __init__(self, client_id: str, client_secret: str, scopes: Optional[list] = None):
        """
        Initialize the Google OAuth strategy.
        
        Args:
            client_id: Google OAuth client ID
            client_secret: Google OAuth client secret
            scopes: List of OAuth scopes to request (default: email, profile, openid)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.scopes = scopes or [
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
            "openid"
        ]
    
    async def get_authorization_url(self, redirect_uri: str, state: str) -> str:
        """
        Generate the Google OAuth authorization URL.
        
        Args:
            redirect_uri: The URI to redirect to after authorization
            state: A unique state token for CSRF protection
            
        Returns:
            The authorization URL to redirect the user to
        """
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "state": state,
            "access_type": "offline",  # Request refresh token
            "prompt": "consent"  # Force consent to get refresh token
        }
        return f"{self.AUTHORIZATION_BASE_URL}?{urlencode(params)}"
    
    async def exchange_code_for_token(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """
        Exchange an authorization code for access tokens.
        
        Args:
            code: The authorization code received from Google
            redirect_uri: The redirect URI used in the initial authorization request
            
        Returns:
            A dictionary containing access_token, refresh_token, and other token data
        """
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(self.TOKEN_URL, data=data)
            response.raise_for_status()
            return response.json()
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        Retrieve user information from Google.
        
        Args:
            access_token: The access token obtained from Google
            
        Returns:
            A dictionary containing user information (email, name, profile picture, etc.)
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(self.USER_INFO_URL, headers=headers)
            response.raise_for_status()
            return response.json()
    
    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh an expired access token using a refresh token.
        
        Args:
            refresh_token: The refresh token to use
            
        Returns:
            A dictionary containing the new access_token and related data
        """
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(self.TOKEN_URL, data=data)
            response.raise_for_status()
            return response.json()
    
    async def revoke_token(self, token: str) -> bool:
        """
        Revoke an access or refresh token.
        
        Args:
            token: The token to revoke
            
        Returns:
            True if revocation was successful, False otherwise
        """
        params = {"token": token}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(self.REVOKE_URL, params=params)
            return response.status_code == 200

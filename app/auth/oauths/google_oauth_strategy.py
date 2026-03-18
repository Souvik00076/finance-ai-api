import base64
import json
from typing import Any
import httpx
from fastapi import HTTPException, status

from app.core.config import Settings
from app.auth.oauths.oauth_strategy import OAuthStrategy, OAuthUserInfo
from app.core.config import settings


class GoogleOAuthStrategy(OAuthStrategy):
    def __init__(self):
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        self.redirect_uri = f"{
            settings.BACKEND_URL}/api/v1/auth/oauth/google/callback"

    def get_auth_url(self, state: str, redirect_uri_params: dict[str, Any] = {}) -> str:
        state_data = {
            "state": state,
            "redirect_uri_params": redirect_uri_params
        }
        state_encoded = base64.b64encode(
            json.dumps(state_data).encode()).decode()
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state_encoded
        }
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"https://accounts.google.com/o/oauth2/v2/auth?{query_string}"

    async def exchange_code_for_token(self, code: str) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "code": code,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": self.redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
        if response.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Code")
        data = response.json()
        return data["access_token"]

    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
        if response.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Token")
        data = response.json()
        return OAuthUserInfo(
            id=data["id"],
            email=data["email"],
            name=data["name"],
            picture=data.get("picture"),
            email_verified=data.get("verified_email", False),
        )

    def get_provider_name(self) -> str:
        return "google"

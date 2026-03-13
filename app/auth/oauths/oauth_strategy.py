from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class OAuthStrategy(ABC):
    """
    Abstract base class for OAuth authentication strategies.

    This class defines the interface that all OAuth strategy implementations
    must follow, ensuring consistent authentication flow across different providers.
    """

    @abstractmethod
    async def get_authorization_url(self, redirect_uri: str, state: str) -> str:
        """
        Generate the OAuth provider's authorization URL.

        Args:
            redirect_uri: The URI to redirect to after authorization
            state: A unique state token for CSRF protection

        Returns:
            The authorization URL to redirect the user to
        """
        pass

    @abstractmethod
    async def exchange_code_for_token(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """
        Exchange an authorization code for access tokens.

        Args:
            code: The authorization code received from the OAuth provider
            redirect_uri: The redirect URI used in the initial authorization request

        Returns:
            A dictionary containing access_token, refresh_token, and other token data
        """
        pass

    @abstractmethod
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        Retrieve user information from the OAuth provider.

        Args:
            access_token: The access token obtained from the provider

        Returns:
            A dictionary containing user information (email, name, profile picture, etc.)
        """
        pass

    @abstractmethod
    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh an expired access token using a refresh token.

        Args:
            refresh_token: The refresh token to use

        Returns:
            A dictionary containing the new access_token and related data
        """
        pass

    @abstractmethod
    async def revoke_token(self, token: str) -> bool:
        """
        Revoke an access or refresh token.

        Args:
            token: The token to revoke

        Returns:
            True if revocation was successful, False otherwise
        """
        pass

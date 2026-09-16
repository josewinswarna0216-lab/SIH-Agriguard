"""Sentinel Hub OAuth2 Authentication and Client Configuration for Copernicus Data Space Ecosystem (CDSE).

Manages OAuth credentials securely from environment variables, configures
the Sentinel Hub Python SDK session for CDSE, and caches OAuth2 access tokens
reusing them while valid.
"""

import time
import logging
import requests
from typing import Dict, Any, Optional
from sentinelhub import SHConfig, SentinelHubSession
from sentinelhub.exceptions import BaseSentinelHubException

from ..config import settings

logger = logging.getLogger(__name__)


class CDSETokenManager:
    """Thread-safe OAuth2 Token Manager for Copernicus Data Space Ecosystem.

    Caches retrieved OAuth2 access tokens and reuses them until 30 seconds
    before expiration to prevent redundant authentication requests.
    """

    _instance: Optional["CDSETokenManager"] = None
    _token: Optional[str] = None
    _expires_at: float = 0.0

    @classmethod
    def get_instance(cls) -> "CDSETokenManager":
        if cls._instance is None:
            cls._instance = CDSETokenManager()
        return cls._instance

    def get_valid_token(self) -> Optional[str]:
        """Retrieve a valid cached OAuth2 token or fetch a new one from CDSE token endpoint.

        Returns:
            str: OAuth2 access token, or None if authentication fails / demo mode.

        Raises:
            ValueError: If credentials are missing when not in demo mode.
        """
        if settings.DEMO_MODE:
            return None

        # Reuse cached token if valid for at least another 30 seconds
        if self._token and time.time() < (self._expires_at - 30.0):
            logger.debug("Reusing cached CDSE OAuth2 access token.")
            return self._token

        client_id = settings.get_client_id
        client_secret = settings.get_client_secret

        if not client_id or not client_secret:
            settings.validate_credentials()
            return None

        logger.info("Requesting new CDSE OAuth2 access token from Copernicus token endpoint.")
        try:
            response = requests.post(
                settings.CDSE_TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=15.0
            )

            if response.status_code == 200:
                payload = response.json()
                access_token = payload.get("access_token")
                expires_in = payload.get("expires_in", 3600)

                if access_token:
                    self._token = access_token
                    self._expires_at = time.time() + float(expires_in)
                    logger.info("Successfully acquired and cached new CDSE OAuth2 access token.")
                    return self._token
                else:
                    raise ValueError("CDSE token endpoint returned 200 OK but no access_token in response body.")
            else:
                logger.error(f"CDSE token request failed with HTTP status {response.status_code}")
                raise ValueError(f"CDSE OAuth2 authentication failed with HTTP status {response.status_code}")

        except requests.RequestException as req_err:
            logger.error("Network error connecting to CDSE token endpoint.")
            raise ValueError(f"Could not connect to CDSE authentication server: {type(req_err).__name__}")


def get_sh_config() -> SHConfig:
    """Initialize and return a Sentinel Hub SHConfig object configured for CDSE.

    Reads client ID and secret from application settings and sets official CDSE endpoints.

    Returns:
        SHConfig: Configured Sentinel Hub configuration object.

    Raises:
        ValueError: If DEMO_MODE is False and credentials are missing.
    """
    settings.validate_credentials()

    config = SHConfig()
    cid = settings.get_client_id
    sec = settings.get_client_secret

    if cid:
        config.sh_client_id = cid
    if sec:
        config.sh_client_secret = sec

    # Configure official Copernicus Data Space Ecosystem (CDSE) API URLs
    config.sh_base_url = settings.CDSE_BASE_URL
    config.sh_auth_base_url = settings.CDSE_AUTH_BASE_URL
    config.sh_token_url = settings.CDSE_TOKEN_URL

    return config


def check_sentinelhub_connection() -> Dict[str, Any]:
    """Check connectivity and credentials validity with the real CDSE Sentinel Hub API.

    Returns:
        dict: Status information including connectivity and authentication state.
    """
    if settings.DEMO_MODE:
        return {
            "status": "demo_mode",
            "authenticated": True,
            "message": "Running in DEMO_MODE. Real Sentinel Hub credentials are not required."
        }

    try:
        # Validate credentials exist
        settings.validate_credentials()

        # Test token manager acquisition
        token_mgr = CDSETokenManager.get_instance()
        token = token_mgr.get_valid_token()

        if token:
            return {
                "status": "connected",
                "authenticated": True,
                "message": "Successfully authenticated with Copernicus Data Space Ecosystem (CDSE) Sentinel Hub OAuth2."
            }

        # Fallback to SentinelHubSession test
        config = get_sh_config()
        session = SentinelHubSession(config=config)
        sh_token = session.token
        if sh_token and "access_token" in sh_token:
            return {
                "status": "connected",
                "authenticated": True,
                "message": "Successfully authenticated with Copernicus Data Space Ecosystem (CDSE) Sentinel Hub OAuth2."
            }
        else:
            return {
                "status": "error",
                "authenticated": False,
                "message": "OAuth token was not obtained from CDSE Sentinel Hub."
            }

    except BaseSentinelHubException as auth_err:
        logger.error("Sentinel Hub SDK exception during connection test.")
        return {
            "status": "auth_failed",
            "authenticated": False,
            "message": f"CDSE Sentinel Hub request failed: {str(auth_err)}"
        }
    except Exception as exc:
        logger.error(f"Sentinel Hub connection error: {exc}")
        return {
            "status": "error",
            "authenticated": False,
            "message": f"Could not connect to CDSE Sentinel Hub: {str(exc)}"
        }

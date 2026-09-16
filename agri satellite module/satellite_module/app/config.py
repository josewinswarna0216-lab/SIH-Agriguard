"""Configuration module for the Satellite / Geospatial Integration Module.

Manages environment variables, thresholds, and Sentinel Hub credentials.
"""

from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = BASE_DIR / "outputs"
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    # Sentinel Hub OAuth2 credentials (supports both SENTINELHUB_ and SENTINEL_HUB_ naming)
    SENTINELHUB_CLIENT_ID: Optional[str] = Field(default=None, description="Sentinel Hub OAuth2 Client ID")
    SENTINELHUB_CLIENT_SECRET: Optional[str] = Field(default=None, description="Sentinel Hub OAuth2 Client Secret")
    SENTINEL_HUB_CLIENT_ID: Optional[str] = Field(default=None, description="Copernicus Data Space Sentinel Hub Client ID")
    SENTINEL_HUB_CLIENT_SECRET: Optional[str] = Field(default=None, description="Copernicus Data Space Sentinel Hub Client Secret")

    # Copernicus Data Space Ecosystem (CDSE) API URLs
    CDSE_BASE_URL: str = Field(default="https://sh.dataspace.copernicus.eu", description="Sentinel Hub API Base URL")
    CDSE_TOKEN_URL: str = Field(
        default="https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
        description="CDSE OpenID Connect OAuth2 Token URL"
    )
    CDSE_AUTH_BASE_URL: str = Field(
        default="https://identity.dataspace.copernicus.eu/auth/realms/CDSE",
        description="CDSE Keycloak Auth Base URL"
    )

    # Operating mode: when true, runs using realistic simulated Sentinel-2 data
    DEMO_MODE: bool = Field(
        default=True,
        description="Run in demonstration mode without live Sentinel Hub credentials"
    )

    # Cloud filtering threshold (percentage 0 - 100)
    MAX_CLOUD_COVER: float = Field(
        default=20.0,
        description="Maximum acceptable scene cloud cover percentage"
    )

    # Vegetation stress thresholds
    NDVI_HEALTHY_THRESHOLD: float = Field(
        default=0.65,
        description="NDVI >= this value is classified as HEALTHY"
    )
    NDVI_MODERATE_THRESHOLD: float = Field(
        default=0.45,
        description="NDVI between MODERATE and HEALTHY is classified as MODERATE STRESS"
    )

    # Geospatial filtering threshold
    MIN_STRESS_AREA_HECTARES: float = Field(
        default=0.01,
        description="Minimum polygon area in hectares to eliminate isolated pixel noise"
    )

    # Server configuration
    HOST: str = Field(default="127.0.0.1", description="FastAPI server host")
    PORT: int = Field(default=8000, description="FastAPI server port")

    # Output directory
    OUTPUT_PATH: Path = Field(default=OUTPUTS_DIR, description="Directory to save generated maps")

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def get_client_id(self) -> Optional[str]:
        """Resolve client ID from SENTINEL_HUB_CLIENT_ID or SENTINELHUB_CLIENT_ID."""
        cid = self.SENTINEL_HUB_CLIENT_ID or self.SENTINELHUB_CLIENT_ID
        if cid and cid.strip() and cid.strip() not in ("your_client_id_here", "your_client_id"):
            return cid.strip()
        return None

    @property
    def get_client_secret(self) -> Optional[str]:
        """Resolve client secret from SENTINEL_HUB_CLIENT_SECRET or SENTINELHUB_CLIENT_SECRET."""
        sec = self.SENTINEL_HUB_CLIENT_SECRET or self.SENTINELHUB_CLIENT_SECRET
        if sec and sec.strip() and sec.strip() not in ("your_client_secret_here", "your_client_secret"):
            return sec.strip()
        return None

    def validate_credentials(self) -> None:
        """Validate that Sentinel Hub credentials are provided when not in demo mode.

        Raises:
            ValueError: If credentials are missing while DEMO_MODE is False.
        """
        if not self.DEMO_MODE:
            missing = []
            if not self.get_client_id:
                missing.append("SENTINEL_HUB_CLIENT_ID")
            if not self.get_client_secret:
                missing.append("SENTINEL_HUB_CLIENT_SECRET")

            if missing:
                raise ValueError(
                    f"Sentinel Hub authentication failed: Missing required credentials: {', '.join(missing)}.\n"
                    f"Please add your Sentinel Hub OAuth Client ID and Secret to your .env file or environment variables,\n"
                    f"or set DEMO_MODE=true to run in demonstration mode."
                )


# Singleton configuration instance
settings = Settings()


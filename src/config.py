"""
Configuration management for Social Sync
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class ConfigurationError(Exception):
    """Raised when configuration is missing or invalid."""

    pass


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Bluesky Configuration
    bluesky_handle: str = Field(default="", description="Bluesky handle")
    bluesky_password: str = Field(default="", description="Bluesky app password")

    # Mastodon Configuration
    mastodon_api_base_url: str = Field(
        default="https://mastodon.social", description="Mastodon instance URL"
    )
    mastodon_access_token: str = Field(default="", description="Mastodon access token")

    # Sync Configuration
    sync_interval_minutes: int = Field(
        default=60, description="Sync interval in minutes"
    )
    max_posts_per_sync: int = Field(default=10, description="Maximum posts per sync")
    sync_start_date: Optional[str] = Field(
        default=None,
        description="Start date for syncing posts (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS). If not set, starts from 7 days ago",
    )
    dry_run: bool = Field(default=False, description="Run in dry-run mode")
    disable_source_platform: bool = Field(
        default=False,
        description="Disable adding source platform attribution to synced posts",
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")

    # State file to track last synced post
    state_file: str = Field(default="sync_state.json", description="State file path")

    model_config = {"env_file": ".env", "case_sensitive": False, "extra": "ignore"}

    @field_validator("bluesky_handle")
    @classmethod
    def validate_bluesky_handle(cls, v):
        if not v or v == "your-handle.bsky.social":
            raise ValueError("Please set a valid Bluesky handle")
        return v

    @field_validator("bluesky_password")
    @classmethod
    def validate_bluesky_password(cls, v):
        if not v or v == "your-app-password":
            raise ValueError("Please set a valid Bluesky app password")
        return v

    @field_validator("mastodon_access_token")
    @classmethod
    def validate_mastodon_token(cls, v):
        if not v or v == "your-access-token":
            raise ValueError("Please set a valid Mastodon access token")
        return v

    @field_validator("sync_start_date")
    @classmethod
    def validate_sync_start_date(cls, v):
        if v is None:
            return v
        try:
            # Try to parse the date string
            if "T" in v:
                # Full datetime format
                datetime.fromisoformat(v.replace("Z", "+00:00"))
            else:
                # Date only format - add time
                datetime.fromisoformat(f"{v}T00:00:00+00:00")
            return v
        except ValueError:
            raise ValueError(
                "sync_start_date must be in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"
            )

    def get_sync_start_datetime(self) -> datetime:
        """Get the sync start date as a datetime object"""
        if self.sync_start_date:
            try:
                if "T" in self.sync_start_date:
                    # Full datetime format
                    return datetime.fromisoformat(
                        self.sync_start_date.replace("Z", "+00:00")
                    )
                else:
                    # Date only format - start at beginning of day UTC
                    return datetime.fromisoformat(
                        f"{self.sync_start_date}T00:00:00+00:00"
                    )
            except ValueError:
                pass

        # Default: 7 days ago
        from datetime import timedelta

        return datetime.now(timezone.utc) - timedelta(days=7)


def check_env_file_exists() -> bool:
    """Check if .env file exists in the current directory."""
    return Path(".env").exists()


def get_settings() -> Settings:
    """Get application settings with user-friendly error handling."""
    env_file_exists = check_env_file_exists()

    try:
        return Settings()
    except Exception as e:
        # Check if this is a validation error due to missing credentials
        if "Please set a valid" in str(e):
            if not env_file_exists:
                raise ConfigurationError(
                    "Configuration file missing!\n\n"
                    "To get started:\n"
                    "1. Copy the example configuration file:\n"
                    "   cp .env.example .env\n\n"
                    "2. Edit .env with your credentials:\n"
                    "   - Set your Bluesky handle and app password\n"
                    "   - Set your Mastodon instance URL and access token\n"
                    "   - Optionally configure sync settings\n\n"
                    "3. Run the command again\n\n"
                    "For detailed setup instructions, see: docs/SETUP.md"
                ) from e
            else:
                raise ConfigurationError(
                    "Configuration incomplete!\n\n"
                    "Your .env file exists but is missing required credentials.\n"
                    "Please check your .env file and ensure these are set:\n"
                    "- BLUESKY_HANDLE (your Bluesky handle)\n"
                    "- BLUESKY_PASSWORD (your Bluesky app password)\n"
                    "- MASTODON_ACCESS_TOKEN (your Mastodon access token)\n\n"
                    "For detailed setup instructions, see: docs/SETUP.md\n\n"
                    f"Original error: {e}"
                ) from e

        # Re-raise other types of errors
        raise

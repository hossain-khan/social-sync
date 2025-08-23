"""
Configuration management for Social Sync
"""
import os
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Bluesky Configuration
    bluesky_handle: str = Field(default="", description="Bluesky handle")
    bluesky_password: str = Field(default="", description="Bluesky app password")
    
    # Mastodon Configuration
    mastodon_api_base_url: str = Field(default="https://mastodon.social", description="Mastodon instance URL")
    mastodon_access_token: str = Field(default="", description="Mastodon access token")
    
    # Sync Configuration
    sync_interval_minutes: int = Field(default=15, description="Sync interval in minutes")
    max_posts_per_sync: int = Field(default=10, description="Maximum posts per sync")
    dry_run: bool = Field(default=False, description="Run in dry-run mode")
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    
    # State file to track last synced post
    state_file: str = Field(default="sync_state.json", description="State file path")
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore"
    }
    
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


def get_settings() -> Settings:
    """Get application settings"""
    return Settings()

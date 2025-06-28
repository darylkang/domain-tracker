"""
Domain tracker settings management with Pydantic Settings.

This module handles configuration for domain availability monitoring.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Domain tracker settings with environment variable support.

    Example:
        >>> settings = Settings()
        >>> settings.whois_api_key  # Loaded from WHOIS_API_KEY env var
        >>> settings.slack_webhook_url  # Loaded from SLACK_WEBHOOK_URL env var
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Legacy compatibility field
    debug: bool = Field(
        default=False,
        description="Debug mode for development and testing compatibility"
    )

    default_transform: str = Field(
        default="uppercase",
        description="Default transformation for legacy compatibility"
    )

    # Required API configuration
    whois_api_key: str = Field(
        description="API key for WhoisXML API service",
        min_length=1
    )

    slack_webhook_url: HttpUrl = Field(
        ...,
        description="Slack webhook URL for domain availability notifications"
    )

    # Domain monitoring settings
    check_interval_hours: int = Field(
        default=1,
        ge=1,
        le=24,
        description="Hours between domain availability checks"
    )

    domains_file_path: Path = Field(
        default=Path("domains.txt"),
        description="Path to file containing domains to monitor"
    )

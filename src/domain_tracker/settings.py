"""
Domain tracker settings management with Pydantic Settings.

This module handles configuration for domain availability monitoring
including API keys, webhook URLs, and monitoring intervals.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Domain tracker configuration with environment variable support.

    All settings can be configured via environment variables or .env file.
    Required variables: WHOIS_API_KEY, SLACK_WEBHOOK_URL
    Optional variables: CHECK_INTERVAL_HOURS, DOMAINS_FILE_PATH

    Example:
        >>> # With environment variables set
        >>> settings = Settings()
        >>> settings.whois_api_key  # Loaded from WHOIS_API_KEY
        >>> settings.slack_webhook_url  # Loaded from SLACK_WEBHOOK_URL
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Required API configuration
    whois_api_key: str = Field(
        description="API key for WhoisXML API service",
        min_length=1,
    )

    slack_webhook_url: HttpUrl = Field(
        description="Slack webhook URL for domain availability notifications",
    )

    # Domain monitoring configuration
    check_interval_hours: int = Field(
        default=1,
        ge=1,
        le=24,
        description="Hours between domain availability checks",
    )

    domains_file_path: Path = Field(
        default=Path("domains.txt"),
        description="Path to file containing domains to monitor",
    )

    # Legacy compatibility fields (for test compatibility)
    debug: bool = Field(
        default=False,
        description="Debug mode for development and testing compatibility",
    )

    default_transform: str = Field(
        default="uppercase",
        description="Default transformation for legacy compatibility",
    )

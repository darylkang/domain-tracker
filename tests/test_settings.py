"""
Tests for domain tracker settings configuration.

Following TDD approach - these tests define the expected behavior for
domain-specific configuration management.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from domain_tracker.settings import Settings


class TestDomainTrackerSettings:
    """Test domain tracker specific configuration."""

    def test_settings_requires_whois_api_key(self) -> None:
        """Test that WHOIS_API_KEY is required."""
        # ARRANGE: No environment variables set and no .env file loading
        with patch.dict(os.environ, {}, clear=True):
            # ACT & ASSERT: Should raise validation error for missing API key
            with pytest.raises(ValidationError) as exc_info:
                Settings(_env_file=None)  # Prevent .env file loading

            # Verify the error message mentions the missing field
            assert "whois_api_key" in str(exc_info.value).lower()

    def test_settings_requires_slack_webhook_url(self) -> None:
        """Test that SLACK_WEBHOOK_URL is required."""
        # ARRANGE: Only WHOIS_API_KEY set, missing SLACK_WEBHOOK_URL
        test_env = {"WHOIS_API_KEY": "test_key"}
        with patch.dict(os.environ, test_env, clear=True):
            # ACT & ASSERT: Should raise validation error for missing Slack URL
            with pytest.raises(ValidationError) as exc_info:
                Settings(_env_file=None)

            # Verify the error message mentions the missing field
            assert "slack_webhook_url" in str(exc_info.value).lower()

    def test_settings_loads_from_environment_variables(self) -> None:
        """Test that settings load correctly from environment variables."""
        # ARRANGE: Set required environment variables
        test_env = {
            "WHOIS_API_KEY": "test_whois_key_123",
            "SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"
        }
        with patch.dict(os.environ, test_env, clear=True):
            # ACT: Create settings without .env file
            settings = Settings(_env_file=None)

            # ASSERT: Values loaded correctly
            assert settings.whois_api_key == "test_whois_key_123"
            assert str(settings.slack_webhook_url) == "https://hooks.slack.com/test"

    def test_settings_has_default_check_interval(self) -> None:
        """Test that check interval has a sensible default."""
        # ARRANGE: Required environment variables only
        with patch.dict(os.environ, {
            "WHOIS_API_KEY": "test-key",
            "SLACK_WEBHOOK_URL": "https://hooks.slack.com/test",
        }, clear=True):
            # ACT: Create settings
            settings = Settings()

            # ASSERT: Default check interval is set
            assert hasattr(settings, 'check_interval_hours')
            assert settings.check_interval_hours > 0
            assert isinstance(settings.check_interval_hours, int)

    def test_settings_validates_slack_webhook_url_format(self) -> None:
        """Test that Slack webhook URL is validated for proper format."""
        # ARRANGE: Valid WHOIS key but invalid Slack URL
        with patch.dict(os.environ, {
            "WHOIS_API_KEY": "test-key",
            "SLACK_WEBHOOK_URL": "not-a-valid-url",
        }, clear=True):
            # ACT & ASSERT: Should raise validation error for invalid URL
            with pytest.raises(ValidationError) as exc_info:
                Settings()

            error_msg = str(exc_info.value).lower()
            assert "url" in error_msg or "invalid" in error_msg

    def test_settings_supports_custom_check_interval(self) -> None:
        """Test that check interval can be customized via environment."""
        # ARRANGE: Set all required variables plus custom interval
        with patch.dict(os.environ, {
            "WHOIS_API_KEY": "test-key",
            "SLACK_WEBHOOK_URL": "https://hooks.slack.com/test",
            "CHECK_INTERVAL_HOURS": "6",
        }, clear=True):
            # ACT: Create settings
            settings = Settings()

            # ASSERT: Custom interval is used
            assert settings.check_interval_hours == 6

    def test_settings_has_domains_file_path(self) -> None:
        """Test that settings includes path to domains file."""
        # ARRANGE: Required environment variables
        with patch.dict(os.environ, {
            "WHOIS_API_KEY": "test-key",
            "SLACK_WEBHOOK_URL": "https://hooks.slack.com/test",
        }, clear=True):
            # ACT: Create settings
            settings = Settings()

            # ASSERT: Domains file path is configured
            assert hasattr(settings, 'domains_file_path')
            assert str(settings.domains_file_path).endswith('domains.txt')

    def test_settings_loads_from_env_file(self) -> None:
        """Test that settings can load from .env file."""
        # ACT: Create settings with default .env file loading
        settings = Settings()

        # ASSERT: Values loaded from .env file
        assert settings.whois_api_key is not None
        assert settings.slack_webhook_url is not None
        assert len(settings.whois_api_key) > 0

    def test_default_values_are_set(self) -> None:
        """Test that default values are properly set."""
        # ARRANGE: Set only required fields
        test_env = {
            "WHOIS_API_KEY": "test_key",
            "SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"
        }
        with patch.dict(os.environ, test_env, clear=True):
            # ACT: Create settings
            settings = Settings(_env_file=None)

            # ASSERT: Default values are set
            assert settings.check_interval_hours == 1
            assert str(settings.domains_file_path) == "domains.txt"

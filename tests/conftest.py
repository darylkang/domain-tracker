"""
Shared test fixtures and configuration.

This file provides common test fixtures for the test suite.
"""

from __future__ import annotations

import pytest
from pydantic import HttpUrl

from domain_tracker.settings import Settings


@pytest.fixture
def test_settings() -> Settings:
    """Provide test settings with required fields for testing."""
    return Settings(
        whois_api_key="test-whois-key",
        slack_webhook_url=HttpUrl("https://hooks.slack.com/test"),
        debug=True,
    )

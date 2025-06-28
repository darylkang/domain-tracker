"""
Shared test fixtures and configuration.

This file provides common test fixtures for the test suite.
"""

from __future__ import annotations

import pytest

from domain_tracker.settings import Settings


@pytest.fixture
def test_settings() -> Settings:
    """Provide test settings with debug enabled."""
    return Settings(debug=True, log_level="DEBUG")

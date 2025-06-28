"""
WhoisXML API client for domain availability checking.

This module provides functionality to check domain availability using the
WhoisXML API service with robust error handling and validation.
"""

from __future__ import annotations

import json
import re

import requests
from requests.exceptions import ConnectionError, RequestException, Timeout

from domain_tracker.settings import Settings

# API Configuration
WHOISXML_API_URL = "https://domain-availability.whoisxmlapi.com/api/v1"
REQUEST_TIMEOUT_SECONDS = 30
MAX_DOMAIN_LENGTH = 253


def check_domain_availability(domain: str, settings: Settings | None = None) -> bool:
    """
    Check if a domain is available for registration using WhoisXML API.

    Args:
        domain: Domain name to check (e.g., 'example.com').
        settings: Settings instance with API configuration. If None, loads from environment.

    Returns:
        True if the domain is available for registration, False otherwise.
        Returns False for any errors or ambiguous responses (conservative approach).

    Example:
        >>> settings = Settings(whois_api_key="key", slack_webhook_url="url")
        >>> check_domain_availability('available-domain.com', settings)
        True
        >>> check_domain_availability('google.com', settings)
        False
    """
    # Validate domain format before making API call
    if not _is_valid_domain_format(domain):
        return False

    try:
        # Load settings and API key
        if settings is None:
            settings = Settings()  # type: ignore[call-arg]
        api_key = settings.whois_api_key

        # Prepare API request parameters
        request_params = {
            "apiKey": api_key,
            "domainName": domain,
            "format": "json",
        }

        # Make API request with timeout
        response = requests.get(
            WHOISXML_API_URL, params=request_params, timeout=REQUEST_TIMEOUT_SECONDS
        )

        # Check HTTP status
        response.raise_for_status()

        # Parse JSON response safely
        try:
            response_data = response.json()
        except json.JSONDecodeError:
            # Invalid JSON response - return False (conservative approach)
            return False

        # Extract domain availability status
        domain_info = response_data.get("DomainInfo", {})
        availability_status = str(domain_info.get("domainAvailability", "")).upper()

        # Return True only if explicitly marked as AVAILABLE
        return availability_status == "AVAILABLE"

    except (Timeout, ConnectionError, RequestException):
        # Network errors - return False (conservative approach)
        return False
    except Exception:
        # Any other unexpected error - return False (conservative approach)
        return False


def _is_valid_domain_format(domain: str) -> bool:
    """
    Validate basic domain format before making API call.

    Args:
        domain: Domain string to validate.

    Returns:
        True if domain format appears valid, False otherwise.
    """
    # Basic validation checks
    if not domain or not isinstance(domain, str):
        return False

    # Normalize and check length
    domain = domain.strip()
    if len(domain) == 0 or len(domain) > MAX_DOMAIN_LENGTH:
        return False

    # Cannot start or end with dot
    if domain.startswith(".") or domain.endswith("."):
        return False

    # Must contain at least one dot (for TLD)
    if "." not in domain:
        return False

    # Domain format validation regex
    # Validates: labels (up to 63 chars), dots, and TLD (minimum 2 chars)
    domain_format_pattern = re.compile(
        r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?"  # First label
        r"(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*"  # Additional labels
        r"\.[a-zA-Z]{2,}$"  # TLD (minimum 2 characters)
    )

    return bool(domain_format_pattern.match(domain))

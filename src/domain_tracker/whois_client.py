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

# Domain statuses that indicate a domain is not truly available
PROBLEMATIC_DOMAIN_STATUSES = {
    "pendingdelete",
    "redemptionperiod",
    "clienthold",
    "serverhold",
    "renewperiod",
    "transferperiod",
}


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
    # Use the detailed check and return only the availability status
    is_available, _ = check_domain_status_detailed(domain, settings)
    return is_available


def check_domain_status_detailed(
    domain: str, settings: Settings | None = None
) -> tuple[bool, list[str]]:
    """
    Check domain availability and return detailed status information.

    Args:
        domain: Domain name to check (e.g., 'example.com').
        settings: Settings instance with API configuration. If None, loads from environment.

    Returns:
        Tuple of (is_available, problematic_statuses):
        - is_available: True if domain is available for registration, False otherwise
        - problematic_statuses: List of problematic statuses found (empty if none)

    Example:
        >>> settings = Settings(whois_api_key="key", slack_webhook_url="url")
        >>> is_available, statuses = check_domain_status_detailed('pending-domain.com', settings)
        >>> print(is_available, statuses)
        False ['pendingDelete']
    """
    # Validate domain format before making API call
    if not _is_valid_domain_format(domain):
        return False, []

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
            return False, []

        # Extract domain availability status
        domain_info = response_data.get("DomainInfo", {})
        availability_status = str(domain_info.get("domainAvailability", "")).upper()

        # If not marked as available, return False immediately
        if availability_status != "AVAILABLE":
            return False, []

        # Check for problematic statuses
        domain_statuses = domain_info.get("status", [])
        problematic_statuses = _extract_problematic_statuses(domain_statuses)

        # Domain is considered available only if it's marked available AND has no problematic statuses
        is_truly_available = len(problematic_statuses) == 0

        return is_truly_available, problematic_statuses

    except (Timeout, ConnectionError, RequestException):
        # Network errors - return False (conservative approach)
        return False, []
    except Exception:
        # Any other unexpected error - return False (conservative approach)
        return False, []


def _extract_problematic_statuses(domain_statuses: list[str] | None) -> list[str]:
    """
    Extract problematic statuses from the domain status list.

    Args:
        domain_statuses: List of domain statuses from the API response.

    Returns:
        List of problematic statuses that indicate the domain is not truly available.
    """
    if not domain_statuses:
        return []

    problematic_found = []

    for status in domain_statuses:
        # Normalize status to lowercase and remove spaces for comparison
        normalized_status = str(status).lower().replace(" ", "")

        if normalized_status in PROBLEMATIC_DOMAIN_STATUSES:
            # Add the original normalized camelCase format for consistent reporting
            problematic_found.append(_normalize_status_name(normalized_status))

    return problematic_found


def _normalize_status_name(status: str) -> str:
    """
    Normalize status name to consistent camelCase format.

    Args:
        status: Raw status string from API.

    Returns:
        Normalized status name in camelCase format.
    """
    # Map of normalized statuses to consistent camelCase names
    status_mapping = {
        "pendingdelete": "pendingDelete",
        "redemptionperiod": "redemptionPeriod",
        "clienthold": "clientHold",
        "serverhold": "serverHold",
        "renewperiod": "renewPeriod",
        "transferperiod": "transferPeriod",
    }

    return status_mapping.get(status.lower().replace(" ", ""), status)


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

"""
WhoisXML API client for domain availability checking.

This module provides functionality to check domain availability using the
WhoisXML API service.
"""

from __future__ import annotations

import json
import re
from typing import Any

import requests
from requests.exceptions import ConnectionError, RequestException, Timeout

from domain_tracker.settings import Settings


# API Configuration Constants
WHOISXML_API_URL = "https://domain-availability.whoisxmlapi.com/api/v1"
DEFAULT_TIMEOUT_SECONDS = 30
MAX_DOMAIN_LENGTH = 253


def check_domain_availability(domain: str) -> bool:
    """
    Check if a domain is available for registration using WhoisXML API.
    
    Args:
        domain: Domain name to check (e.g., 'example.com').
        
    Returns:
        True if the domain is available for registration, False otherwise.
        Returns False for any errors or ambiguous responses (conservative approach).
        
    Example:
        >>> check_domain_availability('available-domain.com')
        True
        >>> check_domain_availability('google.com')
        False
    """
    # Validate domain format first
    if not _is_valid_domain_format(domain):
        return False
    
    try:
        # Load settings and API key
        settings = Settings()
        api_key = settings.whois_api_key
        
        # Prepare API request
        url = WHOISXML_API_URL
        params = {
            "apiKey": api_key,
            "domainName": domain,
            "format": "json"
        }
        
        # Make API request with timeout
        response = requests.get(
            url,
            params=params,
            timeout=DEFAULT_TIMEOUT_SECONDS
        )
        
        # Check HTTP status
        response.raise_for_status()
        
        # Parse JSON response
        try:
            data = response.json()
        except json.JSONDecodeError:
            # Invalid JSON response - return False (conservative)
            return False
        
        # Extract domain availability status
        domain_info = data.get("DomainInfo", {})
        availability = domain_info.get("domainAvailability", "").upper()
        
        # Return True only if explicitly marked as AVAILABLE
        return availability == "AVAILABLE"
        
    except (Timeout, ConnectionError, RequestException):
        # Network errors - return False (conservative approach)
        return False
    except Exception:
        # Any other unexpected error - return False (conservative)
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
    
    # Strip whitespace
    domain = domain.strip()
    
    # Check length
    if len(domain) == 0 or len(domain) > MAX_DOMAIN_LENGTH:
        return False
    
    # Cannot start or end with dot
    if domain.startswith('.') or domain.endswith('.'):
        return False
    
    # Must contain at least one dot (for TLD)
    if '.' not in domain:
        return False
    
    # Basic regex validation for domain format
    domain_pattern = re.compile(
        r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?'  # Label
        r'(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*'  # More labels
        r'\.[a-zA-Z]{2,}$'  # TLD
    )
    
    return bool(domain_pattern.match(domain)) 
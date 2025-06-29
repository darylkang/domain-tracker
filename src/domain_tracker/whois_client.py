"""
Client for WhoisXML API to check domain availability and get detailed domain information.

This module provides functions to interact with the WhoisXML API for domain
availability checking and extracting detailed domain information.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime

import requests
from requests.exceptions import ConnectionError, RequestException, Timeout

from domain_tracker.settings import Settings

# API Configuration
WHOISXML_API_URL = "https://www.whoisxmlapi.com/whoisserver/WhoisService"
REQUEST_TIMEOUT_SECONDS = 60  # Full WHOIS API recommended timeout
MAX_DOMAIN_LENGTH = 253

# Domain statuses that indicate a domain is not truly available
PROBLEMATIC_DOMAIN_STATUSES = {
    # Delete/Expiration related statuses
    "pendingdelete",
    "pendingdelete",
    "redemptionperiod",
    "renewperiod",
    # Hold statuses
    "clienthold",
    "serverhold",
    # Transfer related statuses
    "transferperiod",
    "pendingtransfer",
    "clienttransferprohibited",
    "servertransferprohibited",
    # Update/Delete restrictions that may indicate issues
    "clientdeleteprohibited",
    "serverdeleteprohibited",
    "clientupdateprohibited",
    "serverupdateprohibited",
    # Verification and registration issues
    "registrantverificationpending",
    "pendingverification",
    "pendingnotification",
    "addperiod",
    "autorenewperiod",
    # Additional potentially problematic statuses
    "pendingcreate",
    "pendingupdate",
    "pendingrenew",
    "pendingverification",
    "pendingdelete",
    "pendingrelease",
    "pendingrebill",
    "pendingrestore",
}

# Additional keywords that might indicate problematic status in raw text
PROBLEMATIC_KEYWORDS = {
    "pending",
    "hold",
    "prohibited",
    "redemption",
    "grace",
    "locked",
    "suspended",
    "expired",
    "quarantine",
    "frozen",
}


@dataclass
class DomainInfo:
    """Enhanced domain information from WhoisXML API."""

    domain_name: str
    is_available: bool
    problematic_statuses: list[str]
    expiration_date: datetime | None = None
    creation_date: datetime | None = None
    registrant_name: str | None = None
    registrant_organization: str | None = None
    registrar_name: str | None = None
    registrar_address: str | None = None
    registrar_phone: str | None = None
    registrar_fax: str | None = None
    name_servers: list[str] | None = None
    has_error: bool = False
    error_message: str = ""

    def __post_init__(self) -> None:
        """Initialize name_servers as empty list if None."""
        if self.name_servers is None:
            self.name_servers = []


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
    domain: str, settings: Settings | None = None, debug: bool = False
) -> tuple[bool, list[str]]:
    """
    Check domain availability and return detailed status information.

    Args:
        domain: Domain name to check (e.g., 'example.com').
        settings: Settings instance with API configuration. If None, loads from environment.
        debug: Enable debug output including raw API responses.

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

        # Prepare API request parameters for Full WHOIS API
        request_params = {
            "apiKey": api_key,
            "domainName": domain,
            "outputFormat": "JSON",  # Full WHOIS API parameter
            "da": "2",  # Enable domain availability check (slower but more accurate)
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

        # Debug output: Show raw API response
        if debug:
            print(f"\n🔧 DEBUG: Raw Full WHOIS API response for {domain}:")
            print(f"   URL: {response.url}")
            print(f"   Status Code: {response.status_code}")
            print(f"   Raw Response: {json.dumps(response_data, indent=2)}")
            print("-" * 60)

        # Extract WHOIS record from Full WHOIS API response
        whois_record = response_data.get("WhoisRecord", {})

        # Check for data errors first
        data_error = whois_record.get("dataError")
        if data_error == "MISSING_WHOIS_DATA":
            # Domain not registered, truly available
            if debug:
                print(f"🔧 DEBUG: Domain {domain} not registered (MISSING_WHOIS_DATA)")
            return True, []

        # Handle other data errors conservatively
        if data_error in ["NO_DATA", "INCOMPLETE_DATA"]:
            if debug:
                print(
                    f"🔧 DEBUG: Domain {domain} has data error: {data_error} - treating as unavailable for safety"
                )
            return False, ["dataError"]

        # Check registry data for additional data errors
        registry_data = whois_record.get("registryData", {})
        registry_data_error = registry_data.get("dataError")
        if registry_data_error in ["NO_DATA", "INCOMPLETE_DATA"]:
            if debug:
                print(
                    f"🔧 DEBUG: Domain {domain} has registry data error: {registry_data_error} - treating as unavailable for safety"
                )
            return False, ["registryDataError"]

        # Extract domain availability status from Full WHOIS API
        availability_status = str(whois_record.get("domainAvailability", "")).upper()

        # If not marked as explicitly available, return False immediately
        if availability_status != "AVAILABLE":
            if debug:
                print(
                    f"🔧 DEBUG: Domain {domain} marked as {availability_status} by Full WHOIS API"
                )
            return False, []

        # Extract detailed status information from Full WHOIS API
        # Check both main record and registry data for comprehensive status info
        all_statuses = []

        # Get status from main record (can be string or list)
        main_status = whois_record.get("status", "")
        if main_status:
            if debug:
                print(f"🔧 DEBUG: Main status for {domain}: {main_status}")
            if isinstance(main_status, list):
                all_statuses.extend(main_status)
            else:
                all_statuses.extend(_parse_status_string(main_status))

        # Get status from registry data (can be string or list)
        registry_status = registry_data.get("status", "")
        if registry_status:
            if debug:
                print(f"🔧 DEBUG: Registry status for {domain}: {registry_status}")
            if isinstance(registry_status, list):
                all_statuses.extend(registry_status)
            else:
                all_statuses.extend(_parse_status_string(registry_status))

        if debug:
            print(f"🔧 DEBUG: All extracted statuses for {domain}: {all_statuses}")

        problematic_statuses = _extract_problematic_statuses(all_statuses)

        if debug and problematic_statuses:
            print(
                f"🔧 DEBUG: Found problematic statuses for {domain}: {problematic_statuses}"
            )

        # Domain is considered available only if it's marked available AND has no problematic statuses
        is_truly_available = len(problematic_statuses) == 0

        return is_truly_available, problematic_statuses

    except (Timeout, ConnectionError, RequestException) as e:
        if debug:
            print(f"🔧 DEBUG: Network error for {domain}: {e}")
        # Network errors - return False (conservative approach)
        return False, []
    except Exception as e:
        if debug:
            print(f"🔧 DEBUG: Unexpected error for {domain}: {e}")
        # Any other unexpected error - return False (conservative approach)
        return False, []


def _extract_problematic_statuses(domain_statuses: list[str] | None) -> list[str]:
    """
    Extract problematic statuses from the domain status list.

    This function now performs more comprehensive checking including:
    - Exact matches for known problematic statuses
    - Partial string matching for status keywords
    - Better normalization and parsing of complex status strings

    Args:
        domain_statuses: List of domain statuses from the API response.

    Returns:
        List of problematic statuses that indicate the domain is not truly available.
    """
    if not domain_statuses:
        return []

    problematic_found = []

    for status in domain_statuses:
        if not status:
            continue

        # Convert to string and normalize for comparison
        status_str = str(status).strip()

        # Skip empty statuses
        if not status_str:
            continue

        # Normalize status: lowercase, remove spaces, parentheses, and URLs
        # Many statuses come in format like "clientDeleteProhibited (https://www.icann.org/epp#clientDeleteProhibited)"
        normalized_status = status_str.lower()

        # Extract the actual status code from complex format
        if "(" in normalized_status:
            normalized_status = normalized_status.split("(")[0].strip()

        # Remove common separators and extra whitespace
        normalized_status = (
            normalized_status.replace(" ", "").replace("-", "").replace("_", "")
        )

        # Check for exact matches first
        if normalized_status in PROBLEMATIC_DOMAIN_STATUSES:
            problematic_found.append(_normalize_status_name(normalized_status))
            continue

        # Check for partial matches using keywords
        status_lower = status_str.lower()
        for keyword in PROBLEMATIC_KEYWORDS:
            if keyword in status_lower:
                # Found a problematic keyword, extract a meaningful status name
                if keyword == "pending" and "delete" in status_lower:
                    problematic_found.append("pendingDelete")
                elif keyword == "hold":
                    if "client" in status_lower:
                        problematic_found.append("clientHold")
                    elif "server" in status_lower:
                        problematic_found.append("serverHold")
                    else:
                        problematic_found.append("hold")
                elif keyword == "redemption":
                    problematic_found.append("redemptionPeriod")
                elif keyword == "prohibited":
                    if "transfer" in status_lower:
                        problematic_found.append("transferProhibited")
                    elif "delete" in status_lower:
                        problematic_found.append("deleteProhibited")
                    elif "update" in status_lower:
                        problematic_found.append("updateProhibited")
                    else:
                        problematic_found.append("prohibited")
                else:
                    # Use the keyword as the problematic status
                    problematic_found.append(keyword.title())
                break

    # Remove duplicates while preserving order
    seen = set()
    unique_problematic = []
    for status in problematic_found:
        if status not in seen:
            seen.add(status)
            unique_problematic.append(status)

    return unique_problematic


def _parse_status_string(status_string: str) -> list[str]:
    """
    Parse a status string from Full WHOIS API into individual status codes.

    The Full WHOIS API returns status as a string like:
    "clientUpdateProhibited https://... clientTransferProhibited https://..."

    Args:
        status_string: Raw status string from Full WHOIS API

    Returns:
        List of individual status codes
    """
    if not status_string:
        return []

    # Split on whitespace and filter out URLs
    parts = status_string.split()
    statuses = []

    for part in parts:
        # Skip URLs and empty strings
        if part.startswith("http") or not part.strip():
            continue
        # Remove parentheses and other punctuation
        clean_part = part.strip("()")
        if clean_part:
            statuses.append(clean_part)

    return statuses


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


def get_enhanced_domain_info(
    domain: str, settings: Settings | None = None, debug: bool = False
) -> DomainInfo:
    """
    Get enhanced domain information from WhoisXML API.

    This function extracts detailed information including availability,
    expiration dates, registrant information, and domain statuses for
    rich Slack message formatting.

    Args:
        domain: Domain name to check (e.g., 'example.com')
        settings: Optional settings instance for API configuration
        debug: Enable debug output including raw API responses

    Returns:
        DomainInfo: Enhanced domain information object
    """
    if settings is None:
        settings = Settings()  # type: ignore[call-arg]

    logging.debug(f"Getting enhanced domain info for: {domain}")

    try:
        # Make API request to Full WHOIS API
        response = requests.get(
            WHOISXML_API_URL,
            params={
                "apiKey": settings.whois_api_key,
                "domainName": domain,
                "outputFormat": "JSON",
                "da": "2",  # Enable domain availability check
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()

        data = response.json()

        # Debug output: Show raw API response
        if debug:
            print(f"\n🔧 DEBUG: Enhanced Full WHOIS API response for {domain}:")
            print(f"   URL: {response.url}")
            print(f"   Status Code: {response.status_code}")
            print(f"   Raw Response: {json.dumps(data, indent=2)}")
            print("-" * 60)

        whois_record = data.get("WhoisRecord", {})

        # Check for data errors first
        data_error = whois_record.get("dataError")
        if data_error == "MISSING_WHOIS_DATA":
            # Domain not registered, truly available
            if debug:
                print(
                    f"🔧 DEBUG: Enhanced check - Domain {domain} not registered (MISSING_WHOIS_DATA)"
                )
            return DomainInfo(
                domain_name=domain,
                is_available=True,
                problematic_statuses=[],
            )

        # Handle other data errors conservatively
        if data_error in ["NO_DATA", "INCOMPLETE_DATA"]:
            if debug:
                print(
                    f"🔧 DEBUG: Enhanced check - Domain {domain} has data error: {data_error} - treating as unavailable for safety"
                )
            return DomainInfo(
                domain_name=domain,
                is_available=False,
                problematic_statuses=["dataError"],
                has_error=True,
                error_message=f"API data error: {data_error}",
            )

        # Check registry data for additional data errors
        registry_data = whois_record.get("registryData", {})
        registry_data_error = registry_data.get("dataError")
        if registry_data_error in ["NO_DATA", "INCOMPLETE_DATA"]:
            if debug:
                print(
                    f"🔧 DEBUG: Enhanced check - Domain {domain} has registry data error: {registry_data_error} - treating as unavailable for safety"
                )
            return DomainInfo(
                domain_name=domain,
                is_available=False,
                problematic_statuses=["registryDataError"],
                has_error=True,
                error_message=f"Registry data error: {registry_data_error}",
            )

        # Extract basic availability and status from Full WHOIS API
        availability = whois_record.get("domainAvailability", "UNAVAILABLE")

        # Extract comprehensive status information (can be string or list)
        all_statuses = []
        main_status = whois_record.get("status", "")
        if main_status:
            if isinstance(main_status, list):
                all_statuses.extend(main_status)
            else:
                all_statuses.extend(_parse_status_string(main_status))

        registry_status = registry_data.get("status", "")
        if registry_status:
            if isinstance(registry_status, list):
                all_statuses.extend(registry_status)
            else:
                all_statuses.extend(_parse_status_string(registry_status))

        if debug:
            print(
                f"🔧 DEBUG: Enhanced check - Domain {domain} availability: {availability}"
            )
            print(
                f"🔧 DEBUG: Enhanced check - All domain {domain} statuses: {all_statuses}"
            )

        # Check for problematic statuses
        problematic_statuses = _extract_problematic_statuses(all_statuses)

        if debug and problematic_statuses:
            print(
                f"🔧 DEBUG: Enhanced check - Found problematic statuses for {domain}: {problematic_statuses}"
            )

        # Determine final availability (more conservative approach)
        # Only mark as available if explicitly marked available AND no problematic statuses
        is_available = (availability == "AVAILABLE") and len(problematic_statuses) == 0

        if debug:
            print(
                f"🔧 DEBUG: Enhanced check - Final availability for {domain}: {is_available} (availability={availability}, problematic_count={len(problematic_statuses)})"
            )

        # Parse dates from Full WHOIS API (try both main record and registry data)
        expiration_date = (
            _parse_api_date(whois_record.get("expiresDate"))
            or _parse_api_date(whois_record.get("expiresDateNormalized"))
            or _parse_api_date(registry_data.get("expiresDate"))
            or _parse_api_date(registry_data.get("expiresDateNormalized"))
        )

        creation_date = (
            _parse_api_date(whois_record.get("createdDate"))
            or _parse_api_date(whois_record.get("createdDateNormalized"))
            or _parse_api_date(registry_data.get("createdDate"))
            or _parse_api_date(registry_data.get("createdDateNormalized"))
        )

        # Extract registrant information from Full WHOIS API
        registrant = whois_record.get("registrant", {}) or registry_data.get(
            "registrant", {}
        )
        registrant_name = registrant.get("name")
        registrant_organization = registrant.get("organization")

        # Extract other details from Full WHOIS API
        registrar_name = whois_record.get("registrarName") or registry_data.get(
            "registrarName"
        )

        # Extract registrar contact information if available
        registrar_address = None
        registrar_phone = None
        registrar_fax = None

        # Try to get registrar contact info from various places in the response
        registrar_info = whois_record.get("registrar", {}) or registry_data.get(
            "registrar", {}
        )
        if registrar_info:
            registrar_address = registrar_info.get("streetAddress")
            registrar_phone = registrar_info.get("telephone")
            registrar_fax = registrar_info.get("fax")

        # Alternative locations for registrar contact info
        if not registrar_address:
            registrar_address = whois_record.get(
                "registrarAddress"
            ) or registry_data.get("registrarAddress")
        if not registrar_phone:
            registrar_phone = whois_record.get("registrarPhone") or registry_data.get(
                "registrarPhone"
            )
        if not registrar_fax:
            registrar_fax = whois_record.get("registrarFax") or registry_data.get(
                "registrarFax"
            )

        # Extract name servers
        name_servers = []
        ns_data = whois_record.get("nameServers") or registry_data.get("nameServers")
        if ns_data and isinstance(ns_data, dict):
            name_servers = ns_data.get("hostNames", [])
        elif isinstance(ns_data, list):
            name_servers = ns_data

        return DomainInfo(
            domain_name=domain,
            is_available=is_available,
            problematic_statuses=problematic_statuses,
            expiration_date=expiration_date,
            creation_date=creation_date,
            registrant_name=registrant_name,
            registrant_organization=registrant_organization,
            registrar_name=registrar_name,
            registrar_address=registrar_address,
            registrar_phone=registrar_phone,
            registrar_fax=registrar_fax,
            name_servers=name_servers,
        )

    except (RequestException, Timeout, ConnectionError) as e:
        if debug:
            print(f"🔧 DEBUG: Enhanced check network error for {domain}: {e}")
        logging.error(f"Failed to get enhanced domain info for {domain}: {e}")
        return DomainInfo(
            domain_name=domain,
            is_available=False,
            problematic_statuses=[],
            has_error=True,
            error_message=str(e),
        )
    except Exception as e:
        if debug:
            print(f"🔧 DEBUG: Enhanced check unexpected error for {domain}: {e}")
        logging.error(f"Unexpected error getting domain info for {domain}: {e}")
        return DomainInfo(
            domain_name=domain,
            is_available=False,
            problematic_statuses=[],
            has_error=True,
            error_message=f"Unexpected error: {e}",
        )


def _parse_api_date(date_string: str | None) -> datetime | None:
    """
    Parse date string from API response.

    Args:
        date_string: ISO format date string from API

    Returns:
        datetime object or None if parsing fails
    """
    if not date_string:
        return None

    try:
        # Handle ISO format dates (with or without timezone)
        if date_string.endswith("Z"):
            date_string = date_string[:-1] + "+00:00"
        elif "+" not in date_string and date_string.count(":") == 2:
            date_string += "+00:00"

        return datetime.fromisoformat(date_string.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        logging.warning(f"Failed to parse date: {date_string}")
        return None


# Note: _get_problematic_statuses function removed - now using _extract_problematic_statuses consistently

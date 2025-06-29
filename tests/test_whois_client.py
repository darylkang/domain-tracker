"""
Tests for WhoisXML API client functionality.

Following TDD approach - these tests define the expected behavior for
domain availability checking via WhoisXML API.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import Mock, patch

import requests
from requests.exceptions import ConnectionError, Timeout

from domain_tracker.settings import Settings
from domain_tracker.whois_client import (
    check_domain_availability,
    check_domain_status_detailed,
    get_enhanced_domain_info,
)


class TestWhoisClient:
    """Test WhoisXML API client functionality."""

    def test_check_domain_availability_returns_true_for_available_domain(self) -> None:
        """Test that available domains return True."""
        # ARRANGE: Mock successful API response for available domain
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "DomainInfo": {"domainAvailability": "AVAILABLE"}
        }

        with patch("requests.get", return_value=mock_response):
            # ACT: Check domain availability
            result = check_domain_availability("available-example.com")

            # ASSERT: Should return True for available domain
            assert result is True

    def test_check_domain_availability_returns_false_for_unavailable_domain(
        self,
    ) -> None:
        """Test that unavailable domains return False."""
        # ARRANGE: Mock successful API response for unavailable domain
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "DomainInfo": {"domainAvailability": "UNAVAILABLE"}
        }

        with patch("requests.get", return_value=mock_response):
            # ACT: Check domain availability
            result = check_domain_availability("google.com")

            # ASSERT: Should return False for unavailable domain
            assert result is False

    def test_check_domain_availability_loads_api_key_from_settings(
        self, test_settings: Settings
    ) -> None:
        """Test that API key is loaded from settings configuration."""
        # ARRANGE: Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "DomainInfo": {"domainAvailability": "AVAILABLE"}
        }

        with patch("requests.get", return_value=mock_response) as mock_get:
            # ACT: Check domain availability with test settings
            check_domain_availability("test.com", test_settings)

            # ASSERT: Should use API key from settings in request
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert "apiKey" in call_args[1]["params"]
            assert call_args[1]["params"]["apiKey"] == "test-whois-key"

    def test_check_domain_availability_handles_network_timeout(self) -> None:
        """Test graceful handling of network timeouts."""
        # ARRANGE: Mock timeout exception
        with patch("requests.get", side_effect=Timeout("Request timed out")):
            # ACT & ASSERT: Should raise an exception or return False
            # (We'll decide on error handling strategy in implementation)
            result = check_domain_availability("timeout-test.com")
            assert (
                result is False
            )  # Conservative approach - assume unavailable on timeout

    def test_check_domain_availability_handles_connection_error(self) -> None:
        """Test graceful handling of connection errors."""
        # ARRANGE: Mock connection error
        with patch("requests.get", side_effect=ConnectionError("Unable to connect")):
            # ACT: Check domain availability with connection error
            result = check_domain_availability("connection-error-test.com")

            # ASSERT: Should return False on connection error (conservative)
            assert result is False

    def test_check_domain_availability_handles_http_error_response(self) -> None:
        """Test handling of HTTP error responses (4xx, 5xx)."""
        # ARRANGE: Mock HTTP error response
        mock_response = Mock()
        mock_response.status_code = 429  # Rate limit error
        mock_response.raise_for_status.side_effect = requests.HTTPError(
            "429 Rate Limited"
        )

        with patch("requests.get", return_value=mock_response):
            # ACT: Check domain availability with HTTP error
            result = check_domain_availability("rate-limited-test.com")

            # ASSERT: Should return False on HTTP error (conservative)
            assert result is False

    def test_check_domain_availability_handles_invalid_json_response(self) -> None:
        """Test handling of malformed JSON responses."""
        # ARRANGE: Mock response with invalid JSON
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)

        with patch("requests.get", return_value=mock_response):
            # ACT: Check domain availability with invalid JSON
            result = check_domain_availability("invalid-json-test.com")

            # ASSERT: Should return False on invalid response (conservative)
            assert result is False

    def test_check_domain_availability_handles_missing_domain_info(self) -> None:
        """Test handling of responses missing expected DomainInfo structure."""
        # ARRANGE: Mock response without DomainInfo
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ErrorMessage": "Domain format invalid"}

        with patch("requests.get", return_value=mock_response):
            # ACT: Check domain availability with missing DomainInfo
            result = check_domain_availability("malformed-response-test.com")

            # ASSERT: Should return False when DomainInfo missing (conservative)
            assert result is False

    def test_check_domain_availability_uses_correct_api_endpoint(self) -> None:
        """Test that correct WhoisXML API endpoint is used."""
        # ARRANGE: Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "DomainInfo": {"domainAvailability": "AVAILABLE"}
        }

        with patch("requests.get", return_value=mock_response) as mock_get:
            # ACT: Check domain availability
            check_domain_availability("endpoint-test.com")

            # ASSERT: Should call correct WhoisXML API URL
            mock_get.assert_called_once()
            call_url = mock_get.call_args[0][0]
            assert "domain-availability.whoisxmlapi.com" in call_url

    def test_check_domain_availability_includes_domain_in_request(self) -> None:
        """Test that domain name is included in API request parameters."""
        # ARRANGE: Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "DomainInfo": {"domainAvailability": "AVAILABLE"}
        }

        with patch("requests.get", return_value=mock_response) as mock_get:
            # ACT: Check specific domain availability
            check_domain_availability("parameter-test.com")

            # ASSERT: Should include domain in request parameters
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert "domainName" in call_args[1]["params"]
            assert call_args[1]["params"]["domainName"] == "parameter-test.com"

    def test_check_domain_availability_uses_timeout(self) -> None:
        """Test that API requests use appropriate timeout."""
        # ARRANGE: Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "DomainInfo": {"domainAvailability": "AVAILABLE"}
        }

        with patch("requests.get", return_value=mock_response) as mock_get:
            # ACT: Check domain availability
            check_domain_availability("timeout-test.com")

            # ASSERT: Should use timeout in request
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert "timeout" in call_args[1]
            assert call_args[1]["timeout"] > 0  # Should have reasonable timeout

    def test_check_domain_availability_validates_domain_format(self) -> None:
        """Test that invalid domain formats are handled gracefully."""
        # ARRANGE: Test with clearly invalid domain
        invalid_domains = [
            "",  # Empty string
            "invalid",  # No TLD
            ".com",  # Starts with dot
            "test.",  # Ends with dot
            "too.many.dots.in.this.very.long.domain.name.com",  # Very long
        ]

        for invalid_domain in invalid_domains:
            # ACT & ASSERT: Should return False for invalid domains
            result = check_domain_availability(invalid_domain)
            assert result is False, (
                f"Should return False for invalid domain: {invalid_domain}"
            )

    def test_check_domain_availability_returns_false_for_pending_delete_status(
        self,
    ) -> None:
        """Test that domains in pendingDelete status return False."""
        # ARRANGE: Mock API response with pendingDelete status
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "DomainInfo": {
                "domainAvailability": "AVAILABLE",
                "status": ["pendingDelete"],
            }
        }

        with patch("requests.get", return_value=mock_response):
            # ACT: Check domain availability
            result = check_domain_availability("pending-delete.com")

            # ASSERT: Should return False for pendingDelete status
            assert result is False

    def test_check_domain_availability_returns_false_for_redemption_period_status(
        self,
    ) -> None:
        """Test that domains in redemptionPeriod status return False."""
        # ARRANGE: Mock API response with redemptionPeriod status
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "DomainInfo": {
                "domainAvailability": "AVAILABLE",
                "status": ["redemptionPeriod"],
            }
        }

        with patch("requests.get", return_value=mock_response):
            # ACT: Check domain availability
            result = check_domain_availability("redemption-period.com")

            # ASSERT: Should return False for redemptionPeriod status
            assert result is False

    def test_check_domain_availability_returns_false_for_client_hold_status(
        self,
    ) -> None:
        """Test that domains in clientHold status return False."""
        # ARRANGE: Mock API response with clientHold status
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "DomainInfo": {"domainAvailability": "AVAILABLE", "status": ["clientHold"]}
        }

        with patch("requests.get", return_value=mock_response):
            # ACT: Check domain availability
            result = check_domain_availability("client-hold.com")

            # ASSERT: Should return False for clientHold status
            assert result is False

    def test_check_domain_availability_returns_false_for_server_hold_status(
        self,
    ) -> None:
        """Test that domains in serverHold status return False."""
        # ARRANGE: Mock API response with serverHold status
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "DomainInfo": {"domainAvailability": "AVAILABLE", "status": ["serverHold"]}
        }

        with patch("requests.get", return_value=mock_response):
            # ACT: Check domain availability
            result = check_domain_availability("server-hold.com")

            # ASSERT: Should return False for serverHold status
            assert result is False

    def test_check_domain_availability_returns_false_for_renew_period_status(
        self,
    ) -> None:
        """Test that domains in renewPeriod status return False."""
        # ARRANGE: Mock API response with renewPeriod status
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "DomainInfo": {"domainAvailability": "AVAILABLE", "status": ["renewPeriod"]}
        }

        with patch("requests.get", return_value=mock_response):
            # ACT: Check domain availability
            result = check_domain_availability("renew-period.com")

            # ASSERT: Should return False for renewPeriod status
            assert result is False

    def test_check_domain_availability_returns_false_for_transfer_period_status(
        self,
    ) -> None:
        """Test that domains in transferPeriod status return False."""
        # ARRANGE: Mock API response with transferPeriod status
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "DomainInfo": {
                "domainAvailability": "AVAILABLE",
                "status": ["transferPeriod"],
            }
        }

        with patch("requests.get", return_value=mock_response):
            # ACT: Check domain availability
            result = check_domain_availability("transfer-period.com")

            # ASSERT: Should return False for transferPeriod status
            assert result is False

    def test_check_domain_availability_returns_false_for_multiple_problematic_statuses(
        self,
    ) -> None:
        """Test that domains with multiple problematic statuses return False."""
        # ARRANGE: Mock API response with multiple problematic statuses
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "DomainInfo": {
                "domainAvailability": "AVAILABLE",
                "status": ["pendingDelete", "serverHold", "clientHold"],
            }
        }

        with patch("requests.get", return_value=mock_response):
            # ACT: Check domain availability
            result = check_domain_availability("multiple-status.com")

            # ASSERT: Should return False for multiple problematic statuses
            assert result is False

    def test_check_domain_availability_returns_true_for_available_with_ok_status(
        self,
    ) -> None:
        """Test that domains with acceptable statuses return True when available."""
        # ARRANGE: Mock API response with acceptable status
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "DomainInfo": {
                "domainAvailability": "AVAILABLE",
                "status": ["ok", "inactive"],
            }
        }

        with patch("requests.get", return_value=mock_response):
            # ACT: Check domain availability
            result = check_domain_availability("available-ok.com")

            # ASSERT: Should return True for available domain with acceptable status
            assert result is True

    def test_check_domain_availability_handles_missing_status_field(self) -> None:
        """Test that domains without status field work as before."""
        # ARRANGE: Mock API response without status field (backward compatibility)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "DomainInfo": {"domainAvailability": "AVAILABLE"}
        }

        with patch("requests.get", return_value=mock_response):
            # ACT: Check domain availability
            result = check_domain_availability("no-status-field.com")

            # ASSERT: Should return True when available and no status field
            assert result is True

    def test_check_domain_availability_handles_case_insensitive_status(self) -> None:
        """Test that status checking is case insensitive."""
        # ARRANGE: Mock API response with mixed case status
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "DomainInfo": {
                "domainAvailability": "AVAILABLE",
                "status": ["PendingDelete", "ServerHold"],
            }
        }

        with patch("requests.get", return_value=mock_response):
            # ACT: Check domain availability
            result = check_domain_availability("mixed-case-status.com")

            # ASSERT: Should return False for mixed case problematic statuses
            assert result is False


class TestEnhancedDomainInfo:
    """Test enhanced domain information extraction for rich Slack messages."""

    def test_get_enhanced_domain_info_returns_complete_data_for_available_domain(
        self,
    ) -> None:
        """Test that enhanced domain info returns complete data for available domain."""
        # ARRANGE: Mock API response with full domain data
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "DomainInfo": {
                "domainAvailability": "AVAILABLE",
                "domainName": "example.com",
                "status": ["ok"],
                "expiresDate": "2024-12-31T23:59:59Z",
                "createdDate": "2020-01-01T00:00:00Z",
                "updatedDate": "2023-01-01T00:00:00Z",
                "registrant": {
                    "name": "John Doe",
                    "organization": "Example Corp",
                    "country": "US"
                },
                "nameServers": ["ns1.example.com", "ns2.example.com"],
                "registrarName": "Example Registrar Inc."
            }
        }

        with patch("requests.get", return_value=mock_response):
            # ACT: Get enhanced domain info
            domain_info = get_enhanced_domain_info("example.com")

            # ASSERT: Should return complete domain information
            assert domain_info.domain_name == "example.com"
            assert domain_info.is_available is True
            assert domain_info.problematic_statuses == []
            assert domain_info.expiration_date == datetime(2024, 12, 31, 23, 59, 59, tzinfo=UTC)
            assert domain_info.creation_date == datetime(2020, 1, 1, 0, 0, 0, tzinfo=UTC)
            assert domain_info.registrant_name == "John Doe"
            assert domain_info.registrant_organization == "Example Corp"
            assert domain_info.registrar_name == "Example Registrar Inc."
            assert domain_info.name_servers == ["ns1.example.com", "ns2.example.com"]

    def test_get_enhanced_domain_info_handles_unavailable_domain_with_registrant(
        self,
    ) -> None:
        """Test enhanced domain info for unavailable domain with registrant details."""
        # ARRANGE: Mock API response for unavailable domain
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "DomainInfo": {
                "domainAvailability": "UNAVAILABLE",
                "domainName": "google.com",
                "status": ["clientTransferProhibited", "serverDeleteProhibited"],
                "expiresDate": "2025-09-14T04:00:00Z",
                "createdDate": "1997-09-15T04:00:00Z",
                "registrant": {
                    "name": "Domain Administrator",
                    "organization": "Google LLC",
                    "country": "US"
                },
                "registrarName": "MarkMonitor Inc."
            }
        }

        with patch("requests.get", return_value=mock_response):
            # ACT: Get enhanced domain info
            domain_info = get_enhanced_domain_info("google.com")

            # ASSERT: Should return unavailable domain with registrant info
            assert domain_info.domain_name == "google.com"
            assert domain_info.is_available is False
            assert domain_info.expiration_date == datetime(2025, 9, 14, 4, 0, 0, tzinfo=UTC)
            assert domain_info.registrant_name == "Domain Administrator"
            assert domain_info.registrant_organization == "Google LLC"
            assert domain_info.registrar_name == "MarkMonitor Inc."

    def test_get_enhanced_domain_info_handles_problematic_status_domain(
        self,
    ) -> None:
        """Test enhanced domain info for domain with problematic status."""
        # ARRANGE: Mock API response for domain with problematic status
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "DomainInfo": {
                "domainAvailability": "AVAILABLE",
                "domainName": "pending-example.com",
                "status": ["pendingDelete", "serverHold"],
                "expiresDate": "2024-01-15T12:00:00Z",
                "createdDate": "2020-05-01T10:30:00Z",
                "registrant": {
                    "name": "Previous Owner",
                    "organization": "Old Company Inc."
                }
            }
        }

        with patch("requests.get", return_value=mock_response):
            # ACT: Get enhanced domain info
            domain_info = get_enhanced_domain_info("pending-example.com")

            # ASSERT: Should show as unavailable with problematic statuses listed
            assert domain_info.domain_name == "pending-example.com"
            assert domain_info.is_available is False
            assert "pendingDelete" in domain_info.problematic_statuses
            assert "serverHold" in domain_info.problematic_statuses
            assert domain_info.registrant_name == "Previous Owner"

    def test_get_enhanced_domain_info_handles_missing_optional_fields(
        self,
    ) -> None:
        """Test enhanced domain info gracefully handles missing optional fields."""
        # ARRANGE: Mock API response with minimal data
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "DomainInfo": {
                "domainAvailability": "AVAILABLE",
                "domainName": "minimal-example.com",
                "status": ["ok"]
            }
        }

        with patch("requests.get", return_value=mock_response):
            # ACT: Get enhanced domain info
            domain_info = get_enhanced_domain_info("minimal-example.com")

            # ASSERT: Should handle missing fields gracefully
            assert domain_info.domain_name == "minimal-example.com"
            assert domain_info.is_available is True
            assert domain_info.expiration_date is None
            assert domain_info.creation_date is None
            assert domain_info.registrant_name is None
            assert domain_info.registrant_organization is None
            assert domain_info.registrar_name is None
            assert domain_info.name_servers == []

    def test_get_enhanced_domain_info_handles_api_errors(
        self,
    ) -> None:
        """Test enhanced domain info handles API errors gracefully."""
        # ARRANGE: Mock API timeout
        with patch("requests.get", side_effect=Timeout("Request timed out")):
            # ACT: Get enhanced domain info with error
            domain_info = get_enhanced_domain_info("error-domain.com")

            # ASSERT: Should return error state
            assert domain_info.domain_name == "error-domain.com"
            assert domain_info.is_available is False
            assert domain_info.has_error is True
            assert "Request timed out" in domain_info.error_message


class TestDomainStatusDetailed:
    """Test detailed domain status checking functionality."""

    def test_check_domain_status_detailed_returns_available_true_with_empty_status(
        self,
    ) -> None:
        """Test detailed status check for available domain with no problematic status."""
        # ARRANGE: Mock API response for available domain
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "DomainInfo": {"domainAvailability": "AVAILABLE", "status": ["ok"]}
        }

        with patch("requests.get", return_value=mock_response):
            # ACT: Check detailed domain status
            is_available, problematic_statuses = check_domain_status_detailed(
                "available.com"
            )

            # ASSERT: Should return True with empty problematic statuses
            assert is_available is True
            assert problematic_statuses == []

    def test_check_domain_status_detailed_returns_false_with_problematic_status(
        self,
    ) -> None:
        """Test detailed status check for domain with problematic status."""
        # ARRANGE: Mock API response with pendingDelete status
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "DomainInfo": {
                "domainAvailability": "AVAILABLE",
                "status": ["pendingDelete", "ok"],
            }
        }

        with patch("requests.get", return_value=mock_response):
            # ACT: Check detailed domain status
            is_available, problematic_statuses = check_domain_status_detailed(
                "problematic.com"
            )

            # ASSERT: Should return False with problematic status listed
            assert is_available is False
            assert "pendingDelete" in problematic_statuses

    def test_check_domain_status_detailed_returns_multiple_problematic_statuses(
        self,
    ) -> None:
        """Test detailed status check with multiple problematic statuses."""
        # ARRANGE: Mock API response with multiple problematic statuses
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "DomainInfo": {
                "domainAvailability": "AVAILABLE",
                "status": ["pendingDelete", "serverHold", "ok", "clientHold"],
            }
        }

        with patch("requests.get", return_value=mock_response):
            # ACT: Check detailed domain status
            is_available, problematic_statuses = check_domain_status_detailed(
                "multiple-problems.com"
            )

            # ASSERT: Should return False with all problematic statuses
            assert is_available is False
            assert len(problematic_statuses) == 3
            assert "pendingDelete" in problematic_statuses
            assert "serverHold" in problematic_statuses
            assert "clientHold" in problematic_statuses
            assert "ok" not in problematic_statuses

    def test_check_domain_status_detailed_handles_case_insensitive_statuses(
        self,
    ) -> None:
        """Test detailed status check handles case insensitive statuses."""
        # ARRANGE: Mock API response with mixed case statuses
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "DomainInfo": {
                "domainAvailability": "AVAILABLE",
                "status": ["PendingDelete", "ServerHold"],
            }
        }

        with patch("requests.get", return_value=mock_response):
            # ACT: Check detailed domain status
            is_available, problematic_statuses = check_domain_status_detailed(
                "mixed-case.com"
            )

            # ASSERT: Should return normalized status names
            assert is_available is False
            assert "pendingDelete" in problematic_statuses
            assert "serverHold" in problematic_statuses

    def test_check_domain_status_detailed_handles_unavailable_domain(
        self,
    ) -> None:
        """Test detailed status check for genuinely unavailable domain."""
        # ARRANGE: Mock API response for unavailable domain
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "DomainInfo": {"domainAvailability": "UNAVAILABLE", "status": ["ok"]}
        }

        with patch("requests.get", return_value=mock_response):
            # ACT: Check detailed domain status
            is_available, problematic_statuses = check_domain_status_detailed(
                "unavailable.com"
            )

            # ASSERT: Should return False with empty problematic statuses
            assert is_available is False
            assert problematic_statuses == []

    def test_check_domain_status_detailed_handles_missing_status_field(
        self,
    ) -> None:
        """Test detailed status check handles missing status field."""
        # ARRANGE: Mock API response without status field
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "DomainInfo": {"domainAvailability": "AVAILABLE"}
        }

        with patch("requests.get", return_value=mock_response):
            # ACT: Check detailed domain status
            is_available, problematic_statuses = check_domain_status_detailed(
                "no-status.com"
            )

            # ASSERT: Should return True with empty problematic statuses
            assert is_available is True
            assert problematic_statuses == []

    def test_check_domain_status_detailed_handles_errors(
        self,
    ) -> None:
        """Test detailed status check handles API errors gracefully."""
        # ARRANGE: Mock network error
        with patch("requests.get", side_effect=ConnectionError("Network error")):
            # ACT: Check detailed domain status
            is_available, problematic_statuses = check_domain_status_detailed(
                "error.com"
            )

            # ASSERT: Should return False with empty problematic statuses
            assert is_available is False
            assert problematic_statuses == []

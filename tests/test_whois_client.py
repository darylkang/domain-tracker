"""
Tests for WhoisXML API client functionality.

Following TDD approach - these tests define the expected behavior for
domain availability checking via WhoisXML API.
"""

from __future__ import annotations

import json
from unittest.mock import Mock, patch

import pytest
import requests
from requests.exceptions import ConnectionError, RequestException, Timeout

from domain_tracker.whois_client import check_domain_availability


class TestWhoisClient:
    """Test WhoisXML API client functionality."""

    def test_check_domain_availability_returns_true_for_available_domain(self) -> None:
        """Test that available domains return True."""
        # ARRANGE: Mock successful API response for available domain
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "DomainInfo": {
                "domainAvailability": "AVAILABLE"
            }
        }

        with patch('requests.get', return_value=mock_response):
            # ACT: Check domain availability
            result = check_domain_availability("available-example.com")

            # ASSERT: Should return True for available domain
            assert result is True

    def test_check_domain_availability_returns_false_for_unavailable_domain(self) -> None:
        """Test that unavailable domains return False."""
        # ARRANGE: Mock successful API response for unavailable domain
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "DomainInfo": {
                "domainAvailability": "UNAVAILABLE"
            }
        }

        with patch('requests.get', return_value=mock_response):
            # ACT: Check domain availability
            result = check_domain_availability("google.com")

            # ASSERT: Should return False for unavailable domain
            assert result is False

    def test_check_domain_availability_loads_api_key_from_settings(self) -> None:
        """Test that API key is loaded from settings configuration."""
        # ARRANGE: Mock settings and API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "DomainInfo": {
                "domainAvailability": "AVAILABLE"
            }
        }

        with patch('requests.get', return_value=mock_response) as mock_get, \
             patch('domain_tracker.whois_client.Settings') as mock_settings_class:

            # Configure mock settings
            mock_settings = Mock()
            mock_settings.whois_api_key = "test-api-key-12345"
            mock_settings_class.return_value = mock_settings

            # ACT: Check domain availability
            check_domain_availability("test.com")

            # ASSERT: Should use API key from settings in request
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert 'apiKey' in call_args[1]['params']
            assert call_args[1]['params']['apiKey'] == "test-api-key-12345"

    def test_check_domain_availability_handles_network_timeout(self) -> None:
        """Test graceful handling of network timeouts."""
        # ARRANGE: Mock timeout exception
        with patch('requests.get', side_effect=Timeout("Request timed out")):
            # ACT & ASSERT: Should raise an exception or return False
            # (We'll decide on error handling strategy in implementation)
            result = check_domain_availability("timeout-test.com")
            assert result is False  # Conservative approach - assume unavailable on timeout

    def test_check_domain_availability_handles_connection_error(self) -> None:
        """Test graceful handling of connection errors."""
        # ARRANGE: Mock connection error
        with patch('requests.get', side_effect=ConnectionError("Unable to connect")):
            # ACT: Check domain availability with connection error
            result = check_domain_availability("connection-error-test.com")

            # ASSERT: Should return False on connection error (conservative)
            assert result is False

    def test_check_domain_availability_handles_http_error_response(self) -> None:
        """Test handling of HTTP error responses (4xx, 5xx)."""
        # ARRANGE: Mock HTTP error response
        mock_response = Mock()
        mock_response.status_code = 429  # Rate limit error
        mock_response.raise_for_status.side_effect = requests.HTTPError("429 Rate Limited")

        with patch('requests.get', return_value=mock_response):
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

        with patch('requests.get', return_value=mock_response):
            # ACT: Check domain availability with invalid JSON
            result = check_domain_availability("invalid-json-test.com")

            # ASSERT: Should return False on invalid response (conservative)
            assert result is False

    def test_check_domain_availability_handles_missing_domain_info(self) -> None:
        """Test handling of responses missing expected DomainInfo structure."""
        # ARRANGE: Mock response without DomainInfo
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ErrorMessage": "Domain format invalid"
        }

        with patch('requests.get', return_value=mock_response):
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
            "DomainInfo": {
                "domainAvailability": "AVAILABLE"
            }
        }

        with patch('requests.get', return_value=mock_response) as mock_get:
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
            "DomainInfo": {
                "domainAvailability": "AVAILABLE"
            }
        }

        with patch('requests.get', return_value=mock_response) as mock_get:
            # ACT: Check specific domain availability
            check_domain_availability("parameter-test.com")

            # ASSERT: Should include domain in request parameters
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert 'domainName' in call_args[1]['params']
            assert call_args[1]['params']['domainName'] == "parameter-test.com"

    def test_check_domain_availability_uses_timeout(self) -> None:
        """Test that API requests use appropriate timeout."""
        # ARRANGE: Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "DomainInfo": {
                "domainAvailability": "AVAILABLE"
            }
        }

        with patch('requests.get', return_value=mock_response) as mock_get:
            # ACT: Check domain availability
            check_domain_availability("timeout-test.com")

            # ASSERT: Should use timeout in request
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert 'timeout' in call_args[1]
            assert call_args[1]['timeout'] > 0  # Should have reasonable timeout

    def test_check_domain_availability_validates_domain_format(self) -> None:
        """Test that invalid domain formats are handled gracefully."""
        # ARRANGE: Test with clearly invalid domain
        invalid_domains = [
            "",           # Empty string
            "invalid",    # No TLD
            ".com",       # Starts with dot
            "test.",      # Ends with dot
            "too.many.dots.in.this.very.long.domain.name.com",  # Very long
        ]

        for invalid_domain in invalid_domains:
            # ACT & ASSERT: Should return False for invalid domains
            result = check_domain_availability(invalid_domain)
            assert result is False, f"Should return False for invalid domain: {invalid_domain}"

"""
Test suite for the core module.

Tests for domain checking business logic and service layer.
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from domain_tracker.core import (
    DomainCheckResult,
    DomainCheckService,
    format_domain_summary,
    get_domain_status_display,
    get_legacy_domain_message,
)
from domain_tracker.settings import Settings
from domain_tracker.whois_client import DomainInfo


class TestDomainCheckService:
    """Test cases for DomainCheckService class."""

    @pytest.fixture
    def service(self, test_settings: Settings) -> DomainCheckService:
        """Provide DomainCheckService instance for testing."""
        return DomainCheckService(settings=test_settings)

    def test_service_initialization_with_settings(
        self, test_settings: Settings
    ) -> None:
        """Test DomainCheckService initialization with provided settings."""
        service = DomainCheckService(settings=test_settings)
        assert service.settings is test_settings

    def test_service_initialization_without_settings(self) -> None:
        """Test DomainCheckService initialization with default settings."""
        with patch("domain_tracker.core.Settings") as mock_settings_class:
            mock_settings = Mock()
            mock_settings_class.return_value = mock_settings

            service = DomainCheckService()
            assert service.settings is mock_settings

    @patch("domain_tracker.core.get_enhanced_domain_info")
    def test_check_single_domain_enhanced_format(
        self, mock_get_enhanced: Mock, service: DomainCheckService
    ) -> None:
        """Test checking single domain with enhanced format."""
        # ARRANGE: Mock enhanced domain info
        mock_domain_info = DomainInfo(
            domain_name="example.com",
            is_available=True,
            problematic_statuses=[],
            has_error=False,
        )
        mock_get_enhanced.return_value = mock_domain_info

        # ACT: Check single domain
        result = service.check_single_domain("example.com", use_enhanced_format=True)

        # ASSERT: Should use enhanced format and return result
        mock_get_enhanced.assert_called_once_with("example.com", service.settings, debug=False)
        assert result is mock_domain_info

    @patch("domain_tracker.core.check_domain_status_detailed")
    def test_check_single_domain_legacy_format(
        self, mock_check_detailed: Mock, service: DomainCheckService
    ) -> None:
        """Test checking single domain with legacy format."""
        # ARRANGE: Mock legacy domain check
        mock_check_detailed.return_value = (True, ["pendingDelete"])

        # ACT: Check single domain with legacy format
        result = service.check_single_domain("example.com", use_enhanced_format=False)

        # ASSERT: Should use legacy format and convert to DomainInfo
        mock_check_detailed.assert_called_once_with("example.com", service.settings, debug=False)
        assert result.domain_name == "example.com"
        assert result.is_available is True
        assert result.problematic_statuses == ["pendingDelete"]
        assert result.has_error is False

    @patch("domain_tracker.core.load_domains")
    def test_check_multiple_domains_with_provided_list(
        self, mock_load: Mock, service: DomainCheckService
    ) -> None:
        """Test checking multiple domains with provided domain list."""
        # ARRANGE: Mock domain check
        with patch.object(service, "check_single_domain") as mock_check_single:
            mock_domain_info = DomainInfo(
                domain_name="example.com",
                is_available=True,
                problematic_statuses=[],
                has_error=False,
            )
            mock_check_single.return_value = mock_domain_info

            # ACT: Check multiple domains with provided list
            result = service.check_multiple_domains(
                domains=["example.com"], use_enhanced_format=True
            )

            # ASSERT: Should not load domains from file
            mock_load.assert_not_called()
            assert result.total_domains == 1
            assert result.available_domains == ["example.com"]
            assert len(result.domain_infos) == 1
            assert len(result.errors) == 0

    @patch("domain_tracker.core.send_slack_alert")
    @patch("domain_tracker.core.format_enhanced_slack_message")
    def test_send_slack_notification_success(
        self,
        mock_format_message: Mock,
        mock_send_alert: Mock,
        service: DomainCheckService,
    ) -> None:
        """Test successful Slack notification sending."""
        # ARRANGE: Mock formatting and sending
        mock_format_message.return_value = "formatted message"
        domain_info = DomainInfo(
            domain_name="example.com", is_available=True, problematic_statuses=[]
        )

        # ACT: Send notification
        result = service.send_slack_notification([domain_info], trigger_type="manual")

        # ASSERT: Should format and send message
        mock_format_message.assert_called_once()
        mock_send_alert.assert_called_once_with("formatted message", service.settings)
        assert result is True

    def test_send_slack_notification_no_domains(
        self, service: DomainCheckService
    ) -> None:
        """Test Slack notification with no domains."""
        # ACT: Send notification with empty list
        result = service.send_slack_notification([], trigger_type="manual")

        # ASSERT: Should not send notification
        assert result is False


class TestDomainCheckResult:
    """Test cases for DomainCheckResult named tuple."""

    def test_domain_check_result_creation(self) -> None:
        """Test creating DomainCheckResult with valid data."""
        domain_info = DomainInfo(
            domain_name="example.com", is_available=True, problematic_statuses=[]
        )
        result = DomainCheckResult(
            total_domains=1,
            available_domains=["example.com"],
            domain_infos=[domain_info],
            errors=[],
        )

        assert result.total_domains == 1
        assert result.available_domains == ["example.com"]
        assert len(result.domain_infos) == 1
        assert len(result.errors) == 0


class TestUtilityFunctions:
    """Test cases for utility functions."""

    def test_get_legacy_domain_message_available(self) -> None:
        """Test legacy message formatting for available domain."""
        message = get_legacy_domain_message("example.com", True, [])
        assert "✅ Domain available: example.com" in message

    def test_get_legacy_domain_message_unavailable(self) -> None:
        """Test legacy message formatting for unavailable domain."""
        message = get_legacy_domain_message("example.com", False, [])
        assert "❌ Domain NOT available: example.com" in message

    def test_get_legacy_domain_message_problematic(self) -> None:
        """Test legacy message formatting for domain with problematic status."""
        message = get_legacy_domain_message("example.com", False, ["pendingDelete"])
        assert "⚠️" in message
        assert "pendingDelete" in message
        assert "example.com" in message

    def test_format_domain_summary_with_available_domains(self) -> None:
        """Test formatting domain summary with available domains."""
        summary = format_domain_summary(3, ["example.com", "test.org"])
        assert "Checked 3 domains" in summary
        assert "Found 2 available domains" in summary
        assert "example.com, test.org" in summary

    def test_format_domain_summary_no_available_domains(self) -> None:
        """Test formatting domain summary with no available domains."""
        summary = format_domain_summary(2, [])
        assert "Checked 2 domains" in summary
        assert "Found 0 available domains" in summary
        assert "No domains available" in summary

    def test_get_domain_status_display_available(self) -> None:
        """Test domain status display for available domain."""
        domain_info = DomainInfo(
            domain_name="example.com", is_available=True, problematic_statuses=[]
        )
        display = get_domain_status_display(domain_info)
        assert "✅ Available" == display

    def test_get_domain_status_display_unavailable(self) -> None:
        """Test domain status display for unavailable domain."""
        domain_info = DomainInfo(
            domain_name="example.com", is_available=False, problematic_statuses=[]
        )
        display = get_domain_status_display(domain_info)
        assert "❌ Unavailable" == display

    def test_get_domain_status_display_problematic(self) -> None:
        """Test domain status display for domain with problematic status."""
        domain_info = DomainInfo(
            domain_name="example.com",
            is_available=False,
            problematic_statuses=["pendingDelete", "serverHold"],
        )
        display = get_domain_status_display(domain_info)
        assert "⚠️ Problematic status" in display
        assert "pendingDelete, serverHold" in display

    def test_get_domain_status_display_error(self) -> None:
        """Test domain status display for domain with error."""
        domain_info = DomainInfo(
            domain_name="example.com",
            is_available=False,
            problematic_statuses=[],
            has_error=True,
            error_message="API timeout",
        )
        display = get_domain_status_display(domain_info)
        assert "❌ Error: API timeout" == display

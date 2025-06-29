"""
Tests for CLI domain checking functionality.

Following TDD approach - these tests define the expected behavior for
the CLI interface that checks domains and sends Slack alerts.
"""

from __future__ import annotations

import logging
from unittest.mock import Mock, patch

from typer.testing import CliRunner

from domain_tracker import __version__
from domain_tracker.cli import app
from domain_tracker.core import DomainCheckResult
from domain_tracker.whois_client import DomainInfo


class TestCLIDomainsCommand:
    """Test CLI domain checking functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_check_domains_command_exists(self) -> None:
        """Test that check-domains command exists and is accessible."""
        # ARRANGE & ACT: Try to get help for check-domains command
        result = self.runner.invoke(app, ["check-domains", "--help"])

        # ASSERT: Command should exist and show help
        assert result.exit_code == 0
        assert "check-domains" in result.stdout
        assert "Check domain availability" in result.stdout

    @patch("domain_tracker.cli._load_settings")
    @patch("domain_tracker.cli.DomainCheckService")
    def test_check_domains_loads_domains_and_checks_availability(
        self, mock_service_class: Mock, mock_load_settings: Mock
    ) -> None:
        """Test that check-domains uses service to load and check domains."""
        # ARRANGE: Mock service and its methods
        mock_settings = Mock()
        mock_load_settings.return_value = mock_settings
        mock_service = Mock()
        mock_service_class.return_value = mock_service

        # Mock service result
        domain_infos = [
            DomainInfo(
                domain_name="example.com", is_available=True, problematic_statuses=[]
            ),
            DomainInfo(
                domain_name="test.org", is_available=False, problematic_statuses=[]
            ),
        ]
        check_result = DomainCheckResult(
            total_domains=2,
            available_domains=["example.com"],
            domain_infos=domain_infos,
            errors=[],
        )
        mock_service.check_multiple_domains.return_value = check_result
        mock_service.send_slack_notification.return_value = True

        # ACT: Run check-domains command
        result = self.runner.invoke(app, ["check-domains"])

        # ASSERT: Should use service to check domains
        assert result.exit_code == 0
        mock_service_class.assert_called_once_with(mock_settings)
        mock_service.check_multiple_domains.assert_called_once_with(
            use_enhanced_format=True, debug=False
        )
        mock_service.send_slack_notification.assert_called_once()

    @patch("domain_tracker.cli._load_settings")
    @patch("domain_tracker.cli.DomainCheckService")
    def test_check_domains_sends_slack_alert_for_available_domains(
        self, mock_service_class: Mock, mock_load_settings: Mock
    ) -> None:
        """Test that Slack alerts are sent through the service for available domains."""
        # ARRANGE: Mock service
        mock_settings = Mock()
        mock_load_settings.return_value = mock_settings
        mock_service = Mock()
        mock_service_class.return_value = mock_service

        # Mock service result with available domain
        domain_infos = [
            DomainInfo(
                domain_name="available.com", is_available=True, problematic_statuses=[]
            ),
            DomainInfo(
                domain_name="unavailable.com",
                is_available=False,
                problematic_statuses=[],
            ),
        ]
        check_result = DomainCheckResult(
            total_domains=2,
            available_domains=["available.com"],
            domain_infos=domain_infos,
            errors=[],
        )
        mock_service.check_multiple_domains.return_value = check_result
        mock_service.send_slack_notification.return_value = True

        # ACT: Run check-domains command
        result = self.runner.invoke(app, ["check-domains"])

        # ASSERT: Should send notification through service
        assert result.exit_code == 0
        mock_service.send_slack_notification.assert_called_once_with(
            domain_infos, trigger_type="manual", notify_all=False
        )

    @patch("domain_tracker.cli._load_settings")
    @patch("domain_tracker.cli.DomainCheckService")
    def test_check_domains_with_notify_all_flag(
        self, mock_service_class: Mock, mock_load_settings: Mock
    ) -> None:
        """Test that --notify-all sends alerts for all domains through service."""
        # ARRANGE: Mock service
        mock_settings = Mock()
        mock_load_settings.return_value = mock_settings
        mock_service = Mock()
        mock_service_class.return_value = mock_service

        # Mock service result
        domain_infos = [
            DomainInfo(
                domain_name="available.com", is_available=True, problematic_statuses=[]
            ),
            DomainInfo(
                domain_name="unavailable.com",
                is_available=False,
                problematic_statuses=[],
            ),
        ]
        check_result = DomainCheckResult(
            total_domains=2,
            available_domains=["available.com"],
            domain_infos=domain_infos,
            errors=[],
        )
        mock_service.check_multiple_domains.return_value = check_result
        mock_service.send_slack_notification.return_value = True

        # ACT: Run check-domains with --notify-all
        result = self.runner.invoke(app, ["check-domains", "--notify-all"])

        # ASSERT: Should send notification with notify_all=True
        assert result.exit_code == 0
        mock_service.send_slack_notification.assert_called_once_with(
            domain_infos, trigger_type="manual", notify_all=True
        )

    @patch("domain_tracker.cli._load_settings")
    @patch("domain_tracker.cli.DomainCheckService")
    def test_check_domains_with_debug_flag_enables_logging(
        self, mock_service_class: Mock, mock_load_settings: Mock
    ) -> None:
        """Test that --debug flag enables debug logging."""
        # ARRANGE: Mock service
        mock_settings = Mock()
        mock_load_settings.return_value = mock_settings
        mock_service = Mock()
        mock_service_class.return_value = mock_service

        check_result = DomainCheckResult(
            total_domains=1,
            available_domains=["test.com"],
            domain_infos=[
                DomainInfo(
                    domain_name="test.com", is_available=True, problematic_statuses=[]
                )
            ],
            errors=[],
        )
        mock_service.check_multiple_domains.return_value = check_result
        mock_service.send_slack_notification.return_value = True

        # ACT: Run check-domains with --debug
        with patch("domain_tracker.cli.logging.basicConfig") as mock_basic_config:
            result = self.runner.invoke(app, ["check-domains", "--debug"])

        # ASSERT: Should configure debug logging
        assert result.exit_code == 0
        mock_basic_config.assert_called_once_with(level=logging.DEBUG)

    @patch("domain_tracker.cli._load_settings")
    @patch("domain_tracker.cli.DomainCheckService")
    def test_check_domains_prints_summary_when_no_domains_available(
        self, mock_service_class: Mock, mock_load_settings: Mock
    ) -> None:
        """Test that a summary is printed when no domains are available."""
        # ARRANGE: Mock service with no available domains
        mock_settings = Mock()
        mock_load_settings.return_value = mock_settings
        mock_service = Mock()
        mock_service_class.return_value = mock_service

        domain_infos = [
            DomainInfo(
                domain_name="test1.com", is_available=False, problematic_statuses=[]
            ),
            DomainInfo(
                domain_name="test2.com", is_available=False, problematic_statuses=[]
            ),
        ]
        check_result = DomainCheckResult(
            total_domains=2, available_domains=[], domain_infos=domain_infos, errors=[]
        )
        mock_service.check_multiple_domains.return_value = check_result
        mock_service.send_slack_notification.return_value = False

        # ACT: Run check-domains command
        result = self.runner.invoke(app, ["check-domains"])

        # ASSERT: Should print summary with no available domains
        assert result.exit_code == 0
        assert "No domains available" in result.stdout
        assert "Total domains checked: 2" in result.stdout

    @patch("domain_tracker.cli._load_settings")
    @patch("domain_tracker.cli.DomainCheckService")
    def test_check_domains_handles_domain_loading_errors_gracefully(
        self, mock_service_class: Mock, mock_load_settings: Mock
    ) -> None:
        """Test that domain loading errors are handled gracefully."""
        # ARRANGE: Mock service to raise FileNotFoundError
        mock_settings = Mock()
        mock_load_settings.return_value = mock_settings
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.check_multiple_domains.side_effect = FileNotFoundError(
            "domains.txt not found"
        )

        # ACT: Run check-domains command
        result = self.runner.invoke(app, ["check-domains"])

        # ASSERT: Should exit with error and show helpful message
        assert result.exit_code == 1
        assert "Error loading domains" in result.stdout

    @patch("domain_tracker.cli._load_settings")
    @patch("domain_tracker.cli.DomainCheckService")
    def test_check_domains_handles_api_errors_gracefully(
        self, mock_service_class: Mock, mock_load_settings: Mock
    ) -> None:
        """Test that API errors during domain checking are handled gracefully."""
        # ARRANGE: Mock service with error domain
        mock_settings = Mock()
        mock_load_settings.return_value = mock_settings
        mock_service = Mock()
        mock_service_class.return_value = mock_service

        domain_infos = [
            DomainInfo(
                domain_name="test.com",
                is_available=False,
                problematic_statuses=[],
                has_error=True,
                error_message="API error",
            )
        ]
        check_result = DomainCheckResult(
            total_domains=1,
            available_domains=[],
            domain_infos=domain_infos,
            errors=["test.com: API error"],
        )
        mock_service.check_multiple_domains.return_value = check_result
        mock_service.send_slack_notification.return_value = True

        # ACT: Run check-domains command
        result = self.runner.invoke(app, ["check-domains"])

        # ASSERT: Should handle error gracefully
        assert result.exit_code == 0
        # Should show error status in output
        assert "Error: API error" in result.stdout

    @patch("domain_tracker.cli._load_settings")
    @patch("domain_tracker.cli.DomainCheckService")
    def test_check_domains_handles_slack_errors_gracefully(
        self, mock_service_class: Mock, mock_load_settings: Mock
    ) -> None:
        """Test that Slack errors are handled gracefully by the service."""
        # ARRANGE: Mock service with Slack error
        mock_settings = Mock()
        mock_load_settings.return_value = mock_settings
        mock_service = Mock()
        mock_service_class.return_value = mock_service

        domain_infos = [
            DomainInfo(
                domain_name="test.com", is_available=True, problematic_statuses=[]
            )
        ]
        check_result = DomainCheckResult(
            total_domains=1,
            available_domains=["test.com"],
            domain_infos=domain_infos,
            errors=[],
        )
        mock_service.check_multiple_domains.return_value = check_result
        mock_service.send_slack_notification.return_value = False  # Slack error

        # ACT: Run check-domains command
        result = self.runner.invoke(app, ["check-domains"])

        # ASSERT: Should complete successfully even with Slack error
        assert result.exit_code == 0

    @patch("domain_tracker.cli._load_settings")
    @patch("domain_tracker.cli.DomainCheckService")
    def test_check_domains_displays_progress_information(
        self, mock_service_class: Mock, mock_load_settings: Mock
    ) -> None:
        """Test that progress information is displayed for each domain."""
        # ARRANGE: Mock service
        mock_settings = Mock()
        mock_load_settings.return_value = mock_settings
        mock_service = Mock()
        mock_service_class.return_value = mock_service

        domain_infos = [
            DomainInfo(
                domain_name="test1.com", is_available=True, problematic_statuses=[]
            ),
            DomainInfo(
                domain_name="test2.com", is_available=False, problematic_statuses=[]
            ),
        ]
        check_result = DomainCheckResult(
            total_domains=2,
            available_domains=["test1.com"],
            domain_infos=domain_infos,
            errors=[],
        )
        mock_service.check_multiple_domains.return_value = check_result
        mock_service.send_slack_notification.return_value = True

        # ACT: Run check-domains command
        result = self.runner.invoke(app, ["check-domains"])

        # ASSERT: Should display progress for each domain
        assert result.exit_code == 0
        assert "test1.com" in result.stdout
        assert "test2.com" in result.stdout
        assert "Available" in result.stdout
        assert "Unavailable" in result.stdout
        assert "Available" in result.stdout
        assert "Unavailable" in result.stdout


class TestCLISingleDomainCheck:
    """Test CLI single domain checking functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("domain_tracker.cli._load_settings")
    @patch("domain_tracker.cli.DomainCheckService")
    def test_single_domain_check_available_domain(
        self, mock_service_class: Mock, mock_load_settings: Mock
    ) -> None:
        """Test checking a single available domain via check command."""
        # ARRANGE: Mock service
        mock_settings = Mock()
        mock_load_settings.return_value = mock_settings
        mock_service = Mock()
        mock_service_class.return_value = mock_service

        domain_info = DomainInfo(
            domain_name="example.com", is_available=True, problematic_statuses=[]
        )
        mock_service.check_single_domain.return_value = domain_info
        mock_service.send_slack_notification.return_value = True

        # ACT: Run CLI with check command
        result = self.runner.invoke(app, ["check", "example.com"])

        # ASSERT: Should check domain and send notification
        assert result.exit_code == 0
        assert "example.com" in result.stdout
        assert "Available" in result.stdout
        mock_service.check_single_domain.assert_called_once_with(
            "example.com", use_enhanced_format=True, debug=False
        )
        mock_service.send_slack_notification.assert_called_once()

    @patch("domain_tracker.cli._load_settings")
    @patch("domain_tracker.cli.DomainCheckService")
    def test_single_domain_check_unavailable_domain(
        self, mock_service_class: Mock, mock_load_settings: Mock
    ) -> None:
        """Test checking a single unavailable domain via check command."""
        # ARRANGE: Mock service
        mock_settings = Mock()
        mock_load_settings.return_value = mock_settings
        mock_service = Mock()
        mock_service_class.return_value = mock_service

        domain_info = DomainInfo(
            domain_name="unavailable.com", is_available=False, problematic_statuses=[]
        )
        mock_service.check_single_domain.return_value = domain_info
        mock_service.send_slack_notification.return_value = True

        # ACT: Run CLI with check command
        result = self.runner.invoke(app, ["check", "unavailable.com"])

        # ASSERT: Should check domain and show unavailable status
        assert result.exit_code == 0
        assert "unavailable.com" in result.stdout
        assert "Unavailable" in result.stdout
        mock_service.send_slack_notification.assert_called_once()

    @patch("domain_tracker.cli._load_settings")
    @patch("domain_tracker.cli.DomainCheckService")
    def test_single_domain_check_handles_api_errors_gracefully(
        self, mock_service_class: Mock, mock_load_settings: Mock
    ) -> None:
        """Test that API errors during single domain checking are handled gracefully."""
        # ARRANGE: Mock service with error
        mock_settings = Mock()
        mock_load_settings.return_value = mock_settings
        mock_service = Mock()
        mock_service_class.return_value = mock_service

        domain_info = DomainInfo(
            domain_name="error.com",
            is_available=False,
            problematic_statuses=[],
            has_error=True,
            error_message="API connection failed",
        )
        mock_service.check_single_domain.return_value = domain_info

        # ACT: Run CLI with check command
        result = self.runner.invoke(app, ["check", "error.com"])

        # ASSERT: Should handle error gracefully
        assert result.exit_code == 0
        assert "error.com" in result.stdout
        assert "Error: API connection failed" in result.stdout

    @patch("domain_tracker.cli._load_settings")
    @patch("domain_tracker.cli.DomainCheckService")
    def test_single_domain_check_handles_slack_errors_gracefully(
        self, mock_service_class: Mock, mock_load_settings: Mock
    ) -> None:
        """Test that Slack errors during single domain check are handled gracefully."""
        # ARRANGE: Mock service and domain info with error
        mock_settings = Mock()
        mock_load_settings.return_value = mock_settings
        mock_service = Mock()
        mock_service_class.return_value = mock_service

        domain_info = DomainInfo(
            domain_name="test.com",
            is_available=False,
            problematic_statuses=[],
            has_error=True,
            error_message="API request timeout",
        )
        mock_service.check_single_domain.return_value = domain_info
        mock_service.send_slack_notification.return_value = True

        # ACT: Run CLI with check command
        result = self.runner.invoke(app, ["check", "test.com"])

        # ASSERT: Should handle error gracefully and use enhanced notification
        assert result.exit_code == 0
        # Should send enhanced notification with error included
        mock_service.send_slack_notification.assert_called_once_with(
            [domain_info], trigger_type="manual", notify_all=True
        )

    def test_no_domain_argument_falls_back_to_existing_behavior(self) -> None:
        """Test that missing domain argument shows error."""
        # ACT: Run check command without domain argument
        result = self.runner.invoke(app, ["check"])

        # ASSERT: Should show error for missing argument
        assert result.exit_code == 2  # Typer error code for missing argument
        # Check that error is in the output
        assert "Missing argument" in result.output or "Error" in result.output

    def test_single_domain_check_validates_domain_format(self) -> None:
        """Test validation of domain format (basic behavior test)."""
        # Note: Domain format validation happens at the API level, not CLI level
        # This test ensures the CLI accepts domain-like strings
        with (
            patch("domain_tracker.cli._load_settings"),
            patch("domain_tracker.cli.DomainCheckService"),
        ):
            result = self.runner.invoke(app, ["check", "example.com"])
            # Should not fail on well-formed domain
            assert result.exit_code == 0

    @patch("domain_tracker.cli._load_settings")
    @patch("domain_tracker.cli.DomainCheckService")
    def test_single_domain_check_with_problematic_status(
        self, mock_service_class: Mock, mock_load_settings: Mock
    ) -> None:
        """Test checking a domain with problematic status."""
        # ARRANGE: Mock service
        mock_settings = Mock()
        mock_load_settings.return_value = mock_settings
        mock_service = Mock()
        mock_service_class.return_value = mock_service

        domain_info = DomainInfo(
            domain_name="problematic.com",
            is_available=False,
            problematic_statuses=["pendingDelete"],
        )
        mock_service.check_single_domain.return_value = domain_info
        mock_service.send_slack_notification.return_value = True

        # ACT: Run CLI with check command
        result = self.runner.invoke(app, ["check", "problematic.com"])

        # ASSERT: Should show problematic status
        assert result.exit_code == 0
        assert "problematic.com" in result.stdout
        assert "⚠️  Problematic (pendingdelete)" in result.stdout

    @patch("domain_tracker.cli._load_settings")
    @patch("domain_tracker.cli.DomainCheckService")
    def test_single_domain_check_with_multiple_problematic_statuses(
        self, mock_service_class: Mock, mock_load_settings: Mock
    ) -> None:
        """Test checking a domain with multiple problematic statuses."""
        # ARRANGE: Mock service
        mock_settings = Mock()
        mock_load_settings.return_value = mock_settings
        mock_service = Mock()
        mock_service_class.return_value = mock_service

        domain_info = DomainInfo(
            domain_name="multiple-issues.com",
            is_available=False,
            problematic_statuses=["pendingDelete", "serverHold"],
        )
        mock_service.check_single_domain.return_value = domain_info
        mock_service.send_slack_notification.return_value = True

        # ACT: Run CLI with check command
        result = self.runner.invoke(app, ["check", "multiple-issues.com"])

        # ASSERT: Should show all problematic statuses
        assert result.exit_code == 0
        assert "multiple-issues.com" in result.stdout
        assert "⚠️  Problematic (pendingdelete, hold)" in result.stdout

    @patch("domain_tracker.cli._load_settings")
    @patch("domain_tracker.cli.DomainCheckService")
    def test_check_single_domain_command_sends_enhanced_slack_alert(
        self, mock_service_class: Mock, mock_load_settings: Mock
    ) -> None:
        """Test that single domain check sends enhanced Slack alert."""
        # ARRANGE: Mock service and domain info
        mock_settings = Mock()
        mock_load_settings.return_value = mock_settings
        mock_service = Mock()
        mock_service_class.return_value = mock_service

        # Mock domain info
        domain_info = DomainInfo(
            domain_name="example.com", is_available=True, problematic_statuses=[]
        )
        mock_service.check_single_domain.return_value = domain_info
        mock_service.send_slack_notification.return_value = True

        # ACT: Run check command with single domain
        result = self.runner.invoke(app, ["check", "example.com"])

        # ASSERT: Should send notification through service with notify_all=True
        assert result.exit_code == 0
        mock_service.send_slack_notification.assert_called_once_with(
            [domain_info], trigger_type="manual", notify_all=True
        )

    @patch("domain_tracker.cli._load_settings")
    @patch("domain_tracker.cli.DomainCheckService")
    def test_check_multiple_domains_command_sends_enhanced_slack_alert(
        self, mock_service_class: Mock, mock_load_settings: Mock
    ) -> None:
        """Test that multiple domains check sends enhanced Slack alert."""
        # ARRANGE: Mock service and settings
        mock_settings = Mock()
        mock_load_settings.return_value = mock_settings
        mock_service = Mock()
        mock_service_class.return_value = mock_service

        # Mock service result for multiple domains
        domain_infos = [
            DomainInfo(
                domain_name="example.com", is_available=True, problematic_statuses=[]
            ),
            DomainInfo(
                domain_name="test.org", is_available=False, problematic_statuses=[]
            ),
        ]
        check_result = DomainCheckResult(
            total_domains=2,
            available_domains=["example.com"],
            domain_infos=domain_infos,
            errors=[],
        )
        mock_service.check_multiple_domains.return_value = check_result
        mock_service.send_slack_notification.return_value = True

        # ACT: Run check command with multiple domains
        result = self.runner.invoke(app, ["check", "example.com", "test.org"])

        # ASSERT: Should use check_multiple_domains and send notification
        assert result.exit_code == 0
        mock_service.check_multiple_domains.assert_called_once_with(
            domains=["example.com", "test.org"], use_enhanced_format=True, debug=False
        )
        mock_service.send_slack_notification.assert_called_once_with(
            domain_infos, trigger_type="manual", notify_all=True
        )


class TestCLIBulkProblematicStatuses:
    """Test CLI handling of problematic domain statuses in bulk operations."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("domain_tracker.cli._load_settings")
    @patch("domain_tracker.cli.DomainCheckService")
    def test_check_domains_displays_problematic_statuses(
        self, mock_service_class: Mock, mock_load_settings: Mock
    ) -> None:
        """Test that problematic statuses are displayed properly during bulk checking."""
        # ARRANGE: Mock service
        mock_settings = Mock()
        mock_load_settings.return_value = mock_settings
        mock_service = Mock()
        mock_service_class.return_value = mock_service

        domain_infos = [
            DomainInfo(
                domain_name="available.com", is_available=True, problematic_statuses=[]
            ),
            DomainInfo(
                domain_name="problematic.com",
                is_available=False,
                problematic_statuses=["pendingDelete"],
            ),
            DomainInfo(
                domain_name="unavailable.com",
                is_available=False,
                problematic_statuses=[],
            ),
        ]
        check_result = DomainCheckResult(
            total_domains=3,
            available_domains=["available.com"],
            domain_infos=domain_infos,
            errors=[],
        )
        mock_service.check_multiple_domains.return_value = check_result
        mock_service.send_slack_notification.return_value = True

        # ACT: Run check-domains command
        result = self.runner.invoke(app, ["check-domains"])

        # ASSERT: Should display all domain statuses properly
        assert result.exit_code == 0
        assert "available.com" in result.stdout and "Available" in result.stdout
        assert (
            "problematic.com" in result.stdout
            and "⚠️  Problematic (pendingdelete)" in result.stdout
        )
        assert "unavailable.com" in result.stdout and "Unavailable" in result.stdout

    @patch("domain_tracker.cli._load_settings")
    @patch("domain_tracker.cli.DomainCheckService")
    def test_check_domains_with_notify_all_sends_enhanced_alerts(
        self, mock_service_class: Mock, mock_load_settings: Mock
    ) -> None:
        """Test that --notify-all sends enhanced alerts with problematic statuses."""
        # ARRANGE: Mock service
        mock_settings = Mock()
        mock_load_settings.return_value = mock_settings
        mock_service = Mock()
        mock_service_class.return_value = mock_service

        domain_infos = [
            DomainInfo(
                domain_name="available.com", is_available=True, problematic_statuses=[]
            ),
            DomainInfo(
                domain_name="problematic.com",
                is_available=False,
                problematic_statuses=["serverHold", "clientHold"],
            ),
        ]
        check_result = DomainCheckResult(
            total_domains=2,
            available_domains=["available.com"],
            domain_infos=domain_infos,
            errors=[],
        )
        mock_service.check_multiple_domains.return_value = check_result
        mock_service.send_slack_notification.return_value = True

        # ACT: Run check-domains with --notify-all
        result = self.runner.invoke(app, ["check-domains", "--notify-all"])

        # ASSERT: Should send enhanced notification
        assert result.exit_code == 0
        mock_service.send_slack_notification.assert_called_once_with(
            domain_infos, trigger_type="manual", notify_all=True
        )


class TestCLIOtherCommands:
    """Test other CLI commands and general functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_cli_app_exists_and_shows_help(self) -> None:
        """Test that the main CLI app exists and shows help."""
        # ACT: Run CLI with --help
        result = self.runner.invoke(app, ["--help"])

        # ASSERT: Should show help information
        assert result.exit_code == 0
        assert "Domain Drop Tracker" in result.stdout

    def test_version_command_works(self) -> None:
        """Test that --version shows the correct version."""
        # ACT: Run CLI with --version
        result = self.runner.invoke(app, ["--version"])

        # ASSERT: Should show version
        assert result.exit_code == 0
        assert __version__ in result.stdout

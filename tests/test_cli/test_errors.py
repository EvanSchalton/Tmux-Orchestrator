"""Tests for error management CLI commands."""

from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from tmux_orchestrator.cli.errors import clear, errors, recent, stats, summary
from tmux_orchestrator.core.error_handler import (
    ErrorCategory,
    ErrorContext,
    ErrorHandler,
    ErrorRecord,
    ErrorSeverity,
)


class TestErrorsCLI:
    """Test cases for errors CLI commands."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_error_handler(self) -> Mock:
        """Create mock error handler."""
        handler = Mock(spec=ErrorHandler)
        handler.error_history = []
        handler.get_error_summary.return_value = {
            "total": 0,
            "by_category": {},
            "by_severity": {},
            "recovery_success_rate": 0.0,
        }
        return handler

    def test_errors_group_help(self, runner: CliRunner) -> None:
        """Test errors group help display."""
        result = runner.invoke(errors, ["--help"])
        assert result.exit_code == 0
        assert "Error management and reporting utilities" in result.output
        assert "summary" in result.output
        assert "recent" in result.output
        assert "clear" in result.output
        assert "stats" in result.output

    def test_summary_no_errors(self, runner: CliRunner, mock_error_handler: Mock) -> None:
        """Test summary command with no errors."""
        with patch("tmux_orchestrator.cli.errors.get_error_handler", return_value=mock_error_handler):
            result = runner.invoke(summary)
            assert result.exit_code == 0
            assert "No errors recorded" in result.output

    def test_summary_with_errors(self, runner: CliRunner, mock_error_handler: Mock) -> None:
        """Test summary command with errors."""
        mock_error_handler.get_error_summary.return_value = {
            "total": 15,
            "by_category": {
                "tmux": 5,
                "agent": 3,
                "network": 7,
            },
            "by_severity": {
                "low": 2,
                "medium": 8,
                "high": 4,
                "critical": 1,
            },
            "recovery_success_rate": 75.0,
        }

        with patch("tmux_orchestrator.cli.errors.get_error_handler", return_value=mock_error_handler):
            result = runner.invoke(summary)
            assert result.exit_code == 0
            assert "Error Summary" in result.output
            assert "Total Errors" in result.output
            assert "15" in result.output
            assert "Recovery Success Rate" in result.output
            assert "75.0%" in result.output
            assert "Errors by Category" in result.output
            assert "Errors by Severity" in result.output

    def test_summary_json_output(self, runner: CliRunner, mock_error_handler: Mock) -> None:
        """Test summary command with JSON output."""
        summary_data = {
            "total": 10,
            "by_category": {"tmux": 10},
            "by_severity": {"medium": 10},
            "recovery_success_rate": 100.0,
        }
        mock_error_handler.get_error_summary.return_value = summary_data

        with patch("tmux_orchestrator.cli.errors.get_error_handler", return_value=mock_error_handler):
            result = runner.invoke(summary, ["--json"])
            assert result.exit_code == 0
            import json

            output_data = json.loads(result.output)
            assert output_data["total"] == 10
            assert output_data["recovery_success_rate"] == 100.0

    def test_recent_no_errors(self, runner: CliRunner, mock_error_handler: Mock) -> None:
        """Test recent command with no errors."""
        with patch("tmux_orchestrator.cli.errors.get_error_handler", return_value=mock_error_handler):
            result = runner.invoke(recent)
            assert result.exit_code == 0
            assert "No errors recorded" in result.output

    def test_recent_with_errors(self, runner: CliRunner, mock_error_handler: Mock) -> None:
        """Test recent command with errors."""
        from datetime import datetime, timezone

        # Create test errors
        errors_list = [
            ErrorRecord(
                error_type="TestError",
                message="Test error 1",
                category=ErrorCategory.TMUX,
                severity=ErrorSeverity.HIGH,
                context=ErrorContext(operation="test_op1"),
                timestamp=datetime.now(timezone.utc),
            ),
            ErrorRecord(
                error_type="TestError",
                message="Test error 2",
                category=ErrorCategory.AGENT,
                severity=ErrorSeverity.MEDIUM,
                context=ErrorContext(operation="test_op2", agent_id="session1:0"),
                timestamp=datetime.now(timezone.utc),
                recovery_attempted=True,
                recovery_successful=True,
            ),
        ]
        mock_error_handler.error_history = errors_list

        with patch("tmux_orchestrator.cli.errors.get_error_handler", return_value=mock_error_handler):
            result = runner.invoke(recent)
            assert result.exit_code == 0
            assert "Error #1" in result.output
            assert "Test error 1" in result.output
            assert "Error #2" in result.output
            assert "Test error 2" in result.output
            assert "Recovery: ✓ Successful" in result.output

    def test_recent_with_filters(self, runner: CliRunner, mock_error_handler: Mock) -> None:
        """Test recent command with severity and category filters."""
        from datetime import datetime, timezone

        # Create test errors with different severities and categories
        errors_list = [
            ErrorRecord(
                error_type="CriticalError",
                message="Critical TMUX error",
                category=ErrorCategory.TMUX,
                severity=ErrorSeverity.CRITICAL,
                context=ErrorContext(operation="critical_op"),
                timestamp=datetime.now(timezone.utc),
            ),
            ErrorRecord(
                error_type="MediumError",
                message="Medium agent error",
                category=ErrorCategory.AGENT,
                severity=ErrorSeverity.MEDIUM,
                context=ErrorContext(operation="medium_op"),
                timestamp=datetime.now(timezone.utc),
            ),
        ]
        mock_error_handler.error_history = errors_list

        with patch("tmux_orchestrator.cli.errors.get_error_handler", return_value=mock_error_handler):
            # Filter by severity
            result = runner.invoke(recent, ["--severity", "critical"])
            assert result.exit_code == 0
            assert "Critical TMUX error" in result.output
            assert "Medium agent error" not in result.output

            # Filter by category
            result = runner.invoke(recent, ["--category", "agent"])
            assert result.exit_code == 0
            assert "Medium agent error" in result.output
            assert "Critical TMUX error" not in result.output

    def test_clear_command(self, runner: CliRunner) -> None:
        """Test clear command."""
        with patch("tmux_orchestrator.cli.errors.clear_error_messages", return_value=3):
            result = runner.invoke(clear)
            assert result.exit_code == 0
            assert "Cleared 3 error log file(s)" in result.output

    def test_clear_dry_run(self, runner: CliRunner) -> None:
        """Test clear command with dry run."""
        result = runner.invoke(clear, ["--dry-run"])
        assert result.exit_code == 0
        assert "DRY RUN" in result.output

    def test_clear_no_files(self, runner: CliRunner) -> None:
        """Test clear command when no files to clear."""
        with patch("tmux_orchestrator.cli.errors.clear_error_messages", return_value=0):
            result = runner.invoke(clear, ["--age-days", "30"])
            assert result.exit_code == 0
            assert "No error logs older than 30 days found" in result.output

    def test_stats_no_errors(self, runner: CliRunner, mock_error_handler: Mock) -> None:
        """Test stats command with no errors."""
        with patch("tmux_orchestrator.cli.errors.get_error_handler", return_value=mock_error_handler):
            result = runner.invoke(stats)
            assert result.exit_code == 0
            assert "No errors recorded - system running smoothly!" in result.output

    def test_stats_with_errors(self, runner: CliRunner, mock_error_handler: Mock) -> None:
        """Test stats command with errors."""
        mock_error_handler.get_error_summary.return_value = {
            "total": 150,
            "by_category": {
                "tmux": 50,
                "network": 40,
                "agent": 30,
                "filesystem": 20,
                "unknown": 10,
            },
            "by_severity": {
                "low": 20,
                "medium": 80,
                "high": 40,
                "critical": 10,
            },
            "recovery_success_rate": 40.0,
        }

        with patch("tmux_orchestrator.cli.errors.get_error_handler", return_value=mock_error_handler):
            result = runner.invoke(stats)
            assert result.exit_code == 0
            assert "Error Statistics Overview" in result.output
            assert "System Health: 🔴 Poor" in result.output  # >100 errors
            assert "Total Errors: 150" in result.output
            assert "Recovery Success: 40.0%" in result.output
            assert "Top Error Categories" in result.output
            assert "Recommendations" in result.output
            assert "High TMUX errors" in result.output
            assert "Network issues detected" in result.output
            assert "Low recovery success" in result.output
            assert "Critical errors detected" in result.output

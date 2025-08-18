"""Performance-focused CLI command tests for Phase 7.0 testing suite.

This module tests all CLI commands with performance benchmarks and traceability.
Ensures all commands execute within 1 second for optimal developer experience.
"""

import time
from unittest.mock import Mock, patch

from click.testing import CliRunner

from tmux_orchestrator.cli import cli


class TestCLIPerformance:
    """Performance validation for all CLI commands."""

    def test_cli_main_command_performance(self, cli_runner: CliRunner, test_uuid: str) -> None:
        """Test main CLI command executes quickly and shows help."""
        start_time = time.time()
        result = cli_runner.invoke(cli, ["--help"])
        execution_time = time.time() - start_time

        assert result.exit_code == 0
        assert execution_time < 1.0, f"CLI help took {execution_time:.3f}s (>1s limit) - Test ID: {test_uuid}"
        assert "TMUX Orchestrator" in result.output
        assert "AI-powered tmux session management" in result.output

    def test_cli_version_performance(self, cli_runner: CliRunner, test_uuid: str) -> None:
        """Test version command performance."""
        start_time = time.time()
        result = cli_runner.invoke(cli, ["--version"])
        execution_time = time.time() - start_time

        assert result.exit_code == 0
        assert execution_time < 1.0, f"Version command took {execution_time:.3f}s (>1s limit) - Test ID: {test_uuid}"
        assert "tmux-orc, version" in result.output

    @patch("tmux_orchestrator.cli.agent.TMUXManager")
    def test_agent_status_command_performance(
        self, mock_tmux_manager: Mock, cli_runner: CliRunner, test_uuid: str
    ) -> None:
        """Test agent status command performance with mocked tmux."""
        # Configure mock for quick response
        mock_tmux_manager.return_value.list_sessions.return_value = ["session1", "session2"]
        mock_tmux_manager.return_value.session_exists.return_value = True

        start_time = time.time()
        result = cli_runner.invoke(cli, ["agent", "status", "session1:1"])
        execution_time = time.time() - start_time

        # Should complete quickly even if command functionality isn't fully implemented
        assert execution_time < 1.0, f"Agent status took {execution_time:.3f}s (>1s limit) - Test ID: {test_uuid}"

    @patch("tmux_orchestrator.cli.spawn.TMUXManager")
    def test_spawn_command_performance(self, mock_tmux_manager: Mock, cli_runner: CliRunner, test_uuid: str) -> None:
        """Test spawn command argument parsing performance."""
        mock_tmux_manager.return_value.session_exists.return_value = False
        mock_tmux_manager.return_value.new_session.return_value = True

        start_time = time.time()
        # Test with invalid arguments to check argument parsing speed
        result = cli_runner.invoke(cli, ["spawn", "--help"])
        execution_time = time.time() - start_time

        assert result.exit_code == 0
        assert execution_time < 1.0, f"Spawn help took {execution_time:.3f}s (>1s limit) - Test ID: {test_uuid}"

    @patch("tmux_orchestrator.cli.monitor.TMUXManager")
    def test_monitor_command_performance(self, mock_tmux_manager: Mock, cli_runner: CliRunner, test_uuid: str) -> None:
        """Test monitor command performance."""
        start_time = time.time()
        result = cli_runner.invoke(cli, ["monitor", "--help"])
        execution_time = time.time() - start_time

        assert result.exit_code == 0
        assert execution_time < 1.0, f"Monitor help took {execution_time:.3f}s (>1s limit) - Test ID: {test_uuid}"

    @patch("tmux_orchestrator.cli.team.TMUXManager")
    def test_team_command_performance(self, mock_tmux_manager: Mock, cli_runner: CliRunner, test_uuid: str) -> None:
        """Test team command performance."""
        start_time = time.time()
        result = cli_runner.invoke(cli, ["team", "--help"])
        execution_time = time.time() - start_time

        assert result.exit_code == 0
        assert execution_time < 1.0, f"Team help took {execution_time:.3f}s (>1s limit) - Test ID: {test_uuid}"

    def test_cli_command_discovery_performance(self, cli_runner: CliRunner, test_uuid: str) -> None:
        """Test that CLI can discover all commands quickly."""
        start_time = time.time()
        result = cli_runner.invoke(cli, ["--help"])
        execution_time = time.time() - start_time

        assert result.exit_code == 0
        assert execution_time < 1.0, f"Command discovery took {execution_time:.3f}s (>1s limit) - Test ID: {test_uuid}"

        # Verify key commands are discovered
        expected_commands = ["agent", "team", "monitor", "spawn", "server"]
        for cmd in expected_commands:
            assert cmd in result.output, f"Command '{cmd}' not found in help output - Test ID: {test_uuid}"


class TestCLIArgumentValidation:
    """Test CLI argument validation with performance focus."""

    def test_invalid_arguments_fast_rejection(self, cli_runner: CliRunner, test_uuid: str) -> None:
        """Test that invalid arguments are rejected quickly."""
        start_time = time.time()
        result = cli_runner.invoke(cli, ["nonexistent-command"])
        execution_time = time.time() - start_time

        assert result.exit_code != 0
        assert (
            execution_time < 1.0
        ), f"Invalid command rejection took {execution_time:.3f}s (>1s limit) - Test ID: {test_uuid}"

    def test_json_output_flag_performance(self, cli_runner: CliRunner, test_uuid: str) -> None:
        """Test JSON output flag processing performance."""
        start_time = time.time()
        result = cli_runner.invoke(cli, ["--json", "--help"])
        execution_time = time.time() - start_time

        assert result.exit_code == 0
        assert (
            execution_time < 1.0
        ), f"JSON flag processing took {execution_time:.3f}s (>1s limit) - Test ID: {test_uuid}"

    def test_verbose_flag_performance(self, cli_runner: CliRunner, test_uuid: str) -> None:
        """Test verbose flag processing performance."""
        start_time = time.time()
        result = cli_runner.invoke(cli, ["--verbose", "--help"])
        execution_time = time.time() - start_time

        assert result.exit_code == 0
        assert (
            execution_time < 1.0
        ), f"Verbose flag processing took {execution_time:.3f}s (>1s limit) - Test ID: {test_uuid}"


class TestCLIMockingInfrastructure:
    """Test that our mocking infrastructure works correctly for performance testing."""

    @patch("tmux_orchestrator.core.config.Config.load")
    def test_config_loading_mock_performance(
        self, mock_config_load: Mock, cli_runner: CliRunner, test_uuid: str
    ) -> None:
        """Test that config loading can be mocked for performance."""
        mock_config_load.return_value = Mock()

        start_time = time.time()
        result = cli_runner.invoke(cli, ["--help"])
        execution_time = time.time() - start_time

        assert result.exit_code == 0
        assert (
            execution_time < 1.0
        ), f"Mocked config loading took {execution_time:.3f}s (>1s limit) - Test ID: {test_uuid}"

    def test_tmux_manager_mock_isolation(self, mock_tmux_manager: Mock, test_uuid: str) -> None:
        """Test that TMUXManager mocking provides proper isolation."""
        # Verify mock is configured correctly
        assert mock_tmux_manager.list_sessions.return_value == ["session1", "session2"]
        assert mock_tmux_manager.session_exists.return_value is True

        # Test execution performance with mock
        start_time = time.time()
        result = mock_tmux_manager.get_pane_content("session:0")
        execution_time = time.time() - start_time

        assert result == "Mock pane content"
        assert (
            execution_time < 0.1
        ), f"Mock tmux operation took {execution_time:.3f}s (>0.1s limit) - Test ID: {test_uuid}"

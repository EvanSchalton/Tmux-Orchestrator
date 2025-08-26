"""Tests for agent kill-all command."""

from unittest.mock import Mock

import pytest
from click.testing import CliRunner

from tmux_orchestrator.cli.agent import agent, kill_all
from tmux_orchestrator.utils.tmux import TMUXManager

# TMUXManager import removed - using comprehensive_mock_tmux fixture


@pytest.fixture
def runner() -> CliRunner:
    """Create Click test runner."""
    return CliRunner()


@pytest.fixture
def mock_tmux() -> Mock:
    """Create mock TMUXManager."""
    return Mock(spec=TMUXManager)


class TestAgentKillAll:
    """Test cases for agent kill-all command."""

    def test_kill_all_no_agents(self, runner: CliRunner, mock_tmux: Mock) -> None:
        """Test kill-all when no agents exist."""
        mock_tmux.list_agents.return_value = []

        result = runner.invoke(agent, ["kill-all"], obj={"tmux": mock_tmux})

        assert result.exit_code == 0
        assert "No agents found to kill" in result.output
        mock_tmux.list_agents.assert_called_once()

    def test_kill_all_with_confirmation_yes(self, runner: CliRunner, mock_tmux: Mock) -> None:
        """Test kill-all with user confirming the operation."""
        # Setup mock agents
        mock_agents = [
            {"session": "project-a", "window": "0", "type": "Project Manager", "status": "Active"},
            {"session": "project-a", "window": "1", "type": "Developer", "status": "Active"},
            {"session": "project-b", "window": "0", "type": "QA Engineer", "status": "Idle"},
        ]
        mock_tmux.list_agents.return_value = mock_agents
        mock_tmux.kill_window.return_value = True

        # Simulate user confirming with 'y'
        result = runner.invoke(agent, ["kill-all"], obj={"tmux": mock_tmux}, input="y\n")

        assert result.exit_code == 0
        assert "WARNING: Kill All Agents" in result.output
        assert "This will terminate 3 agent(s) across 2 session(s)" in result.output
        assert "Session: project-a" in result.output
        assert "Session: project-b" in result.output
        assert "Successfully killed all 3 agent(s)" in result.output
        assert "Sessions affected: project-a, project-b" in result.output

        # Verify kill_window was called for each agent
        assert mock_tmux.kill_window.call_count == 3
        mock_tmux.kill_window.assert_any_call("project-a:0")
        mock_tmux.kill_window.assert_any_call("project-a:1")
        mock_tmux.kill_window.assert_any_call("project-b:0")

    def test_kill_all_with_confirmation_no(self, runner: CliRunner, mock_tmux: Mock) -> None:
        """Test kill-all with user cancelling the operation."""
        mock_agents = [
            {"session": "project-a", "window": "0", "type": "Developer", "status": "Active"},
        ]
        mock_tmux.list_agents.return_value = mock_agents

        # Simulate user declining with 'n'
        result = runner.invoke(agent, ["kill-all"], obj={"tmux": mock_tmux}, input="n\n")

        assert result.exit_code == 0
        assert "WARNING: Kill All Agents" in result.output
        assert "Kill-all operation cancelled" in result.output

        # Verify no windows were killed
        mock_tmux.kill_window.assert_not_called()

    def test_kill_all_with_force_flag(self, runner: CliRunner, mock_tmux: Mock) -> None:
        """Test kill-all with --force flag (no confirmation)."""
        mock_agents = [
            {"session": "test-session", "window": "0", "type": "Developer", "status": "Active"},
            {"session": "test-session", "window": "1", "type": "QA", "status": "Active"},
        ]
        mock_tmux.list_agents.return_value = mock_agents
        mock_tmux.kill_window.return_value = True

        result = runner.invoke(agent, ["kill-all", "--force"], obj={"tmux": mock_tmux})

        assert result.exit_code == 0
        # Should NOT show warning/confirmation
        assert "WARNING: Kill All Agents" not in result.output
        assert "Are you sure" not in result.output
        assert "Successfully killed all 2 agent(s)" in result.output

        # Verify windows were killed
        assert mock_tmux.kill_window.call_count == 2

    def test_kill_all_partial_failure(self, runner: CliRunner, mock_tmux: Mock) -> None:
        """Test kill-all when some kills fail."""
        mock_agents = [
            {"session": "session-a", "window": "0", "type": "PM", "status": "Active"},
            {"session": "session-a", "window": "1", "type": "Dev", "status": "Active"},
            {"session": "session-b", "window": "0", "type": "QA", "status": "Active"},
        ]
        mock_tmux.list_agents.return_value = mock_agents

        # Make second kill fail
        mock_tmux.kill_window.side_effect = [True, False, True]

        result = runner.invoke(agent, ["kill-all", "--force"], obj={"tmux": mock_tmux})

        assert result.exit_code == 0
        assert "Killed 2/3 agent(s)" in result.output
        assert "Failed: session-a:1" in result.output

    def test_kill_all_with_exception(self, runner: CliRunner, mock_tmux: Mock) -> None:
        """Test kill-all when kill_window raises exception."""
        mock_agents = [
            {"session": "test", "window": "0", "type": "Dev", "status": "Active"},
        ]
        mock_tmux.list_agents.return_value = mock_agents
        mock_tmux.kill_window.side_effect = Exception("Connection error")

        result = runner.invoke(agent, ["kill-all", "--force"], obj={"tmux": mock_tmux})

        assert result.exit_code == 0
        assert "Killed 0/1 agent(s)" in result.output
        assert "error: Connection error" in result.output

    def test_kill_all_json_output_success(self, runner: CliRunner, mock_tmux: Mock) -> None:
        """Test kill-all with --json flag for successful operation."""
        mock_agents = [
            {"session": "project", "window": "0", "type": "PM", "status": "Active"},
            {"session": "project", "window": "1", "type": "Dev", "status": "Active"},
        ]
        mock_tmux.list_agents.return_value = mock_agents
        mock_tmux.kill_window.return_value = True

        result = runner.invoke(agent, ["kill-all", "--force", "--json"], obj={"tmux": mock_tmux})

        assert result.exit_code == 0

        # Parse JSON output - handle multi-line JSON
        import json

        # The JSON module outputs with indent=2, so we need to capture all lines
        json_text = result.output.strip()

        # If there's non-JSON output before the JSON, find where JSON starts
        lines = json_text.split("\n")
        json_start = -1
        for i, line in enumerate(lines):
            if line.strip() == "{":
                json_start = i
                break

        if json_start >= 0:
            json_lines = lines[json_start:]
            json_text = "\n".join(json_lines)

        output_data = json.loads(json_text)

        assert output_data["success"] is True
        assert output_data["agents_killed"] == 2
        assert output_data["total_agents"] == 2
        assert "project" in output_data["sessions_affected"]
        assert "Successfully killed all 2 agent(s)" in output_data["message"]

    def test_kill_all_json_output_cancelled(self, runner: CliRunner, mock_tmux: Mock) -> None:
        """Test kill-all JSON output when operation is cancelled."""
        mock_agents = [
            {"session": "test", "window": "0", "type": "Dev", "status": "Active"},
        ]
        mock_tmux.list_agents.return_value = mock_agents

        result = runner.invoke(agent, ["kill-all", "--json"], obj={"tmux": mock_tmux}, input="n\n")

        assert result.exit_code == 0

        # Handle multi-line JSON output
        import json

        json_lines = []
        in_json = False
        for line in result.output.strip().split("\n"):
            if line.strip().startswith("{"):
                in_json = True
            if in_json:
                json_lines.append(line)
            if line.strip().endswith("}") and in_json:
                break

        json_output = "\n".join(json_lines)
        assert json_output, f"No JSON found in output: {result.output}"
        output_data = json.loads(json_output)

        assert output_data["success"] is False
        assert output_data["agents_killed"] == 0
        assert output_data["message"] == "Kill-all operation cancelled"

    def test_kill_all_json_output_no_agents(self, runner: CliRunner, mock_tmux: Mock) -> None:
        """Test kill-all JSON output when no agents exist."""
        mock_tmux.list_agents.return_value = []

        result = runner.invoke(agent, ["kill-all", "--json"], obj={"tmux": mock_tmux})

        assert result.exit_code == 0

        import json

        output_data = json.loads(result.output)

        assert output_data["success"] is True
        assert output_data["agents_killed"] == 0
        assert output_data["message"] == "No agents found to kill"
        assert output_data["sessions_affected"] == []

    def test_kill_all_complex_session_layout(self, runner: CliRunner, mock_tmux: Mock) -> None:
        """Test kill-all with complex multi-session layout."""
        mock_agents = [
            # Session 1: Full team
            {"session": "frontend", "window": "0", "type": "PM", "status": "Active"},
            {"session": "frontend", "window": "1", "type": "Frontend Dev", "status": "Active"},
            {"session": "frontend", "window": "2", "type": "UI Designer", "status": "Idle"},
            {"session": "frontend", "window": "3", "type": "QA", "status": "Active"},
            # Session 2: Backend team
            {"session": "backend", "window": "0", "type": "Backend Lead", "status": "Active"},
            {"session": "backend", "window": "1", "type": "API Dev", "status": "Active"},
            {"session": "backend", "window": "2", "type": "DB Expert", "status": "Idle"},
            # Session 3: Single agent
            {"session": "docs", "window": "0", "type": "Tech Writer", "status": "Active"},
        ]
        mock_tmux.list_agents.return_value = mock_agents
        mock_tmux.kill_window.return_value = True

        result = runner.invoke(agent, ["kill-all"], obj={"tmux": mock_tmux}, input="y\n")

        assert result.exit_code == 0
        assert "This will terminate 8 agent(s) across 3 session(s)" in result.output
        assert "Successfully killed all 8 agent(s)" in result.output
        assert mock_tmux.kill_window.call_count == 8

    def test_kill_all_direct_function_call(self, runner: CliRunner, mock_tmux: Mock) -> None:
        """Test kill_all function directly."""
        mock_agents = [
            {"session": "test", "window": "0", "type": "Dev", "status": "Active"},
        ]
        mock_tmux.list_agents.return_value = mock_agents
        mock_tmux.kill_window.return_value = True

        # Test direct function call
        result = runner.invoke(kill_all, ["--force"], obj={"tmux": mock_tmux})

        assert result.exit_code == 0
        assert "Successfully killed all 1 agent(s)" in result.output

    def test_kill_all_in_agent_command_list(self) -> None:
        """Verify kill-all is registered in agent command group."""
        command_names = list(agent.commands.keys())
        assert "kill-all" in command_names

    def test_kill_all_empty_session_names(self, runner: CliRunner, mock_tmux: Mock) -> None:
        """Test kill-all handles agents with edge case session names."""
        mock_agents = [
            {"session": "", "window": "0", "type": "Dev", "status": "Active"},  # Empty session
            {"session": "session-with-special-chars!@#", "window": "0", "type": "PM", "status": "Active"},
        ]
        mock_tmux.list_agents.return_value = mock_agents
        mock_tmux.kill_window.return_value = True

        result = runner.invoke(agent, ["kill-all", "--force"], obj={"tmux": mock_tmux})

        assert result.exit_code == 0
        assert "Successfully killed all 2 agent(s)" in result.output

"""Tests for advanced agent CLI commands - list and spawn functionality."""

from unittest.mock import Mock

import pytest
from click.testing import CliRunner

from tmux_orchestrator.cli.agent import agent
from tmux_orchestrator.utils.tmux import TMUXManager


@pytest.fixture
def runner() -> CliRunner:
    """Create Click test runner."""
    return CliRunner()


def test_agent_list_command() -> None:
    """Test agent list command."""
    runner = CliRunner()

    mock_tmux = Mock(spec=TMUXManager)
    mock_tmux.list_agents.return_value = [
        {"session": "test-project", "window": "0", "type": "PM", "status": "Active"},
        {"session": "test-project", "window": "1", "type": "Developer", "status": "Idle"},
        {"session": "test-project", "window": "2", "type": "QA", "status": "Active"},
    ]
    mock_tmux.list_windows.return_value = [
        {"index": "0", "name": "Claude-pm"},
        {"index": "1", "name": "Claude-developer"},
        {"index": "2", "name": "Claude-qa"},
    ]

    # Test normal list
    result = runner.invoke(agent, ["list"], obj={"tmux": mock_tmux})
    assert result.exit_code == 0
    assert "Active Agents" in result.output
    assert "test-project" in result.output
    assert "Summary: 3 agents (2 active, 1 idle)" in result.output

    # Test JSON output
    result = runner.invoke(agent, ["list", "--json"], obj={"tmux": mock_tmux})
    assert result.exit_code == 0
    import json

    agents = json.loads(result.output.strip())
    assert len(agents) == 3
    assert agents[0]["session"] == "test-project"

    # Test session filter
    mock_tmux.list_agents.return_value = [
        {"session": "test-project", "window": "0", "type": "PM", "status": "Active"},
    ]
    result = runner.invoke(agent, ["list", "--session", "test-project"], obj={"tmux": mock_tmux})
    assert result.exit_code == 0
    assert "test-project" in result.output
    assert "Filtered by session: test-project" in result.output

    # Test no agents found
    mock_tmux.list_agents.return_value = []
    result = runner.invoke(agent, ["list"], obj={"tmux": mock_tmux})
    assert result.exit_code == 0
    assert "No agents found in any session" in result.output

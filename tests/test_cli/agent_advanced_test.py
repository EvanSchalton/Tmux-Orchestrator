"""Tests for advanced agent CLI commands - list and spawn functionality."""

from unittest.mock import Mock, patch

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


def test_agent_spawn_command() -> None:
    """Test agent spawn command."""
    runner = CliRunner()

    mock_tmux = Mock(spec=TMUXManager)
    mock_tmux.has_session.return_value = True
    mock_tmux.create_window.return_value = True
    # Mock list_windows to return different values on different calls
    # First call: check for conflicts (only pm exists)
    # Second call: after creating window (both pm and api-specialist exist)
    mock_tmux.list_windows.side_effect = [
        [{"index": "0", "name": "Claude-pm"}],  # First call - check for conflicts
        [
            {"index": "0", "name": "Claude-pm"},
            {"index": "1", "name": "Claude-api-specialist"},
        ],  # Second call - after creation
    ]
    mock_tmux.send_text.return_value = True
    mock_tmux.press_enter.return_value = True
    mock_tmux.send_message.return_value = True

    # Test basic spawn
    with patch("time.sleep"):
        result = runner.invoke(agent, ["spawn", "api-specialist", "myproject:1"], obj={"tmux": mock_tmux})

    assert result.exit_code == 0
    assert "Spawned custom agent 'api-specialist'" in result.output
    assert "Claude-api-specialist" in result.output
    mock_tmux.create_window.assert_called_once_with("myproject", "Claude-api-specialist", None)
    mock_tmux.send_text.assert_any_call("myproject:1", "claude --dangerously-skip-permissions")
    mock_tmux.press_enter.assert_any_call("myproject:1")

    # Test spawn with briefing
    mock_tmux.create_window.reset_mock()
    mock_tmux.send_text.reset_mock()
    mock_tmux.press_enter.reset_mock()
    mock_tmux.send_message.reset_mock()

    # Update mock to return the new window
    mock_tmux.list_windows.side_effect = [
        [{"index": "0", "name": "Claude-pm"}],  # First call - check for conflicts
        [
            {"index": "0", "name": "Claude-pm"},
            {"index": "1", "name": "Claude-perf-engineer"},
        ],  # Second call - after creation
    ]

    with patch("time.sleep"):
        result = runner.invoke(
            agent,
            ["spawn", "perf-engineer", "backend:2", "--briefing", "You are a performance engineer..."],
            obj={"tmux": mock_tmux},
        )

    assert result.exit_code == 0
    assert "Custom briefing: ✓ Sent" in result.output
    mock_tmux.send_message.assert_called_once_with("backend:1", "You are a performance engineer...")

    # Test spawn with working directory
    mock_tmux.create_window.reset_mock()

    # Update mock for db-expert window
    mock_tmux.list_windows.side_effect = [
        [{"index": "0", "name": "Claude-pm"}],  # First call - check for conflicts
        [
            {"index": "0", "name": "Claude-pm"},
            {"index": "1", "name": "Claude-db-expert"},
        ],  # Second call - after creation
    ]

    with patch("time.sleep"):
        result = runner.invoke(
            agent, ["spawn", "db-expert", "data:3", "--working-dir", "/workspaces/database"], obj={"tmux": mock_tmux}
        )

    assert result.exit_code == 0
    assert "Working directory: /workspaces/database" in result.output
    mock_tmux.create_window.assert_called_once_with("data", "Claude-db-expert", "/workspaces/database")

    # Test JSON output
    # Update mock for test-agent window
    mock_tmux.list_windows.side_effect = [
        [],  # First call - check for conflicts (empty session)
        [{"index": "0", "name": "Claude-test-agent"}],  # Second call - after creation
    ]

    with patch("time.sleep"):
        result = runner.invoke(agent, ["spawn", "test-agent", "test:0", "--json"], obj={"tmux": mock_tmux})

    assert result.exit_code == 0
    import json

    output = json.loads(result.output.strip())
    assert output["success"] is True
    assert output["name"] == "test-agent"
    assert output["window_name"] == "Claude-test-agent"

    # Test invalid target format
    result = runner.invoke(agent, ["spawn", "bad-agent", "invalid-format"], obj={"tmux": mock_tmux})
    assert result.exit_code == 0
    assert "Invalid target format" in result.output

    # Test session creation when it doesn't exist
    mock_tmux.has_session.return_value = False
    mock_tmux.create_session.return_value = True
    # Add side_effect for the new session test
    mock_tmux.list_windows.side_effect = [
        [],  # First call - check for conflicts (new session, empty)
        [{"index": "0", "name": "Claude-new-agent"}],  # Second call - after creation
    ]

    with patch("time.sleep"):
        result = runner.invoke(agent, ["spawn", "new-agent", "newsession:0"], obj={"tmux": mock_tmux})

    assert result.exit_code == 0
    mock_tmux.create_session.assert_called_once_with("newsession")

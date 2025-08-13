"""Tests for get_session_status MCP tool."""

import pytest

from tmux_orchestrator.server.tools.get_session_status import (
    AgentStatusRequest,
    AgentStatusResult,
    SessionStatusResult,
    get_agent_status,
    get_session_status,
)


def test_get_session_status_success(mock_tmux) -> None:
    """Test successful session status retrieval."""
    mock_sessions = [
        {"name": "project1", "attached": "0", "windows": "3", "created": "2024-01-01"},
        {"name": "project2", "attached": "1", "windows": "2", "created": "2024-01-02"},
    ]
    mock_agents = [
        {"session": "project1", "window": "0", "type": "pm", "status": "Active"},
        {"session": "project1", "window": "1", "type": "developer", "status": "Active"},
        {"session": "project2", "window": "0", "type": "pm", "status": "Idle"},
    ]

    mock_tmux.list_sessions.return_value = mock_sessions
    mock_tmux.list_agents.return_value = mock_agents

    result = get_session_status(mock_tmux)

    assert isinstance(result, SessionStatusResult)
    assert result.total_sessions == 2
    assert result.total_agents == 3
    assert result.active_agents == 2
    assert result.idle_agents == 1
    assert result.sessions == mock_sessions
    assert result.agents == mock_agents


def test_get_session_status_empty(mock_tmux) -> None:
    """Test session status with no sessions or agents."""
    mock_tmux.list_sessions.return_value = []
    mock_tmux.list_agents.return_value = []

    result = get_session_status(mock_tmux)

    assert result.total_sessions == 0
    assert result.total_agents == 0
    assert result.active_agents == 0
    assert result.idle_agents == 0
    assert result.sessions == []
    assert result.agents == []


def test_get_session_status_with_mixed_agent_statuses(mock_tmux) -> None:
    """Test session status with various agent statuses."""
    mock_agents = [
        {"session": "proj", "window": "0", "type": "pm", "status": "Active"},
        {"session": "proj", "window": "1", "type": "dev1", "status": "Active"},
        {"session": "proj", "window": "2", "type": "dev2", "status": "Idle"},
        {"session": "proj", "window": "3", "type": "qa", "status": "Idle"},
        {"session": "proj", "window": "4", "type": "devops", "status": "Active"},
    ]

    mock_tmux.list_sessions.return_value = [{"name": "proj", "attached": "0", "windows": "5", "created": "2024-01-01"}]
    mock_tmux.list_agents.return_value = mock_agents

    result = get_session_status(mock_tmux)

    assert result.total_agents == 5
    assert result.active_agents == 3  # pm, dev1, devops
    assert result.idle_agents == 2  # dev2, qa


def test_get_session_status_tmux_failure(mock_tmux) -> None:
    """Test session status when tmux operations fail."""
    mock_tmux.list_sessions.side_effect = Exception("TMUX not running")

    with pytest.raises(RuntimeError, match="Failed to retrieve session status"):
        get_session_status(mock_tmux)


def test_get_session_status_agents_failure(mock_tmux) -> None:
    """Test session status when agent listing fails."""
    mock_tmux.list_sessions.return_value = [{"name": "test", "attached": "0", "windows": "1", "created": "2024-01-01"}]
    mock_tmux.list_agents.side_effect = Exception("Agent listing failed")

    with pytest.raises(RuntimeError, match="Failed to retrieve session status"):
        get_session_status(mock_tmux)


def test_get_agent_status_success(mock_tmux) -> None:
    """Test successful agent status retrieval."""
    request = AgentStatusRequest(session="myproject", window="Claude-PM", lines=50)
    mock_output = "Human: Please work on the login feature\nAssistant: I'll help you implement the login feature.\nLet me analyze the current code..."

    mock_tmux.has_session.return_value = True
    mock_tmux.capture_pane.return_value = mock_output
    mock_tmux._is_idle.return_value = False

    result = get_agent_status(mock_tmux, request)

    assert isinstance(result, AgentStatusResult)
    assert result.session == "myproject"
    assert result.window == "Claude-PM"
    assert result.target == "myproject:Claude-PM"
    assert result.status == "active"
    assert len(result.recent_output) > 0
    assert result.error_message == ""

    # Verify tmux methods were called correctly
    mock_tmux.has_session.assert_called_once_with("myproject")
    mock_tmux.capture_pane.assert_called_once_with("myproject:Claude-PM", lines=50)


def test_get_agent_status_idle_agent(mock_tmux) -> None:
    """Test agent status for idle agent."""
    request = AgentStatusRequest(session="project", window="Claude-Dev")
    mock_output = "Human: \nWaiting for your next instruction..."

    mock_tmux.has_session.return_value = True
    mock_tmux.capture_pane.return_value = mock_output
    mock_tmux._is_idle.return_value = True

    result = get_agent_status(mock_tmux, request)

    assert result.status == "idle"
    assert result.target == "project:Claude-Dev"


def test_get_agent_status_empty_session_name(mock_tmux) -> None:
    """Test agent status with empty session name."""
    request = AgentStatusRequest(session="", window="test")

    result = get_agent_status(mock_tmux, request)

    assert result.status == "error"
    assert "Session name cannot be empty" in result.error_message
    assert result.target == ""
    # Should not call tmux methods
    mock_tmux.has_session.assert_not_called()


def test_get_agent_status_empty_window_name(mock_tmux) -> None:
    """Test agent status with empty window name."""
    request = AgentStatusRequest(session="test", window="")

    result = get_agent_status(mock_tmux, request)

    assert result.status == "error"
    assert "Window name cannot be empty" in result.error_message
    assert result.target == ""


def test_get_agent_status_whitespace_names(mock_tmux) -> None:
    """Test agent status with whitespace-only names."""
    request = AgentStatusRequest(session="  ", window="\t\n")

    result = get_agent_status(mock_tmux, request)

    assert result.status == "error"
    assert "Session name cannot be empty" in result.error_message


def test_get_agent_status_session_not_found(mock_tmux) -> None:
    """Test agent status when session doesn't exist."""
    request = AgentStatusRequest(session="nonexistent", window="test")

    mock_tmux.has_session.return_value = False

    result = get_agent_status(mock_tmux, request)

    assert result.status == "not_found"
    assert result.target == "nonexistent:test"
    assert "Session 'nonexistent' not found" in result.error_message
    assert result.recent_output == []


def test_get_agent_status_capture_failure(mock_tmux) -> None:
    """Test agent status when pane capture fails."""
    request = AgentStatusRequest(session="project", window="broken")

    mock_tmux.has_session.return_value = True
    mock_tmux.capture_pane.side_effect = Exception("Pane not accessible")

    result = get_agent_status(mock_tmux, request)

    assert result.status == "error"
    assert "Error retrieving agent status: Pane not accessible" in result.error_message
    assert result.target == "project:broken"
    assert result.recent_output == []


def test_get_agent_status_with_custom_lines(mock_tmux) -> None:
    """Test agent status with custom line count."""
    request = AgentStatusRequest(session="test", window="agent", lines=200)
    mock_output = "\n".join([f"Line {i}" for i in range(1, 51)])  # 50 lines

    mock_tmux.has_session.return_value = True
    mock_tmux.capture_pane.return_value = mock_output
    mock_tmux._is_idle.return_value = True

    result = get_agent_status(mock_tmux, request)

    assert result.output_length == 50  # 50 lines after splitting
    # The output is split into lines, recent_output gets last 10 lines
    assert len(result.recent_output) == 10  # Last 10 lines
    assert "Line 50" in result.recent_output[-1]

    # Verify custom line count was passed
    mock_tmux.capture_pane.assert_called_once_with("test:agent", lines=200)


def test_get_agent_status_empty_output(mock_tmux) -> None:
    """Test agent status with empty pane output."""
    request = AgentStatusRequest(session="empty", window="agent")

    mock_tmux.has_session.return_value = True
    mock_tmux.capture_pane.return_value = ""
    mock_tmux._is_idle.return_value = True

    result = get_agent_status(mock_tmux, request)

    assert result.status == "idle"
    assert result.recent_output == []
    assert result.output_length == 0


def test_agent_status_request_defaults() -> None:
    """Test AgentStatusRequest default values."""
    request = AgentStatusRequest(session="test", window="agent")

    assert request.session == "test"
    assert request.window == "agent"
    assert request.lines == 100  # Default value


def test_agent_status_result_dataclass() -> None:
    """Test AgentStatusResult dataclass structure."""
    result = AgentStatusResult(
        session="test",
        window="agent",
        target="test:agent",
        status="active",
        recent_output=["line1", "line2"],
        output_length=2,
        error_message="",
    )

    assert result.session == "test"
    assert result.window == "agent"
    assert result.target == "test:agent"
    assert result.status == "active"
    assert result.recent_output == ["line1", "line2"]
    assert result.output_length == 2
    assert result.error_message == ""


def test_session_status_result_dataclass() -> None:
    """Test SessionStatusResult dataclass structure."""
    sessions = [{"name": "test", "attached": "0", "windows": "1", "created": "2024-01-01"}]
    agents = [{"session": "test", "window": "0", "type": "pm", "status": "Active"}]

    result = SessionStatusResult(
        total_sessions=1, total_agents=1, active_agents=1, idle_agents=0, sessions=sessions, agents=agents
    )

    assert result.total_sessions == 1
    assert result.total_agents == 1
    assert result.active_agents == 1
    assert result.idle_agents == 0
    assert result.sessions == sessions
    assert result.agents == agents

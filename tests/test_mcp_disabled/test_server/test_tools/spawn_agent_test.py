"""Tests for spawn_agent business logic."""

from unittest.mock import Mock

import pytest

from tmux_orchestrator.server.tools.spawn_agent import SpawnAgentRequest, spawn_agent
from tmux_orchestrator.utils.tmux import TMUXManager


@pytest.mark.asyncio
async def test_spawn_agent_empty_session_name() -> None:
    """Test spawn_agent with empty session name returns error."""
    tmux = Mock(spec=TMUXManager)
    request = SpawnAgentRequest(session_name="", agent_type="developer")

    result = await spawn_agent(tmux, request)

    assert not result.success
    assert result.error_message is not None
    assert "Session name cannot be empty" in result.error_message
    assert result.session == ""
    assert result.window == ""
    assert result.target == ""


@pytest.mark.asyncio
async def test_spawn_agent_invalid_agent_type() -> None:
    """Test spawn_agent with invalid agent type returns error."""
    tmux = Mock(spec=TMUXManager)
    request = SpawnAgentRequest(session_name="test-session", agent_type="invalid-type")

    result = await spawn_agent(tmux, request)

    assert not result.success
    assert result.error_message is not None
    assert "Invalid agent type" in result.error_message
    assert "developer, pm, qa, devops, reviewer, researcher, docs" in result.error_message


@pytest.mark.asyncio
async def test_spawn_agent_new_session_success() -> None:
    """Test successful agent spawn in new session."""
    tmux = Mock(spec=TMUXManager)
    tmux.has_session.return_value = False
    tmux.create_session.return_value = True
    tmux.send_keys.return_value = True

    request = SpawnAgentRequest(
        session_name="test-session",
        agent_type="developer",
        project_path="/test/path",
    )

    result = await spawn_agent(tmux, request)

    assert result.success
    assert result.session == "test-session"
    assert result.window == "Claude-developer"
    assert result.target == "test-session:Claude-developer"
    assert result.error_message is None

    # Verify tmux calls
    tmux.has_session.assert_called_once_with("test-session")
    tmux.create_session.assert_called_once_with("test-session", "Claude-developer", "/test/path")
    assert tmux.send_keys.call_count == 2  # Claude command + Enter


@pytest.mark.asyncio
async def test_spawn_agent_existing_session_success() -> None:
    """Test successful agent spawn in existing session."""
    tmux = Mock(spec=TMUXManager)
    tmux.has_session.return_value = True
    tmux.create_window.return_value = True
    tmux.send_keys.return_value = True

    request = SpawnAgentRequest(session_name="existing-session", agent_type="pm")

    result = await spawn_agent(tmux, request)

    assert result.success
    assert result.session == "existing-session"
    assert result.window == "Claude-pm"
    assert result.target == "existing-session:Claude-pm"

    # Verify correct method called for existing session
    tmux.create_window.assert_called_once_with("existing-session", "Claude-pm", None)


@pytest.mark.asyncio
async def test_spawn_agent_session_creation_fails() -> None:
    """Test agent spawn fails when session creation fails."""
    tmux = Mock(spec=TMUXManager)
    tmux.has_session.return_value = False
    tmux.create_session.return_value = False

    request = SpawnAgentRequest(session_name="test-session", agent_type="developer")

    result = await spawn_agent(tmux, request)

    assert not result.success
    assert result.error_message is not None
    assert "Failed to create new session" in result.error_message


@pytest.mark.asyncio
async def test_spawn_agent_window_creation_fails() -> None:
    """Test agent spawn fails when window creation fails."""
    tmux = Mock(spec=TMUXManager)
    tmux.has_session.return_value = True
    tmux.create_window.return_value = False

    request = SpawnAgentRequest(session_name="existing-session", agent_type="qa")

    result = await spawn_agent(tmux, request)

    assert not result.success
    assert result.error_message is not None
    assert "Failed to create window in existing session" in result.error_message


@pytest.mark.asyncio
async def test_spawn_agent_send_keys_fails() -> None:
    """Test agent spawn fails when sending keys fails."""
    tmux = Mock(spec=TMUXManager)
    tmux.has_session.return_value = False
    tmux.create_session.return_value = True
    tmux.send_keys.return_value = False  # First send_keys call fails

    request = SpawnAgentRequest(session_name="test-session", agent_type="developer")

    result = await spawn_agent(tmux, request)

    assert not result.success
    assert result.error_message is not None
    assert "Failed to start Claude command" in result.error_message
    assert result.target == "test-session:Claude-developer"


@pytest.mark.asyncio
async def test_spawn_agent_exception_handling() -> None:
    """Test agent spawn handles unexpected exceptions."""
    tmux = Mock(spec=TMUXManager)
    tmux.has_session.side_effect = Exception("Unexpected error")

    request = SpawnAgentRequest(session_name="test-session", agent_type="developer")

    result = await spawn_agent(tmux, request)

    assert not result.success
    assert result.error_message is not None
    assert "Unexpected error during agent spawn" in result.error_message
    assert "Unexpected error" in result.error_message


@pytest.mark.parametrize(
    "agent_type",
    ["developer", "pm", "qa", "devops", "reviewer", "researcher", "docs"],
)
@pytest.mark.asyncio
async def test_spawn_agent_all_valid_types(agent_type: str) -> None:
    """Test spawn_agent accepts all valid agent types."""
    tmux = Mock(spec=TMUXManager)
    tmux.has_session.return_value = False
    tmux.create_session.return_value = True
    tmux.send_keys.return_value = True

    request = SpawnAgentRequest(session_name="test-session", agent_type=agent_type)

    result = await spawn_agent(tmux, request)

    assert result.success
    assert result.window == f"Claude-{agent_type}"

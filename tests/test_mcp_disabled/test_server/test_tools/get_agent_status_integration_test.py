"""Integration tests for get_agent_status - team checks, error handling, and complex scenarios."""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from tmux_orchestrator.server.tools.get_agent_status import (
    AgentStatusRequest,
    HealthStatus,
    get_agent_status,
)
from tmux_orchestrator.server.tools.report_activity import ActivityType


@pytest.fixture
def sample_activity_data():
    """Create sample activity records for testing."""
    base_time = datetime.now()
    return [
        {
            "record_id": "rec-001",
            "agent_id": "frontend-project:0",
            "activity_type": "working",
            "description": "Implementing user dashboard",
            "timestamp": (base_time - timedelta(minutes=5)).isoformat(),
            "session_id": "frontend-project",
            "team_id": "team-alpha",
            "tags": ["ui", "feature"],
            "metadata": {"priority": "high"},
        },
        {
            "record_id": "rec-002",
            "agent_id": "backend-project:1",
            "activity_type": "idle",
            "description": "Waiting for next task",
            "timestamp": (base_time - timedelta(minutes=30)).isoformat(),
            "session_id": "backend-project",
            "team_id": "team-alpha",
            "tags": [],
            "metadata": {},
        },
        {
            "record_id": "rec-003",
            "agent_id": "team-alpha:2",
            "activity_type": "blocked",
            "description": "Waiting for API approval",
            "timestamp": (base_time - timedelta(hours=2)).isoformat(),
            "session_id": "team-alpha",
            "team_id": "team-alpha",
            "tags": ["blocked", "api"],
            "metadata": {},
        },
    ]


def test_get_agent_status_single_agent_by_id_success(mock_tmux, temp_activity_file, sample_activity_data) -> None:
    """Test get_agent_status for single agent by ID."""
    # Setup activity file with sample data
    with open(temp_activity_file, "w") as f:
        json.dump(sample_activity_data, f)

    request = AgentStatusRequest(agent_id="frontend-project:0")

    with patch(
        "tmux_orchestrator.server.tools.get_agent_status._get_activity_file_path", return_value=temp_activity_file
    ):
        result = get_agent_status(mock_tmux, request)

    assert result.success
    assert len(result.agent_metrics) == 1

    metrics = result.agent_metrics[0]
    assert metrics.agent_id == "frontend-project:0"
    assert metrics.health_status == HealthStatus.HEALTHY
    assert metrics.last_activity_type == ActivityType.WORKING
    assert metrics.last_activity_description == "Implementing user dashboard"
    assert metrics.session_active is True
    assert metrics.session_info is not None and metrics.session_info["status"] == "Active"


def test_get_agent_status_single_agent_by_target_success(mock_tmux, temp_activity_file, sample_activity_data) -> None:
    """Test get_agent_status for single agent by target."""
    # Setup activity file with sample data
    with open(temp_activity_file, "w") as f:
        json.dump(sample_activity_data, f)

    request = AgentStatusRequest(target="backend-project:1")

    with patch(
        "tmux_orchestrator.server.tools.get_agent_status._get_activity_file_path", return_value=temp_activity_file
    ):
        result = get_agent_status(mock_tmux, request)

    assert result.success
    assert len(result.agent_metrics) == 1

    metrics = result.agent_metrics[0]
    assert metrics.agent_id == "backend-project:1"
    assert metrics.health_status == HealthStatus.IDLE
    assert metrics.last_activity_type == ActivityType.IDLE
    assert metrics.session_info is not None and metrics.session_info["status"] == "Idle"


def test_get_agent_status_agent_not_found(mock_tmux, temp_activity_file) -> None:
    """Test get_agent_status when agent not found."""
    request = AgentStatusRequest(agent_id="nonexistent:0")

    with patch(
        "tmux_orchestrator.server.tools.get_agent_status._get_activity_file_path", return_value=temp_activity_file
    ):
        result = get_agent_status(mock_tmux, request)

    assert result.success is False
    assert result.error_message is not None and "Agent 'nonexistent:0' not found" in result.error_message


def test_get_agent_status_offline_agent(mock_tmux, temp_activity_file, sample_activity_data) -> None:
    """Test get_agent_status for offline agent (not in tmux but has activity)."""
    # Setup activity file with sample data
    with open(temp_activity_file, "w") as f:
        json.dump(sample_activity_data, f)

    # Mock list_agents to exclude frontend-project (simulate offline)
    mock_tmux.list_agents.return_value = [
        {
            "session": "backend-project",
            "window": "1",
            "type": "Backend",
            "status": "Idle",
        },
    ]

    request = AgentStatusRequest(agent_id="frontend-project:0")

    with patch(
        "tmux_orchestrator.server.tools.get_agent_status._get_activity_file_path", return_value=temp_activity_file
    ):
        result = get_agent_status(mock_tmux, request)

    assert result.success
    assert len(result.agent_metrics) == 1

    metrics = result.agent_metrics[0]
    assert metrics.agent_id == "frontend-project:0"
    assert metrics.health_status == HealthStatus.OFFLINE
    assert metrics.session_active is False
    # Should still have activity data
    assert metrics.last_activity_type == ActivityType.WORKING


def test_get_agent_status_team_health_check(mock_tmux, temp_activity_file, sample_activity_data) -> None:
    """Test get_agent_status for team health check."""
    # Setup activity file with sample data
    with open(temp_activity_file, "w") as f:
        json.dump(sample_activity_data, f)

    request = AgentStatusRequest(team_id="team-alpha")

    with patch(
        "tmux_orchestrator.server.tools.get_agent_status._get_activity_file_path", return_value=temp_activity_file
    ):
        result = get_agent_status(mock_tmux, request)

    assert result.success
    assert len(result.agent_metrics) == 3  # All agents in team-alpha
    assert result.total_agents == 3

    # Check that we got all team members
    agent_ids = {metrics.agent_id for metrics in result.agent_metrics}
    expected_ids = {"frontend-project:0", "backend-project:1", "team-alpha:2"}
    assert agent_ids == expected_ids

    # Verify health statuses are correct
    health_statuses = {metrics.agent_id: metrics.health_status for metrics in result.agent_metrics}
    assert health_statuses["frontend-project:0"] == HealthStatus.HEALTHY
    assert health_statuses["backend-project:1"] == HealthStatus.IDLE
    assert health_statuses["team-alpha:2"] == HealthStatus.BLOCKED


def test_get_agent_status_file_permission_error(mock_tmux, temp_activity_file) -> None:
    """Test get_agent_status handles file permission errors."""
    request = AgentStatusRequest(agent_id="test:0")

    with patch(
        "tmux_orchestrator.server.tools.get_agent_status._get_activity_file_path", return_value=temp_activity_file
    ):
        with patch("builtins.open", side_effect=PermissionError("Access denied")):
            result = get_agent_status(mock_tmux, request)

    assert result.success is False
    assert result.error_message is not None and "Permission denied" in result.error_message


def test_get_agent_status_json_decode_error(mock_tmux, temp_activity_file) -> None:
    """Test get_agent_status handles JSON decode errors."""
    # Write invalid JSON to file
    with open(temp_activity_file, "w") as f:
        f.write("invalid json content")

    request = AgentStatusRequest(agent_id="test:0")

    with patch(
        "tmux_orchestrator.server.tools.get_agent_status._get_activity_file_path", return_value=temp_activity_file
    ):
        result = get_agent_status(mock_tmux, request)

    assert result.success is False
    assert result.error_message is not None and (
        "Invalid JSON" in result.error_message or "JSON" in result.error_message
    )


def test_get_agent_status_unexpected_error(mock_tmux, temp_activity_file) -> None:
    """Test get_agent_status handles unexpected errors."""
    request = AgentStatusRequest(agent_id="test:0")

    with patch(
        "tmux_orchestrator.server.tools.get_agent_status._get_activity_file_path", return_value=temp_activity_file
    ):
        with patch(
            "tmux_orchestrator.server.tools.get_agent_status._load_activities",
            side_effect=RuntimeError("Unexpected error"),
        ):
            result = get_agent_status(mock_tmux, request)

    assert result.success is False
    assert result.error_message is not None and "Unexpected error" in result.error_message


def test_get_agent_status_activity_file_not_exist(mock_tmux) -> None:
    """Test get_agent_status when activity file doesn't exist."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_file = Path(temp_dir) / "nonexistent.json"

        request = AgentStatusRequest(agent_id="test:0")

        with patch("tmux_orchestrator.server.tools.get_agent_status._get_activity_file_path", return_value=temp_file):
            result = get_agent_status(mock_tmux, request)

        # Should fail when agent not found and no activity
        assert result.success is False
        assert result.error_message is not None and "Agent 'test:0' not found" in result.error_message


def test_get_agent_status_mixed_health_states_team(mock_tmux, temp_activity_file) -> None:
    """Test team health check with mixed health states."""
    # Create diverse activity data
    mixed_activities = [
        {
            "record_id": "rec-001",
            "agent_id": "healthy-agent:0",
            "activity_type": "working",
            "description": "Active and productive",
            "timestamp": datetime.now().isoformat(),
            "session_id": "healthy-agent",
            "team_id": "team-beta",
            "tags": [],
            "metadata": {},
        },
        {
            "record_id": "rec-002",
            "agent_id": "stale-agent:1",
            "activity_type": "working",
            "description": "Old activity",
            "timestamp": (datetime.now() - timedelta(hours=8)).isoformat(),
            "session_id": "stale-agent",
            "team_id": "team-beta",
            "tags": [],
            "metadata": {},
        },
        {
            "record_id": "rec-003",
            "agent_id": "blocked-agent:2",
            "activity_type": "blocked",
            "description": "Stuck on dependency",
            "timestamp": (datetime.now() - timedelta(minutes=30)).isoformat(),
            "session_id": "blocked-agent",
            "team_id": "team-beta",
            "tags": ["blocked"],
            "metadata": {},
        },
    ]

    with open(temp_activity_file, "w") as f:
        json.dump(mixed_activities, f)

    # Mock varied tmux statuses
    mock_tmux.list_agents.return_value = [
        {"session": "healthy-agent", "window": "0", "type": "Dev", "status": "Active"},
        {"session": "stale-agent", "window": "1", "type": "Dev", "status": "Active"},
        {"session": "blocked-agent", "window": "2", "type": "Dev", "status": "Active"},
    ]

    request = AgentStatusRequest(team_id="team-beta")

    with patch(
        "tmux_orchestrator.server.tools.get_agent_status._get_activity_file_path", return_value=temp_activity_file
    ):
        result = get_agent_status(mock_tmux, request)

    assert result.success
    assert len(result.agent_metrics) == 3

    # Verify different health states
    health_map = {m.agent_id: m.health_status for m in result.agent_metrics}
    assert health_map["healthy-agent:0"] == HealthStatus.HEALTHY
    assert health_map["stale-agent:1"] == HealthStatus.UNRESPONSIVE
    assert health_map["blocked-agent:2"] == HealthStatus.BLOCKED


def test_get_agent_status_empty_team(mock_tmux, temp_activity_file) -> None:
    """Test team health check with no team members."""
    request = AgentStatusRequest(team_id="empty-team")

    with patch(
        "tmux_orchestrator.server.tools.get_agent_status._get_activity_file_path", return_value=temp_activity_file
    ):
        result = get_agent_status(mock_tmux, request)

    assert result.success
    assert len(result.agent_metrics) == 0
    assert result.total_agents == 0

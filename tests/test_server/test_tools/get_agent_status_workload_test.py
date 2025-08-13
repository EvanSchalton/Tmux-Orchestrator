"""Workload and performance tests for get_agent_status."""

import json
from datetime import datetime, timedelta
from unittest.mock import patch

from tmux_orchestrator.server.tools.get_agent_status import (
    AgentStatusRequest,
    HealthStatus,
    get_agent_status,
)
from tmux_orchestrator.server.tools.report_activity import ActivityType


def test_get_agent_status_include_activity_history(mock_tmux, temp_activity_file) -> None:
    """Test get_agent_status with activity history included."""
    # Create multiple activity records for same agent
    base_time = datetime.now()
    activity_records = []

    for i in range(5):
        record = {
            "record_id": f"rec-{i:03d}",
            "agent_id": "busy-agent:0",
            "activity_type": "working",
            "description": f"Task {i + 1}",
            "timestamp": (base_time - timedelta(minutes=i * 10)).isoformat(),
            "session_id": "busy-project",
            "team_id": "team-alpha",
            "tags": [f"task-{i + 1}"],
            "metadata": {},
        }
        activity_records.append(record)

    with open(temp_activity_file, "w") as f:
        json.dump(activity_records, f)

    request = AgentStatusRequest(agent_id="busy-agent:0", include_activity_history=True, activity_limit=3)

    with patch(
        "tmux_orchestrator.server.tools.get_agent_status._get_activity_file_path", return_value=temp_activity_file
    ):
        result = get_agent_status(mock_tmux, request)

    assert result.success
    assert len(result.agent_metrics) == 1

    metrics = result.agent_metrics[0]
    assert hasattr(metrics, "activity_history")
    # Should have limited to 3 records as requested
    assert len(metrics.activity_history) == 3


def test_get_agent_status_responsiveness_score_calculation(mock_tmux, temp_activity_file) -> None:
    """Test responsiveness score calculation based on activity frequency."""
    # Create recent activity records (high responsiveness)
    base_time = datetime.now()
    recent_activities = []

    # 10 activities in last hour (high responsiveness)
    for i in range(10):
        record = {
            "record_id": f"rec-{i:03d}",
            "agent_id": "responsive-agent:0",
            "activity_type": "working",
            "description": f"Task {i + 1}",
            "timestamp": (base_time - timedelta(minutes=i * 5)).isoformat(),
            "session_id": "active-project",
            "team_id": "team-alpha",
            "tags": [],
            "metadata": {},
        }
        recent_activities.append(record)

    with open(temp_activity_file, "w") as f:
        json.dump(recent_activities, f)

    request = AgentStatusRequest(agent_id="responsive-agent:0")

    with patch(
        "tmux_orchestrator.server.tools.get_agent_status._get_activity_file_path", return_value=temp_activity_file
    ):
        result = get_agent_status(mock_tmux, request)

    assert result.success
    metrics = result.agent_metrics[0]
    # Should have a high responsiveness score due to frequent activity
    assert metrics.responsiveness_score is not None
    assert metrics.responsiveness_score > 0.7  # High responsiveness


def test_get_agent_status_unresponsive_agent(mock_tmux, temp_activity_file) -> None:
    """Test get_agent_status identifies unresponsive agents."""
    # Create activity data with old timestamp
    old_activity = [
        {
            "record_id": "rec-001",
            "agent_id": "stale-agent:0",
            "activity_type": "working",
            "description": "Last seen hours ago",
            "timestamp": (datetime.now() - timedelta(hours=6)).isoformat(),
            "session_id": "stale-agent",
            "team_id": "team-alpha",
            "tags": [],
            "metadata": {},
        }
    ]

    with open(temp_activity_file, "w") as f:
        json.dump(old_activity, f)

    # Mock list_agents to show agent as active in tmux
    mock_tmux.list_agents.return_value = [
        {
            "session": "stale-agent",
            "window": "0",
            "type": "Developer",
            "status": "Active",
        }
    ]

    request = AgentStatusRequest(agent_id="stale-agent:0")

    with patch(
        "tmux_orchestrator.server.tools.get_agent_status._get_activity_file_path", return_value=temp_activity_file
    ):
        result = get_agent_status(mock_tmux, request)

    assert result.success
    assert len(result.agent_metrics) == 1

    metrics = result.agent_metrics[0]
    assert metrics.agent_id == "stale-agent:0"
    assert metrics.health_status == HealthStatus.UNRESPONSIVE
    assert metrics.session_active is True


def test_get_agent_status_blocked_agent_from_activity(mock_tmux, temp_activity_file) -> None:
    """Test get_agent_status correctly identifies blocked agents from activity."""
    sample_activity_data = [
        {
            "record_id": "rec-003",
            "agent_id": "team-alpha:2",
            "activity_type": "blocked",
            "description": "Waiting for API approval",
            "timestamp": (datetime.now() - timedelta(hours=2)).isoformat(),
            "session_id": "team-alpha",
            "team_id": "team-alpha",
            "tags": ["blocked", "api"],
            "metadata": {},
        }
    ]

    # Setup activity file with sample data
    with open(temp_activity_file, "w") as f:
        json.dump(sample_activity_data, f)

    request = AgentStatusRequest(agent_id="team-alpha:2")

    with patch(
        "tmux_orchestrator.server.tools.get_agent_status._get_activity_file_path", return_value=temp_activity_file
    ):
        result = get_agent_status(mock_tmux, request)

    assert result.success
    assert len(result.agent_metrics) == 1

    metrics = result.agent_metrics[0]
    assert metrics.agent_id == "team-alpha:2"
    assert metrics.health_status == HealthStatus.BLOCKED
    assert metrics.last_activity_type == ActivityType.BLOCKED
    assert metrics.last_activity_description == "Waiting for API approval"
    assert "blocked" in metrics.activity_tags
    assert "api" in metrics.activity_tags


def test_get_agent_status_degraded_health_from_tmux_status(mock_tmux, temp_activity_file) -> None:
    """Test agent health marked as degraded based on tmux status."""
    sample_activity_data = [
        {
            "record_id": "rec-001",
            "agent_id": "frontend-project:0",
            "activity_type": "working",
            "description": "Implementing user dashboard",
            "timestamp": datetime.now().isoformat(),
            "session_id": "frontend-project",
            "team_id": "team-alpha",
            "tags": ["ui", "feature"],
            "metadata": {"priority": "high"},
        }
    ]

    # Setup activity file with sample data
    with open(temp_activity_file, "w") as f:
        json.dump(sample_activity_data, f)

    # Mock list_agents to show agent with concerning status
    mock_tmux.list_agents.return_value = [
        {
            "session": "frontend-project",
            "window": "0",
            "type": "Frontend",
            "status": "Degraded",  # Custom status indicating issues
        }
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
    # Should be degraded based on tmux status despite recent activity
    assert metrics.health_status == HealthStatus.DEGRADED

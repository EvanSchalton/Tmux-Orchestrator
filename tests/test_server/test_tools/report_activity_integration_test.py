"""Integration tests for report_activity - complex workflows and multi-agent scenarios."""

import json
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import patch

from tmux_orchestrator.server.tools.report_activity import (
    ActivityHistoryRequest,
    ActivityType,
    ReportActivityRequest,
    get_activity_history,
    report_activity,
)


def test_report_activity_success_minimal(mock_tmux, temp_activity_file) -> None:
    """Test successful activity reporting with minimal fields."""
    request = ReportActivityRequest(
        agent_id="dev-agent", activity_type=ActivityType.WORKING, description="Implementing authentication module"
    )

    with patch(
        "tmux_orchestrator.server.tools.report_activity._get_activity_file_path", return_value=temp_activity_file
    ):
        result = report_activity(mock_tmux, request)

    assert result.success
    assert result.agent_id == "dev-agent"
    assert result.activity_type == ActivityType.WORKING
    assert result.description == "Implementing authentication module"
    assert result.record_id is not None
    assert result.timestamp is not None
    assert result.error_message is None

    # Verify the activity was saved to file
    with open(temp_activity_file) as f:
        records = json.load(f)
    assert len(records) == 1
    assert records[0]["agent_id"] == "dev-agent"
    assert records[0]["activity_type"] == "working"
    assert records[0]["description"] == "Implementing authentication module"


def test_report_activity_success_full_fields(mock_tmux, temp_activity_file) -> None:
    """Test successful activity reporting with all fields."""
    request = ReportActivityRequest(
        agent_id="pm-agent",
        activity_type=ActivityType.BLOCKED,
        description="Waiting for external API approval",
        session_id="session-pm-001",
        team_id="team-backend",
        tags=["api", "blocked", "external"],
        metadata={"priority": "high", "issue": "API-456", "estimated_hours": 8},
    )

    with patch(
        "tmux_orchestrator.server.tools.report_activity._get_activity_file_path", return_value=temp_activity_file
    ):
        result = report_activity(mock_tmux, request)

    assert result.success
    assert result.session_id == "session-pm-001"
    assert result.team_id == "team-backend"
    assert result.tags == ["api", "blocked", "external"]
    assert result.metadata == {"priority": "high", "issue": "API-456", "estimated_hours": 8}

    # Verify record was saved with all fields
    with open(temp_activity_file) as f:
        records = json.load(f)
    assert len(records) == 1
    record = records[0]
    assert record["session_id"] == "session-pm-001"
    assert record["team_id"] == "team-backend"
    assert record["tags"] == ["api", "blocked", "external"]
    assert record["metadata"] == {"priority": "high", "issue": "API-456", "estimated_hours": 8}


def test_report_activity_all_activity_types(mock_tmux, temp_activity_file) -> None:
    """Test reporting all different activity types."""
    activities = [
        (ActivityType.WORKING, "Coding new feature"),
        (ActivityType.IDLE, "Taking lunch break"),
        (ActivityType.BLOCKED, "Waiting for code review"),
        (ActivityType.COMPLETED, "Feature implementation done"),
    ]

    with patch(
        "tmux_orchestrator.server.tools.report_activity._get_activity_file_path", return_value=temp_activity_file
    ):
        for activity_type, description in activities:
            request = ReportActivityRequest(agent_id="test-agent", activity_type=activity_type, description=description)
            result = report_activity(mock_tmux, request)
            assert result.success
            assert result.activity_type == activity_type

    # Verify all activities were saved
    with open(temp_activity_file) as f:
        records = json.load(f)
    assert len(records) == 4

    # Check each activity type was saved correctly
    saved_types = [record["activity_type"] for record in records]
    expected_types = [at.value for at, _ in activities]
    assert saved_types == expected_types


def test_report_activity_multiple_agents(mock_tmux, temp_activity_file) -> None:
    """Test reporting activities for multiple agents."""
    agents = ["dev-agent", "qa-agent", "pm-agent", "devops-agent"]

    with patch(
        "tmux_orchestrator.server.tools.report_activity._get_activity_file_path", return_value=temp_activity_file
    ):
        record_ids = []
        for i, agent in enumerate(agents):
            request = ReportActivityRequest(
                agent_id=agent, activity_type=ActivityType.WORKING, description=f"Working on task {i + 1}"
            )
            result = report_activity(mock_tmux, request)
            assert result.success
            record_ids.append(result.record_id)

    # Verify all record IDs are unique
    assert len(set(record_ids)) == 4

    # Verify all activities were saved
    with open(temp_activity_file) as f:
        records = json.load(f)
    assert len(records) == 4

    # Verify each agent has their activity
    saved_agents = {record["agent_id"] for record in records}
    assert saved_agents == set(agents)


def test_get_activity_history_all_records(mock_tmux, temp_activity_file) -> None:
    """Test getting all activity records without filters."""
    # Populate file with test data
    test_records = []
    base_time = datetime.now()

    for i in range(5):
        record: dict[str, Any] = {
            "record_id": f"record-{i}",
            "agent_id": f"agent-{i}",
            "activity_type": "working",
            "description": f"Task {i}",
            "timestamp": (base_time + timedelta(minutes=i)).isoformat(),
            "session_id": None,
            "team_id": None,
            "tags": [],
            "metadata": {},
        }
        test_records.append(record)

    with open(temp_activity_file, "w") as f:
        json.dump(test_records, f)

    request = ActivityHistoryRequest()

    with patch(
        "tmux_orchestrator.server.tools.report_activity._get_activity_file_path", return_value=temp_activity_file
    ):
        result = get_activity_history(mock_tmux, request)

    assert result.success
    assert len(result.records) == 5
    assert result.total_records == 5

    # Records should be sorted by timestamp descending (most recent first)
    timestamps = [record.timestamp for record in result.records if record.timestamp is not None]
    assert timestamps == sorted(timestamps, reverse=True)


def test_get_activity_history_agent_filter(mock_tmux, temp_activity_file) -> None:
    """Test filtering by agent_id."""
    # Create records for multiple agents
    test_records = []
    base_time = datetime.now()

    agents = ["agent-1", "agent-2", "agent-1", "agent-3", "agent-1"]
    for i, agent in enumerate(agents):
        record: dict[str, Any] = {
            "record_id": f"record-{i}",
            "agent_id": agent,
            "activity_type": "working",
            "description": f"Task {i}",
            "timestamp": (base_time + timedelta(minutes=i)).isoformat(),
            "session_id": None,
            "team_id": None,
            "tags": [],
            "metadata": {},
        }
        test_records.append(record)

    with open(temp_activity_file, "w") as f:
        json.dump(test_records, f)

    request = ActivityHistoryRequest(agent_id="agent-1")

    with patch(
        "tmux_orchestrator.server.tools.report_activity._get_activity_file_path", return_value=temp_activity_file
    ):
        result = get_activity_history(mock_tmux, request)

    assert result.success
    assert len(result.records) == 3
    assert all(record.agent_id == "agent-1" for record in result.records)


def test_get_activity_history_team_filter(mock_tmux, temp_activity_file) -> None:
    """Test filtering by team_id."""
    # Create records for multiple teams
    test_records = []
    base_time = datetime.now()

    teams = ["team-alpha", "team-beta", "team-alpha", None, "team-gamma"]
    for i, team in enumerate(teams):
        record: dict[str, Any] = {
            "record_id": f"record-{i}",
            "agent_id": f"agent-{i}",
            "activity_type": "working",
            "description": f"Task {i}",
            "timestamp": (base_time + timedelta(minutes=i)).isoformat(),
            "session_id": None,
            "team_id": team,
            "tags": [],
            "metadata": {},
        }
        test_records.append(record)

    with open(temp_activity_file, "w") as f:
        json.dump(test_records, f)

    request = ActivityHistoryRequest(team_id="team-alpha")

    with patch(
        "tmux_orchestrator.server.tools.report_activity._get_activity_file_path", return_value=temp_activity_file
    ):
        result = get_activity_history(mock_tmux, request)

    assert result.success
    assert len(result.records) == 2
    assert all(record.team_id == "team-alpha" for record in result.records)


def test_get_activity_history_activity_type_filter(mock_tmux, temp_activity_file) -> None:
    """Test filtering by activity type."""
    # Create records with different activity types
    test_records = []
    base_time = datetime.now()

    activity_types = ["working", "idle", "blocked", "working", "completed"]
    for i, activity_type in enumerate(activity_types):
        record: dict[str, Any] = {
            "record_id": f"record-{i}",
            "agent_id": f"agent-{i}",
            "activity_type": activity_type,
            "description": f"Task {i}",
            "timestamp": (base_time + timedelta(minutes=i)).isoformat(),
            "session_id": None,
            "team_id": None,
            "tags": [],
            "metadata": {},
        }
        test_records.append(record)

    with open(temp_activity_file, "w") as f:
        json.dump(test_records, f)

    request = ActivityHistoryRequest(activity_types=[ActivityType.WORKING, ActivityType.BLOCKED])

    with patch(
        "tmux_orchestrator.server.tools.report_activity._get_activity_file_path", return_value=temp_activity_file
    ):
        result = get_activity_history(mock_tmux, request)

    assert result.success
    assert len(result.records) == 3
    assert all(record.activity_type in [ActivityType.WORKING, ActivityType.BLOCKED] for record in result.records)


def test_get_activity_history_timestamp_filter(mock_tmux, temp_activity_file) -> None:
    """Test filtering by timestamp range."""
    # Create records across time range
    test_records = []
    base_time = datetime.now()

    for i in range(6):
        record: dict[str, Any] = {
            "record_id": f"record-{i}",
            "agent_id": f"agent-{i}",
            "activity_type": "working",
            "description": f"Task {i}",
            "timestamp": (base_time + timedelta(hours=i)).isoformat(),
            "session_id": None,
            "team_id": None,
            "tags": [],
            "metadata": {},
        }
        test_records.append(record)

    with open(temp_activity_file, "w") as f:
        json.dump(test_records, f)

    # Filter for records in the middle 2 hours
    since_time = base_time + timedelta(hours=2)
    request = ActivityHistoryRequest(since_timestamp=since_time)

    with patch(
        "tmux_orchestrator.server.tools.report_activity._get_activity_file_path", return_value=temp_activity_file
    ):
        result = get_activity_history(mock_tmux, request)

    assert result.success
    assert len(result.records) == 4  # Records from hour 2, 3, 4, 5
    assert all(record.timestamp is not None and record.timestamp >= since_time for record in result.records)


def test_get_activity_history_limit(mock_tmux, temp_activity_file) -> None:
    """Test limiting number of results."""
    # Create many records
    test_records = []
    base_time = datetime.now()

    for i in range(20):
        record: dict[str, Any] = {
            "record_id": f"record-{i}",
            "agent_id": f"agent-{i}",
            "activity_type": "working",
            "description": f"Task {i}",
            "timestamp": (base_time + timedelta(minutes=i)).isoformat(),
            "session_id": None,
            "team_id": None,
            "tags": [],
            "metadata": {},
        }
        test_records.append(record)

    with open(temp_activity_file, "w") as f:
        json.dump(test_records, f)

    request = ActivityHistoryRequest(limit=5)

    with patch(
        "tmux_orchestrator.server.tools.report_activity._get_activity_file_path", return_value=temp_activity_file
    ):
        result = get_activity_history(mock_tmux, request)

    assert result.success
    assert len(result.records) == 5
    assert result.total_records == 20  # Total count before limit


def test_get_activity_history_tags_filter(mock_tmux, temp_activity_file) -> None:
    """Test filtering by tags."""
    # Create records with different tags
    test_records = []
    base_time = datetime.now()

    tags_list = [["backend", "api"], ["frontend"], ["backend", "database"], [], ["api", "testing"]]
    for i, tags in enumerate(tags_list):
        record: dict[str, Any] = {
            "record_id": f"record-{i}",
            "agent_id": f"agent-{i}",
            "activity_type": "working",
            "description": f"Task {i}",
            "timestamp": (base_time + timedelta(minutes=i)).isoformat(),
            "session_id": None,
            "team_id": None,
            "tags": tags,
            "metadata": {},
        }
        test_records.append(record)

    with open(temp_activity_file, "w") as f:
        json.dump(test_records, f)

    request = ActivityHistoryRequest(tags=["backend"])

    with patch(
        "tmux_orchestrator.server.tools.report_activity._get_activity_file_path", return_value=temp_activity_file
    ):
        result = get_activity_history(mock_tmux, request)

    assert result.success
    assert len(result.records) == 2  # Records with "backend" tag
    assert all("backend" in record.tags for record in result.records)


def test_get_activity_history_combined_filters(mock_tmux, temp_activity_file) -> None:
    """Test using multiple filters together."""
    # Create diverse records
    test_records = []
    base_time = datetime.now()

    for i in range(10):
        record: dict[str, Any] = {
            "record_id": f"record-{i}",
            "agent_id": f"agent-{i % 3}",  # 3 different agents
            "activity_type": ["working", "idle", "blocked"][i % 3],
            "description": f"Task {i}",
            "timestamp": (base_time + timedelta(minutes=i * 10)).isoformat(),
            "session_id": None,
            "team_id": "team-alpha" if i % 2 == 0 else "team-beta",
            "tags": ["urgent"] if i < 5 else ["normal"],
            "metadata": {},
        }
        test_records.append(record)

    with open(temp_activity_file, "w") as f:
        json.dump(test_records, f)

    # Complex filter: agent-0, working type, team-alpha, urgent tag
    request = ActivityHistoryRequest(
        agent_id="agent-0",
        team_id="team-alpha",
        activity_types=[ActivityType.WORKING],
        tags=["urgent"],
    )

    with patch(
        "tmux_orchestrator.server.tools.report_activity._get_activity_file_path", return_value=temp_activity_file
    ):
        result = get_activity_history(mock_tmux, request)

    assert result.success
    # Should match records at index 0 and 3 (agent-0, working, team-alpha, urgent)
    assert len(result.records) == 1
    assert result.records[0].agent_id == "agent-0"
    assert result.records[0].activity_type == ActivityType.WORKING
    assert result.records[0].team_id == "team-alpha"
    assert "urgent" in result.records[0].tags

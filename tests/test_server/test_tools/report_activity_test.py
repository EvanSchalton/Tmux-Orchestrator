"""Tests for report_activity business logic tool."""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tmux_orchestrator.server.tools.report_activity import (
    ActivityHistoryRequest,
    ActivityRecord,
    ActivityType,
    ReportActivityRequest,
    get_activity_history,
    report_activity,
)


@pytest.fixture
def mock_tmux():
    """Create a mock TMUXManager for testing."""
    return MagicMock()


@pytest.fixture
def temp_activity_file():
    """Create a temporary activity file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        temp_path = Path(f.name)
        # Initialize empty activity file
        json.dump([], f)
    yield temp_path
    # Clean up
    if temp_path.exists():
        temp_path.unlink()


class TestActivityType:
    """Test ActivityType enum."""

    def test_activity_type_values(self):
        """Test all required activity types are defined."""
        assert ActivityType.WORKING.value == "working"
        assert ActivityType.IDLE.value == "idle"
        assert ActivityType.BLOCKED.value == "blocked"
        assert ActivityType.COMPLETED.value == "completed"


class TestReportActivityRequest:
    """Test ReportActivityRequest dataclass."""

    def test_report_activity_request_minimal(self):
        """Test ReportActivityRequest with minimal required fields."""
        request = ReportActivityRequest(
            agent_id="test-agent", activity_type=ActivityType.WORKING, description="Working on feature implementation"
        )

        assert request.agent_id == "test-agent"
        assert request.activity_type == ActivityType.WORKING
        assert request.description == "Working on feature implementation"
        assert request.session_id is None
        assert request.team_id is None
        assert request.tags == []
        assert request.metadata == {}

    def test_report_activity_request_full(self):
        """Test ReportActivityRequest with all fields."""
        request = ReportActivityRequest(
            agent_id="pm-agent",
            activity_type=ActivityType.BLOCKED,
            description="Waiting for code review",
            session_id="session-123",
            team_id="team-alpha",
            tags=["code-review", "blocked"],
            metadata={"priority": "high", "issue_id": "GH-123"},
        )

        assert request.agent_id == "pm-agent"
        assert request.activity_type == ActivityType.BLOCKED
        assert request.description == "Waiting for code review"
        assert request.session_id == "session-123"
        assert request.team_id == "team-alpha"
        assert request.tags == ["code-review", "blocked"]
        assert request.metadata == {"priority": "high", "issue_id": "GH-123"}


class TestActivityRecord:
    """Test ActivityRecord dataclass."""

    def test_activity_record_creation(self):
        """Test ActivityRecord creation with auto timestamp."""
        record = ActivityRecord(
            agent_id="test-agent",
            activity_type=ActivityType.WORKING,
            description="Implementing new feature",
            session_id="session-123",
        )

        assert record.agent_id == "test-agent"
        assert record.activity_type == ActivityType.WORKING
        assert record.description == "Implementing new feature"
        assert record.session_id == "session-123"
        assert record.team_id is None
        assert record.tags == []
        assert record.metadata == {}
        assert record.timestamp is not None
        assert isinstance(record.timestamp, datetime)

    def test_activity_record_with_timestamp(self):
        """Test ActivityRecord creation with custom timestamp."""
        custom_time = datetime.now() - timedelta(hours=1)
        record = ActivityRecord(
            agent_id="qa-agent",
            activity_type=ActivityType.COMPLETED,
            description="Testing completed",
            timestamp=custom_time,
        )

        assert record.timestamp == custom_time

    def test_activity_record_post_init_creates_timestamp(self):
        """Test that __post_init__ creates timestamp if None."""
        # Create record with None timestamp
        record = ActivityRecord(
            agent_id="test-agent", activity_type=ActivityType.IDLE, description="Taking a break", timestamp=None
        )

        # __post_init__ should have created a timestamp
        assert record.timestamp is not None
        assert isinstance(record.timestamp, datetime)


class TestReportActivity:
    """Test report_activity function."""

    def test_report_activity_invalid_agent_id_empty(self, mock_tmux, temp_activity_file):
        """Test report_activity with empty agent_id."""
        request = ReportActivityRequest(agent_id="", activity_type=ActivityType.WORKING, description="Test activity")

        with patch(
            "tmux_orchestrator.server.tools.report_activity._get_activity_file_path", return_value=temp_activity_file
        ):
            result = report_activity(mock_tmux, request)

        assert not result.success
        assert result.error_message == "Agent ID cannot be empty"
        assert result.record_id is None

    def test_report_activity_invalid_agent_id_whitespace(self, mock_tmux, temp_activity_file):
        """Test report_activity with whitespace-only agent_id."""
        request = ReportActivityRequest(agent_id="   ", activity_type=ActivityType.WORKING, description="Test activity")

        with patch(
            "tmux_orchestrator.server.tools.report_activity._get_activity_file_path", return_value=temp_activity_file
        ):
            result = report_activity(mock_tmux, request)

        assert not result.success
        assert result.error_message == "Agent ID cannot be empty"

    def test_report_activity_empty_description(self, mock_tmux, temp_activity_file):
        """Test report_activity with empty description."""
        request = ReportActivityRequest(agent_id="test-agent", activity_type=ActivityType.WORKING, description="")

        with patch(
            "tmux_orchestrator.server.tools.report_activity._get_activity_file_path", return_value=temp_activity_file
        ):
            result = report_activity(mock_tmux, request)

        assert not result.success
        assert result.error_message == "Activity description cannot be empty"

    def test_report_activity_whitespace_description(self, mock_tmux, temp_activity_file):
        """Test report_activity with whitespace-only description."""
        request = ReportActivityRequest(
            agent_id="test-agent", activity_type=ActivityType.WORKING, description="   \n\t   "
        )

        with patch(
            "tmux_orchestrator.server.tools.report_activity._get_activity_file_path", return_value=temp_activity_file
        ):
            result = report_activity(mock_tmux, request)

        assert not result.success
        assert result.error_message == "Activity description cannot be empty"

    def test_report_activity_success_minimal(self, mock_tmux, temp_activity_file):
        """Test successful activity reporting with minimal fields."""
        request = ReportActivityRequest(
            agent_id="dev-agent", activity_type=ActivityType.WORKING, description="Implementing authentication module"
        )

        with patch(
            "tmux_orchestrator.server.tools.report_activity._get_activity_file_path", return_value=temp_activity_file
        ):
            result = report_activity(mock_tmux, request)

        assert result.success
        assert result.error_message is None
        assert result.record_id is not None
        assert len(result.record_id) > 0
        assert result.agent_id == "dev-agent"
        assert result.activity_type == ActivityType.WORKING
        assert result.description == "Implementing authentication module"
        assert result.timestamp is not None

        # Verify record was saved to file
        with open(temp_activity_file) as f:
            records = json.load(f)
        assert len(records) == 1
        assert records[0]["agent_id"] == "dev-agent"
        assert records[0]["activity_type"] == "working"
        assert records[0]["description"] == "Implementing authentication module"

    def test_report_activity_success_full_fields(self, mock_tmux, temp_activity_file):
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

    def test_report_activity_all_activity_types(self, mock_tmux, temp_activity_file):
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
                request = ReportActivityRequest(
                    agent_id="test-agent", activity_type=activity_type, description=description
                )
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

    def test_report_activity_multiple_agents(self, mock_tmux, temp_activity_file):
        """Test reporting activities for multiple agents."""
        agents = ["dev-agent", "qa-agent", "pm-agent", "devops-agent"]

        with patch(
            "tmux_orchestrator.server.tools.report_activity._get_activity_file_path", return_value=temp_activity_file
        ):
            record_ids = []
            for i, agent in enumerate(agents):
                request = ReportActivityRequest(
                    agent_id=agent, activity_type=ActivityType.WORKING, description=f"Working on task {i+1}"
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

    def test_report_activity_file_not_exist(self, mock_tmux):
        """Test report_activity creates new file if it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file = Path(temp_dir) / "new_activity.json"

            request = ReportActivityRequest(
                agent_id="test-agent", activity_type=ActivityType.WORKING, description="First activity"
            )

            with patch(
                "tmux_orchestrator.server.tools.report_activity._get_activity_file_path", return_value=temp_file
            ):
                result = report_activity(mock_tmux, request)

            assert result.success
            assert temp_file.exists()

            # Verify file contains the activity
            with open(temp_file) as f:
                records = json.load(f)
            assert len(records) == 1

    def test_report_activity_file_permission_error(self, mock_tmux, temp_activity_file):
        """Test report_activity handles file permission errors."""
        request = ReportActivityRequest(
            agent_id="test-agent", activity_type=ActivityType.WORKING, description="Test activity"
        )

        # Mock file operations to raise PermissionError
        with patch(
            "tmux_orchestrator.server.tools.report_activity._get_activity_file_path", return_value=temp_activity_file
        ):
            with patch("builtins.open", side_effect=PermissionError("Access denied")):
                result = report_activity(mock_tmux, request)

        assert not result.success
        assert "Permission denied" in result.error_message

    def test_report_activity_json_decode_error(self, mock_tmux, temp_activity_file):
        """Test report_activity handles JSON decode errors gracefully."""
        # Write invalid JSON to file
        with open(temp_activity_file, "w") as f:
            f.write("invalid json content")

        request = ReportActivityRequest(
            agent_id="test-agent", activity_type=ActivityType.WORKING, description="Test activity"
        )

        with patch(
            "tmux_orchestrator.server.tools.report_activity._get_activity_file_path", return_value=temp_activity_file
        ):
            result = report_activity(mock_tmux, request)

        assert not result.success
        assert "Invalid JSON" in result.error_message or "JSON" in result.error_message

    def test_report_activity_unexpected_error(self, mock_tmux, temp_activity_file):
        """Test report_activity handles unexpected errors."""
        request = ReportActivityRequest(
            agent_id="test-agent", activity_type=ActivityType.WORKING, description="Test activity"
        )

        # Mock to raise unexpected exception during save
        with patch(
            "tmux_orchestrator.server.tools.report_activity._get_activity_file_path", return_value=temp_activity_file
        ):
            with patch(
                "tmux_orchestrator.server.tools.report_activity._save_activities",
                side_effect=RuntimeError("Unexpected error"),
            ):
                result = report_activity(mock_tmux, request)

        assert not result.success
        assert "Unexpected error" in result.error_message


class TestActivityHistoryRequest:
    """Test ActivityHistoryRequest dataclass."""

    def test_activity_history_request_defaults(self):
        """Test default values for ActivityHistoryRequest."""
        request = ActivityHistoryRequest()

        assert request.agent_id is None
        assert request.team_id is None
        assert request.session_id is None
        assert request.activity_types == []
        assert request.since_timestamp is None
        assert request.limit == 100
        assert request.tags == []

    def test_activity_history_request_agent_filter(self):
        """Test ActivityHistoryRequest with agent filter."""
        request = ActivityHistoryRequest(agent_id="dev-agent", limit=50)

        assert request.agent_id == "dev-agent"
        assert request.limit == 50

    def test_activity_history_request_full_filters(self):
        """Test ActivityHistoryRequest with all filters."""
        since = datetime.now() - timedelta(hours=24)
        request = ActivityHistoryRequest(
            agent_id="pm-agent",
            team_id="team-alpha",
            session_id="session-123",
            activity_types=[ActivityType.WORKING, ActivityType.BLOCKED],
            since_timestamp=since,
            limit=25,
            tags=["urgent", "feature"],
        )

        assert request.agent_id == "pm-agent"
        assert request.team_id == "team-alpha"
        assert request.session_id == "session-123"
        assert request.activity_types == [ActivityType.WORKING, ActivityType.BLOCKED]
        assert request.since_timestamp == since
        assert request.limit == 25
        assert request.tags == ["urgent", "feature"]


class TestGetActivityHistory:
    """Test get_activity_history function."""

    def test_get_activity_history_empty_file(self, mock_tmux, temp_activity_file):
        """Test getting history from empty file."""
        request = ActivityHistoryRequest()

        with patch(
            "tmux_orchestrator.server.tools.report_activity._get_activity_file_path", return_value=temp_activity_file
        ):
            result = get_activity_history(mock_tmux, request)

        assert result.success
        assert result.records == []
        assert result.total_records == 0
        assert result.error_message is None

    def test_get_activity_history_file_not_exist(self, mock_tmux):
        """Test getting history when file doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file = Path(temp_dir) / "nonexistent.json"

            request = ActivityHistoryRequest()

            with patch(
                "tmux_orchestrator.server.tools.report_activity._get_activity_file_path", return_value=temp_file
            ):
                result = get_activity_history(mock_tmux, request)

            assert result.success
            assert result.records == []
            assert result.total_records == 0

    def test_get_activity_history_all_records(self, mock_tmux, temp_activity_file):
        """Test getting all activity records without filters."""
        # Populate file with test data
        test_records = []
        base_time = datetime.now()

        for i in range(5):
            record = {
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
        timestamps = [record.timestamp for record in result.records]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_get_activity_history_agent_filter(self, mock_tmux, temp_activity_file):
        """Test filtering by agent_id."""
        # Create records for multiple agents
        test_records = []
        base_time = datetime.now()

        agents = ["agent-1", "agent-2", "agent-1", "agent-3", "agent-1"]
        for i, agent in enumerate(agents):
            record = {
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
        assert len(result.records) == 3  # Only agent-1 records
        assert result.total_records == 3

        # All records should be for agent-1
        for record in result.records:
            assert record.agent_id == "agent-1"

    def test_get_activity_history_team_filter(self, mock_tmux, temp_activity_file):
        """Test filtering by team_id."""
        # Create records for multiple teams
        test_records = []
        base_time = datetime.now()

        teams = ["team-alpha", "team-beta", "team-alpha", None, "team-gamma"]
        for i, team in enumerate(teams):
            record = {
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
        assert len(result.records) == 2  # Only team-alpha records
        assert result.total_records == 2

        # All records should be for team-alpha
        for record in result.records:
            assert record.team_id == "team-alpha"

    def test_get_activity_history_activity_type_filter(self, mock_tmux, temp_activity_file):
        """Test filtering by activity types."""
        # Create records with different activity types
        test_records = []
        base_time = datetime.now()

        activity_types = ["working", "idle", "blocked", "working", "completed"]
        for i, activity_type in enumerate(activity_types):
            record = {
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
        assert len(result.records) == 3  # working, blocked, working
        assert result.total_records == 3

        # All records should be working or blocked
        for record in result.records:
            assert record.activity_type in [ActivityType.WORKING, ActivityType.BLOCKED]

    def test_get_activity_history_timestamp_filter(self, mock_tmux, temp_activity_file):
        """Test filtering by timestamp."""
        # Create records with different timestamps
        test_records = []
        base_time = datetime.now() - timedelta(hours=2)

        for i in range(5):
            record = {
                "record_id": f"record-{i}",
                "agent_id": f"agent-{i}",
                "activity_type": "working",
                "description": f"Task {i}",
                "timestamp": (base_time + timedelta(minutes=i * 30)).isoformat(),
                "session_id": None,
                "team_id": None,
                "tags": [],
                "metadata": {},
            }
            test_records.append(record)

        with open(temp_activity_file, "w") as f:
            json.dump(test_records, f)

        # Filter for records newer than 1 hour ago
        since_time = datetime.now() - timedelta(hours=1)
        request = ActivityHistoryRequest(since_timestamp=since_time)

        with patch(
            "tmux_orchestrator.server.tools.report_activity._get_activity_file_path", return_value=temp_activity_file
        ):
            result = get_activity_history(mock_tmux, request)

        assert result.success
        # Should get records from last 3 time slots (1 hour worth)
        assert len(result.records) >= 2

        # All returned records should be newer than since_time
        for record in result.records:
            assert record.timestamp >= since_time

    def test_get_activity_history_limit(self, mock_tmux, temp_activity_file):
        """Test limit parameter."""
        # Create more records than limit
        test_records = []
        base_time = datetime.now()

        for i in range(10):
            record = {
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

        request = ActivityHistoryRequest(limit=3)

        with patch(
            "tmux_orchestrator.server.tools.report_activity._get_activity_file_path", return_value=temp_activity_file
        ):
            result = get_activity_history(mock_tmux, request)

        assert result.success
        assert len(result.records) == 3  # Limited to 3
        assert result.total_records == 10  # Total available

    def test_get_activity_history_tags_filter(self, mock_tmux, temp_activity_file):
        """Test filtering by tags."""
        # Create records with different tags
        test_records = []
        base_time = datetime.now()

        tag_sets = [
            ["urgent", "feature"],
            ["bug", "critical"],
            ["feature", "enhancement"],
            ["maintenance"],
            ["urgent", "bug"],
        ]

        for i, tags in enumerate(tag_sets):
            record = {
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

        request = ActivityHistoryRequest(tags=["urgent"])

        with patch(
            "tmux_orchestrator.server.tools.report_activity._get_activity_file_path", return_value=temp_activity_file
        ):
            result = get_activity_history(mock_tmux, request)

        assert result.success
        assert len(result.records) == 2  # Records with "urgent" tag
        assert result.total_records == 2

        # All records should have "urgent" tag
        for record in result.records:
            assert "urgent" in record.tags

    def test_get_activity_history_combined_filters(self, mock_tmux, temp_activity_file):
        """Test combining multiple filters."""
        # Create diverse test data
        test_records = []
        base_time = datetime.now() - timedelta(hours=1)

        # Mix of agents, teams, activity types, and timestamps
        record_data = [
            ("agent-1", "team-alpha", "working", ["urgent"], base_time + timedelta(minutes=0)),
            ("agent-2", "team-beta", "idle", ["break"], base_time + timedelta(minutes=10)),
            ("agent-1", "team-alpha", "blocked", ["urgent", "blocked"], base_time + timedelta(minutes=20)),
            ("agent-3", "team-alpha", "working", ["feature"], base_time + timedelta(minutes=30)),
            ("agent-1", "team-gamma", "completed", ["done"], base_time + timedelta(minutes=40)),
        ]

        for i, (agent, team, activity_type, tags, timestamp) in enumerate(record_data):
            record = {
                "record_id": f"record-{i}",
                "agent_id": agent,
                "activity_type": activity_type,
                "description": f"Task {i}",
                "timestamp": timestamp.isoformat(),
                "session_id": None,
                "team_id": team,
                "tags": tags,
                "metadata": {},
            }
            test_records.append(record)

        with open(temp_activity_file, "w") as f:
            json.dump(test_records, f)

        # Filter: agent-1 in team-alpha with urgent tag
        request = ActivityHistoryRequest(agent_id="agent-1", team_id="team-alpha", tags=["urgent"])

        with patch(
            "tmux_orchestrator.server.tools.report_activity._get_activity_file_path", return_value=temp_activity_file
        ):
            result = get_activity_history(mock_tmux, request)

        assert result.success
        assert len(result.records) == 2  # Should match records 0 and 2
        assert result.total_records == 2

        # Verify all filters were applied correctly
        for record in result.records:
            assert record.agent_id == "agent-1"
            assert record.team_id == "team-alpha"
            assert "urgent" in record.tags

    def test_get_activity_history_json_error(self, mock_tmux, temp_activity_file):
        """Test get_activity_history handles JSON errors."""
        # Write invalid JSON to file
        with open(temp_activity_file, "w") as f:
            f.write("invalid json content")

        request = ActivityHistoryRequest()

        with patch(
            "tmux_orchestrator.server.tools.report_activity._get_activity_file_path", return_value=temp_activity_file
        ):
            result = get_activity_history(mock_tmux, request)

        assert not result.success
        assert "Invalid JSON" in result.error_message or "JSON" in result.error_message
        assert result.records == []
        assert result.total_records == 0

    def test_get_activity_history_permission_error(self, mock_tmux, temp_activity_file):
        """Test get_activity_history handles permission errors."""
        request = ActivityHistoryRequest()

        # Mock file operations to raise PermissionError
        with patch(
            "tmux_orchestrator.server.tools.report_activity._get_activity_file_path", return_value=temp_activity_file
        ):
            with patch("builtins.open", side_effect=PermissionError("Access denied")):
                result = get_activity_history(mock_tmux, request)

        assert not result.success
        assert "Permission denied" in result.error_message
        assert result.records == []
        assert result.total_records == 0

    def test_get_activity_history_unexpected_error(self, mock_tmux, temp_activity_file):
        """Test get_activity_history handles unexpected errors."""
        request = ActivityHistoryRequest()

        # Mock to raise unexpected exception
        with patch(
            "tmux_orchestrator.server.tools.report_activity._get_activity_file_path", return_value=temp_activity_file
        ):
            with patch(
                "tmux_orchestrator.server.tools.report_activity._load_activities",
                side_effect=RuntimeError("Unexpected error"),
            ):
                result = get_activity_history(mock_tmux, request)

        assert not result.success
        assert "Unexpected error" in result.error_message
        assert result.records == []
        assert result.total_records == 0

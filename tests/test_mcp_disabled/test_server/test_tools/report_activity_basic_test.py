"""Basic tests for report_activity - validation, models, and error handling."""

from datetime import datetime, timedelta
from unittest.mock import patch

from tmux_orchestrator.server.tools.report_activity import (
    ActivityHistoryRequest,
    ActivityRecord,
    ActivityType,
    ReportActivityRequest,
    report_activity,
)


def test_activity_type_values() -> None:
    """Test all required activity types are defined."""
    assert ActivityType.WORKING.value == "working"
    assert ActivityType.IDLE.value == "idle"
    assert ActivityType.BLOCKED.value == "blocked"
    assert ActivityType.COMPLETED.value == "completed"


def test_report_activity_request_minimal() -> None:
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


def test_report_activity_request_full() -> None:
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


def test_activity_record_creation() -> None:
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


def test_activity_record_with_timestamp() -> None:
    """Test ActivityRecord with explicit timestamp."""
    custom_time = datetime(2025, 8, 13, 12, 0, 0)
    record = ActivityRecord(
        agent_id="test-agent",
        activity_type=ActivityType.COMPLETED,
        description="Task completed",
        timestamp=custom_time,
    )

    assert record.timestamp == custom_time


def test_activity_record_post_init_creates_timestamp() -> None:
    """Test ActivityRecord __post_init__ sets timestamp if None."""
    record = ActivityRecord(
        agent_id="test-agent",
        activity_type=ActivityType.IDLE,
        description="Idle state",
        timestamp=None,  # Explicitly set to None
    )

    assert record.timestamp is not None
    assert isinstance(record.timestamp, datetime)


def test_report_activity_invalid_agent_id_empty(mock_tmux, temp_activity_file) -> None:
    """Test report_activity with empty agent_id returns error."""
    request = ReportActivityRequest(agent_id="", activity_type=ActivityType.WORKING, description="Working on task")

    with patch(
        "tmux_orchestrator.server.tools.report_activity._get_activity_file_path", return_value=temp_activity_file
    ):
        result = report_activity(mock_tmux, request)

    assert not result.success
    assert result.error_message == "Agent ID cannot be empty"


def test_report_activity_invalid_agent_id_whitespace(mock_tmux, temp_activity_file) -> None:
    """Test report_activity with whitespace agent_id returns error."""
    request = ReportActivityRequest(agent_id="   ", activity_type=ActivityType.WORKING, description="Working on task")

    with patch(
        "tmux_orchestrator.server.tools.report_activity._get_activity_file_path", return_value=temp_activity_file
    ):
        result = report_activity(mock_tmux, request)

    assert not result.success
    assert result.error_message == "Agent ID cannot be empty"


def test_report_activity_empty_description(mock_tmux, temp_activity_file) -> None:
    """Test report_activity with empty description returns error."""
    request = ReportActivityRequest(agent_id="test-agent", activity_type=ActivityType.WORKING, description="")

    with patch(
        "tmux_orchestrator.server.tools.report_activity._get_activity_file_path", return_value=temp_activity_file
    ):
        result = report_activity(mock_tmux, request)

    assert not result.success
    assert result.error_message == "Activity description cannot be empty"


def test_report_activity_whitespace_description(mock_tmux, temp_activity_file) -> None:
    """Test report_activity with whitespace description returns error."""
    request = ReportActivityRequest(agent_id="test-agent", activity_type=ActivityType.WORKING, description="   ")

    with patch(
        "tmux_orchestrator.server.tools.report_activity._get_activity_file_path", return_value=temp_activity_file
    ):
        result = report_activity(mock_tmux, request)

    assert not result.success
    assert result.error_message == "Activity description cannot be empty"


def test_activity_history_request_defaults() -> None:
    """Test ActivityHistoryRequest default values."""
    request = ActivityHistoryRequest()

    assert request.agent_id is None
    assert request.team_id is None
    assert request.activity_types == []
    assert request.limit == 100
    assert request.since_timestamp is None
    assert request.tags == []


def test_activity_history_request_agent_filter() -> None:
    """Test ActivityHistoryRequest with agent filter."""
    request = ActivityHistoryRequest(agent_id="pm-agent")

    assert request.agent_id == "pm-agent"
    assert request.limit == 100  # Default


def test_activity_history_request_full_filters() -> None:
    """Test ActivityHistoryRequest with all filters."""
    since_time = datetime.now() - timedelta(days=1)

    request = ActivityHistoryRequest(
        agent_id="dev-agent",
        team_id="team-beta",
        activity_types=[ActivityType.WORKING, ActivityType.BLOCKED],
        limit=50,
        since_timestamp=since_time,
        tags=["feature", "backend"],
    )

    assert request.agent_id == "dev-agent"
    assert request.team_id == "team-beta"
    assert request.activity_types == [ActivityType.WORKING, ActivityType.BLOCKED]
    assert request.limit == 50
    assert request.since_timestamp == since_time
    assert request.tags == ["feature", "backend"]

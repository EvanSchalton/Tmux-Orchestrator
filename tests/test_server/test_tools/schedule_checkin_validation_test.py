"""Tests for schedule_checkin validation and error handling."""

from datetime import datetime, timedelta
from unittest.mock import patch

from tmux_orchestrator.server.tools.schedule_checkin import (
    ScheduleCheckinRequest,
    ScheduleType,
    schedule_checkin,
)


def test_schedule_checkin_invalid_agent_id(mock_tmux, temp_schedule_file) -> None:
    """Test schedule_checkin with empty agent_id."""
    request = ScheduleCheckinRequest(
        agent_id="",
        message="Test check-in",
        schedule_time=datetime.now() + timedelta(hours=1),
    )

    with patch(
        "tmux_orchestrator.server.tools.schedule_checkin._get_schedule_file_path", return_value=temp_schedule_file
    ):
        result = schedule_checkin(mock_tmux, request)

    assert not result.success
    assert result.error_message == "Agent ID cannot be empty"
    assert result.schedule_id is None


def test_schedule_checkin_empty_message(mock_tmux, temp_schedule_file) -> None:
    """Test schedule_checkin with empty message."""
    request = ScheduleCheckinRequest(
        agent_id="test-agent",
        message="",
        schedule_time=datetime.now() + timedelta(hours=1),
    )

    with patch(
        "tmux_orchestrator.server.tools.schedule_checkin._get_schedule_file_path", return_value=temp_schedule_file
    ):
        result = schedule_checkin(mock_tmux, request)

    assert not result.success
    assert result.error_message == "Check-in message cannot be empty"


def test_schedule_checkin_past_time(mock_tmux, temp_schedule_file) -> None:
    """Test schedule_checkin with past schedule time."""
    past_time = datetime.now() - timedelta(hours=1)
    request = ScheduleCheckinRequest(
        agent_id="test-agent",
        message="Test check-in",
        schedule_time=past_time,
    )

    with patch(
        "tmux_orchestrator.server.tools.schedule_checkin._get_schedule_file_path", return_value=temp_schedule_file
    ):
        result = schedule_checkin(mock_tmux, request)

    assert not result.success
    assert result.error_message == "Schedule time must be in the future"


def test_schedule_checkin_recurring_no_interval(mock_tmux, temp_schedule_file) -> None:
    """Test schedule_checkin recurring without interval."""
    request = ScheduleCheckinRequest(
        agent_id="test-agent",
        message="Test check-in",
        schedule_time=datetime.now() + timedelta(hours=1),
        schedule_type=ScheduleType.RECURRING,
    )

    with patch(
        "tmux_orchestrator.server.tools.schedule_checkin._get_schedule_file_path", return_value=temp_schedule_file
    ):
        result = schedule_checkin(mock_tmux, request)

    assert not result.success
    assert result.error_message == "Recurring schedules must specify recurring_interval"


def test_schedule_checkin_weekly_no_days(mock_tmux, temp_schedule_file) -> None:
    """Test schedule_checkin weekly without days."""
    request = ScheduleCheckinRequest(
        agent_id="test-agent",
        message="Test check-in",
        schedule_time=datetime.now() + timedelta(hours=1),
        schedule_type=ScheduleType.WEEKLY,
    )

    with patch(
        "tmux_orchestrator.server.tools.schedule_checkin._get_schedule_file_path", return_value=temp_schedule_file
    ):
        result = schedule_checkin(mock_tmux, request)

    assert not result.success
    assert result.error_message == "Weekly schedules must specify recurring_days"


def test_schedule_checkin_weekly_invalid_days(mock_tmux, temp_schedule_file) -> None:
    """Test schedule_checkin weekly with invalid days."""
    request = ScheduleCheckinRequest(
        agent_id="test-agent",
        message="Test check-in",
        schedule_time=datetime.now() + timedelta(hours=1),
        schedule_type=ScheduleType.WEEKLY,
        recurring_days=["funday", "badday"],
    )

    with patch(
        "tmux_orchestrator.server.tools.schedule_checkin._get_schedule_file_path", return_value=temp_schedule_file
    ):
        result = schedule_checkin(mock_tmux, request)

    assert not result.success
    assert "Invalid weekday names" in result.error_message


def test_schedule_checkin_duplicate_agent_conflict(mock_tmux, temp_schedule_file) -> None:
    """Test scheduling conflict when agent already has active schedule at same time."""
    schedule_time = datetime.now() + timedelta(hours=1)

    # Create first schedule
    request1 = ScheduleCheckinRequest(
        agent_id="test-agent",
        message="First check-in",
        schedule_time=schedule_time,
    )

    with patch(
        "tmux_orchestrator.server.tools.schedule_checkin._get_schedule_file_path", return_value=temp_schedule_file
    ):
        result1 = schedule_checkin(mock_tmux, request1)
        assert result1.success

        # Try to create conflicting schedule (within 5 minutes)
        request2 = ScheduleCheckinRequest(
            agent_id="test-agent",
            message="Conflicting check-in",
            schedule_time=schedule_time + timedelta(minutes=2),
        )

        result2 = schedule_checkin(mock_tmux, request2)

    assert not result2.success
    assert "Scheduling conflict" in result2.error_message


def test_schedule_checkin_file_permission_error(mock_tmux, temp_schedule_file) -> None:
    """Test schedule_checkin handles file permission errors."""
    request = ScheduleCheckinRequest(
        agent_id="test-agent",
        message="Test check-in",
        schedule_time=datetime.now() + timedelta(hours=1),
    )

    # Mock file operations to raise PermissionError
    with patch(
        "tmux_orchestrator.server.tools.schedule_checkin._get_schedule_file_path", return_value=temp_schedule_file
    ):
        with patch("builtins.open", side_effect=PermissionError("Access denied")):
            result = schedule_checkin(mock_tmux, request)

    assert not result.success
    assert "Permission denied" in result.error_message


def test_schedule_checkin_json_error(mock_tmux, temp_schedule_file) -> None:
    """Test schedule_checkin handles JSON errors gracefully."""
    # Write invalid JSON to file
    with open(temp_schedule_file, "w") as f:
        f.write("invalid json content")

    request = ScheduleCheckinRequest(
        agent_id="test-agent",
        message="Test check-in",
        schedule_time=datetime.now() + timedelta(hours=1),
    )

    with patch(
        "tmux_orchestrator.server.tools.schedule_checkin._get_schedule_file_path", return_value=temp_schedule_file
    ):
        result = schedule_checkin(mock_tmux, request)

    assert not result.success
    assert "Invalid JSON" in result.error_message or "JSON" in result.error_message

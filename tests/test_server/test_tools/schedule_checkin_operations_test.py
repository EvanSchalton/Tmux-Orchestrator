"""Tests for schedule_checkin operations and complex scenarios."""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from tmux_orchestrator.server.tools.schedule_checkin import (
    ScheduleCheckinRequest,
    ScheduleType,
    schedule_checkin,
)


def test_schedule_checkin_success_one_time(mock_tmux, temp_schedule_file) -> None:
    """Test successful one-time schedule creation."""
    future_time = datetime.now() + timedelta(hours=1)
    request = ScheduleCheckinRequest(
        agent_id="test-agent",
        message="One-time check-in",
        schedule_time=future_time,
        schedule_type=ScheduleType.ONE_TIME,
    )

    with patch(
        "tmux_orchestrator.server.tools.schedule_checkin._get_schedule_file_path", return_value=temp_schedule_file
    ):
        result = schedule_checkin(mock_tmux, request)

    assert result.success
    assert result.error_message is None
    assert result.schedule_id is not None
    assert len(result.schedule_id) > 0
    assert result.schedule_time == future_time
    assert result.schedule_type == ScheduleType.ONE_TIME

    # Verify schedule was saved to file
    with open(temp_schedule_file) as f:
        schedules = json.load(f)
    assert len(schedules) == 1
    assert schedules[0]["agent_id"] == "test-agent"
    assert schedules[0]["message"] == "One-time check-in"


def test_schedule_checkin_success_recurring(mock_tmux, temp_schedule_file) -> None:
    """Test successful recurring schedule creation."""
    future_time = datetime.now() + timedelta(hours=1)
    request = ScheduleCheckinRequest(
        agent_id="pm-agent",
        message="Daily standup",
        schedule_time=future_time,
        schedule_type=ScheduleType.RECURRING,
        recurring_interval=24,
    )

    with patch(
        "tmux_orchestrator.server.tools.schedule_checkin._get_schedule_file_path", return_value=temp_schedule_file
    ):
        result = schedule_checkin(mock_tmux, request)

    assert result.success
    assert result.schedule_type == ScheduleType.RECURRING
    assert result.recurring_interval == 24

    # Verify schedule was saved with recurring info
    with open(temp_schedule_file) as f:
        schedules = json.load(f)
    assert len(schedules) == 1
    assert schedules[0]["schedule_type"] == "recurring"
    assert schedules[0]["recurring_interval"] == 24


def test_schedule_checkin_success_weekly(mock_tmux, temp_schedule_file) -> None:
    """Test successful weekly schedule creation."""
    future_time = datetime.now() + timedelta(hours=1)
    request = ScheduleCheckinRequest(
        agent_id="qa-agent",
        message="Weekly report",
        schedule_time=future_time,
        schedule_type=ScheduleType.WEEKLY,
        recurring_days=["monday", "friday"],
    )

    with patch(
        "tmux_orchestrator.server.tools.schedule_checkin._get_schedule_file_path", return_value=temp_schedule_file
    ):
        result = schedule_checkin(mock_tmux, request)

    assert result.success
    assert result.schedule_type == ScheduleType.WEEKLY
    assert result.recurring_days == ["monday", "friday"]

    # Verify schedule was saved with weekly info
    with open(temp_schedule_file) as f:
        schedules = json.load(f)
    assert len(schedules) == 1
    assert schedules[0]["schedule_type"] == "weekly"
    assert schedules[0]["recurring_days"] == ["monday", "friday"]


def test_schedule_checkin_update_existing(mock_tmux, temp_schedule_file) -> None:
    """Test updating existing schedule by providing schedule_id."""
    # Create initial schedule
    initial_time = datetime.now() + timedelta(hours=1)
    request1 = ScheduleCheckinRequest(
        agent_id="test-agent",
        message="Initial check-in",
        schedule_time=initial_time,
    )

    with patch(
        "tmux_orchestrator.server.tools.schedule_checkin._get_schedule_file_path", return_value=temp_schedule_file
    ):
        result1 = schedule_checkin(mock_tmux, request1)
        assert result1.success
        schedule_id = result1.schedule_id

        # Update the schedule
        updated_time = datetime.now() + timedelta(hours=2)
        request2 = ScheduleCheckinRequest(
            agent_id="test-agent",
            message="Updated check-in",
            schedule_time=updated_time,
            schedule_id=schedule_id,
        )

        result2 = schedule_checkin(mock_tmux, request2)

    assert result2.success
    assert result2.schedule_id == schedule_id
    assert result2.message == "Updated check-in"

    # Verify only one schedule exists in file
    with open(temp_schedule_file) as f:
        schedules = json.load(f)
    assert len(schedules) == 1
    assert schedules[0]["message"] == "Updated check-in"


def test_schedule_checkin_file_not_exist(mock_tmux) -> None:
    """Test schedule_checkin creates new file if it doesn't exist."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_file = Path(temp_dir) / "new_schedule.json"

        request = ScheduleCheckinRequest(
            agent_id="test-agent",
            message="Test check-in",
            schedule_time=datetime.now() + timedelta(hours=1),
        )

        with patch("tmux_orchestrator.server.tools.schedule_checkin._get_schedule_file_path", return_value=temp_file):
            result = schedule_checkin(mock_tmux, request)

        assert result.success
        assert temp_file.exists()

        # Verify file contains the schedule
        with open(temp_file) as f:
            schedules = json.load(f)
        assert len(schedules) == 1


def test_schedule_checkin_multiple_schedules(mock_tmux, temp_schedule_file) -> None:
    """Test creating multiple schedules for different agents."""
    base_time = datetime.now() + timedelta(hours=1)

    agents = ["dev-agent", "qa-agent", "pm-agent"]
    schedule_ids = []

    with patch(
        "tmux_orchestrator.server.tools.schedule_checkin._get_schedule_file_path", return_value=temp_schedule_file
    ):
        for i, agent in enumerate(agents):
            request = ScheduleCheckinRequest(
                agent_id=agent,
                message=f"Check-in for {agent}",
                schedule_time=base_time + timedelta(minutes=i * 10),
            )

            result = schedule_checkin(mock_tmux, request)
            assert result.success
            schedule_ids.append(result.schedule_id)

    # Verify all schedules are unique and saved
    assert len(set(schedule_ids)) == 3  # All IDs should be unique

    with open(temp_schedule_file) as f:
        schedules = json.load(f)
    assert len(schedules) == 3

    # Verify each agent has their schedule
    agent_ids = {s["agent_id"] for s in schedules}
    assert agent_ids == set(agents)

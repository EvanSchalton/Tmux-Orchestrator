"""Tests for schedule_checkin business logic tool."""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tmux_orchestrator.server.tools.schedule_checkin import (
    CheckinSchedule,
    ScheduleCheckinRequest,
    ScheduleType,
    schedule_checkin,
)


@pytest.fixture
def mock_tmux():
    """Create a mock TMUXManager for testing."""
    return MagicMock()


@pytest.fixture
def temp_schedule_file():
    """Create a temporary schedule file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        temp_path = Path(f.name)
        # Initialize empty schedule file
        json.dump([], f)
    yield temp_path
    # Clean up
    if temp_path.exists():
        temp_path.unlink()


class TestScheduleCheckinRequest:
    """Test ScheduleCheckinRequest dataclass."""

    def test_schedule_checkin_request_defaults(self):
        """Test default values for ScheduleCheckinRequest."""
        request = ScheduleCheckinRequest(
            agent_id="test-agent",
            message="Test check-in",
            schedule_time=datetime.now(),
        )

        assert request.agent_id == "test-agent"
        assert request.message == "Test check-in"
        assert request.schedule_type == ScheduleType.ONE_TIME
        assert request.recurring_interval is None
        assert request.recurring_days is None
        assert request.schedule_id is None

    def test_schedule_checkin_request_recurring(self):
        """Test ScheduleCheckinRequest with recurring schedule."""
        request = ScheduleCheckinRequest(
            agent_id="test-agent",
            message="Daily standup",
            schedule_time=datetime.now(),
            schedule_type=ScheduleType.RECURRING,
            recurring_interval=24,  # Every 24 hours
        )

        assert request.schedule_type == ScheduleType.RECURRING
        assert request.recurring_interval == 24

    def test_schedule_checkin_request_weekly(self):
        """Test ScheduleCheckinRequest with weekly schedule."""
        request = ScheduleCheckinRequest(
            agent_id="test-agent",
            message="Weekly report",
            schedule_time=datetime.now(),
            schedule_type=ScheduleType.WEEKLY,
            recurring_days=["monday", "friday"],
        )

        assert request.schedule_type == ScheduleType.WEEKLY
        assert request.recurring_days == ["monday", "friday"]


class TestCheckinSchedule:
    """Test CheckinSchedule dataclass."""

    def test_checkin_schedule_one_time(self):
        """Test CheckinSchedule for one-time schedule."""
        schedule_time = datetime.now() + timedelta(hours=1)
        schedule = CheckinSchedule(
            schedule_id="test-123",
            agent_id="test-agent",
            message="One-time check-in",
            schedule_time=schedule_time,
            schedule_type=ScheduleType.ONE_TIME,
        )

        assert schedule.schedule_id == "test-123"
        assert schedule.agent_id == "test-agent"
        assert schedule.message == "One-time check-in"
        assert schedule.schedule_time == schedule_time
        assert schedule.schedule_type == ScheduleType.ONE_TIME
        assert schedule.recurring_interval is None
        assert schedule.recurring_days is None
        assert schedule.created_at is not None
        assert schedule.last_executed is None
        assert schedule.is_active is True

    def test_checkin_schedule_recurring(self):
        """Test CheckinSchedule for recurring schedule."""
        schedule_time = datetime.now() + timedelta(hours=1)
        schedule = CheckinSchedule(
            schedule_id="recurring-123",
            agent_id="pm-agent",
            message="Daily check-in",
            schedule_time=schedule_time,
            schedule_type=ScheduleType.RECURRING,
            recurring_interval=24,
        )

        assert schedule.schedule_type == ScheduleType.RECURRING
        assert schedule.recurring_interval == 24

    def test_checkin_schedule_is_due_one_time(self):
        """Test is_due method for one-time schedule."""
        past_time = datetime.now() - timedelta(minutes=5)
        future_time = datetime.now() + timedelta(minutes=5)

        # Past schedule should be due
        past_schedule = CheckinSchedule(
            schedule_id="past-123",
            agent_id="test-agent",
            message="Past check-in",
            schedule_time=past_time,
            schedule_type=ScheduleType.ONE_TIME,
        )
        assert past_schedule.is_due()

        # Future schedule should not be due
        future_schedule = CheckinSchedule(
            schedule_id="future-123",
            agent_id="test-agent",
            message="Future check-in",
            schedule_time=future_time,
            schedule_type=ScheduleType.ONE_TIME,
        )
        assert not future_schedule.is_due()

    def test_checkin_schedule_is_due_recurring(self):
        """Test is_due method for recurring schedule."""
        # Schedule for 1 hour ago with 30 minute interval
        base_time = datetime.now() - timedelta(hours=1)
        schedule = CheckinSchedule(
            schedule_id="recurring-123",
            agent_id="test-agent",
            message="Recurring check-in",
            schedule_time=base_time,
            schedule_type=ScheduleType.RECURRING,
            recurring_interval=0.5,  # 30 minutes
        )

        # Should be due since more than 30 minutes have passed
        assert schedule.is_due()

    def test_checkin_schedule_is_due_weekly(self):
        """Test is_due method for weekly schedule."""
        # Create schedule for current weekday
        now = datetime.now()
        weekday_name = now.strftime("%A").lower()

        schedule = CheckinSchedule(
            schedule_id="weekly-123",
            agent_id="test-agent",
            message="Weekly check-in",
            schedule_time=now - timedelta(minutes=30),  # 30 minutes ago
            schedule_type=ScheduleType.WEEKLY,
            recurring_days=[weekday_name],
        )

        # Should be due if today is in recurring_days and time has passed
        assert schedule.is_due()

    def test_checkin_schedule_execute(self):
        """Test execute method updates last_executed."""
        schedule = CheckinSchedule(
            schedule_id="test-123",
            agent_id="test-agent",
            message="Test check-in",
            schedule_time=datetime.now(),
            schedule_type=ScheduleType.ONE_TIME,
        )

        assert schedule.last_executed is None

        before_execute = datetime.now()
        schedule.execute()
        after_execute = datetime.now()

        assert schedule.last_executed is not None
        assert before_execute <= schedule.last_executed <= after_execute

    def test_checkin_schedule_deactivate(self):
        """Test deactivate method sets is_active to False."""
        schedule = CheckinSchedule(
            schedule_id="test-123",
            agent_id="test-agent",
            message="Test check-in",
            schedule_time=datetime.now(),
            schedule_type=ScheduleType.ONE_TIME,
        )

        assert schedule.is_active is True
        schedule.deactivate()
        assert schedule.is_active is False


class TestScheduleCheckin:
    """Test schedule_checkin function."""

    def test_schedule_checkin_invalid_agent_id(self, mock_tmux, temp_schedule_file):
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

    def test_schedule_checkin_empty_message(self, mock_tmux, temp_schedule_file):
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

    def test_schedule_checkin_past_time(self, mock_tmux, temp_schedule_file):
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

    def test_schedule_checkin_recurring_no_interval(self, mock_tmux, temp_schedule_file):
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

    def test_schedule_checkin_weekly_no_days(self, mock_tmux, temp_schedule_file):
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

    def test_schedule_checkin_weekly_invalid_days(self, mock_tmux, temp_schedule_file):
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

    def test_schedule_checkin_success_one_time(self, mock_tmux, temp_schedule_file):
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

    def test_schedule_checkin_success_recurring(self, mock_tmux, temp_schedule_file):
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

    def test_schedule_checkin_success_weekly(self, mock_tmux, temp_schedule_file):
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

    def test_schedule_checkin_duplicate_agent_conflict(self, mock_tmux, temp_schedule_file):
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

    def test_schedule_checkin_update_existing(self, mock_tmux, temp_schedule_file):
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

    def test_schedule_checkin_file_not_exist(self, mock_tmux):
        """Test schedule_checkin creates new file if it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file = Path(temp_dir) / "new_schedule.json"

            request = ScheduleCheckinRequest(
                agent_id="test-agent",
                message="Test check-in",
                schedule_time=datetime.now() + timedelta(hours=1),
            )

            with patch(
                "tmux_orchestrator.server.tools.schedule_checkin._get_schedule_file_path", return_value=temp_file
            ):
                result = schedule_checkin(mock_tmux, request)

            assert result.success
            assert temp_file.exists()

            # Verify file contains the schedule
            with open(temp_file) as f:
                schedules = json.load(f)
            assert len(schedules) == 1

    def test_schedule_checkin_file_permission_error(self, mock_tmux, temp_schedule_file):
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

    def test_schedule_checkin_json_error(self, mock_tmux, temp_schedule_file):
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

    def test_schedule_checkin_multiple_schedules(self, mock_tmux, temp_schedule_file):
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

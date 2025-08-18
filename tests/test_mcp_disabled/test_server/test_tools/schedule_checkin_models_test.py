"""Tests for schedule_checkin models and data structures."""

from datetime import datetime, timedelta

from tmux_orchestrator.server.tools.schedule_checkin import (
    CheckinSchedule,
    ScheduleCheckinRequest,
    ScheduleType,
)


def test_schedule_checkin_request_defaults() -> None:
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


def test_schedule_checkin_request_recurring() -> None:
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


def test_schedule_checkin_request_weekly() -> None:
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


def test_checkin_schedule_one_time() -> None:
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


def test_checkin_schedule_recurring() -> None:
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


def test_checkin_schedule_is_due_one_time() -> None:
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


def test_checkin_schedule_is_due_recurring() -> None:
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


def test_checkin_schedule_is_due_weekly() -> None:
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


def test_checkin_schedule_execute() -> None:
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


def test_checkin_schedule_deactivate() -> None:
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

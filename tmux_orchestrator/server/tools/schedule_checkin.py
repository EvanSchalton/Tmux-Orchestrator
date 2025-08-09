"""Business logic for scheduling agent check-ins."""

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional

from tmux_orchestrator.utils.tmux import TMUXManager


class ScheduleType(Enum):
    """Types of check-in schedules."""

    ONE_TIME = "one_time"
    RECURRING = "recurring"
    WEEKLY = "weekly"


@dataclass
class ScheduleCheckinRequest:
    """Request parameters for scheduling a check-in."""

    agent_id: str
    message: str
    schedule_time: datetime
    schedule_type: ScheduleType = ScheduleType.ONE_TIME
    recurring_interval: Optional[float] = None  # Hours between recurring check-ins
    recurring_days: Optional[list[str]] = None  # Days of week for weekly schedules
    schedule_id: Optional[str] = None  # For updating existing schedules


@dataclass
class CheckinSchedule:
    """Represents a scheduled check-in."""

    schedule_id: str
    agent_id: str
    message: str
    schedule_time: datetime
    schedule_type: ScheduleType
    recurring_interval: Optional[float] = None
    recurring_days: Optional[list[str]] = None
    created_at: datetime = None
    last_executed: Optional[datetime] = None
    is_active: bool = True

    def __post_init__(self) -> None:
        """Set created_at if not provided."""
        if self.created_at is None:
            self.created_at = datetime.now()

    def is_due(self, current_time: Optional[datetime] = None) -> bool:
        """Check if this schedule is due for execution."""
        if not self.is_active:
            return False

        if current_time is None:
            current_time = datetime.now()

        if self.schedule_type == ScheduleType.ONE_TIME:
            # One-time schedules are due if current time is past schedule time
            return current_time >= self.schedule_time

        elif self.schedule_type == ScheduleType.RECURRING:
            if self.recurring_interval is None:
                return False

            # Check if enough time has passed since last execution or initial schedule time
            reference_time = self.last_executed if self.last_executed else self.schedule_time
            time_since_reference = current_time - reference_time
            return time_since_reference >= timedelta(hours=self.recurring_interval)

        elif self.schedule_type == ScheduleType.WEEKLY:
            if not self.recurring_days:
                return False

            # Check if today is one of the specified weekdays
            current_weekday = current_time.strftime("%A").lower()
            if current_weekday not in self.recurring_days:
                return False

            # If we're on the right weekday, check if time has passed
            return current_time >= self.schedule_time

        return False

    def execute(self) -> None:
        """Mark this schedule as executed."""
        self.last_executed = datetime.now()

        # Deactivate one-time schedules after execution
        if self.schedule_type == ScheduleType.ONE_TIME:
            self.is_active = False

    def deactivate(self) -> None:
        """Deactivate this schedule."""
        self.is_active = False


@dataclass
class ScheduleCheckinResult:
    """Result of scheduling a check-in operation."""

    success: bool
    agent_id: str
    message: str
    schedule_time: datetime
    schedule_type: ScheduleType
    schedule_id: Optional[str] = None
    recurring_interval: Optional[float] = None
    recurring_days: Optional[list[str]] = None
    error_message: Optional[str] = None


def schedule_checkin(tmux: TMUXManager, request: ScheduleCheckinRequest) -> ScheduleCheckinResult:
    """
    Schedule a check-in for a Claude agent.

    Supports one-time, recurring, and weekly schedules with persistence.

    Args:
        tmux: TMUXManager instance for tmux operations
        request: ScheduleCheckinRequest with schedule details

    Returns:
        ScheduleCheckinResult indicating success/failure and schedule details

    Raises:
        ValueError: If request parameters are invalid
    """
    # Validate input parameters
    validation_error = _validate_request(request)
    if validation_error:
        return ScheduleCheckinResult(
            success=False,
            agent_id=request.agent_id,
            message=request.message,
            schedule_time=request.schedule_time,
            schedule_type=request.schedule_type,
            error_message=validation_error,
        )

    try:
        # Load existing schedules
        schedule_file = _get_schedule_file_path()
        schedules = _load_schedules(schedule_file)

        # Check for scheduling conflicts (unless updating existing schedule)
        if not request.schedule_id:
            conflict_error = _check_scheduling_conflicts(schedules, request)
            if conflict_error:
                return ScheduleCheckinResult(
                    success=False,
                    agent_id=request.agent_id,
                    message=request.message,
                    schedule_time=request.schedule_time,
                    schedule_type=request.schedule_type,
                    error_message=conflict_error,
                )

        # Create or update schedule
        if request.schedule_id:
            # Update existing schedule
            schedule = _update_existing_schedule(schedules, request)
            if schedule is None:
                return ScheduleCheckinResult(
                    success=False,
                    agent_id=request.agent_id,
                    message=request.message,
                    schedule_time=request.schedule_time,
                    schedule_type=request.schedule_type,
                    error_message=f"Schedule with ID '{request.schedule_id}' not found",
                )
        else:
            # Create new schedule
            schedule = _create_new_schedule(request)
            schedules.append(schedule)

        # Save schedules to file
        _save_schedules(schedule_file, schedules)

        return ScheduleCheckinResult(
            success=True,
            agent_id=schedule.agent_id,
            message=schedule.message,
            schedule_time=schedule.schedule_time,
            schedule_type=schedule.schedule_type,
            schedule_id=schedule.schedule_id,
            recurring_interval=schedule.recurring_interval,
            recurring_days=schedule.recurring_days,
        )

    except PermissionError as e:
        return ScheduleCheckinResult(
            success=False,
            agent_id=request.agent_id,
            message=request.message,
            schedule_time=request.schedule_time,
            schedule_type=request.schedule_type,
            error_message=f"Permission denied accessing schedule file: {str(e)}",
        )
    except json.JSONDecodeError as e:
        return ScheduleCheckinResult(
            success=False,
            agent_id=request.agent_id,
            message=request.message,
            schedule_time=request.schedule_time,
            schedule_type=request.schedule_type,
            error_message=f"Invalid JSON in schedule file: {str(e)}",
        )
    except Exception as e:
        return ScheduleCheckinResult(
            success=False,
            agent_id=request.agent_id,
            message=request.message,
            schedule_time=request.schedule_time,
            schedule_type=request.schedule_type,
            error_message=f"Unexpected error scheduling check-in: {str(e)}",
        )


def _validate_request(request: ScheduleCheckinRequest) -> Optional[str]:
    """Validate schedule request parameters."""
    # Validate agent_id
    if not request.agent_id or not request.agent_id.strip():
        return "Agent ID cannot be empty"

    # Validate message
    if not request.message or not request.message.strip():
        return "Check-in message cannot be empty"

    # Validate schedule time is in future (unless updating existing)
    if not request.schedule_id and request.schedule_time <= datetime.now():
        return "Schedule time must be in the future"

    # Validate recurring schedule parameters
    if request.schedule_type == ScheduleType.RECURRING:
        if request.recurring_interval is None or request.recurring_interval <= 0:
            return "Recurring schedules must specify recurring_interval"

    # Validate weekly schedule parameters
    if request.schedule_type == ScheduleType.WEEKLY:
        if not request.recurring_days:
            return "Weekly schedules must specify recurring_days"

        valid_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        invalid_days = [day for day in request.recurring_days if day.lower() not in valid_days]
        if invalid_days:
            return f"Invalid weekday names: {', '.join(invalid_days)}"

    return None


def _check_scheduling_conflicts(schedules: list[CheckinSchedule], request: ScheduleCheckinRequest) -> Optional[str]:
    """Check for scheduling conflicts with existing active schedules."""
    conflict_window = timedelta(minutes=5)  # Consider schedules within 5 minutes as conflicts

    for schedule in schedules:
        if not schedule.is_active or schedule.agent_id != request.agent_id:
            continue

        # Check if schedules are too close in time
        time_diff = abs(schedule.schedule_time - request.schedule_time)
        if time_diff <= conflict_window:
            return f"Scheduling conflict: Agent '{request.agent_id}' already has a check-in scheduled at {schedule.schedule_time.strftime('%Y-%m-%d %H:%M:%S')}"

    return None


def _create_new_schedule(request: ScheduleCheckinRequest) -> CheckinSchedule:
    """Create a new CheckinSchedule from request."""
    schedule_id = str(uuid.uuid4())[:8]  # Use first 8 characters for readability

    return CheckinSchedule(
        schedule_id=schedule_id,
        agent_id=request.agent_id,
        message=request.message,
        schedule_time=request.schedule_time,
        schedule_type=request.schedule_type,
        recurring_interval=request.recurring_interval,
        recurring_days=request.recurring_days,
    )


def _update_existing_schedule(
    schedules: list[CheckinSchedule], request: ScheduleCheckinRequest
) -> Optional[CheckinSchedule]:
    """Update an existing schedule with new parameters."""
    for i, schedule in enumerate(schedules):
        if schedule.schedule_id == request.schedule_id:
            # Update the existing schedule
            schedules[i].agent_id = request.agent_id
            schedules[i].message = request.message
            schedules[i].schedule_time = request.schedule_time
            schedules[i].schedule_type = request.schedule_type
            schedules[i].recurring_interval = request.recurring_interval
            schedules[i].recurring_days = request.recurring_days
            return schedules[i]

    return None


def _get_schedule_file_path() -> Path:
    """Get the path to the schedule file."""
    # Store schedules in .tmux-orchestrator directory
    schedule_dir = Path.home() / ".tmux-orchestrator"
    schedule_dir.mkdir(exist_ok=True)
    return schedule_dir / "scheduled_checkins.json"


def _load_schedules(schedule_file: Path) -> list[CheckinSchedule]:
    """Load schedules from JSON file."""
    if not schedule_file.exists():
        return []

    with open(schedule_file) as f:
        data = json.load(f)

    schedules = []
    for item in data:
        # Convert datetime strings back to datetime objects
        item["schedule_time"] = datetime.fromisoformat(item["schedule_time"])
        if item.get("created_at"):
            item["created_at"] = datetime.fromisoformat(item["created_at"])
        if item.get("last_executed"):
            item["last_executed"] = datetime.fromisoformat(item["last_executed"])

        # Convert schedule_type string back to enum
        item["schedule_type"] = ScheduleType(item["schedule_type"])

        schedules.append(CheckinSchedule(**item))

    return schedules


def _save_schedules(schedule_file: Path, schedules: list[CheckinSchedule]) -> None:
    """Save schedules to JSON file."""
    # Convert schedules to JSON-serializable format
    data = []
    for schedule in schedules:
        schedule_dict = asdict(schedule)

        # Convert datetime objects to ISO format strings
        schedule_dict["schedule_time"] = schedule.schedule_time.isoformat()
        if schedule.created_at:
            schedule_dict["created_at"] = schedule.created_at.isoformat()
        if schedule.last_executed:
            schedule_dict["last_executed"] = schedule.last_executed.isoformat()

        # Convert enum to string
        schedule_dict["schedule_type"] = schedule.schedule_type.value

        data.append(schedule_dict)

    # Ensure directory exists
    schedule_file.parent.mkdir(parents=True, exist_ok=True)

    with open(schedule_file, "w") as f:
        json.dump(data, f, indent=2, default=str)

"""Business logic for reporting agent activity status."""

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from tmux_orchestrator.utils.tmux import TMUXManager


class ActivityType(Enum):
    """Types of agent activity."""

    WORKING = "working"
    IDLE = "idle"
    BLOCKED = "blocked"
    COMPLETED = "completed"


@dataclass
class ReportActivityRequest:
    """Request parameters for reporting agent activity."""

    agent_id: str
    activity_type: ActivityType
    description: str
    session_id: str | None = None
    team_id: str | None = None
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        """Initialize default values for mutable fields."""
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ActivityRecord:
    """Represents an agent activity record."""

    agent_id: str
    activity_type: ActivityType
    description: str
    session_id: str | None = None
    team_id: str | None = None
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None
    timestamp: datetime | None = None
    record_id: str | None = None

    def __post_init__(self) -> None:
        """Initialize default values and auto-generate fields."""
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.record_id is None:
            self.record_id = str(uuid.uuid4())[:12]  # Use first 12 characters for readability


@dataclass
class ReportActivityResult:
    """Result of reporting activity operation."""

    success: bool
    agent_id: str
    activity_type: ActivityType
    description: str
    timestamp: datetime
    record_id: str | None = None
    session_id: str | None = None
    team_id: str | None = None
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        """Initialize default values for mutable fields."""
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ActivityHistoryRequest:
    """Request parameters for retrieving activity history."""

    agent_id: str | None = None
    team_id: str | None = None
    session_id: str | None = None
    activity_types: list[ActivityType] | None = None
    since_timestamp: datetime | None = None
    limit: int = 100
    tags: list[str] | None = None

    def __post_init__(self) -> None:
        """Initialize default values for mutable fields."""
        if self.activity_types is None:
            self.activity_types = []
        if self.tags is None:
            self.tags = []


@dataclass
class ActivityHistoryResult:
    """Result of retrieving activity history."""

    success: bool
    records: list[ActivityRecord]
    total_records: int
    error_message: str | None = None


def report_activity(tmux: TMUXManager, request: ReportActivityRequest) -> ReportActivityResult:
    """
    Report agent activity status with persistence.

    Stores activity records with timestamps, agent identification, and metadata
    for tracking work status across teams and sessions.

    Args:
        tmux: TMUXManager instance for tmux operations
        request: ReportActivityRequest with activity details

    Returns:
        ReportActivityResult indicating success/failure and activity details

    Raises:
        ValueError: If request parameters are invalid
    """
    # Validate input parameters
    validation_error = _validate_report_request(request)
    if validation_error:
        return ReportActivityResult(
            success=False,
            agent_id=request.agent_id,
            activity_type=request.activity_type,
            description=request.description,
            timestamp=datetime.now(),
            error_message=validation_error,
        )

    try:
        # Load existing activities
        activity_file = _get_activity_file_path()
        activities = _load_activities(activity_file)

        # Create new activity record
        record = ActivityRecord(
            agent_id=request.agent_id,
            activity_type=request.activity_type,
            description=request.description,
            session_id=request.session_id,
            team_id=request.team_id,
            tags=request.tags.copy() if request.tags else [],
            metadata=request.metadata.copy() if request.metadata else {},
        )

        # Add record to activities list
        activities.append(record)

        # Save activities to file
        _save_activities(activity_file, activities)

        return ReportActivityResult(
            success=True,
            agent_id=record.agent_id,
            activity_type=record.activity_type,
            description=record.description,
            timestamp=record.timestamp or datetime.now(),
            record_id=record.record_id,
            session_id=record.session_id,
            team_id=record.team_id,
            tags=record.tags.copy(),
            metadata=record.metadata.copy(),
        )

    except PermissionError as e:
        return ReportActivityResult(
            success=False,
            agent_id=request.agent_id,
            activity_type=request.activity_type,
            description=request.description,
            timestamp=datetime.now(),
            error_message=f"Permission denied accessing activity file: {str(e)}",
        )
    except json.JSONDecodeError as e:
        return ReportActivityResult(
            success=False,
            agent_id=request.agent_id,
            activity_type=request.activity_type,
            description=request.description,
            timestamp=datetime.now(),
            error_message=f"Invalid JSON in activity file: {str(e)}",
        )
    except Exception as e:
        return ReportActivityResult(
            success=False,
            agent_id=request.agent_id,
            activity_type=request.activity_type,
            description=request.description,
            timestamp=datetime.now(),
            error_message=f"Unexpected error reporting activity: {str(e)}",
        )


def get_activity_history(tmux: TMUXManager, request: ActivityHistoryRequest) -> ActivityHistoryResult:
    """
    Retrieve activity history with optional filtering.

    Supports filtering by agent, team, session, activity types, timestamps, and tags.
    Results are sorted by timestamp in descending order (most recent first).

    Args:
        tmux: TMUXManager instance for tmux operations
        request: ActivityHistoryRequest with filter criteria

    Returns:
        ActivityHistoryResult with filtered activity records

    Raises:
        ValueError: If request parameters are invalid
    """
    try:
        # Load activities from file
        activity_file = _get_activity_file_path()
        activities = _load_activities(activity_file)

        # Apply filters
        filtered_activities = _apply_filters(activities, request)

        # Sort by timestamp descending (most recent first)
        filtered_activities.sort(key=lambda x: x.timestamp or datetime.min, reverse=True)

        # Apply limit
        total_records = len(filtered_activities)
        if request.limit > 0:
            filtered_activities = filtered_activities[: request.limit]

        return ActivityHistoryResult(
            success=True,
            records=filtered_activities,
            total_records=total_records,
        )

    except PermissionError as e:
        return ActivityHistoryResult(
            success=False,
            records=[],
            total_records=0,
            error_message=f"Permission denied accessing activity file: {str(e)}",
        )
    except json.JSONDecodeError as e:
        return ActivityHistoryResult(
            success=False,
            records=[],
            total_records=0,
            error_message=f"Invalid JSON in activity file: {str(e)}",
        )
    except Exception as e:
        return ActivityHistoryResult(
            success=False,
            records=[],
            total_records=0,
            error_message=f"Unexpected error retrieving activity history: {str(e)}",
        )


def _validate_report_request(request: ReportActivityRequest) -> str | None:
    """Validate activity report request parameters."""
    # Validate agent_id
    if not request.agent_id or not request.agent_id.strip():
        return "Agent ID cannot be empty"

    # Validate description
    if not request.description or not request.description.strip():
        return "Activity description cannot be empty"

    return None


def _apply_filters(activities: list[ActivityRecord], request: ActivityHistoryRequest) -> list[ActivityRecord]:
    """Apply filtering criteria to activity records."""
    filtered_activities = activities

    # Filter by agent_id
    if request.agent_id:
        filtered_activities = [a for a in filtered_activities if a.agent_id == request.agent_id]

    # Filter by team_id
    if request.team_id:
        filtered_activities = [a for a in filtered_activities if a.team_id == request.team_id]

    # Filter by session_id
    if request.session_id:
        filtered_activities = [a for a in filtered_activities if a.session_id == request.session_id]

    # Filter by activity types
    if request.activity_types:
        activity_type_values = [at.value if isinstance(at, ActivityType) else at for at in request.activity_types]
        filtered_activities = [
            a
            for a in filtered_activities
            if (a.activity_type.value if isinstance(a.activity_type, ActivityType) else a.activity_type)
            in activity_type_values
        ]

    # Filter by timestamp
    if request.since_timestamp:
        filtered_activities = [a for a in filtered_activities if a.timestamp and a.timestamp >= request.since_timestamp]

    # Filter by tags (must have all specified tags)
    if request.tags:
        filtered_activities = [a for a in filtered_activities if all(tag in a.tags for tag in request.tags)]

    return filtered_activities


def _get_activity_file_path() -> Path:
    """Get the path to the activity file."""
    # Store activities in .tmux-orchestrator directory
    activity_dir = Path.home() / ".tmux-orchestrator"
    activity_dir.mkdir(exist_ok=True)
    return activity_dir / "agent_activities.json"


def _load_activities(activity_file: Path) -> list[ActivityRecord]:
    """Load activity records from JSON file."""
    if not activity_file.exists():
        return []

    with open(activity_file) as f:
        data = json.load(f)

    activities = []
    for item in data:
        # Convert timestamp string back to datetime object
        if item.get("timestamp"):
            item["timestamp"] = datetime.fromisoformat(item["timestamp"])

        # Convert activity_type string back to enum
        if isinstance(item.get("activity_type"), str):
            item["activity_type"] = ActivityType(item["activity_type"])

        # Ensure required fields have defaults
        item.setdefault("tags", [])
        item.setdefault("metadata", {})

        activities.append(ActivityRecord(**item))

    return activities


def _save_activities(activity_file: Path, activities: list[ActivityRecord]) -> None:
    """Save activity records to JSON file."""
    # Convert activities to JSON-serializable format
    data = []
    for activity in activities:
        activity_dict = asdict(activity)

        # Convert datetime object to ISO format string
        if activity.timestamp:
            activity_dict["timestamp"] = activity.timestamp.isoformat()

        # Convert enum to string
        if isinstance(activity.activity_type, ActivityType):
            activity_dict["activity_type"] = activity.activity_type.value

        data.append(activity_dict)

    # Ensure directory exists
    activity_file.parent.mkdir(parents=True, exist_ok=True)

    with open(activity_file, "w") as f:
        json.dump(data, f, indent=2, default=str)

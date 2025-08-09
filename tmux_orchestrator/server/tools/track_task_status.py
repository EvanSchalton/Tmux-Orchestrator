"""Business logic for tracking task status and completion updates."""

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

from tmux_orchestrator.core.error_handler import (
    ErrorSeverity,
    handle_errors,
    retry_on_error,
)
from tmux_orchestrator.utils.tmux import TMUXManager


class TaskStatus(Enum):
    """Valid task status values."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


@dataclass
class TaskStatusRequest:
    """Request parameters for task status tracking."""

    task_id: str = ""
    agent_id: str = ""
    status: str = ""
    description: Optional[str] = None
    priority: str = "medium"
    estimated_hours: Optional[int] = None
    actual_hours: Optional[int] = None
    progress_percentage: Optional[int] = None
    completion_notes: Optional[str] = None
    blockers: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


@dataclass
class TaskStatusUpdate:
    """Internal model for task status updates."""

    task_id: str
    agent_id: str = ""
    status: str = ""
    description: Optional[str] = None
    priority: str = "medium"
    estimated_hours: Optional[int] = None
    actual_hours: Optional[int] = None
    progress_percentage: Optional[int] = None
    completion_notes: Optional[str] = None
    blockers: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    previous_status: Optional[str] = None


@dataclass
class TaskStatusResult:
    """Result of task status tracking operation."""

    success: bool
    task_id: str = ""
    agent_id: str = ""
    status: str = ""
    description: Optional[str] = None
    priority: str = "medium"
    estimated_hours: Optional[int] = None
    actual_hours: Optional[int] = None
    progress_percentage: Optional[int] = None
    completion_notes: Optional[str] = None
    blockers: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    previous_status: Optional[str] = None
    tracking_metadata: Optional[dict] = None
    error_message: Optional[str] = None


@dataclass
class TaskListResult:
    """Result of task listing operation."""

    success: bool
    tasks: list[TaskStatusUpdate] = field(default_factory=list)
    total_count: int = 0
    filtered_count: int = 0
    error_message: Optional[str] = None


def track_task_status(tmux: TMUXManager, request: TaskStatusRequest) -> TaskStatusResult:
    """
    Track task status updates from agents.

    Provides comprehensive task status tracking for agent coordination,
    including status changes, progress updates, blocker reporting, and
    completion tracking. Integrates with existing task management and
    supports filtering, persistence, and metadata collection.

    Args:
        tmux: TMUXManager instance for tmux operations
        request: TaskStatusRequest with task status information

    Returns:
        TaskStatusResult indicating success/failure and status details

    Raises:
        ValueError: If request parameters are invalid
        RuntimeError: If persistence operations fail
    """
    # Validate input parameters
    validation_error = _validate_request(request)
    if validation_error:
        return TaskStatusResult(
            success=False,
            task_id=request.task_id,
            agent_id=request.agent_id,
            error_message=validation_error,
        )

    try:
        # Load existing task status if it exists
        existing_task = _load_task_status(request.task_id)
        previous_status = existing_task.status if existing_task else None

        # Create updated task status
        now = datetime.now(timezone.utc)

        updated_task = TaskStatusUpdate(
            task_id=request.task_id,
            agent_id=request.agent_id,
            status=request.status,
            description=request.description,
            priority=request.priority,
            estimated_hours=request.estimated_hours,
            actual_hours=request.actual_hours,
            progress_percentage=request.progress_percentage,
            completion_notes=request.completion_notes,
            blockers=request.blockers,
            tags=request.tags,
            created_at=existing_task.created_at if existing_task else now,
            updated_at=now,
            previous_status=previous_status,
        )

        # Save updated task status
        success = _save_task_status(updated_task)
        if not success:
            return TaskStatusResult(
                success=False,
                task_id=request.task_id,
                agent_id=request.agent_id,
                error_message="Failed to save task status",
            )

        # Generate tracking metadata
        tracking_metadata = _generate_tracking_metadata(request.agent_id, now)

        return TaskStatusResult(
            success=True,
            task_id=updated_task.task_id,
            agent_id=updated_task.agent_id,
            status=updated_task.status,
            description=updated_task.description,
            priority=updated_task.priority,
            estimated_hours=updated_task.estimated_hours,
            actual_hours=updated_task.actual_hours,
            progress_percentage=updated_task.progress_percentage,
            completion_notes=updated_task.completion_notes,
            blockers=updated_task.blockers,
            tags=updated_task.tags,
            previous_status=previous_status,
            tracking_metadata=tracking_metadata,
        )

    except Exception as e:
        return TaskStatusResult(
            success=False,
            task_id=request.task_id,
            agent_id=request.agent_id,
            error_message=f"Unexpected error during task status tracking: {str(e)}",
        )


def get_task_status(request: TaskStatusRequest) -> TaskStatusResult:
    """
    Retrieve current status of a specific task.

    Args:
        request: TaskStatusRequest with task_id

    Returns:
        TaskStatusResult with current task status or error
    """
    try:
        if not request.task_id.strip():
            return TaskStatusResult(
                success=False,
                error_message="Task ID cannot be empty",
            )

        task_status = _load_task_status(request.task_id)
        if not task_status:
            return TaskStatusResult(
                success=False,
                task_id=request.task_id,
                error_message=f"Task '{request.task_id}' not found",
            )

        return TaskStatusResult(
            success=True,
            task_id=task_status.task_id,
            agent_id=task_status.agent_id,
            status=task_status.status,
            description=task_status.description,
            priority=task_status.priority,
            estimated_hours=task_status.estimated_hours,
            actual_hours=task_status.actual_hours,
            progress_percentage=task_status.progress_percentage,
            completion_notes=task_status.completion_notes,
            blockers=task_status.blockers,
            tags=task_status.tags,
            previous_status=task_status.previous_status,
        )

    except Exception as e:
        return TaskStatusResult(
            success=False,
            task_id=request.task_id,
            error_message=f"Error retrieving task status: {str(e)}",
        )


def update_task_status(tmux: TMUXManager, request: TaskStatusRequest) -> TaskStatusResult:
    """
    Update existing task status with new information.

    Args:
        tmux: TMUXManager instance for tmux operations
        request: TaskStatusRequest with updated status information

    Returns:
        TaskStatusResult indicating success/failure and updated details
    """
    try:
        # Verify task exists
        existing_task = _load_task_status(request.task_id)
        if not existing_task:
            return TaskStatusResult(
                success=False,
                task_id=request.task_id,
                error_message=f"Task '{request.task_id}' not found",
            )

        # Update with new status information
        return track_task_status(tmux, request)

    except Exception as e:
        return TaskStatusResult(
            success=False,
            task_id=request.task_id,
            error_message=f"Error updating task status: {str(e)}",
        )


def list_tasks_by_status(request: TaskStatusRequest) -> TaskListResult:
    """
    List tasks filtered by status, agent, or other criteria.

    Args:
        request: TaskStatusRequest with filtering criteria

    Returns:
        TaskListResult with filtered task list or error
    """
    try:
        all_tasks = _load_all_task_statuses()
        filtered_tasks = all_tasks

        # Apply status filter
        if request.status and request.status.strip():
            filtered_tasks = [task for task in filtered_tasks if task.status == request.status]

        # Apply agent filter
        if request.agent_id and request.agent_id.strip():
            filtered_tasks = [task for task in filtered_tasks if task.agent_id == request.agent_id]

        # Sort by updated_at descending (most recent first)
        filtered_tasks.sort(key=lambda t: t.updated_at or t.created_at or datetime.min, reverse=True)

        return TaskListResult(
            success=True,
            tasks=filtered_tasks,
            total_count=len(all_tasks),
            filtered_count=len(filtered_tasks),
        )

    except Exception as e:
        return TaskListResult(
            success=False,
            error_message=f"Error listing tasks: {str(e)}",
        )


def _validate_request(request: TaskStatusRequest) -> Optional[str]:
    """Validate task status request parameters."""
    # Validate task ID
    if not request.task_id.strip():
        return "Task ID cannot be empty"

    # Validate agent ID for tracking operations
    if request.status and request.status.strip():  # Only require agent_id for status updates
        if not request.agent_id or not request.agent_id.strip():
            return "Agent ID cannot be empty"

        agent_pattern = r"^[^:]+:[^:]+$"
        if not re.match(agent_pattern, request.agent_id):
            return "Agent ID must be in format 'session:window'"

    # Validate status if provided
    if request.status and request.status.strip():
        valid_statuses = [status.value for status in TaskStatus]
        if request.status not in valid_statuses:
            return f"Invalid status '{request.status}'. Must be one of: {', '.join(valid_statuses)}"

    # Validate priority
    valid_priorities = ["low", "medium", "high", "critical"]
    if request.priority not in valid_priorities:
        return f"Invalid priority '{request.priority}'. Must be one of: {', '.join(valid_priorities)}"

    # Validate progress percentage
    if request.progress_percentage is not None:
        if not 0 <= request.progress_percentage <= 100:
            return "Progress percentage must be between 0 and 100"

    # Validate estimated/actual hours
    if request.estimated_hours is not None and request.estimated_hours < 0:
        return "Estimated hours must be non-negative"

    if request.actual_hours is not None and request.actual_hours < 0:
        return "Actual hours must be non-negative"

    return None


def _get_task_status_file_path(task_id: str) -> Path:
    """Get file path for task status storage."""
    home_dir = Path.home() / ".tmux-orchestrator"
    tasks_dir = home_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    return tasks_dir / f"{task_id}.json"


@retry_on_error(max_attempts=3, initial_delay=0.1, exceptions=(IOError, OSError))
def _load_task_status(task_id: str) -> Optional[TaskStatusUpdate]:
    """Load task status from persistent storage."""
    try:
        file_path = _get_task_status_file_path(task_id)
        if not file_path.exists():
            return None

        with open(file_path) as f:
            data = json.load(f)

        # Convert timestamps back to datetime objects
        if data.get("created_at"):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])

        return TaskStatusUpdate(**data)

    except Exception:
        return None


@retry_on_error(max_attempts=3, initial_delay=0.1, exceptions=(IOError, OSError))
@handle_errors(severity=ErrorSeverity.HIGH, operation="save_task_status", attempt_recovery=True)
def _save_task_status(task_status: TaskStatusUpdate) -> bool:
    """Save task status to persistent storage."""
    try:
        file_path = _get_task_status_file_path(task_status.task_id)

        # Convert to dictionary for JSON serialization
        data = {
            "task_id": task_status.task_id,
            "agent_id": task_status.agent_id,
            "status": task_status.status,
            "description": task_status.description,
            "priority": task_status.priority,
            "estimated_hours": task_status.estimated_hours,
            "actual_hours": task_status.actual_hours,
            "progress_percentage": task_status.progress_percentage,
            "completion_notes": task_status.completion_notes,
            "blockers": task_status.blockers,
            "tags": task_status.tags,
            "created_at": task_status.created_at.isoformat() if task_status.created_at else None,
            "updated_at": task_status.updated_at.isoformat() if task_status.updated_at else None,
            "previous_status": task_status.previous_status,
        }

        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)

        return True

    except Exception:
        return False


def _load_all_task_statuses() -> list[TaskStatusUpdate]:
    """Load all task statuses from persistent storage."""
    try:
        tasks_dir = Path.home() / ".tmux-orchestrator" / "tasks"
        if not tasks_dir.exists():
            return []

        tasks = []
        for file_path in tasks_dir.glob("*.json"):
            try:
                with open(file_path) as f:
                    data = json.load(f)

                # Convert timestamps back to datetime objects
                if data.get("created_at"):
                    data["created_at"] = datetime.fromisoformat(data["created_at"])
                if data.get("updated_at"):
                    data["updated_at"] = datetime.fromisoformat(data["updated_at"])

                tasks.append(TaskStatusUpdate(**data))

            except Exception:
                continue  # Skip corrupted files

        return tasks

    except Exception:
        return []


def _generate_tracking_metadata(agent_id: str, timestamp: datetime) -> dict:
    """Generate tracking metadata for task status updates."""
    metadata = {
        "tracking_id": str(uuid.uuid4()),
        "tracked_at": timestamp.isoformat(),
    }

    # Extract session and window from agent_id
    if agent_id and ":" in agent_id:
        session, window = agent_id.split(":", 1)
        metadata["session"] = session
        metadata["window"] = window

    return metadata

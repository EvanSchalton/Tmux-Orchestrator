"""Business logic for assigning tasks to agents dynamically."""

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from tmux_orchestrator.core.error_handler import (
    ErrorSeverity,
    handle_errors,
)
from tmux_orchestrator.utils.tmux import TMUXManager


@dataclass
class AssignTaskRequest:
    """Request parameters for task assignment operations."""

    task_id: str = ""
    agent_id: str = ""
    task_title: Optional[str] = None
    task_description: Optional[str] = None
    priority: str = "medium"
    estimated_hours: Optional[int] = None
    due_date: Optional[str] = None
    dependencies: list[str] = field(default_factory=list)
    completion_criteria: list[str] = field(default_factory=list)
    required_skills: list[str] = field(default_factory=list)
    load_balance: bool = False
    reason: Optional[str] = None


@dataclass
class AssignTaskResult:
    """Result of task assignment operation."""

    success: bool
    task_id: str = ""
    assigned_agent: str = ""
    previous_agent: Optional[str] = None
    task_title: Optional[str] = None
    priority: str = "medium"
    estimated_hours: Optional[int] = None
    due_date: Optional[str] = None
    dependencies: list[str] = field(default_factory=list)
    completion_criteria: list[str] = field(default_factory=list)
    reason: Optional[str] = None
    assignment_metadata: Optional[dict] = None
    error_message: Optional[str] = None


@dataclass
class AgentWorkloadResult:
    """Result of agent workload query."""

    success: bool
    agent_id: str = ""
    total_tasks: int = 0
    active_tasks: int = 0
    pending_tasks: int = 0
    completed_tasks: int = 0
    total_estimated_hours: int = 0
    task_list: list[dict] = field(default_factory=list)
    error_message: Optional[str] = None


@dataclass
class AvailableAgentsResult:
    """Result of available agents query."""

    success: bool
    available_agents: list[dict] = field(default_factory=list)
    total_agents: int = 0
    filtered_agents: int = 0
    error_message: Optional[str] = None


@handle_errors(severity=ErrorSeverity.HIGH, operation="assign_task", attempt_recovery=True)
def assign_task(tmux: TMUXManager, request: AssignTaskRequest) -> AssignTaskResult:
    """
    Assign tasks dynamically to agents with load balancing.

    Enables PM agents to assign tasks to team members with intelligent
    load balancing, skill matching, and workload distribution. Supports
    task dependencies, completion criteria, and priority management for
    comprehensive project coordination.

    Args:
        tmux: TMUXManager instance for tmux operations
        request: AssignTaskRequest with assignment configuration

    Returns:
        AssignTaskResult indicating success/failure and assignment details

    Raises:
        ValueError: If request parameters are invalid
        RuntimeError: If assignment operations fail
    """
    # Validate input parameters
    validation_error = _validate_request(request)
    if validation_error:
        return AssignTaskResult(
            success=False,
            task_id=request.task_id,
            assigned_agent=request.agent_id,
            error_message=validation_error,
        )

    try:
        # Verify agent is accessible
        agent_status = tmux.capture_pane(request.agent_id)
        if agent_status is None:
            return AssignTaskResult(
                success=False,
                task_id=request.task_id,
                assigned_agent=request.agent_id,
                error_message=f"Agent '{request.agent_id}' is not accessible or offline",
            )

        # Create assignment record
        now = datetime.now(timezone.utc)
        assignment = {
            "assignment_id": str(uuid.uuid4()),
            "task_id": request.task_id,
            "agent_id": request.agent_id,
            "task_title": request.task_title,
            "task_description": request.task_description,
            "priority": request.priority,
            "estimated_hours": request.estimated_hours,
            "due_date": request.due_date,
            "dependencies": request.dependencies,
            "completion_criteria": request.completion_criteria,
            "status": "assigned",
            "assigned_at": now.isoformat(),
            "assigned_by": "orchestrator",  # Could be enhanced to track who assigned
        }

        # Save assignment record
        save_success = _save_assignment(assignment)
        if not save_success:
            return AssignTaskResult(
                success=False,
                task_id=request.task_id,
                assigned_agent=request.agent_id,
                error_message="Failed to save task assignment",
            )

        # Update task status in task tracking system
        update_success = _update_task_status(request.task_id, "assigned", request.agent_id)
        if not update_success:
            # Log warning but don't fail assignment
            pass

        # Send assignment message to agent
        assignment_message = _create_assignment_message(request)
        message_success = tmux.send_keys(request.agent_id, assignment_message)
        if not message_success:
            return AssignTaskResult(
                success=False,
                task_id=request.task_id,
                assigned_agent=request.agent_id,
                error_message="Failed to send assignment message",
            )

        # Generate assignment metadata
        assignment_metadata = _generate_assignment_metadata(request, now)

        return AssignTaskResult(
            success=True,
            task_id=request.task_id,
            assigned_agent=request.agent_id,
            task_title=request.task_title,
            priority=request.priority,
            estimated_hours=request.estimated_hours,
            due_date=request.due_date,
            dependencies=request.dependencies,
            completion_criteria=request.completion_criteria,
            assignment_metadata=assignment_metadata,
        )

    except Exception as e:
        return AssignTaskResult(
            success=False,
            task_id=request.task_id,
            assigned_agent=request.agent_id,
            error_message=f"Unexpected error during task assignment: {str(e)}",
        )


def get_agent_workload(request: AssignTaskRequest) -> AgentWorkloadResult:
    """
    Get current workload information for a specific agent.

    Args:
        request: AssignTaskRequest with agent_id

    Returns:
        AgentWorkloadResult with workload details or error
    """
    try:
        if not request.agent_id.strip():
            return AgentWorkloadResult(
                success=False,
                error_message="Agent ID cannot be empty",
            )

        assignments = _load_agent_assignments(request.agent_id)

        # Calculate workload metrics
        total_tasks = len(assignments)
        active_tasks = len([a for a in assignments if a.get("status") in ["assigned", "in_progress"]])
        pending_tasks = len([a for a in assignments if a.get("status") == "pending"])
        completed_tasks = len([a for a in assignments if a.get("status") == "completed"])

        total_estimated_hours = sum(a.get("estimated_hours", 0) or 0 for a in assignments)

        return AgentWorkloadResult(
            success=True,
            agent_id=request.agent_id,
            total_tasks=total_tasks,
            active_tasks=active_tasks,
            pending_tasks=pending_tasks,
            completed_tasks=completed_tasks,
            total_estimated_hours=total_estimated_hours,
            task_list=assignments,
        )

    except Exception as e:
        return AgentWorkloadResult(
            success=False,
            agent_id=request.agent_id,
            error_message=f"Error retrieving agent workload: {str(e)}",
        )


def list_available_agents(tmux: TMUXManager, request: AssignTaskRequest) -> AvailableAgentsResult:
    """
    List available agents with workload information for load balancing.

    Args:
        tmux: TMUXManager instance for tmux operations
        request: AssignTaskRequest with filtering criteria

    Returns:
        AvailableAgentsResult with available agent list or error
    """
    try:
        available_agents = []

        # Get all active sessions
        sessions = tmux.list_sessions() or []

        for session_dict in sessions:
            session_name = session_dict["name"]
            # Get windows for each session
            windows = tmux.list_windows(session_name) or []

            for window_dict in windows:
                window_index = window_dict["index"]
                agent_id = f"{session_name}:{window_index}"

                # Check if agent is accessible
                if tmux.capture_pane(agent_id):
                    # Get agent workload
                    assignments = _load_agent_assignments(agent_id)
                    active_tasks = len([a for a in assignments if a.get("status") in ["assigned", "in_progress"]])
                    total_hours = sum(a.get("estimated_hours", 0) or 0 for a in assignments)

                    # Check skill requirements if specified
                    if request.required_skills:
                        agent_skills = _get_agent_skills(agent_id)
                        if not all(skill in agent_skills for skill in request.required_skills):
                            continue  # Skip agents without required skills

                    # Calculate load score for sorting
                    load_score = _calculate_load_score(active_tasks, total_hours)

                    agent_info = {
                        "agent_id": agent_id,
                        "session": session_name,
                        "window": window_index,
                        "active_tasks": active_tasks,
                        "total_estimated_hours": total_hours,
                        "load_score": load_score,
                        "available": True,
                    }

                    available_agents.append(agent_info)

        # Sort by load score (ascending - lower load first)
        available_agents.sort(key=lambda x: x["load_score"])

        return AvailableAgentsResult(
            success=True,
            available_agents=available_agents,
            total_agents=len(available_agents),
            filtered_agents=len(available_agents),
        )

    except Exception as e:
        return AvailableAgentsResult(
            success=False,
            error_message=f"Error listing available agents: {str(e)}",
        )


def reassign_task(tmux: TMUXManager, request: AssignTaskRequest) -> AssignTaskResult:
    """
    Reassign an existing task to a different agent.

    Args:
        tmux: TMUXManager instance for tmux operations
        request: AssignTaskRequest with new assignment details

    Returns:
        AssignTaskResult indicating success/failure and reassignment details
    """
    try:
        # Load existing assignment
        existing_assignment = _load_assignment(request.task_id)
        if not existing_assignment:
            return AssignTaskResult(
                success=False,
                task_id=request.task_id,
                error_message=f"Task assignment '{request.task_id}' not found",
            )

        previous_agent = existing_assignment.get("agent_id")

        # Create new assignment with updated agent
        request_copy = AssignTaskRequest(
            task_id=request.task_id,
            agent_id=request.agent_id,
            task_title=existing_assignment.get("task_title"),
            task_description=existing_assignment.get("task_description"),
            priority=existing_assignment.get("priority", "medium"),
            estimated_hours=existing_assignment.get("estimated_hours"),
            due_date=existing_assignment.get("due_date"),
            dependencies=existing_assignment.get("dependencies", []),
            completion_criteria=existing_assignment.get("completion_criteria", []),
            reason=request.reason,
        )

        # Perform the reassignment
        result = assign_task(tmux, request_copy)
        if result.success:
            result.previous_agent = previous_agent
            result.reason = request.reason

        return result

    except Exception as e:
        return AssignTaskResult(
            success=False,
            task_id=request.task_id,
            error_message=f"Error reassigning task: {str(e)}",
        )


def _validate_request(request: AssignTaskRequest) -> Optional[str]:
    """Validate task assignment request parameters."""
    # Validate task ID
    if not request.task_id.strip():
        return "Task ID cannot be empty"

    # Validate agent ID
    if not request.agent_id.strip():
        return "Agent ID cannot be empty"

    agent_pattern = r"^[^:]+:[^:]+$"
    if not re.match(agent_pattern, request.agent_id):
        return "Agent ID must be in format 'session:window'"

    # Validate priority
    valid_priorities = ["low", "medium", "high", "critical"]
    if request.priority not in valid_priorities:
        return f"Invalid priority '{request.priority}'. Must be one of: {', '.join(valid_priorities)}"

    # Validate estimated hours
    if request.estimated_hours is not None and request.estimated_hours < 0:
        return "Estimated hours must be non-negative"

    return None


def _get_assignments_dir() -> Path:
    """Get the directory for storing task assignments."""
    home_dir = Path.home() / ".tmux-orchestrator"
    assignments_dir = home_dir / "assignments"
    assignments_dir.mkdir(parents=True, exist_ok=True)
    return assignments_dir


def _save_assignment(assignment: dict) -> bool:
    """Save task assignment to persistent storage."""
    try:
        assignments_dir = _get_assignments_dir()
        file_path = assignments_dir / f"{assignment['task_id']}.json"

        with open(file_path, "w") as f:
            json.dump(assignment, f, indent=2)

        return True

    except Exception:
        return False


def _load_assignment(task_id: str) -> Optional[dict]:
    """Load task assignment from persistent storage."""
    try:
        assignments_dir = _get_assignments_dir()
        file_path = assignments_dir / f"{task_id}.json"

        if not file_path.exists():
            return None

        with open(file_path) as f:
            data = json.load(f)
            return data if isinstance(data, dict) else None

    except Exception:
        return None


def _load_agent_assignments(agent_id: str) -> list[dict]:
    """Load all assignments for a specific agent."""
    try:
        assignments_dir = _get_assignments_dir()
        if not assignments_dir.exists():
            return []

        assignments = []
        for file_path in assignments_dir.glob("*.json"):
            try:
                with open(file_path) as f:
                    assignment = json.load(f)

                if assignment.get("agent_id") == agent_id:
                    assignments.append(assignment)

            except Exception:
                continue  # Skip corrupted files

        return assignments

    except Exception:
        return []


def _update_task_status(task_id: str, status: str, agent_id: str) -> bool:
    """Update task status in the task tracking system."""
    try:
        # This would integrate with the task status tracking system
        # For now, we'll just return True to indicate the integration point
        return True
    except Exception:
        return False


def _get_agent_skills(agent_id: str) -> list[str]:
    """Get skills/capabilities for an agent (placeholder for future enhancement)."""
    # This is a placeholder - in a real implementation, this could:
    # - Read from agent configuration files
    # - Query agent capabilities via MCP
    # - Use machine learning to infer skills from past tasks

    # For now, return basic skills based on session name
    session = agent_id.split(":")[0]
    if "dev" in session.lower():
        return ["python", "javascript", "api", "backend", "frontend"]
    elif "qa" in session.lower():
        return ["testing", "automation", "quality-assurance"]
    elif "devops" in session.lower():
        return ["docker", "kubernetes", "ci-cd", "deployment"]
    else:
        return ["general"]


def _calculate_load_score(active_tasks: int, total_hours: int) -> float:
    """Calculate a load score for load balancing (0.0 = no load, 1.0 = maximum load)."""
    # Simple scoring algorithm - can be enhanced based on requirements
    task_score = min(active_tasks / 10.0, 1.0)  # Normalize to 10 max active tasks
    hours_score = min(total_hours / 80.0, 1.0)  # Normalize to 80 hours max
    return (task_score + hours_score) / 2.0


def _create_assignment_message(request: AssignTaskRequest) -> str:
    """Create formatted assignment message for the target agent."""
    message_parts = [
        "===== TASK ASSIGNMENT =====",
        f"Task ID: {request.task_id}",
    ]

    if request.task_title:
        message_parts.append(f"Title: {request.task_title}")

    if request.task_description:
        message_parts.extend(
            [
                "",
                "DESCRIPTION:",
                request.task_description,
            ]
        )

    message_parts.extend(
        [
            "",
            f"Priority: {request.priority}",
        ]
    )

    if request.estimated_hours:
        message_parts.append(f"Estimated Hours: {request.estimated_hours}")

    if request.due_date:
        message_parts.append(f"Due Date: {request.due_date}")

    if request.dependencies:
        message_parts.extend(
            [
                "",
                "DEPENDENCIES:",
                ", ".join(request.dependencies),
            ]
        )

    if request.completion_criteria:
        message_parts.extend(
            [
                "",
                "COMPLETION CRITERIA:",
                *[f"- {criterion}" for criterion in request.completion_criteria],
            ]
        )

    message_parts.extend(
        [
            "",
            "Please acknowledge this assignment and update task status as you progress.",
            "===== END ASSIGNMENT =====",
        ]
    )

    return "\n".join(message_parts)


def _generate_assignment_metadata(request: AssignTaskRequest, timestamp: datetime) -> dict:
    """Generate assignment metadata for tracking and coordination."""
    metadata = {
        "assignment_id": str(uuid.uuid4()),
        "assigned_at": timestamp.isoformat(),
        "load_balanced": request.load_balance,
    }

    # Add load balancing metrics if enabled
    if request.load_balance:
        # Get current agent workload for load score
        assignments = _load_agent_assignments(request.agent_id)
        active_tasks = len([a for a in assignments if a.get("status") in ["assigned", "in_progress"]])
        total_hours = sum(a.get("estimated_hours", 0) or 0 for a in assignments)
        load_score = _calculate_load_score(active_tasks, total_hours)
        metadata["load_score"] = load_score

    # Extract session and window information
    if ":" in request.agent_id:
        session, window = request.agent_id.split(":", 1)
        metadata["session"] = session
        metadata["window"] = window

    return metadata

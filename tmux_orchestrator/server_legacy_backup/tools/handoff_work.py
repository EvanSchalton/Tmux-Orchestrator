"""Business logic for handing off work between agents."""

import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from tmux_orchestrator.utils.tmux import TMUXManager


@dataclass
class HandoffWorkRequest:
    """Request parameters for handing off work between agents."""

    from_agent: str
    to_agent: str
    work_description: str
    preserve_context: bool = True
    priority: str = "medium"
    deadline: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class HandoffWorkResult:
    """Result of work handoff operation."""

    success: bool
    from_agent: str = ""
    to_agent: str = ""
    work_description: str = ""
    context_preserved: bool = False
    priority: Optional[str] = None
    deadline: Optional[str] = None
    notes: Optional[str] = None
    handoff_metadata: Optional[dict] = None
    error_message: Optional[str] = None


def handoff_work(tmux: TMUXManager, request: HandoffWorkRequest) -> HandoffWorkResult:
    """
    Hand off work from one agent to another with context preservation.

    Enables smooth work transfer between agents by communicating task details,
    preserving work context when requested, and maintaining continuity across
    agent transitions. Supports priority levels, deadlines, and additional notes
    for comprehensive handoff coordination.

    Args:
        tmux: TMUXManager instance for tmux operations
        request: HandoffWorkRequest with handoff configuration

    Returns:
        HandoffWorkResult indicating success/failure and handoff details

    Raises:
        ValueError: If request parameters are invalid
        RuntimeError: If tmux operations fail
    """
    # Validate input parameters
    validation_error = _validate_request(request)
    if validation_error:
        return HandoffWorkResult(
            success=False,
            from_agent=request.from_agent if request.from_agent.strip() else "",
            to_agent=request.to_agent if request.to_agent.strip() else "",
            work_description=request.work_description,
            error_message=validation_error,
        )

    try:
        # Verify both agents exist and are accessible
        from_context = None
        if request.preserve_context:
            from_context = tmux.capture_pane(request.from_agent)
            if from_context is None:
                return HandoffWorkResult(
                    success=False,
                    from_agent=request.from_agent,
                    to_agent=request.to_agent,
                    error_message=f"From agent '{request.from_agent}' not found or not accessible",
                )

        # Verify target agent exists
        to_verification = tmux.capture_pane(request.to_agent)
        if to_verification is None:
            return HandoffWorkResult(
                success=False,
                from_agent=request.from_agent,
                to_agent=request.to_agent,
                error_message=f"To agent '{request.to_agent}' not found or not accessible",
            )

        # Generate handoff message
        handoff_message = _create_handoff_message(
            from_agent=request.from_agent,
            work_description=request.work_description,
            context=from_context if request.preserve_context else None,
            priority=request.priority,
            deadline=request.deadline,
            notes=request.notes,
        )

        # Send handoff message to target agent
        success = tmux.send_keys(request.to_agent, handoff_message)
        if not success:
            return HandoffWorkResult(
                success=False,
                from_agent=request.from_agent,
                to_agent=request.to_agent,
                error_message=f"Failed to send handoff message to {request.to_agent}",
            )

        # Generate handoff metadata for tracking
        handoff_metadata = _generate_handoff_metadata(
            from_agent=request.from_agent,
            to_agent=request.to_agent,
            work_description=request.work_description,
            priority=request.priority,
            deadline=request.deadline,
            context_preserved=request.preserve_context,
        )

        return HandoffWorkResult(
            success=True,
            from_agent=request.from_agent,
            to_agent=request.to_agent,
            work_description=request.work_description,
            context_preserved=request.preserve_context,
            priority=request.priority,
            deadline=request.deadline,
            notes=request.notes,
            handoff_metadata=handoff_metadata,
        )

    except Exception as e:
        return HandoffWorkResult(
            success=False,
            from_agent=request.from_agent,
            to_agent=request.to_agent,
            error_message=f"Unexpected error during work handoff: {str(e)}",
        )


def _validate_request(request: HandoffWorkRequest) -> Optional[str]:
    """Validate handoff work request parameters."""
    # Validate agent identifiers
    if not request.from_agent.strip():
        return "From agent cannot be empty"

    if not request.to_agent.strip():
        return "To agent cannot be empty"

    # Validate agent format (session:window)
    agent_pattern = r"^[^:]+:[^:]+$"
    if not re.match(agent_pattern, request.from_agent):
        return "From agent must be in format 'session:window'"

    if not re.match(agent_pattern, request.to_agent):
        return "To agent must be in format 'session:window'"

    # Prevent self-handoff
    if request.from_agent == request.to_agent:
        return "Cannot handoff work to the same agent"

    # Validate work description
    if not request.work_description.strip():
        return "Work description cannot be empty"

    if len(request.work_description) > 2000:
        return "Work description must be 2000 characters or less"

    # Validate priority
    valid_priorities = ["low", "medium", "high", "critical"]
    if request.priority not in valid_priorities:
        return f"Priority must be one of: {', '.join(valid_priorities)}"

    # Validate notes length
    if request.notes and len(request.notes) > 1000:
        return "Notes must be 1000 characters or less"

    return None


def _create_handoff_message(
    from_agent: str,
    work_description: str,
    context: Optional[str],
    priority: str,
    deadline: Optional[str],
    notes: Optional[str],
) -> str:
    """Create formatted handoff message for target agent."""
    message_parts = [
        f"===== WORK HANDOFF FROM: {from_agent} =====",
        "",
        f"DESCRIPTION: {work_description}",
        f"Priority: {priority}",
    ]

    if deadline:
        message_parts.append(f"Deadline: {deadline}")

    message_parts.append("")

    # Add context if provided
    if context:
        # Truncate context if too long to avoid message size issues
        truncated_context = context
        if len(context) > 3000:
            truncated_context = context[:3000] + "... [context truncated]"

        message_parts.extend(
            [
                "CONTEXT:",
                truncated_context,
                "",
            ]
        )

    # Add notes if provided
    if notes:
        message_parts.extend(
            [
                "NOTES:",
                notes,
                "",
            ]
        )

    message_parts.append("===== END HANDOFF =====")

    return "\n".join(message_parts)


def _generate_handoff_metadata(
    from_agent: str,
    to_agent: str,
    work_description: str,
    priority: str,
    deadline: Optional[str],
    context_preserved: bool,
) -> dict:
    """Generate comprehensive handoff metadata for tracking and coordination."""
    now = datetime.now(timezone.utc)
    handoff_id = str(uuid.uuid4())

    metadata = {
        "handoff_id": handoff_id,
        "timestamp": now.isoformat(),
        "from_agent": from_agent,
        "to_agent": to_agent,
        "work_description": work_description,
        "priority": priority,
        "context_preserved": context_preserved,
    }

    if deadline:
        metadata["deadline"] = deadline

    # Extract session information
    from_session = from_agent.split(":")[0]
    to_session = to_agent.split(":")[0]

    metadata["from_session"] = from_session
    metadata["to_session"] = to_session
    metadata["cross_session"] = from_session != to_session

    return metadata

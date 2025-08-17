"""Business logic for retrieving agent status and health metrics."""

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from tmux_orchestrator.server.tools.report_activity import (
    ActivityRecord,
    ActivityType,
    _get_activity_file_path,
    _load_activities,
)
from tmux_orchestrator.utils.tmux import TMUXManager


class HealthStatus(Enum):
    """Agent health status indicators."""

    HEALTHY = "healthy"
    IDLE = "idle"
    BLOCKED = "blocked"
    OFFLINE = "offline"
    UNRESPONSIVE = "unresponsive"
    DEGRADED = "degraded"


@dataclass
class AgentHealthMetrics:
    """Health metrics for an agent."""

    agent_id: str
    health_status: HealthStatus
    session_active: bool
    last_activity_time: datetime | None = None
    last_activity_type: ActivityType | None = None
    last_activity_description: str | None = None
    responsiveness_score: float | None = None
    session_info: dict[str, Any] | None = None
    team_id: str | None = None
    activity_tags: list[str] | None = None
    activity_history: list[ActivityRecord] | None = None

    def __post_init__(self) -> None:
        """Initialize default values for mutable fields."""
        if self.session_info is None:
            self.session_info = {}
        if self.activity_tags is None:
            self.activity_tags = []
        if self.activity_history is None:
            self.activity_history = []


@dataclass
class AgentStatusRequest:
    """Request parameters for retrieving agent status."""

    agent_id: str | None = None
    target: str | None = None  # session:window format
    team_id: str | None = None
    include_activity_history: bool = False
    activity_limit: int = 10

    def __post_init__(self) -> None:
        """Initialize default values."""
        pass


@dataclass
class AgentStatusResult:
    """Result of retrieving agent status."""

    success: bool
    agent_metrics: list[AgentHealthMetrics]
    total_agents: int = 0
    error_message: str | None = None


def get_agent_status(tmux: TMUXManager, request: AgentStatusRequest) -> AgentStatusResult:
    """
    Retrieve agent status and health metrics for peer monitoring.

    Supports checking individual agent status by agent_id or session:window target,
    as well as team health checks. Integrates with existing activity tracking to
    provide comprehensive status information including health metrics, activity
    status, responsiveness, and session status.

    Args:
        tmux: TMUXManager instance for tmux operations
        request: AgentStatusRequest with query criteria

    Returns:
        AgentStatusResult with agent health metrics and status information

    Raises:
        ValueError: If request parameters are invalid
    """
    # Validate input parameters
    validation_error = _validate_request(request)
    if validation_error:
        return AgentStatusResult(
            success=False,
            agent_metrics=[],
            error_message=validation_error,
        )

    try:
        # Load activity data
        activity_file = _get_activity_file_path()
        activities = _load_activities(activity_file)

        # Get active agents from tmux
        active_agents = tmux.list_agents()

        # Determine which agents to analyze
        target_agents = _determine_target_agents(request, active_agents, activities)
        if not target_agents and request.agent_id:
            return AgentStatusResult(
                success=False,
                agent_metrics=[],
                error_message=f"Agent '{request.agent_id}' not found",
            )

        # Analyze each agent
        agent_metrics = []
        for agent_info in target_agents:
            metrics = _analyze_agent_health(
                agent_info, activities, active_agents, tmux, request.include_activity_history, request.activity_limit
            )
            agent_metrics.append(metrics)

        return AgentStatusResult(
            success=True,
            agent_metrics=agent_metrics,
            total_agents=len(agent_metrics),
        )

    except PermissionError as e:
        return AgentStatusResult(
            success=False,
            agent_metrics=[],
            error_message=f"Permission denied accessing activity file: {str(e)}",
        )
    except json.JSONDecodeError as e:
        return AgentStatusResult(
            success=False,
            agent_metrics=[],
            error_message=f"Invalid JSON in activity file: {str(e)}",
        )
    except Exception as e:
        return AgentStatusResult(
            success=False,
            agent_metrics=[],
            error_message=f"Unexpected error retrieving agent status: {str(e)}",
        )


def _validate_request(request: AgentStatusRequest) -> str | None:
    """Validate agent status request parameters."""
    # Must specify exactly one search criteria
    criteria_count = sum(1 for x in [request.agent_id, request.target, request.team_id] if x is not None)

    if criteria_count == 0:
        return "Must specify agent_id, target, or team_id"

    if criteria_count > 1:
        return "Only one of agent_id, target, or team_id can be specified"

    # Validate agent_id
    if request.agent_id is not None and not request.agent_id.strip():
        return "Agent ID cannot be empty"

    # Validate target format
    if request.target is not None:
        if ":" not in request.target:
            return "Target must be in format 'session:window'"

    # Validate activity_limit
    if request.activity_limit < 0:
        return "Activity limit must be non-negative"

    return None


def _determine_target_agents(
    request: AgentStatusRequest, active_agents: list[dict], activities: list[ActivityRecord]
) -> list[dict]:
    """Determine which agents to analyze based on request criteria."""
    if request.agent_id:
        # Look for specific agent by ID
        # First check in active agents
        for agent in active_agents:
            agent_id = f"{agent['session']}:{agent['window']}"
            if agent_id == request.agent_id:
                return [agent]

        # If not found in active agents, check if it exists in activity history
        for activity in activities:
            if activity.agent_id == request.agent_id:
                # Create synthetic agent info for offline agent
                parts = request.agent_id.split(":")
                return [
                    {
                        "session": parts[0] if len(parts) > 0 else "unknown",
                        "window": parts[1] if len(parts) > 1 else "0",
                        "type": "Unknown",
                        "status": "Offline",
                    }
                ]

        return []

    elif request.target:
        # Convert target to agent_id format and search
        agent_id = request.target
        for agent in active_agents:
            if f"{agent['session']}:{agent['window']}" == agent_id:
                return [agent]
        return []

    elif request.team_id:
        # Get all agents that have activity in this team
        team_agent_ids = set()
        for activity in activities:
            if activity.team_id == request.team_id:
                team_agent_ids.add(activity.agent_id)

        # Find corresponding active agents and create metrics for all team members
        team_agents = []
        for agent in active_agents:
            agent_id = f"{agent['session']}:{agent['window']}"
            if agent_id in team_agent_ids:
                team_agents.append(agent)

        # Also include offline agents that have team activity
        for agent_id in team_agent_ids:
            # Check if already included as active agent
            found_active = False
            for agent in team_agents:
                if f"{agent['session']}:{agent['window']}" == agent_id:
                    found_active = True
                    break

            if not found_active:
                # Create synthetic agent info for offline team member
                parts = agent_id.split(":")
                team_agents.append(
                    {
                        "session": parts[0] if len(parts) > 0 else "unknown",
                        "window": parts[1] if len(parts) > 1 else "0",
                        "type": "Unknown",
                        "status": "Offline",
                    }
                )

        return team_agents

    return []


def _analyze_agent_health(
    agent_info: dict,
    activities: list[ActivityRecord],
    active_agents: list[dict],
    tmux: TMUXManager,
    include_history: bool = False,
    history_limit: int = 10,
) -> AgentHealthMetrics:
    """Analyze agent health and generate comprehensive metrics."""
    agent_id = f"{agent_info['session']}:{agent_info['window']}"

    # Check if agent is currently active in tmux
    is_active = agent_info.get("status") != "Offline"

    # Get agent's activity history
    agent_activities = [activity for activity in activities if activity.agent_id == agent_id]

    # Sort by timestamp descending (most recent first)
    agent_activities.sort(key=lambda x: x.timestamp or datetime.min, reverse=True)

    # Get latest activity
    latest_activity = agent_activities[0] if agent_activities else None

    # Calculate health status
    health_status = _calculate_health_status(agent_info, latest_activity, is_active, agent_activities)

    # Get team_id from latest activity
    team_id = latest_activity.team_id if latest_activity else None

    # Extract activity tags from recent activities
    activity_tags: list[str] = []
    for activity in agent_activities[:5]:  # Last 5 activities
        if activity.tags:
            activity_tags.extend(activity.tags)
    activity_tags = list(set(activity_tags))  # Remove duplicates

    # Calculate responsiveness score
    responsiveness_score = _calculate_responsiveness_score(agent_activities)

    # Prepare activity history if requested
    history = agent_activities[:history_limit] if include_history else []

    return AgentHealthMetrics(
        agent_id=agent_id,
        health_status=health_status,
        session_active=is_active,
        last_activity_time=latest_activity.timestamp if latest_activity else None,
        last_activity_type=latest_activity.activity_type if latest_activity else None,
        last_activity_description=latest_activity.description if latest_activity else None,
        responsiveness_score=responsiveness_score,
        session_info={
            "session": agent_info["session"],
            "window": agent_info["window"],
            "type": agent_info["type"],
            "status": agent_info["status"],
        },
        team_id=team_id,
        activity_tags=activity_tags,
        activity_history=history,
    )


def _calculate_health_status(
    agent_info: dict,
    latest_activity: ActivityRecord | None,
    is_active: bool,
    agent_activities: list[ActivityRecord],
) -> HealthStatus:
    """Calculate overall health status for an agent."""
    # If not active in tmux, mark as offline
    if not is_active or agent_info.get("status") == "Offline":
        return HealthStatus.OFFLINE

    # Check if tmux reports degraded status
    if agent_info.get("status") == "Degraded":
        return HealthStatus.DEGRADED

    # No activity data available
    if not latest_activity:
        return HealthStatus.UNRESPONSIVE

    # Check if latest activity indicates blocked state
    if latest_activity.activity_type == ActivityType.BLOCKED:
        return HealthStatus.BLOCKED

    # Check if agent is unresponsive based on activity age
    if latest_activity.timestamp:
        time_since_activity = datetime.now() - latest_activity.timestamp
        if time_since_activity > timedelta(hours=4):
            return HealthStatus.UNRESPONSIVE

    # Check if latest activity indicates idle state
    if latest_activity.activity_type == ActivityType.IDLE:
        return HealthStatus.IDLE

    # Agent appears healthy
    return HealthStatus.HEALTHY


def _calculate_responsiveness_score(agent_activities: list[ActivityRecord]) -> float:
    """
    Calculate responsiveness score based on activity frequency and recency.

    Score is between 0.0 and 1.0, where:
    - 1.0 = Very responsive (frequent recent activity)
    - 0.0 = Unresponsive (no activity or very old activity)
    """
    if not agent_activities:
        return 0.0

    now = datetime.now()

    # Weight recent activities more heavily
    total_score = 0.0
    max_weight = 0.0

    for i, activity in enumerate(agent_activities[:20]):  # Consider last 20 activities
        if not activity.timestamp:
            continue

        # Calculate time-based weight (more recent = higher weight)
        hours_ago = (now - activity.timestamp).total_seconds() / 3600
        time_weight = max(0, 1 - (hours_ago / 24))  # Decays to 0 after 24 hours

        # Calculate position weight (earlier in list = more recent = higher weight)
        position_weight = max(0, 1 - (i / 20))

        # Activity type weight
        activity_weight = 1.0
        if activity.activity_type == ActivityType.WORKING:
            activity_weight = 1.0
        elif activity.activity_type == ActivityType.COMPLETED:
            activity_weight = 0.9
        elif activity.activity_type == ActivityType.IDLE:
            activity_weight = 0.3
        elif activity.activity_type == ActivityType.BLOCKED:
            activity_weight = 0.1

        weight = time_weight * position_weight * activity_weight
        total_score += weight
        max_weight += 1.0  # Max possible weight for this position

    # Normalize to 0-1 range
    if max_weight > 0:
        return min(1.0, total_score / (max_weight * 0.5))  # Adjusted to allow reaching 1.0

    return 0.0

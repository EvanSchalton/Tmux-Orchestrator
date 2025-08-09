"""Business logic for creating dynamic agent teams."""

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from tmux_orchestrator.utils.tmux import TMUXManager


@dataclass
class TeamMemberSpec:
    """Specification for a team member role."""

    role: str
    count: int = 1
    briefing: str | None = None
    skills: list[str] = field(default_factory=list)
    custom_session: str | None = None


@dataclass
class CreateTeamRequest:
    """Request parameters for creating an agent team."""

    team_name: str
    team_members: list[TeamMemberSpec]
    project_path: str | None = None
    coordination_strategy: str = "hub_and_spoke"


@dataclass
class CreateTeamResult:
    """Result of creating an agent team operation."""

    success: bool
    team_name: str
    created_agents: list[dict[str, str]] = field(default_factory=list)
    team_metadata: dict[str, Any] | None = None
    error_message: str | None = None


def create_team(tmux: TMUXManager, request: CreateTeamRequest) -> CreateTeamResult:
    """
    Create a dynamic agent team with custom compositions.

    Supports creating new agent teams dynamically based on requirements specification.
    Allows custom team compositions with role definitions, agent counts, and session
    assignments. Integrates with existing tmux session management and agent spawning.
    Includes team metadata tracking and persistence for coordination purposes.

    Args:
        tmux: TMUXManager instance for tmux operations
        request: CreateTeamRequest with team configuration

    Returns:
        CreateTeamResult indicating success/failure and created team details

    Raises:
        ValueError: If request parameters are invalid
        RuntimeError: If tmux operations fail
    """
    # Validate input parameters
    validation_error = _validate_request(request)
    if validation_error:
        return CreateTeamResult(
            success=False,
            team_name=request.team_name,
            error_message=validation_error,
        )

    try:
        # Check if team already exists
        if tmux.has_session(request.team_name):
            return CreateTeamResult(
                success=False,
                team_name=request.team_name,
                error_message=f"Team '{request.team_name}' already exists",
            )

        created_agents: list[dict[str, Any]] = []
        agent_role_counts: dict[str, int] = {}
        created_sessions = set()

        # Create agents based on team member specifications
        for member_spec in request.team_members:
            for i in range(member_spec.count):
                # Generate unique window name for this agent
                role_count = agent_role_counts.get(member_spec.role, 0) + 1
                agent_role_counts[member_spec.role] = role_count

                window_name = f"Claude-{member_spec.role}-{role_count}"
                session_name = member_spec.custom_session or request.team_name

                # Determine if this is the first agent for this session
                is_first_agent = session_name not in created_sessions

                # Create session or window for the agent
                agent_result = _create_agent(
                    tmux=tmux,
                    session_name=session_name,
                    window_name=window_name,
                    agent_role=member_spec.role,
                    project_path=request.project_path,
                    briefing=member_spec.briefing,
                    is_first_agent=is_first_agent,
                )

                if not agent_result["success"]:
                    # Return partial success with created agents and error
                    return CreateTeamResult(
                        success=False,
                        team_name=request.team_name,
                        created_agents=created_agents,
                        error_message=agent_result["error"],
                    )

                created_agents.append(agent_result["agent"])
                created_sessions.add(session_name)

        # Generate team metadata
        team_metadata = _generate_team_metadata(
            team_name=request.team_name,
            project_path=request.project_path,
            coordination_strategy=request.coordination_strategy,
            created_agents=created_agents,
            agent_role_counts=agent_role_counts,
        )

        return CreateTeamResult(
            success=True,
            team_name=request.team_name,
            created_agents=created_agents,
            team_metadata=team_metadata,
        )

    except Exception as e:
        return CreateTeamResult(
            success=False,
            team_name=request.team_name,
            created_agents=[],
            error_message=f"Unexpected error during team creation: {str(e)}",
        )


def _validate_request(request: CreateTeamRequest) -> str | None:
    """Validate team creation request parameters."""
    # Validate team name
    if not request.team_name.strip():
        return "Team name cannot be empty"

    # Team name format validation - alphanumeric, hyphens, underscores only
    if not re.match(r"^[a-zA-Z0-9_-]+$", request.team_name):
        return "Team name must contain only alphanumeric characters, hyphens, and underscores"

    # Validate team members
    if not request.team_members:
        return "Team must have at least one member"

    # Valid agent roles
    valid_agent_types = [
        "pm",
        "developer",
        "qa",
        "devops",
        "reviewer",
        "researcher",
        "docs",
    ]

    # Valid coordination strategies
    valid_strategies = ["hub_and_spoke", "peer_to_peer", "hierarchical"]
    if request.coordination_strategy not in valid_strategies:
        return f"Invalid coordination strategy. Must be one of: {', '.join(valid_strategies)}"

    total_agents = 0
    for member_spec in request.team_members:
        # Validate agent role
        if member_spec.role not in valid_agent_types:
            return f"Invalid agent role '{member_spec.role}'. Must be one of: {', '.join(valid_agent_types)}"

        # Validate agent count
        if member_spec.count <= 0:
            return "Agent count must be positive"

        total_agents += member_spec.count

        # Validate briefing length
        if member_spec.briefing and len(member_spec.briefing) > 1000:
            return "Briefing must be 1000 characters or less"

        # Validate custom session name format
        if member_spec.custom_session and not re.match(r"^[a-zA-Z0-9_-]+$", member_spec.custom_session):
            return "Custom session name must contain only alphanumeric characters, hyphens, and underscores"

    # Validate total agent count
    if total_agents > 20:
        return "Total agent count cannot exceed 20"

    return None


def _create_agent(
    tmux: TMUXManager,
    session_name: str,
    window_name: str,
    agent_role: str,
    project_path: str | None,
    briefing: str | None,
    is_first_agent: bool,
) -> dict[str, Any]:
    """
    Create a single agent in the specified session and window.

    Returns:
        dict with 'success' bool, 'agent' dict (if successful), and 'error' string (if failed)
    """
    try:
        # Create session or window
        if is_first_agent:
            # Create new session for the first agent
            success = tmux.create_session(session_name, window_name, project_path)
            if not success:
                return {"success": False, "error": f"Failed to create session '{session_name}'"}
        else:
            # Create new window in existing session
            success = tmux.create_window(session_name, window_name, project_path)
            if not success:
                return {
                    "success": False,
                    "error": f"Failed to create window '{window_name}' in session '{session_name}'",
                }

        # Start Claude in the new window/session
        target = f"{session_name}:{window_name}"

        start_success = tmux.send_keys(target, "claude --dangerously-skip-permissions")
        if not start_success:
            return {"success": False, "error": f"Failed to start Claude command in {target}"}

        enter_success = tmux.send_keys(target, "Enter")
        if not enter_success:
            return {"success": False, "error": f"Failed to send Enter key to {target}"}

        # Create agent info
        agent_info = {
            "role": agent_role,
            "session": session_name,
            "window": window_name,
            "target": target,
            "status": "active",
        }

        # Add briefing if provided
        if briefing:
            agent_info["briefing"] = briefing

        return {"success": True, "agent": agent_info}

    except Exception as e:
        return {"success": False, "error": f"Exception creating agent {window_name}: {str(e)}"}


def _generate_team_metadata(
    team_name: str,
    project_path: str | None,
    coordination_strategy: str,
    created_agents: list[dict[str, Any]],
    agent_role_counts: dict[str, int],
) -> dict[str, Any]:
    """Generate comprehensive team metadata for tracking and coordination."""
    now = datetime.now(timezone.utc)

    metadata = {
        "team_name": team_name,
        "project_path": project_path,
        "coordination_strategy": coordination_strategy,
        "total_agents": len(created_agents),
        "agent_roles": agent_role_counts,
        "created_at": now.isoformat(),
        "agents": created_agents,
    }

    # Add coordination-specific metadata
    if coordination_strategy == "hub_and_spoke":
        # Identify hub (typically the PM or first agent)
        hub_agent = None
        for agent in created_agents:
            if agent["role"] == "pm":
                hub_agent = agent["target"]
                break
        if not hub_agent and created_agents:
            hub_agent = created_agents[0]["target"]

        metadata["coordination_config"] = {
            "hub": hub_agent,
            "spokes": [agent["target"] for agent in created_agents if agent["target"] != hub_agent],
        }

    elif coordination_strategy == "hierarchical":
        # Group agents by role hierarchy
        hierarchy_order = ["pm", "developer", "qa", "devops", "reviewer", "researcher", "docs"]
        metadata["coordination_config"] = {
            "hierarchy": {
                role: [agent["target"] for agent in created_agents if agent["role"] == role]
                for role in hierarchy_order
                if any(agent["role"] == role for agent in created_agents)
            }
        }

    elif coordination_strategy == "peer_to_peer":
        # All agents are peers
        metadata["coordination_config"] = {"peers": [agent["target"] for agent in created_agents]}

    return metadata

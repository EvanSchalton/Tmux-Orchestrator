"""Team coordination and deployment routes for MCP server."""

from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from tmux_orchestrator.core.team_operations import (
    broadcast_to_team,
    get_team_status,
    list_all_teams,
)
from tmux_orchestrator.core.team_operations.deploy_team import recover_team_agents
from tmux_orchestrator.utils.tmux import TMUXManager

router = APIRouter()
tmux = TMUXManager()


class TeamMember(BaseModel):
    """API model for team member definition."""

    role: str  # pm, developer, qa, devops, reviewer
    briefing: Optional[str] = None
    skills: list[str] = []


class TeamDeploymentRequest(BaseModel):
    """API request model for team deployment."""

    project_name: str
    project_path: str
    team_members: list[TeamMember]
    coordination_strategy: str = "hub_and_spoke"  # hub_and_spoke, peer_to_peer


class TeamDeploymentResponse(BaseModel):
    """API response model for team deployment."""

    success: bool
    session_name: str
    deployed_agents: list[dict[str, str]]
    coordination_setup: dict[str, Any]


class StandupRequest(BaseModel):
    """API request model for standup coordination."""

    session_names: list[str]
    include_idle_agents: bool = True
    timeout_seconds: int = 30


class StandupResponse(BaseModel):
    """API response model for standup results."""

    success: bool
    standup_initiated: bool
    results: list[dict[str, Any]]
    total_agents_contacted: int


class TeamRecoveryRequest(BaseModel):
    """API request model for team recovery."""

    session_name: str
    recovery_strategy: str = "restart_failed"  # restart_failed, restart_all


class TeamRecoveryResponse(BaseModel):
    """API response model for team recovery."""

    success: bool
    message: str
    recovered_agents: list[str]
    failed_recoveries: list[str]


class TeamStatusRequest(BaseModel):
    """API request model for team status."""

    session_name: str


class TeamStatusResponse(BaseModel):
    """API response model for team status."""

    success: bool
    session_info: dict[str, Any]
    windows: list[dict[str, Any]]
    summary: dict[str, int]


@router.post("/deploy-team", response_model=TeamDeploymentResponse)
async def tmux_create_team(request: TeamDeploymentRequest, background_tasks: BackgroundTasks) -> TeamDeploymentResponse:
    """Deploy a complete agent team for a project.

    Primary MCP tool for team deployment.
    """
    try:
        session_name = request.project_name.replace(" ", "-").lower()
        deployed_agents: list[dict[str, str]] = []

        # Create main project session
        if not tmux.has_session(session_name):
            success = tmux.create_session(session_name, "Project-Shell", request.project_path)
            if not success:
                raise HTTPException(status_code=500, detail="Failed to create project session")

        # Deploy each team member
        for i, member in enumerate(request.team_members):
            window_name = f"Claude-{member.role}"

            # Create window for agent
            success = tmux.create_window(session_name, window_name, request.project_path)
            if not success:
                raise HTTPException(status_code=500, detail=f"Failed to create window for {member.role}")

            # Start Claude
            target = f"{session_name}:{window_name}"
            tmux.send_keys(target, "claude --dangerously-skip-permissions")
            tmux.send_keys(target, "Enter")

            deployed_agents.append(
                {
                    "role": member.role,
                    "session": session_name,
                    "window": window_name,
                    "target": target,
                }
            )

        # Set up coordination structure
        coordination_setup: dict[str, Any] = {"strategy": request.coordination_strategy}
        if request.coordination_strategy == "hub_and_spoke":
            # Find PM agent
            pm_agent = next((a for a in deployed_agents if a["role"] == "pm"), None)
            if pm_agent:
                coordination_setup.update(
                    {
                        "hub": pm_agent["target"],
                        "spokes": [a["target"] for a in deployed_agents if a["role"] != "pm"],
                    }
                )

        return TeamDeploymentResponse(
            success=True,
            session_name=session_name,
            deployed_agents=deployed_agents,
            coordination_setup=coordination_setup,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/standup", response_model=StandupResponse)
async def conduct_standup_tool(request: StandupRequest) -> StandupResponse:
    """Conduct async standup across multiple sessions.

    MCP tool for team coordination.
    """
    try:
        standup_message = """STATUS UPDATE REQUEST:
Please provide:
1) Completed tasks since last update
2) Current work in progress
3) Any blockers or impediments
4) ETA for current task

Format: Keep it brief and focused."""

        results = []
        total_contacted = 0

        for session_name in request.session_names:
            if not tmux.has_session(session_name):
                results.append(
                    {
                        "session": session_name,
                        "status": "session_not_found",
                        "agents_contacted": 0,
                    }
                )
                continue

            # Use core business logic for broadcasting
            success, summary_message, broadcast_results = broadcast_to_team(tmux, session_name, standup_message)

            session_contacted = len([r for r in broadcast_results if r.get("success", False)])
            total_contacted += session_contacted

            results.append(
                {
                    "session": session_name,
                    "status": "completed" if success else "failed",
                    "message": summary_message,
                    "agents_contacted": session_contacted,
                    "details": broadcast_results,
                }
            )

        return StandupResponse(
            success=True,
            standup_initiated=True,
            results=results,
            total_agents_contacted=total_contacted,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recover-team", response_model=TeamRecoveryResponse)
async def recover_team_tool(request: TeamRecoveryRequest) -> TeamRecoveryResponse:
    """Recover failed agents in a team session.

    MCP tool for team recovery operations.
    """
    try:
        # Use core business logic for team recovery
        success, message = recover_team_agents(tmux, request.session_name)

        # For detailed recovery info, we'd need to enhance the core function
        # For now, provide basic response
        return TeamRecoveryResponse(
            success=success,
            message=message,
            recovered_agents=[],  # Would be populated by enhanced core function
            failed_recoveries=[],  # Would be populated by enhanced core function
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/team-status/{session_name}", response_model=TeamStatusResponse)
async def get_team_status_tool(session_name: str) -> TeamStatusResponse:
    """Get detailed status for a team session.

    MCP tool for team monitoring.
    """
    try:
        # Use core business logic for team status
        team_status = get_team_status(tmux, session_name)

        if not team_status:
            raise HTTPException(status_code=404, detail=f"Session '{session_name}' not found")

        return TeamStatusResponse(
            success=True,
            session_info=team_status["session_info"],
            windows=team_status["windows"],
            summary=team_status["summary"],
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list-teams")
async def list_all_teams_tool() -> dict[str, Any]:
    """List all active team sessions.

    MCP tool for team discovery.
    """
    try:
        # Use core business logic for listing teams
        teams = list_all_teams(tmux)

        return {"success": True, "teams": teams, "total_teams": len(teams)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/coordinate/hub-spoke")
async def setup_hub_spoke_coordination(session_name: str, hub_agent_type: str = "pm") -> dict[str, Any]:
    """Set up hub-and-spoke coordination pattern.

    MCP tool for coordination pattern setup.
    """
    try:
        if not tmux.has_session(session_name):
            raise HTTPException(status_code=404, detail=f"Session '{session_name}' not found")

        # Get all agents in session
        all_agents = tmux.list_agents()
        session_agents = [agent for agent in all_agents if agent["session"] == session_name]

        # Find hub agent
        hub_agent = next((agent for agent in session_agents if agent["type"] == hub_agent_type), None)

        if not hub_agent:
            raise HTTPException(
                status_code=400,
                detail=f"No {hub_agent_type} agent found in session '{session_name}'",
            )

        # Get spoke agents (all others)
        spoke_agents = [agent for agent in session_agents if agent["type"] != hub_agent_type]

        # Send coordination setup message to hub
        hub_target = f"{hub_agent['session']}:{hub_agent['window']}"
        coordination_message = f"""COORDINATION SETUP:
You are now the HUB in a hub-and-spoke coordination pattern.

Your spoke agents:
{chr(10).join([f"- {agent['type']}: {agent['session']}:{agent['window']}" for agent in spoke_agents])}

Responsibilities:
- Coordinate work between team members
- Collect status updates from spokes
- Report team progress to orchestrator
- Resolve conflicts and blockers"""

        hub_message_sent = tmux.send_message(hub_target, coordination_message)

        # Send coordination message to each spoke
        spoke_results = []
        for spoke in spoke_agents:
            spoke_target = f"{spoke['session']}:{spoke['window']}"
            spoke_message = f"""COORDINATION SETUP:
You are a SPOKE in a hub-and-spoke coordination pattern.

Your hub agent: {hub_agent['type']} ({hub_target})

Responsibilities:
- Report status updates to your hub
- Coordinate through the hub, not directly with other spokes
- Escalate blockers to the hub
- Focus on your assigned tasks"""

            success = tmux.send_message(spoke_target, spoke_message)
            spoke_results.append(
                {
                    "agent": spoke["type"],
                    "target": spoke_target,
                    "message_sent": success,
                }
            )

        return {
            "success": True,
            "coordination_pattern": "hub_and_spoke",
            "hub_agent": {
                "type": hub_agent["type"],
                "target": hub_target,
                "message_sent": hub_message_sent,
            },
            "spoke_agents": spoke_results,
            "total_agents_configured": 1 + len(spoke_results),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

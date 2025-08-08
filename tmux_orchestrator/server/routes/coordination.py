"""Team coordination and deployment routes for MCP server."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from tmux_orchestrator.utils.tmux import TMUXManager

router = APIRouter()
tmux = TMUXManager()


class TeamMember(BaseModel):
    """API model for team member definition."""
    role: str  # pm, developer, qa, devops, reviewer
    briefing: Optional[str] = None
    skills: List[str] = []


class TeamDeploymentRequest(BaseModel):
    """API request model for team deployment."""
    project_name: str
    project_path: str
    team_members: List[TeamMember]
    coordination_strategy: str = "hub_and_spoke"  # hub_and_spoke, peer_to_peer


class TeamDeploymentResponse(BaseModel):
    """API response model for team deployment."""
    success: bool
    session_name: str
    deployed_agents: List[Dict[str, str]]
    coordination_setup: Dict[str, Any]


@router.post("/deploy-team", response_model=TeamDeploymentResponse)
async def tmux_create_team(
    request: TeamDeploymentRequest,
    background_tasks: BackgroundTasks
) -> TeamDeploymentResponse:
    """Deploy a complete agent team for a project.

    Primary MCP tool for team deployment.
    """
    try:
        session_name = request.project_name.replace(' ', '-').lower()
        deployed_agents: List[Dict[str, str]] = []

        # Create main project session
        if not tmux.has_session(session_name):
            success = tmux.create_session(
                session_name,
                "Project-Shell",
                request.project_path
            )
            if not success:
                raise HTTPException(status_code=500, detail="Failed to create project session")

        # Deploy each team member
        for i, member in enumerate(request.team_members):
            window_name = f"Claude-{member.role}"

            # Create window for agent
            success = tmux.create_window(
                session_name,
                window_name,
                request.project_path
            )
            if not success:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to create window for {member.role}"
                )

            # Start Claude
            target = f"{session_name}:{window_name}"
            tmux.send_keys(target, "claude --dangerously-skip-permissions")
            tmux.send_keys(target, "Enter")

            deployed_agents.append({
                "role": member.role,
                "session": session_name,
                "window": window_name,
                "target": target
            })

        # Set up coordination structure
        coordination_setup: Dict[str, Any] = {"strategy": request.coordination_strategy}
        if request.coordination_strategy == "hub_and_spoke":
            # Find PM agent
            pm_agent = next((a for a in deployed_agents if a['role'] == 'pm'), None)
            if pm_agent:
                coordination_setup.update({
                    "hub": pm_agent['target'],
                    "spokes": [a['target'] for a in deployed_agents if a['role'] != 'pm']
                })

        return TeamDeploymentResponse(
            success=True,
            session_name=session_name,
            deployed_agents=deployed_agents,
            coordination_setup=coordination_setup
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/coordinate/standup")
async def conduct_standup(session_names: List[str]) -> Dict[str, Any]:
    """Conduct async standup across multiple sessions.

    MCP tool for team coordination.
    """
    try:
        standup_request = """STATUS UPDATE REQUEST:
Please provide:
1) Completed tasks since last update
2) Current work in progress
3) Any blockers or impediments
4) ETA for current task

Format: Keep it brief and focused."""

        results = []

        for session_name in session_names:
            if not tmux.has_session(session_name):
                results.append({
                    "session": session_name,
                    "status": "session_not_found"
                })
                continue

            # Get agents in this session
            all_agents = tmux.list_agents()
            session_agents = [
                agent for agent in all_agents
                if agent['session'] == session_name
            ]

            for agent in session_agents:
                target = f"{agent['session']}:{agent['window']}"
                success = tmux.send_message(target, standup_request)

                results.append({
                    "session": session_name,
                    "agent_type": agent['type'],
                    "target": target,
                    "request_sent": success
                })

        return {
            "standup_initiated": True,
            "results": results,
            "total_agents_contacted": len([r for r in results if r.get('request_sent', False)])
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

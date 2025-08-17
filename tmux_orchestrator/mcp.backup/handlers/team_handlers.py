"""Business logic handlers for team operations MCP tools."""

import logging
from typing import Any, Dict, List

from tmux_orchestrator.utils.tmux import TMUXManager

logger = logging.getLogger(__name__)


class TeamHandlers:
    """Handlers for team operation functionality."""

    def __init__(self):
        self.tmux = TMUXManager()

    async def deploy_team(
        self,
        team_name: str,
        team_type: str,
        size: int,
        project_path: str | None = None,
        briefing_context: str | None = None,
    ) -> Dict[str, Any]:
        """Handle team deployment operation."""
        try:
            # Define team compositions based on type
            team_compositions = {
                "frontend": ["developer", "qa", "reviewer"],
                "backend": ["developer", "devops", "qa"],
                "fullstack": ["developer", "developer", "qa", "devops"],
                "testing": ["qa", "qa", "developer"],
            }

            base_agents = team_compositions.get(team_type, ["developer"] * size)

            # Adjust team size
            if size > len(base_agents):
                # Add more developers
                base_agents.extend(["developer"] * (size - len(base_agents)))
            elif size < len(base_agents):
                # Trim to size
                base_agents = base_agents[:size]

            # Mock deployment response (stub implementation)
            mock_agents = []
            for i, agent_type in enumerate(base_agents):
                agent = {
                    "target": f"{team_name}:Claude-{agent_type}-{i+1}",
                    "agent_type": agent_type,
                    "window": f"Claude-{agent_type}-{i+1}",
                    "status": "spawned",
                    "project_path": project_path,
                }
                mock_agents.append(agent)

            return {
                "success": True,
                "team_name": team_name,
                "team_type": team_type,
                "size": len(mock_agents),
                "agents": mock_agents,
                "project_path": project_path,
                "briefing_context": briefing_context,
                "message": f"Successfully deployed {team_type} team '{team_name}' with {len(mock_agents)} agents",
                "deployment_time": "2024-01-01T00:00:00Z",
            }

        except Exception as e:
            logger.error(f"Team deployment failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "team_name": team_name,
                "team_type": team_type,
            }

    async def get_team_status(
        self,
        session: str | None = None,
        detailed: bool = False,
        include_agents: bool = True,
    ) -> Dict[str, Any]:
        """Handle team status retrieval operation."""
        try:
            if session:
                # Single team status
                mock_team = {
                    "session": session,
                    "team_type": "fullstack",
                    "size": 4,
                    "health_status": "healthy",
                    "active_agents": 4,
                    "idle_agents": 0,
                    "last_activity": "2024-01-01T00:00:00Z",
                    "project_path": "/test/project",
                }

                if include_agents:
                    mock_team["agents"] = [
                        {
                            "target": f"{session}:Claude-developer-1",
                            "health_status": "healthy",
                            "last_activity": "2024-01-01T00:00:00Z",
                        },
                        {
                            "target": f"{session}:Claude-qa-1",
                            "health_status": "healthy",
                            "last_activity": "2024-01-01T00:00:00Z",
                        },
                    ]

                return {
                    "success": True,
                    "team": mock_team,
                    "detailed": detailed,
                    "include_agents": include_agents,
                }
            else:
                # All teams status
                mock_teams = [
                    {
                        "session": "frontend-team",
                        "team_type": "frontend",
                        "size": 3,
                        "health_status": "healthy",
                        "active_agents": 3,
                    },
                    {
                        "session": "backend-team",
                        "team_type": "backend",
                        "size": 4,
                        "health_status": "degraded",
                        "active_agents": 3,
                    },
                ]

                return {
                    "success": True,
                    "teams": mock_teams,
                    "total_teams": len(mock_teams),
                    "detailed": detailed,
                    "include_agents": include_agents,
                }

        except Exception as e:
            logger.error(f"Team status retrieval failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "session": session,
            }

    async def team_broadcast(
        self,
        session: str,
        message: str,
        exclude_windows: List[str],
        urgent: bool = False,
    ) -> Dict[str, Any]:
        """Handle team broadcast operation."""
        try:
            # Mock broadcast to team agents
            mock_windows = [
                "Claude-developer-1",
                "Claude-qa-1",
                "Claude-devops-1",
                "Claude-reviewer-1",
            ]

            # Filter excluded windows
            target_windows = [w for w in mock_windows if w not in exclude_windows]

            broadcast_results = []
            successful = 0

            for window in target_windows:
                target = f"{session}:{window}"
                # Mock successful delivery
                result = {
                    "target": target,
                    "success": True,
                    "delivery_time": "2024-01-01T00:00:00Z",
                }
                broadcast_results.append(result)
                successful += 1

            return {
                "success": successful > 0,
                "session": session,
                "message": message[:100] + "..." if len(message) > 100 else message,
                "total_sent": len(broadcast_results),
                "successful": successful,
                "failed": len(broadcast_results) - successful,
                "excluded_windows": exclude_windows,
                "urgent": urgent,
                "results": broadcast_results,
                "broadcast_time": "2024-01-01T00:00:00Z",
            }

        except Exception as e:
            logger.error(f"Team broadcast failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "session": session,
            }

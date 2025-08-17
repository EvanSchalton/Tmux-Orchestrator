"""Business logic handlers for agent management MCP tools."""

import logging
from typing import Any, Dict

from tmux_orchestrator.core.agent_operations.spawn_agent import spawn_agent as core_spawn_agent
from tmux_orchestrator.server.tools.get_agent_status import (
    AgentStatusRequest,
)
from tmux_orchestrator.server.tools.get_agent_status import (
    get_agent_status as core_get_agent_status,
)
from tmux_orchestrator.server.tools.send_message import (
    SendMessageRequest,
)
from tmux_orchestrator.server.tools.send_message import (
    send_message as core_send_message,
)
from tmux_orchestrator.server.tools.spawn_agent import SpawnAgentRequest
from tmux_orchestrator.utils.tmux import TMUXManager

logger = logging.getLogger(__name__)


class AgentHandlers:
    """Handlers for agent management operations."""

    def __init__(self):
        self.tmux = TMUXManager()

    async def spawn_agent(
        self,
        session_name: str,
        agent_type: str = "developer",
        project_path: str | None = None,
        briefing_message: str | None = None,
        use_context: bool = True,
        window_name: str | None = None,
    ) -> Dict[str, Any]:
        """Handle agent spawning operation."""
        try:
            # Create spawn request
            request = SpawnAgentRequest(
                session_name=session_name,
                agent_type=agent_type,
                project_path=project_path,
                briefing_message=briefing_message,
            )

            # Delegate to core business logic
            result = await core_spawn_agent(self.tmux, request)

            if result.success:
                # Send briefing message if provided
                if briefing_message:
                    msg_request = SendMessageRequest(
                        target=result.target,
                        message=briefing_message,
                    )
                    core_send_message(self.tmux, msg_request)

                return {
                    "success": True,
                    "session": result.session,
                    "window": result.window,
                    "target": result.target,
                    "message": f"Successfully spawned {agent_type} agent in {result.target}",
                }
            else:
                return {
                    "success": False,
                    "error": result.error_message or "Failed to spawn agent",
                    "error_type": "SpawnFailure",
                    "context": {
                        "session_name": session_name,
                        "agent_type": agent_type,
                    },
                }

        except Exception as e:
            logger.error(f"Agent spawn failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "context": {"session_name": session_name, "agent_type": agent_type},
            }

    def send_message(
        self,
        target: str,
        message: str,
        urgent: bool = False,
    ) -> Dict[str, Any]:
        """Handle message sending operation."""
        try:
            # Create message request
            request = SendMessageRequest(
                target=target,
                message=message,
            )

            # Delegate to core business logic
            result = core_send_message(self.tmux, request)

            return {
                "success": result.success,
                "target": result.target,
                "message": "Message sent successfully" if result.success else result.error_message,
                "urgent": urgent,
            }

        except Exception as e:
            logger.error(f"Message send failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "context": {"target": target},
            }

    def get_agent_status(
        self,
        target: str | None = None,
        include_history: bool = False,
        include_metrics: bool = True,
    ) -> Dict[str, Any]:
        """Handle agent status retrieval operation."""
        try:
            if target:
                # Single agent status
                status_request = AgentStatusRequest(
                    agent_id=target,
                    include_activity_history=include_history,
                    activity_limit=5 if include_history else 0,
                )
                status_result = core_get_agent_status(self.tmux, status_request)

                if status_result.success and status_result.agent_metrics:
                    metrics = status_result.agent_metrics[0]
                    return {
                        "success": True,
                        "target": target,
                        "health_status": metrics.health_status.value,
                        "session_active": metrics.session_active,
                        "last_activity": metrics.last_activity_time.isoformat() if metrics.last_activity_time else None,
                        "responsiveness_score": metrics.responsiveness_score,
                        "team_id": metrics.team_id,
                    }
                else:
                    return {
                        "success": False,
                        "error": status_result.error_message or "Agent not found",
                        "error_type": "AgentNotFound"
                        if "not found" in (status_result.error_message or "").lower()
                        else "StatusRetrievalFailure",
                        "context": {"target": target},
                    }
            else:
                # All agents status
                agents = self.tmux.list_agents()
                agent_statuses = []

                for agent in agents:
                    agent_target = f"{agent['session']}:{agent.get('window', '0')}"
                    status_request = AgentStatusRequest(
                        agent_id=agent_target,
                        include_activity_history=include_history,
                        activity_limit=5 if include_history else 0,
                    )
                    status_result = core_get_agent_status(self.tmux, status_request)

                    if status_result.success and status_result.agent_metrics:
                        metrics = status_result.agent_metrics[0]
                        agent_statuses.append(
                            {
                                "target": agent_target,
                                "health_status": metrics.health_status.value,
                                "session_active": metrics.session_active,
                                "last_activity": metrics.last_activity_time.isoformat()
                                if metrics.last_activity_time
                                else None,
                                "responsiveness_score": metrics.responsiveness_score,
                                "team_id": metrics.team_id,
                            }
                        )

                return {
                    "success": True,
                    "agents": agent_statuses,
                    "total_count": len(agent_statuses),
                }

        except Exception as e:
            logger.error(f"Agent status retrieval failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "context": {"target": target},
            }

    def kill_agent(
        self,
        target: str,
        force: bool = False,
    ) -> Dict[str, Any]:
        """Handle agent termination operation."""
        try:
            if target == "all":
                # Kill all agents
                agents = self.tmux.list_agents()
                killed_count = 0
                for agent in agents:
                    session_name = agent["session"]
                    if self.tmux.kill_session(session_name):
                        killed_count += 1

                return {
                    "success": True,
                    "message": f"Killed {killed_count} agent sessions",
                    "killed_count": killed_count,
                }
            else:
                # Kill specific agent
                if ":" in target:
                    session_name, window_name = target.split(":", 1)
                    success = self.tmux.kill_window(f"{session_name}:{window_name}")
                    action = f"window {target}"
                else:
                    session_name = target
                    success = self.tmux.kill_session(session_name)
                    action = f"session {session_name}"

                return {
                    "success": success,
                    "target": target,
                    "message": f"Successfully killed {action}" if success else f"Failed to kill {action}",
                }

        except Exception as e:
            logger.error(f"Agent kill failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "context": {"target": target, "force": force},
            }

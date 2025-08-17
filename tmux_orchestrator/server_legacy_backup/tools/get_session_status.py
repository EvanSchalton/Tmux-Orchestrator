"""Business logic for retrieving comprehensive session status."""

from dataclasses import dataclass

from tmux_orchestrator.utils.tmux import TMUXManager


@dataclass
class SessionStatusResult:
    """Result of session status operation."""

    total_sessions: int
    total_agents: int
    active_agents: int
    idle_agents: int
    sessions: list[dict[str, str]]
    agents: list[dict[str, str]]


def get_session_status(tmux: TMUXManager) -> SessionStatusResult:
    """
    Get comprehensive system status including sessions and agents.

    Args:
        tmux: TMUXManager instance for tmux operations

    Returns:
        SessionStatusResult with complete system status

    Raises:
        RuntimeError: If tmux operations fail
    """
    try:
        # Get all sessions
        sessions = tmux.list_sessions()

        # Get all agents
        agents = tmux.list_agents()

        # Count agent statuses
        active_agents = [agent for agent in agents if agent["status"] == "Active"]
        idle_agents = [agent for agent in agents if agent["status"] == "Idle"]

        return SessionStatusResult(
            total_sessions=len(sessions),
            total_agents=len(agents),
            active_agents=len(active_agents),
            idle_agents=len(idle_agents),
            sessions=sessions,
            agents=agents,
        )

    except Exception as e:
        raise RuntimeError(f"Failed to retrieve session status: {str(e)}") from e


@dataclass
class AgentStatusRequest:
    """Request parameters for individual agent status."""

    session: str
    window: str
    lines: int = 100


@dataclass
class AgentStatusResult:
    """Result of individual agent status check."""

    session: str
    window: str
    target: str
    status: str
    recent_output: list[str]
    output_length: int
    error_message: str = ""


def get_agent_status(tmux: TMUXManager, request: AgentStatusRequest) -> AgentStatusResult:
    """
    Get detailed status of a specific agent.

    Args:
        tmux: TMUXManager instance for tmux operations
        request: AgentStatusRequest with agent identification

    Returns:
        AgentStatusResult with agent details

    Raises:
        ValueError: If session or window names are invalid
    """
    if not request.session.strip():
        return AgentStatusResult(
            session=request.session,
            window=request.window,
            target="",
            status="error",
            recent_output=[],
            output_length=0,
            error_message="Session name cannot be empty",
        )

    if not request.window.strip():
        return AgentStatusResult(
            session=request.session,
            window=request.window,
            target="",
            status="error",
            recent_output=[],
            output_length=0,
            error_message="Window name cannot be empty",
        )

    target = f"{request.session}:{request.window}"

    # Check if session exists
    if not tmux.has_session(request.session):
        return AgentStatusResult(
            session=request.session,
            window=request.window,
            target=target,
            status="not_found",
            recent_output=[],
            output_length=0,
            error_message=f"Session '{request.session}' not found",
        )

    try:
        # Capture recent output
        output = tmux.capture_pane(target, lines=request.lines)
        output_lines = output.split("\n") if output else []

        # Determine if agent is idle
        is_idle = tmux._is_idle(output)
        status = "idle" if is_idle else "active"

        return AgentStatusResult(
            session=request.session,
            window=request.window,
            target=target,
            status=status,
            recent_output=output_lines[-10:],  # Last 10 lines
            output_length=len(output_lines),
        )

    except Exception as e:
        return AgentStatusResult(
            session=request.session,
            window=request.window,
            target=target,
            status="error",
            recent_output=[],
            output_length=0,
            error_message=f"Error retrieving agent status: {str(e)}",
        )

"""Check agent health status using enhanced monitoring."""

from datetime import datetime
from typing import NamedTuple

from tmux_orchestrator.utils.tmux import TMUXManager

from .detect_failure import detect_failure


class AgentHealthStatus(NamedTuple):
    """Agent health status data structure."""
    target: str
    is_healthy: bool
    is_idle: bool
    failure_reason: str
    last_check: datetime
    consecutive_failures: int


def check_agent_health(
    tmux: TMUXManager,
    target: str,
    last_response: datetime,
    consecutive_failures: int = 0,
    max_failures: int = 3,
    response_timeout: int = 60
) -> AgentHealthStatus:
    """
    Check the health status of a specific agent.

    Performs comprehensive health checking using bulletproof idle detection
    and error pattern analysis to determine agent status.

    Args:
        tmux: TMUXManager instance for tmux operations
        target: Target agent in format 'session:window'
        last_response: When agent last responded normally
        consecutive_failures: Current consecutive failure count
        max_failures: Maximum failures before agent considered failed
        response_timeout: Timeout in seconds for response detection

    Returns:
        AgentHealthStatus with comprehensive health information

    Raises:
        ValueError: If target format is invalid
        RuntimeError: If health check operations fail
    """
    # Validate target format
    if ':' not in target:
        raise ValueError(f"Invalid target format: {target}. Expected 'session:window'")

    try:
        # Detect failure using comprehensive analysis
        is_failed: bool
        failure_reason: str
        status_details: Dict[str, Any]

        is_failed, failure_reason, status_details = detect_failure(
            tmux=tmux,
            target=target,
            last_response=last_response,
            consecutive_failures=consecutive_failures,
            max_failures=max_failures,
            response_timeout=response_timeout
        )
        
        is_idle: bool = status_details.get('is_idle', False)

        # Determine health status
        is_healthy: bool = not is_failed

        # Update failure count
        new_failure_count: int = (
            consecutive_failures + 1 if is_failed
            else 0
        )

        return AgentHealthStatus(
            target=target,
            is_healthy=is_healthy,
            is_idle=is_idle,
            failure_reason=failure_reason,
            last_check=datetime.now(),
            consecutive_failures=new_failure_count
        )

    except Exception as e:
        # Return unhealthy status on check failure
        return AgentHealthStatus(
            target=target,
            is_healthy=False,
            is_idle=False,
            failure_reason=f"health_check_failed: {str(e)}",
            last_check=datetime.now(),
            consecutive_failures=consecutive_failures + 1
        )

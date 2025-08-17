"""Phase 2 MCP tools for monitoring and system status."""

import logging
from typing import Any, Dict

from tmux_orchestrator.mcp.handlers.monitoring_handlers import MonitoringHandlers
from tmux_orchestrator.mcp.server import mcp

logger = logging.getLogger(__name__)

# Initialize handlers
monitoring_handlers = MonitoringHandlers()


@mcp.tool()
async def start_monitoring(
    interval: int = 30,
    supervised: bool = False,
    auto_recovery: bool = True,
) -> Dict[str, Any]:
    """
    Start the monitoring daemon for agent health tracking.

    Args:
        interval: Monitoring interval in seconds
        supervised: Run in supervised mode
        auto_recovery: Enable automatic recovery of failed agents

    Returns:
        Dict with monitoring daemon status and configuration
    """
    logger.info(f"Starting monitoring daemon with {interval}s interval")

    # Input validation
    if not 5 <= interval <= 300:
        return {
            "success": False,
            "error": "Monitoring interval must be between 5 and 300 seconds",
            "error_type": "ValidationError",
        }

    return await monitoring_handlers.start_monitoring(
        interval=interval,
        supervised=supervised,
        auto_recovery=auto_recovery,
    )


@mcp.tool()
async def get_system_status(
    format_type: str = "summary",
    include_metrics: bool = True,
    include_health: bool = True,
) -> Dict[str, Any]:
    """
    Get comprehensive system status dashboard.

    Args:
        format_type: Status report format (summary, detailed, json)
        include_metrics: Include performance metrics
        include_health: Include health indicators

    Returns:
        Dict with system overview, health status, and performance data
    """
    logger.info(f"Getting system status ({format_type})")

    # Input validation
    valid_formats = ["summary", "detailed", "json"]
    if format_type not in valid_formats:
        return {
            "success": False,
            "error": f"Invalid format type. Must be one of: {', '.join(valid_formats)}",
            "error_type": "ValidationError",
        }

    return await monitoring_handlers.get_system_status(
        format_type=format_type,
        include_metrics=include_metrics,
        include_health=include_health,
    )


@mcp.tool()
async def stop_monitoring(
    stop_recovery: bool = True,
    graceful: bool = True,
) -> Dict[str, Any]:
    """
    Stop the monitoring daemon and related services.

    Args:
        stop_recovery: Also stop recovery daemon
        graceful: Graceful shutdown vs immediate termination

    Returns:
        Dict with shutdown status and final metrics
    """
    logger.info("Stopping monitoring daemon")

    return await monitoring_handlers.stop_monitoring(
        stop_recovery=stop_recovery,
        graceful=graceful,
    )


def register_monitoring_tools() -> None:
    """Register all monitoring tools with FastMCP."""
    logger.info("Phase 2 monitoring tools registered")


# Auto-register tools when module is imported
register_monitoring_tools()

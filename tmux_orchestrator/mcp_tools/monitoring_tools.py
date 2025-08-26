"""
Monitoring & Health Tools

Implements native MCP tools for system monitoring and health checks with exact parameter
signatures from API Designer's specifications.
"""

import logging
from typing import Any, Dict, Optional

from .shared_logic import (
    CommandExecutor,
    ExecutionError,
    ValidationError,
    format_error_response,
    format_success_response,
    validate_session_format,
)

logger = logging.getLogger(__name__)


async def system_status(format: str = "dashboard", include_performance: bool = False) -> Dict[str, Any]:
    """
    Get comprehensive system status.

    Implements API Designer's system_status specification with performance metrics.

    Args:
        format: Output format ("dashboard", "json", "summary")
        include_performance: Include performance metrics

    Returns:
        Structured response with system status information
    """
    try:
        # Validate format parameter
        valid_formats = {"dashboard", "json", "summary"}
        if format not in valid_formats:
            return format_error_response(
                f"Invalid format '{format}'. Valid formats: {', '.join(valid_formats)}",
                "system status",
                ["Use 'dashboard', 'json', or 'summary' format"],
            )

        # Build command
        cmd = ["tmux-orc", "status"]

        # Add format if not default
        if format != "dashboard":
            cmd.extend(["--format", format])

        # Add performance metrics flag
        if include_performance:
            cmd.append("--performance")

        # Execute command
        executor = CommandExecutor()
        result = executor.execute(cmd, expect_json=(format == "json"))

        if result["success"]:
            data = result["data"]

            # Structure response with metadata
            response_data = {
                "format": format,
                "include_performance": include_performance,
                "system_status": data if isinstance(data, dict) else {"raw_status": data},
                "status_timestamp": None,  # Could add if CLI provides it
                "system_health": data.get("health", "unknown") if isinstance(data, dict) else "unknown",
            }

            return format_success_response(response_data, result["command"], "System status retrieved successfully")
        else:
            return format_error_response(
                result.get("stderr", "Failed to get system status"),
                result["command"],
                [
                    "Check if tmux-orc daemon is running",
                    "Verify system permissions",
                    "Ensure monitoring services are active",
                ],
            )

    except ExecutionError as e:
        return format_error_response(str(e), "system status")
    except Exception as e:
        logger.error(f"Unexpected error in system_status: {e}")
        return format_error_response(f"Unexpected error: {e}", "system status")


async def monitor_dashboard(refresh_interval: int = 15, focus_team: Optional[str] = None) -> Dict[str, Any]:
    """
    Display interactive monitoring dashboard.

    Implements API Designer's monitor_dashboard specification with refresh intervals.

    Args:
        refresh_interval: Dashboard refresh interval in seconds (1-300)
        focus_team: Focus dashboard on specific team

    Returns:
        Structured response with dashboard status
    """
    try:
        # Validate refresh interval
        if not (1 <= refresh_interval <= 300):
            return format_error_response(
                f"Invalid refresh interval {refresh_interval}. Must be between 1 and 300 seconds",
                "monitor dashboard",
                ["Use refresh interval between 1-300 seconds"],
            )

        # Validate team name if provided
        if focus_team:
            import re

            if not re.match(r"^[a-zA-Z0-9_-]+$", focus_team):
                return format_error_response(
                    f"Invalid team name '{focus_team}'. Use alphanumeric characters, hyphens, and underscores only",
                    f"monitor dashboard --focus-team {focus_team}",
                )

        # Build command
        cmd = ["tmux-orc", "monitor", "dashboard"]

        # Add refresh interval if not default
        if refresh_interval != 15:
            cmd.extend(["--refresh", str(refresh_interval)])

        # Add team focus if provided
        if focus_team:
            cmd.extend(["--focus-team", focus_team])

        # Note: Dashboard is typically an interactive/daemon command
        # In MCP context, we start it in background and return status

        # Execute command
        executor = CommandExecutor()
        result = executor.execute(cmd, expect_json=True)

        if result["success"]:
            data = result["data"]

            # Structure response with metadata
            response_data = {
                "refresh_interval": refresh_interval,
                "focus_team": focus_team,
                "dashboard_status": data if isinstance(data, dict) else {"started": True},
                "dashboard_url": data.get("url") if isinstance(data, dict) else None,
                "dashboard_pid": data.get("pid") if isinstance(data, dict) else None,
            }

            return format_success_response(
                response_data, result["command"], f"Monitoring dashboard started with {refresh_interval}s refresh"
            )
        else:
            return format_error_response(
                result.get("stderr", "Failed to start monitoring dashboard"),
                result["command"],
                [
                    "Check if monitoring daemon is running",
                    "Verify dashboard port is available",
                    "Ensure sufficient system resources",
                ],
            )

    except ExecutionError as e:
        return format_error_response(str(e), "monitor dashboard")
    except Exception as e:
        logger.error(f"Unexpected error in monitor_dashboard: {e}")
        return format_error_response(f"Unexpected error: {e}", "monitor dashboard")


async def health_check(
    target: Optional[str] = None, deep_check: bool = False, auto_fix: bool = False
) -> Dict[str, Any]:
    """
    Perform comprehensive health check.

    Implements API Designer's health_check specification with auto-fix capability.

    Args:
        target: Specific target to check (session:window or team name)
        deep_check: Perform deep health analysis
        auto_fix: Automatically fix detected issues

    Returns:
        Structured response with health check results
    """
    try:
        # Validate target if provided
        if target:
            # Check if it's a session:window format or team name
            if ":" in target:
                # Validate as session:window target
                validate_session_format(target)
            else:
                # Validate as team/session name
                import re

                if not re.match(r"^[a-zA-Z0-9_-]+$", target):
                    return format_error_response(
                        f"Invalid target '{target}'. Use 'session:window' format or valid team name",
                        f"health check {target}",
                    )

        # Build command
        cmd = ["tmux-orc", "monitor", "health"]

        # Add target if provided
        if target:
            cmd.append(target)

        # Add deep check flag
        if deep_check:
            cmd.append("--deep")

        # Add auto-fix flag
        if auto_fix:
            cmd.append("--auto-fix")

        # Execute command
        executor = CommandExecutor()
        result = executor.execute(cmd, expect_json=True)

        if result["success"]:
            data = result["data"]

            # Structure response with metadata
            response_data = {
                "target": target,
                "deep_check": deep_check,
                "auto_fix": auto_fix,
                "health_results": data if isinstance(data, dict) else {"status": "healthy"},
                "issues_found": data.get("issues", []) if isinstance(data, dict) else [],
                "issues_fixed": data.get("fixed", []) if isinstance(data, dict) else [],
                "overall_health": data.get("overall_health", "unknown") if isinstance(data, dict) else "unknown",
            }

            # Add summary message
            issues_count = len(response_data["issues_found"]) if isinstance(response_data["issues_found"], list) else 0
            fixed_count = len(response_data["issues_fixed"]) if isinstance(response_data["issues_fixed"], list) else 0

            if issues_count == 0:
                summary_msg = "Health check passed - no issues found"
            else:
                summary_msg = f"Health check found {issues_count} issues"
                if auto_fix and fixed_count > 0:
                    summary_msg += f", {fixed_count} fixed automatically"

            if target:
                summary_msg += f" for {target}"

            return format_success_response(response_data, result["command"], summary_msg)
        else:
            return format_error_response(
                result.get("stderr", "Health check failed"),
                result["command"],
                [
                    suggestion
                    for suggestion in [
                        "Check if monitoring services are running",
                        "Verify target exists and is accessible" if target else None,
                        "Ensure sufficient permissions for health checks",
                        "Try without --auto-fix if permission issues occur",
                    ]
                    if suggestion is not None
                ],
            )

    except ValidationError as e:
        return format_error_response(str(e), f"health check {target or 'system'}")
    except ExecutionError as e:
        return format_error_response(str(e), f"health check {target or 'system'}")
    except Exception as e:
        logger.error(f"Unexpected error in health_check: {e}")
        return format_error_response(f"Unexpected error: {e}", f"health check {target or 'system'}")


async def get_monitor_logs(lines: int = 50, follow: bool = False, filter_level: Optional[str] = None) -> Dict[str, Any]:
    """
    Get monitoring system logs.

    Convenience function for retrieving monitor daemon logs.

    Args:
        lines: Number of log lines to retrieve
        follow: Follow log output (stream mode)
        filter_level: Filter by log level ("debug", "info", "warning", "error")

    Returns:
        Structured response with log data
    """
    try:
        # Validate lines parameter
        if not (1 <= lines <= 1000):
            return format_error_response(
                f"Invalid lines count {lines}. Must be between 1 and 1000",
                "get monitor logs",
                ["Use lines count between 1-1000"],
            )

        # Validate filter level if provided
        if filter_level:
            valid_levels = {"debug", "info", "warning", "error"}
            if filter_level not in valid_levels:
                return format_error_response(
                    f"Invalid log level '{filter_level}'. Valid levels: {', '.join(valid_levels)}",
                    "get monitor logs",
                    [f"Use one of: {', '.join(valid_levels)}"],
                )

        # Build command
        cmd = ["tmux-orc", "monitor", "logs"]

        # Add lines parameter
        cmd.extend(["--lines", str(lines)])

        # Add follow flag (note: in MCP context, follow might not be practical)
        if follow:
            cmd.append("--follow")

        # Add level filter if provided
        if filter_level:
            cmd.extend(["--level", filter_level])

        # Execute command
        executor = CommandExecutor(timeout=10)  # Shorter timeout for logs
        result = executor.execute(cmd, expect_json=False)  # Logs are typically text

        if result["success"]:
            # Structure response with metadata
            response_data = {
                "lines": lines,
                "follow": follow,
                "filter_level": filter_level,
                "log_content": result["stdout"],
                "log_lines_count": len(result["stdout"].split("\n")) if result["stdout"] else 0,
            }

            return format_success_response(
                response_data, result["command"], f"Retrieved {response_data['log_lines_count']} monitor log lines"
            )
        else:
            return format_error_response(
                result.get("stderr", "Failed to get monitor logs"),
                result["command"],
                [
                    "Check if monitor daemon is running",
                    "Verify log files are accessible",
                    "Ensure sufficient permissions for log access",
                ],
            )

    except ExecutionError as e:
        return format_error_response(str(e), "get monitor logs")
    except Exception as e:
        logger.error(f"Unexpected error in get_monitor_logs: {e}")
        return format_error_response(f"Unexpected error: {e}", "get monitor logs")

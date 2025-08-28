"""
Team Coordination Tools

Implements native MCP tools for team management and coordination with exact parameter
signatures from API Designer's specifications.
"""

import logging
import re
from typing import Any, Dict, List, Optional

# team_broadcast is implemented in communication_tools.py to avoid circular imports
from .communication_tools import team_broadcast as comm_team_broadcast
from .shared_logic import (
    CommandExecutor,
    ExecutionError,
    format_error_response,
    format_success_response,
)

logger = logging.getLogger(__name__)


async def team_status(
    team_name: Optional[str] = None, include_agents: bool = True, format: str = "table"
) -> Dict[str, Any]:
    """
    Get status of team or all teams.

    Implements API Designer's team_status specification with agent details.

    Args:
        team_name: Specific team name to check (optional for all teams)
        include_agents: Include individual agent status
        format: Output format ("table", "json", "summary")

    Returns:
        Structured response with team status information
    """
    try:
        # Validate team name if provided
        if team_name:
            if not re.match(r"^[a-zA-Z0-9_-]+$", team_name):
                return format_error_response(
                    f"Invalid team name '{team_name}'. Use alphanumeric characters, hyphens, and underscores only",
                    f"team status {team_name}",
                )

        # Validate format parameter
        valid_formats = {"table", "json", "summary"}
        if format not in valid_formats:
            return format_error_response(
                f"Invalid format '{format}'. Valid formats: {', '.join(valid_formats)}",
                "team status",
                ["Use 'table', 'json', or 'summary' format"],
            )

        # Build command
        cmd = ["tmux-orc", "team", "status"]

        # Add team name if provided
        if team_name:
            cmd.append(team_name)

        # Add format if not default
        if format != "table":
            cmd.extend(["--format", format])

        # Add exclude-agents flag if include_agents is false
        if not include_agents:
            cmd.append("--no-agents")

        # Execute command
        executor = CommandExecutor()
        result = executor.execute(cmd, expect_json=(format == "json"))

        if result["success"]:
            data = result["data"]

            # Structure response with metadata
            response_data = {
                "team_name": team_name,
                "include_agents": include_agents,
                "format": format,
                "team_status": data if isinstance(data, dict) else {"raw_status": data},
                "teams": data.get("teams", []) if isinstance(data, dict) else [],
                "team_count": len(data.get("teams", [])) if isinstance(data, dict) else 0,
            }

            if team_name:
                message = f"Status retrieved for team {team_name}"
            else:
                message = f"Status retrieved for {response_data['team_count']} teams"

            return format_success_response(response_data, result["command"], message)
        else:
            return format_error_response(
                result.get("stderr", "Failed to get team status"),
                result["command"],
                [
                    f"Check that team '{team_name}' exists" if team_name else "Check that teams exist",
                    "Verify team agents are running",
                    "Ensure tmux-orc service is active",
                ],
            )

    except ExecutionError as e:
        return format_error_response(str(e), f"team status {team_name or 'all'}")
    except Exception as e:
        logger.error(f"Unexpected error in team_status: {e}")
        return format_error_response(f"Unexpected error: {e}", f"team status {team_name or 'all'}")


async def team_deploy(
    team_name: str, team_type: str, team_size: int, project_context: Optional[str] = None
) -> Dict[str, Any]:
    """
    Deploy a new team.

    Implements API Designer's team_deploy specification with type validation.

    Args:
        team_name: Name for the new team
        team_type: Type of team to deploy ("frontend", "backend", "fullstack", "testing", "devops")
        team_size: Number of agents in the team (2-10)
        project_context: Project context for team briefing

    Returns:
        Structured response with deployment status
    """
    try:
        # Validate team name
        if not re.match(r"^[a-zA-Z0-9_-]+$", team_name):
            return format_error_response(
                f"Invalid team name '{team_name}'. Use alphanumeric characters, hyphens, and underscores only",
                f"team deploy {team_name}",
            )

        # Validate team type
        valid_types = {"frontend", "backend", "fullstack", "testing", "devops"}
        if team_type not in valid_types:
            return format_error_response(
                f"Invalid team type '{team_type}'. Valid types: {', '.join(valid_types)}",
                f"team deploy {team_name}",
                [f"Use one of: {', '.join(valid_types)}"],
            )

        # Validate team size
        if not (2 <= team_size <= 10):
            return format_error_response(
                f"Invalid team size {team_size}. Must be between 2 and 10",
                f"team deploy {team_name}",
                ["Use team size between 2-10"],
            )

        # Build command
        cmd = ["tmux-orc", "team", "deploy", team_type, str(team_size), team_name]

        # Add project context if provided
        if project_context:
            cmd.extend(["--context", project_context])

        # Execute command
        executor = CommandExecutor()
        result = executor.execute(cmd, expect_json=True)

        if result["success"]:
            data = result["data"]

            # Structure response with metadata
            response_data = {
                "team_name": team_name,
                "team_type": team_type,
                "team_size": team_size,
                "project_context": project_context,
                "deployment_status": data if isinstance(data, dict) else {"deployed": True},
                "agents_created": data.get("agents", []) if isinstance(data, dict) else [],
                "session_name": team_name,  # Team typically maps to session
                "deployment_time": data.get("deployment_time") if isinstance(data, dict) else None,
            }

            return format_success_response(
                response_data, result["command"], f"Team {team_name} deployed ({team_type}, {team_size} agents)"
            )
        else:
            return format_error_response(
                result.get("stderr", f"Failed to deploy team {team_name}"),
                result["command"],
                [
                    "Check system resources for multiple agent spawning",
                    f"Verify team name '{team_name}' is not already in use",
                    "Ensure tmux-orc service is running properly",
                    f"Confirm {team_type} is a supported team type",
                ],
            )

    except ExecutionError as e:
        return format_error_response(str(e), f"team deploy {team_name}")
    except Exception as e:
        logger.error(f"Unexpected error in team_deploy: {e}")
        return format_error_response(f"Unexpected error: {e}", f"team deploy {team_name}")


async def team_list(format: str = "table", include_empty: bool = False) -> Dict[str, Any]:
    """
    List all active teams.

    Implements API Designer's team_list specification with empty team handling.

    Args:
        format: Output format ("table", "json", "summary")
        include_empty: Include teams with no active agents

    Returns:
        Structured response with team list
    """
    try:
        # Validate format parameter
        valid_formats = {"table", "json", "summary"}
        if format not in valid_formats:
            return format_error_response(
                f"Invalid format '{format}'. Valid formats: {', '.join(valid_formats)}",
                "team list",
                ["Use 'table', 'json', or 'summary' format"],
            )

        # Build command
        cmd = ["tmux-orc", "team", "list"]

        # Add format if not default
        if format != "table":
            cmd.extend(["--format", format])

        # Add include-empty flag if requested
        if include_empty:
            cmd.append("--include-empty")

        # Execute command
        executor = CommandExecutor()
        result = executor.execute(cmd, expect_json=(format == "json"))

        if result["success"]:
            data = result["data"]

            # Structure response with metadata
            response_data = {
                "format": format,
                "include_empty": include_empty,
                "teams": data.get("teams", []) if isinstance(data, dict) else [],
                "team_count": len(data.get("teams", [])) if isinstance(data, dict) else 0,
                "active_teams": data.get("active_count", 0) if isinstance(data, dict) else 0,
                "empty_teams": data.get("empty_count", 0) if isinstance(data, dict) else 0,
            }

            return format_success_response(
                response_data, result["command"], f"Retrieved {response_data['team_count']} teams"
            )
        else:
            return format_error_response(
                result.get("stderr", "Failed to list teams"),
                result["command"],
                [
                    "Check if any teams are deployed",
                    "Verify tmux-orc service is active",
                    "Ensure team sessions are accessible",
                ],
            )

    except ExecutionError as e:
        return format_error_response(str(e), "team list")
    except Exception as e:
        logger.error(f"Unexpected error in team_list: {e}")
        return format_error_response(f"Unexpected error: {e}", "team list")


async def team_broadcast(
    team_name: str, message: str, priority: str = "normal", exclude_roles: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Send message to all team members.

    This is an alias that imports from communication_tools to avoid circular imports.
    """
    return await comm_team_broadcast(
        team_name=team_name, message=message, priority=priority, exclude_roles=exclude_roles
    )


async def team_kill(team_name: str, graceful: bool = True, timeout: int = 30) -> Dict[str, Any]:
    """
    Terminate an entire team.

    Convenience function for team termination with graceful shutdown.

    Args:
        team_name: Team name to terminate
        graceful: Attempt graceful shutdown of all agents first
        timeout: Timeout in seconds for graceful shutdown

    Returns:
        Structured response with termination status
    """
    try:
        # Validate team name
        if not re.match(r"^[a-zA-Z0-9_-]+$", team_name):
            return format_error_response(
                f"Invalid team name '{team_name}'. Use alphanumeric characters, hyphens, and underscores only",
                f"team kill {team_name}",
            )

        # Validate timeout
        if not (5 <= timeout <= 300):
            return format_error_response(
                f"Invalid timeout {timeout}. Must be between 5 and 300 seconds",
                f"team kill {team_name}",
                ["Use timeout between 5-300 seconds"],
            )

        # Build command
        cmd = ["tmux-orc", "team", "kill", team_name]

        # Add graceful flag (default is true, so add --force if false)
        if not graceful:
            cmd.append("--force")

        # Add timeout if not default
        if timeout != 30:
            cmd.extend(["--timeout", str(timeout)])

        # Execute command
        executor = CommandExecutor(timeout=timeout + 10)  # Add buffer to executor timeout
        result = executor.execute(cmd, expect_json=True)

        if result["success"]:
            data = result["data"]

            # Structure response with metadata
            response_data = {
                "team_name": team_name,
                "graceful": graceful,
                "timeout": timeout,
                "kill_status": data if isinstance(data, dict) else {"killed": True},
                "agents_terminated": data.get("agents_terminated", []) if isinstance(data, dict) else [],
                "session_killed": data.get("session_killed", True) if isinstance(data, dict) else True,
            }

            return format_success_response(
                response_data,
                result["command"],
                f"Team {team_name} terminated {'gracefully' if graceful else 'forcefully'}",
            )
        else:
            return format_error_response(
                result.get("stderr", f"Failed to kill team {team_name}"),
                result["command"],
                [
                    f"Check that team '{team_name}' exists",
                    "Use graceful=false for unresponsive teams",
                    "Verify you have permission to kill the team",
                    "Consider killing individual agents first",
                ],
            )

    except ExecutionError as e:
        return format_error_response(str(e), f"team kill {team_name}")
    except Exception as e:
        logger.error(f"Unexpected error in team_kill: {e}")
        return format_error_response(f"Unexpected error: {e}", f"team kill {team_name}")


async def team_scale(
    team_name: str, target_size: int, role_distribution: Optional[Dict[str, int]] = None
) -> Dict[str, Any]:
    """
    Scale team up or down.

    Convenience function for dynamic team scaling.

    Args:
        team_name: Team name to scale
        target_size: Target number of agents (1-10)
        role_distribution: Optional role distribution for new agents

    Returns:
        Structured response with scaling status
    """
    try:
        # Validate team name
        if not re.match(r"^[a-zA-Z0-9_-]+$", team_name):
            return format_error_response(
                f"Invalid team name '{team_name}'. Use alphanumeric characters, hyphens, and underscores only",
                f"team scale {team_name}",
            )

        # Validate target size
        if not (1 <= target_size <= 10):
            return format_error_response(
                f"Invalid target size {target_size}. Must be between 1 and 10",
                f"team scale {team_name}",
                ["Use target size between 1-10"],
            )

        # Validate role distribution if provided
        if role_distribution:
            total_roles = sum(role_distribution.values())
            if total_roles != target_size:
                return format_error_response(
                    f"Role distribution total ({total_roles}) doesn't match target size ({target_size})",
                    f"team scale {team_name}",
                    ["Ensure role distribution adds up to target size"],
                )

        # Build command
        cmd = ["tmux-orc", "team", "scale", team_name, str(target_size)]

        # Add role distribution if provided
        if role_distribution:
            role_string = ",".join([f"{role}:{count}" for role, count in role_distribution.items()])
            cmd.extend(["--roles", role_string])

        # Execute command
        executor = CommandExecutor()
        result = executor.execute(cmd, expect_json=True)

        if result["success"]:
            data = result["data"]

            # Structure response with metadata
            response_data = {
                "team_name": team_name,
                "target_size": target_size,
                "role_distribution": role_distribution,
                "scaling_status": data if isinstance(data, dict) else {"scaled": True},
                "current_size": data.get("current_size", target_size) if isinstance(data, dict) else target_size,
                "agents_added": data.get("agents_added", []) if isinstance(data, dict) else [],
                "agents_removed": data.get("agents_removed", []) if isinstance(data, dict) else [],
            }

            return format_success_response(
                response_data, result["command"], f"Team {team_name} scaled to {target_size} agents"
            )
        else:
            return format_error_response(
                result.get("stderr", f"Failed to scale team {team_name}"),
                result["command"],
                [
                    f"Check that team '{team_name}' exists",
                    "Verify sufficient system resources for scaling up",
                    "Ensure agents can be gracefully removed for scaling down",
                ],
            )

    except ExecutionError as e:
        return format_error_response(str(e), f"team scale {team_name}")
    except Exception as e:
        logger.error(f"Unexpected error in team_scale: {e}")
        return format_error_response(f"Unexpected error: {e}", f"team scale {team_name}")

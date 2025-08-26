"""
Deployment & Spawning Tools

Implements native MCP tools for agent spawning and deployment with exact parameter
signatures from API Designer's specifications.
"""

import logging
from typing import Any, Dict, List, Optional

from .shared_logic import (
    AgentValidator,
    CommandExecutor,
    ExecutionError,
    ValidationError,
    format_error_response,
    format_success_response,
    validate_session_format,
)

logger = logging.getLogger(__name__)


async def spawn_agent(
    role: str,
    session_name: str,
    briefing: str,
    window: Optional[int] = None,
    technology_stack: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Spawn a new agent.

    Implements API Designer's spawn_agent specification with role validation and tech stack.

    Args:
        role: Agent role/specialization ("developer", "qa", "devops", "pm", "reviewer", "researcher")
        session_name: Target session name
        briefing: Initial briefing/context for the agent
        window: Target window number (optional, auto-assigned if None)
        technology_stack: Technologies the agent should focus on

    Returns:
        Structured response with spawn status and agent info
    """
    try:
        # Validate role
        valid_roles = {"developer", "qa", "devops", "pm", "reviewer", "researcher"}
        if role not in valid_roles:
            return format_error_response(
                f"Invalid role '{role}'. Valid roles: {', '.join(valid_roles)}",
                f"spawn agent {role}",
                [f"Use one of: {', '.join(valid_roles)}"],
            )

        # Validate session name format (no colon allowed)
        import re

        if not re.match(r"^[a-zA-Z0-9_-]+$", session_name):
            return format_error_response(
                f"Invalid session name '{session_name}'. Use alphanumeric characters, hyphens, and underscores only",
                f"spawn agent {role} {session_name}",
            )

        # Validate briefing
        AgentValidator.validate_briefing(briefing)

        # Validate window if provided
        if window is not None:
            if window < 0:
                return format_error_response(
                    f"Invalid window number {window}. Must be >= 0", f"spawn agent {role} {session_name}"
                )
            # Build target for validation
            target = f"{session_name}:{window}"
            validate_session_format(target)

        # Build command
        cmd = ["tmux-orc", "spawn", "agent", role]

        # Add session target
        if window is not None:
            cmd.extend(["--session", f"{session_name}:{window}"])
        else:
            cmd.extend(["--session", session_name])

        # Add briefing
        cmd.extend(["--briefing", briefing])

        # Add technology stack if provided
        if technology_stack:
            tech_string = ", ".join(technology_stack)
            cmd.extend(["--tech-stack", tech_string])

        # Execute command
        executor = CommandExecutor()
        result = executor.execute(cmd, expect_json=True)

        if result["success"]:
            data = result["data"]

            # Structure response with metadata
            response_data = {
                "role": role,
                "session_name": session_name,
                "window": window,
                "briefing": briefing,
                "technology_stack": technology_stack,
                "spawn_status": data if isinstance(data, dict) else {"spawned": True},
                "target": f"{session_name}:{window}" if window is not None else f"{session_name}:auto",
                "agent_id": data.get("agent_id") if isinstance(data, dict) else None,
            }

            return format_success_response(
                response_data,
                result["command"],
                f"Agent {role} spawned in {session_name}" + (f":{window}" if window else ""),
            )
        else:
            return format_error_response(
                result.get("stderr", f"Failed to spawn {role} agent"),
                result["command"],
                [
                    "Check that session exists or can be created",
                    "Verify briefing is comprehensive",
                    "Ensure sufficient system resources",
                    f"Confirm {role} is a valid agent type",
                ],
            )

    except ValidationError as e:
        return format_error_response(str(e), f"spawn agent {role} {session_name}")
    except ExecutionError as e:
        return format_error_response(str(e), f"spawn agent {role} {session_name}")
    except Exception as e:
        logger.error(f"Unexpected error in spawn_agent: {e}")
        return format_error_response(f"Unexpected error: {e}", f"spawn agent {role} {session_name}")


async def spawn_pm(
    session_name: str, window: int = 1, project_context: Optional[str] = None, team_size: Optional[int] = None
) -> Dict[str, Any]:
    """
    Spawn a project manager.

    Implements API Designer's spawn_pm specification with team size awareness.

    Args:
        session_name: Target session name
        window: Target window number (default: 1)
        project_context: Project context and objectives
        team_size: Expected team size to manage (1-10)

    Returns:
        Structured response with PM spawn status
    """
    try:
        # Validate session name
        import re

        if not re.match(r"^[a-zA-Z0-9_-]+$", session_name):
            return format_error_response(
                f"Invalid session name '{session_name}'. Use alphanumeric characters, hyphens, and underscores only",
                f"spawn pm {session_name}",
            )

        # Validate window
        if window < 0:
            return format_error_response(f"Invalid window number {window}. Must be >= 0", f"spawn pm {session_name}")

        # Validate team size if provided
        if team_size is not None:
            if not (1 <= team_size <= 10):
                return format_error_response(
                    f"Invalid team size {team_size}. Must be between 1 and 10",
                    f"spawn pm {session_name}",
                    ["Use team size between 1-10"],
                )

        # Build briefing for PM
        pm_briefing = "Project Manager with standard PM context"
        if project_context:
            pm_briefing = f"Project Manager: {project_context}"
        if team_size:
            pm_briefing += f" (managing team of {team_size})"

        # Build command
        cmd = ["tmux-orc", "spawn", "pm"]

        # Add session target
        target = f"{session_name}:{window}"
        validate_session_format(target)  # Validate the full target
        cmd.extend(["--session", target])

        # Add briefing
        cmd.extend(["--briefing", pm_briefing])

        # Add team size as metadata if provided
        if team_size:
            cmd.extend(["--team-size", str(team_size)])

        # Execute command
        executor = CommandExecutor()
        result = executor.execute(cmd, expect_json=True)

        if result["success"]:
            data = result["data"]

            # Structure response with metadata
            response_data = {
                "session_name": session_name,
                "window": window,
                "project_context": project_context,
                "team_size": team_size,
                "briefing": pm_briefing,
                "spawn_status": data if isinstance(data, dict) else {"spawned": True},
                "target": target,
                "pm_id": data.get("pm_id") if isinstance(data, dict) else None,
            }

            return format_success_response(response_data, result["command"], f"Project Manager spawned in {target}")
        else:
            return format_error_response(
                result.get("stderr", "Failed to spawn Project Manager"),
                result["command"],
                [
                    "Check that session exists or can be created",
                    "Verify window is available",
                    "Ensure sufficient system resources",
                ],
            )

    except ValidationError as e:
        return format_error_response(str(e), f"spawn pm {session_name}")
    except ExecutionError as e:
        return format_error_response(str(e), f"spawn pm {session_name}")
    except Exception as e:
        logger.error(f"Unexpected error in spawn_pm: {e}")
        return format_error_response(f"Unexpected error: {e}", f"spawn pm {session_name}")


async def spawn_orchestrator(session_name: str, window: int = 0, scope: str = "project") -> Dict[str, Any]:
    """
    Spawn an orchestrator agent.

    Implements API Designer's spawn_orchestrator specification with scope definition.

    Args:
        session_name: Target session name
        window: Target window number (default: 0)
        scope: Orchestrator scope of responsibility ("project", "system", "team")

    Returns:
        Structured response with orchestrator spawn status
    """
    try:
        # Validate session name
        import re

        if not re.match(r"^[a-zA-Z0-9_-]+$", session_name):
            return format_error_response(
                f"Invalid session name '{session_name}'. Use alphanumeric characters, hyphens, and underscores only",
                f"spawn orchestrator {session_name}",
            )

        # Validate window
        if window < 0:
            return format_error_response(
                f"Invalid window number {window}. Must be >= 0", f"spawn orchestrator {session_name}"
            )

        # Validate scope
        valid_scopes = {"project", "system", "team"}
        if scope not in valid_scopes:
            return format_error_response(
                f"Invalid scope '{scope}'. Valid scopes: {', '.join(valid_scopes)}",
                f"spawn orchestrator {session_name}",
                [f"Use one of: {', '.join(valid_scopes)}"],
            )

        # Build briefing for orchestrator
        orchestrator_briefing = f"Orchestrator with {scope} scope responsibility"

        # Build command
        cmd = ["tmux-orc", "spawn", "orchestrator"]

        # Add session target
        target = f"{session_name}:{window}"
        validate_session_format(target)  # Validate the full target
        cmd.extend(["--session", target])

        # Add briefing
        cmd.extend(["--briefing", orchestrator_briefing])

        # Add scope as metadata
        cmd.extend(["--scope", scope])

        # Execute command
        executor = CommandExecutor()
        result = executor.execute(cmd, expect_json=True)

        if result["success"]:
            data = result["data"]

            # Structure response with metadata
            response_data = {
                "session_name": session_name,
                "window": window,
                "scope": scope,
                "briefing": orchestrator_briefing,
                "spawn_status": data if isinstance(data, dict) else {"spawned": True},
                "target": target,
                "orchestrator_id": data.get("orchestrator_id") if isinstance(data, dict) else None,
            }

            return format_success_response(
                response_data, result["command"], f"Orchestrator spawned in {target} with {scope} scope"
            )
        else:
            return format_error_response(
                result.get("stderr", "Failed to spawn Orchestrator"),
                result["command"],
                [
                    "Check that session exists or can be created",
                    "Verify window is available",
                    "Ensure sufficient system resources",
                ],
            )

    except ValidationError as e:
        return format_error_response(str(e), f"spawn orchestrator {session_name}")
    except ExecutionError as e:
        return format_error_response(str(e), f"spawn orchestrator {session_name}")
    except Exception as e:
        logger.error(f"Unexpected error in spawn_orchestrator: {e}")
        return format_error_response(f"Unexpected error: {e}", f"spawn orchestrator {session_name}")


async def quick_deploy(
    team_type: str, team_size: int, project_name: Optional[str] = None, technology_focus: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Rapidly deploy optimized team configurations.

    Implements API Designer's quick_deploy specification for rapid deployment.

    Args:
        team_type: Type of team to deploy ("frontend", "backend", "fullstack", "testing")
        team_size: Number of agents in team (2-6)
        project_name: Project name for the team
        technology_focus: Primary technologies/frameworks

    Returns:
        Structured response with deployment status
    """
    try:
        # Validate team type
        valid_team_types = {"frontend", "backend", "fullstack", "testing"}
        if team_type not in valid_team_types:
            return format_error_response(
                f"Invalid team type '{team_type}'. Valid types: {', '.join(valid_team_types)}",
                f"quick deploy {team_type}",
                [f"Use one of: {', '.join(valid_team_types)}"],
            )

        # Validate team size
        if not (2 <= team_size <= 6):
            return format_error_response(
                f"Invalid team size {team_size}. Must be between 2 and 6",
                f"quick deploy {team_type} {team_size}",
                ["Use team size between 2-6 for quick deploy"],
            )

        # Use team type as project name if not provided
        deploy_project_name = project_name or f"{team_type}-project"

        # Build command
        cmd = ["tmux-orc", "team", "deploy", team_type, str(team_size), deploy_project_name]

        # Add technology focus if provided
        if technology_focus:
            tech_string = ",".join(technology_focus)
            cmd.extend(["--tech-focus", tech_string])

        # Execute command
        executor = CommandExecutor()
        result = executor.execute(cmd, expect_json=True)

        if result["success"]:
            data = result["data"]

            # Structure response with metadata
            response_data = {
                "team_type": team_type,
                "team_size": team_size,
                "project_name": deploy_project_name,
                "technology_focus": technology_focus,
                "deployment_status": data if isinstance(data, dict) else {"deployed": True},
                "team_session": deploy_project_name,
                "agents_deployed": data.get("agents") if isinstance(data, dict) else [],
            }

            return format_success_response(
                response_data,
                result["command"],
                f"Quick deployed {team_type} team ({team_size} agents) for {deploy_project_name}",
            )
        else:
            return format_error_response(
                result.get("stderr", f"Failed to quick deploy {team_type} team"),
                result["command"],
                [
                    "Check system resources for multiple agent spawning",
                    "Verify project name is valid",
                    "Ensure tmux-orc service is running properly",
                ],
            )

    except ExecutionError as e:
        return format_error_response(str(e), f"quick deploy {team_type} {team_size}")
    except Exception as e:
        logger.error(f"Unexpected error in quick_deploy: {e}")
        return format_error_response(f"Unexpected error: {e}", f"quick deploy {team_type} {team_size}")

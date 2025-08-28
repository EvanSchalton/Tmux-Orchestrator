"""
Session Management Tools

Implements native MCP tools for tmux session management with exact parameter
signatures from API Designer's specifications.
"""

import logging
import os
import re
from typing import Any, Dict, Optional

from .shared_logic import (
    CommandExecutor,
    ExecutionError,
    format_error_response,
    format_success_response,
)

logger = logging.getLogger(__name__)


async def session_list(format: str = "table", include_empty: bool = True) -> Dict[str, Any]:
    """
    List all tmux sessions.

    Implements API Designer's session_list specification with tree format option.

    Args:
        format: Output format ("table", "json", "tree")
        include_empty: Include sessions with no agents

    Returns:
        Structured response with session list
    """
    try:
        # Validate format parameter
        valid_formats = {"table", "json", "tree"}
        if format not in valid_formats:
            return format_error_response(
                f"Invalid format '{format}'. Valid formats: {', '.join(valid_formats)}",
                "session list",
                ["Use 'table', 'json', or 'tree' format"],
            )

        # Build command
        cmd = ["tmux-orc", "session", "list"]

        # Add format if not default
        if format != "table":
            cmd.extend(["--format", format])

        # Add exclude-empty flag if include_empty is false
        if not include_empty:
            cmd.append("--exclude-empty")

        # Execute command
        executor = CommandExecutor()
        result = executor.execute(cmd, expect_json=(format == "json"))

        if result["success"]:
            data = result["data"]

            # Structure response with metadata
            response_data = {
                "format": format,
                "include_empty": include_empty,
                "sessions": data.get("sessions", []) if isinstance(data, dict) else [],
                "session_count": len(data.get("sessions", [])) if isinstance(data, dict) else 0,
                "active_sessions": data.get("active", 0) if isinstance(data, dict) else 0,
            }

            return format_success_response(
                response_data, result["command"], f"Retrieved {response_data['session_count']} sessions"
            )
        else:
            return format_error_response(
                result.get("stderr", "Failed to list sessions"),
                result["command"],
                ["Check if tmux is running", "Verify session access permissions", "Ensure tmux-orc service is active"],
            )

    except ExecutionError as e:
        return format_error_response(str(e), "session list")
    except Exception as e:
        logger.error(f"Unexpected error in session_list: {e}")
        return format_error_response(f"Unexpected error: {e}", "session list")


async def session_attach(session_name: str, window: Optional[int] = None, read_only: bool = False) -> Dict[str, Any]:
    """
    Attach to a tmux session.

    Implements API Designer's session_attach specification with window targeting.

    Args:
        session_name: Session name to attach to
        window: Specific window to attach to
        read_only: Attach in read-only mode

    Returns:
        Structured response with attachment status
    """
    try:
        # Validate session name
        if not re.match(r"^[a-zA-Z0-9_-]+$", session_name):
            return format_error_response(
                f"Invalid session name '{session_name}'. Use alphanumeric characters, hyphens, and underscores only",
                f"session attach {session_name}",
            )

        # Validate window if provided
        if window is not None and window < 0:
            return format_error_response(
                f"Invalid window number {window}. Must be >= 0",
                f"session attach {session_name}",
                ["Use window number >= 0"],
            )

        # Build command
        cmd = ["tmux-orc", "session", "attach"]

        # Add target (session or session:window)
        if window is not None:
            target = f"{session_name}:{window}"
            cmd.append(target)
        else:
            cmd.append(session_name)

        # Add read-only flag if requested
        if read_only:
            cmd.append("--read-only")

        # Execute command
        executor = CommandExecutor()
        result = executor.execute(cmd, expect_json=True)

        if result["success"]:
            data = result["data"]

            # Structure response with metadata
            response_data = {
                "session_name": session_name,
                "window": window,
                "read_only": read_only,
                "attach_status": data if isinstance(data, dict) else {"attached": True},
                "target": f"{session_name}:{window}" if window is not None else session_name,
                "attach_mode": "read-only" if read_only else "interactive",
            }

            return format_success_response(
                response_data,
                result["command"],
                f"Attached to {response_data['target']} in {response_data['attach_mode']} mode",
            )
        else:
            suggestions = [
                f"Check that session '{session_name}' exists",
                "Ensure you have attach permissions",
                "Use 'tmux-orc session list' to see available sessions",
            ]
            if window is not None:
                suggestions.insert(1, f"Verify window {window} exists")

            return format_error_response(
                result.get("stderr", f"Failed to attach to session {session_name}"), result["command"], suggestions
            )

    except ExecutionError as e:
        return format_error_response(str(e), f"session attach {session_name}")
    except Exception as e:
        logger.error(f"Unexpected error in session_attach: {e}")
        return format_error_response(f"Unexpected error: {e}", f"session attach {session_name}")


async def session_kill(session_name: str, force: bool = False) -> Dict[str, Any]:
    """
    Terminate a tmux session.

    Implements API Designer's session_kill specification with force protection.

    Args:
        session_name: Session name to terminate
        force: Force kill even with active agents

    Returns:
        Structured response with kill status
    """
    try:
        # Validate session name
        if not re.match(r"^[a-zA-Z0-9_-]+$", session_name):
            return format_error_response(
                f"Invalid session name '{session_name}'. Use alphanumeric characters, hyphens, and underscores only",
                f"session kill {session_name}",
            )

        # Build command
        cmd = ["tmux-orc", "session", "kill", session_name]

        # Add force flag if requested
        if force:
            cmd.append("--force")

        # Execute command
        executor = CommandExecutor()
        result = executor.execute(cmd, expect_json=True)

        if result["success"]:
            data = result["data"]

            # Structure response with metadata
            response_data = {
                "session_name": session_name,
                "force": force,
                "kill_status": data if isinstance(data, dict) else {"killed": True},
                "agents_terminated": data.get("agents_terminated", []) if isinstance(data, dict) else [],
                "kill_method": "force" if force else "graceful",
            }

            return format_success_response(
                response_data,
                result["command"],
                f"Session {session_name} terminated {'forcefully' if force else 'gracefully'}",
            )
        else:
            return format_error_response(
                result.get("stderr", f"Failed to kill session {session_name}"),
                result["command"],
                [
                    f"Check that session '{session_name}' exists",
                    "Use --force flag if session has active agents",
                    "Verify you have permission to kill the session",
                    "Consider killing individual agents first",
                ],
            )

    except ExecutionError as e:
        return format_error_response(str(e), f"session kill {session_name}")
    except Exception as e:
        logger.error(f"Unexpected error in session_kill: {e}")
        return format_error_response(f"Unexpected error: {e}", f"session kill {session_name}")


async def session_create(
    session_name: str, start_directory: Optional[str] = None, detached: bool = True
) -> Dict[str, Any]:
    """
    Create a new tmux session.

    Convenience function for session creation with project setup.

    Args:
        session_name: Name for the new session
        start_directory: Starting directory for the session
        detached: Create session in detached mode

    Returns:
        Structured response with creation status
    """
    try:
        # Validate session name
        if not re.match(r"^[a-zA-Z0-9_-]+$", session_name):
            return format_error_response(
                f"Invalid session name '{session_name}'. Use alphanumeric characters, hyphens, and underscores only",
                f"session create {session_name}",
            )

        # Validate start directory if provided
        if start_directory:
            if not os.path.isdir(start_directory):
                return format_error_response(
                    f"Start directory '{start_directory}' does not exist",
                    f"session create {session_name}",
                    ["Provide a valid directory path"],
                )

        # Build command
        cmd = ["tmux-orc", "session", "create", session_name]

        # Add start directory if provided
        if start_directory:
            cmd.extend(["--start-directory", start_directory])

        # Add detached flag (default is true, so add --attached if false)
        if not detached:
            cmd.append("--attached")

        # Execute command
        executor = CommandExecutor()
        result = executor.execute(cmd, expect_json=True)

        if result["success"]:
            data = result["data"]

            # Structure response with metadata
            response_data = {
                "session_name": session_name,
                "start_directory": start_directory,
                "detached": detached,
                "creation_status": data if isinstance(data, dict) else {"created": True},
                "session_id": data.get("session_id") if isinstance(data, dict) else None,
            }

            return format_success_response(
                response_data,
                result["command"],
                f"Session {session_name} created {'in detached mode' if detached else 'and attached'}",
            )
        else:
            suggestions = [
                f"Check that session name '{session_name}' is not already in use",
                "Ensure sufficient system resources",
                "Check tmux is properly installed and configured",
            ]
            if start_directory:
                suggestions.insert(1, "Verify start directory exists and is accessible")

            return format_error_response(
                result.get("stderr", f"Failed to create session {session_name}"), result["command"], suggestions
            )

    except ExecutionError as e:
        return format_error_response(str(e), f"session create {session_name}")
    except Exception as e:
        logger.error(f"Unexpected error in session_create: {e}")
        return format_error_response(f"Unexpected error: {e}", f"session create {session_name}")


async def session_info(session_name: str, include_windows: bool = True) -> Dict[str, Any]:
    """
    Get detailed information about a session.

    Convenience function for session introspection.

    Args:
        session_name: Session name to get info about
        include_windows: Include window details

    Returns:
        Structured response with session information
    """
    try:
        # Validate session name
        if not re.match(r"^[a-zA-Z0-9_-]+$", session_name):
            return format_error_response(
                f"Invalid session name '{session_name}'. Use alphanumeric characters, hyphens, and underscores only",
                f"session info {session_name}",
            )

        # Build command
        cmd = ["tmux-orc", "session", "info", session_name]

        # Add windows flag (default is true, so add --no-windows if false)
        if not include_windows:
            cmd.append("--no-windows")

        # Execute command
        executor = CommandExecutor()
        result = executor.execute(cmd, expect_json=True)

        if result["success"]:
            data = result["data"]

            # Structure response with metadata
            response_data = {
                "session_name": session_name,
                "include_windows": include_windows,
                "session_info": data if isinstance(data, dict) else {"info": data},
                "windows": data.get("windows", []) if isinstance(data, dict) and include_windows else [],
                "window_count": len(data.get("windows", [])) if isinstance(data, dict) else 0,
            }

            return format_success_response(
                response_data, result["command"], f"Session info retrieved for {session_name}"
            )
        else:
            return format_error_response(
                result.get("stderr", f"Failed to get info for session {session_name}"),
                result["command"],
                [
                    f"Check that session '{session_name}' exists",
                    "Verify you have access permissions",
                    "Use 'tmux-orc session list' to see available sessions",
                ],
            )

    except ExecutionError as e:
        return format_error_response(str(e), f"session info {session_name}")
    except Exception as e:
        logger.error(f"Unexpected error in session_info: {e}")
        return format_error_response(f"Unexpected error: {e}", f"session info {session_name}")

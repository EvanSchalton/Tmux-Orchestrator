"""
Shared Business Logic for MCP Tools

This module contains common functionality used across multiple MCP tools,
extracted and refactored from the existing CLI implementations.
"""

import json
import logging
import re
import subprocess
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom exception for parameter validation errors."""

    pass


class ExecutionError(Exception):
    """Custom exception for command execution errors."""

    pass


def validate_session_format(target: str) -> bool:
    """
    Validate session:window format.

    Args:
        target: Target string to validate

    Returns:
        True if valid format

    Raises:
        ValidationError: If format is invalid
    """
    if not target:
        raise ValidationError("Target cannot be empty")

    if ":" not in target:
        raise ValidationError("Target must be in 'session:window' format")

    parts = target.split(":")
    if len(parts) != 2:
        raise ValidationError("Target must be in 'session:window' format")

    session, window = parts
    if not session or not window:
        raise ValidationError("Both session and window must be specified")

    # Validate window is numeric
    if not window.isdigit():
        raise ValidationError("Window must be numeric")

    # Validate session name format (alphanumeric, hyphens, underscores)
    if not re.match(r"^[a-zA-Z0-9_-]+$", session):
        raise ValidationError("Session name must contain only alphanumeric characters, hyphens, and underscores")

    return True


def parse_target(target: str) -> Tuple[str, int]:
    """
    Parse target string into session and window.

    Args:
        target: Target string in 'session:window' format

    Returns:
        Tuple of (session_name, window_number)

    Raises:
        ValidationError: If format is invalid
    """
    validate_session_format(target)
    session, window_str = target.split(":")
    return session, int(window_str)


def build_command(base_command: List[str], options: Optional[Dict[str, Any]] = None) -> List[str]:
    """
    Build command list with options.

    Args:
        base_command: Base command parts
        options: Optional flags and parameters

    Returns:
        Complete command list
    """
    cmd = base_command.copy()

    if options:
        for key, value in options.items():
            if value is True:
                cmd.append(f"--{key}")
            elif value is not False and value is not None:
                cmd.extend([f"--{key}", str(value)])

    return cmd


class CommandExecutor:
    """
    Centralized command execution with consistent error handling and output parsing.
    """

    def __init__(self, timeout: int = 60):
        """
        Initialize command executor.

        Args:
            timeout: Command timeout in seconds
        """
        self.timeout = timeout

    def execute(self, command: List[str], expect_json: bool = True, input_data: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute command and return structured result.

        Args:
            command: Command to execute
            expect_json: Whether to parse output as JSON
            input_data: Optional stdin input

        Returns:
            Structured result dictionary

        Raises:
            ExecutionError: If command fails
        """
        try:
            logger.debug(f"Executing command: {' '.join(command)}")

            # Add --json flag for commands that support it
            if expect_json and "--json" not in command and self._supports_json(command):
                command = command + ["--json"]

            result = subprocess.run(command, capture_output=True, text=True, timeout=self.timeout, input=input_data)

            # Parse output
            parsed_output = {}
            if result.stdout:
                if expect_json:
                    try:
                        parsed_output = json.loads(result.stdout)
                    except json.JSONDecodeError:
                        parsed_output = {"raw_output": result.stdout}
                else:
                    parsed_output = {"output": result.stdout}

            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "data": parsed_output,
                "command": " ".join(command),
            }

        except subprocess.TimeoutExpired:
            raise ExecutionError(f"Command timed out after {self.timeout} seconds")
        except Exception as e:
            raise ExecutionError(f"Command execution failed: {str(e)}")

    def _supports_json(self, command: List[str]) -> bool:
        """
        Check if command supports JSON output.

        Args:
            command: Command to check

        Returns:
            True if JSON is supported
        """
        if len(command) < 2:
            return False

        # Commands known to support JSON
        json_commands = {"list", "status", "reflect", "spawn", "agent", "team", "monitor"}

        # Check if any command part matches
        return any(part in json_commands for part in command)


def execute_command(
    command: List[str], expect_json: bool = True, timeout: int = 60, input_data: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function for command execution.

    Args:
        command: Command to execute
        expect_json: Whether to parse output as JSON
        timeout: Command timeout in seconds
        input_data: Optional stdin input

    Returns:
        Structured result dictionary
    """
    executor = CommandExecutor(timeout)
    return executor.execute(command, expect_json, input_data)


def format_error_response(error: str, command: str, suggestions: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Format consistent error response.

    Args:
        error: Error message
        command: Command that failed
        suggestions: Optional suggestions for fixing the error

    Returns:
        Formatted error response
    """
    response = {
        "success": False,
        "error": error,
        "command": command,
    }

    if suggestions:
        response["suggestions"] = suggestions

    return response


def format_success_response(data: Any, command: str, message: Optional[str] = None) -> Dict[str, Any]:
    """
    Format consistent success response.

    Args:
        data: Response data
        command: Command that succeeded
        message: Optional success message

    Returns:
        Formatted success response
    """
    response = {
        "success": True,
        "data": data,
        "command": command,
    }

    if message:
        response["message"] = message

    return response


class AgentValidator:
    """
    Validation utilities for agent-related operations.
    """

    @staticmethod
    def validate_agent_role(role: str) -> bool:
        """
        Validate agent role.

        Args:
            role: Agent role to validate

        Returns:
            True if valid

        Raises:
            ValidationError: If role is invalid
        """
        valid_roles = {
            "developer",
            "backend-developer",
            "frontend-developer",
            "qa-engineer",
            "devops",
            "code-reviewer",
            "documentation-writer",
            "researcher",
            "project-manager",
        }

        if role not in valid_roles:
            raise ValidationError(f"Invalid agent role '{role}'. Valid roles: {', '.join(valid_roles)}")

        return True

    @staticmethod
    def validate_briefing(briefing: str) -> bool:
        """
        Validate agent briefing.

        Args:
            briefing: Briefing text to validate

        Returns:
            True if valid

        Raises:
            ValidationError: If briefing is invalid
        """
        if not briefing or not briefing.strip():
            raise ValidationError("Briefing cannot be empty")

        if len(briefing.strip()) < 10:
            raise ValidationError("Briefing must be at least 10 characters long")

        return True


class ContextValidator:
    """
    Validation utilities for context operations.
    """

    @staticmethod
    def validate_context_name(context: str) -> bool:
        """
        Validate context name.

        Args:
            context: Context name to validate

        Returns:
            True if valid

        Raises:
            ValidationError: If context is invalid
        """
        valid_contexts = {"orc", "pm", "mcp", "tmux-comms"}

        if context not in valid_contexts:
            raise ValidationError(f"Invalid context '{context}'. Valid contexts: {', '.join(valid_contexts)}")

        return True

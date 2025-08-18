"""Input sanitization utilities for tmux-orchestrator.

Provides validation and sanitization for user inputs to prevent
injection attacks and ensure data integrity.
"""

import re
import shlex
from pathlib import Path
from typing import Any, List

from tmux_orchestrator.utils.exceptions import ValidationError

# Allowed characters for different input types
SAFE_SESSION_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.]+$")
SAFE_WINDOW_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.\s]+$")
SAFE_TARGET_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.]+:[0-9]+$")
SAFE_PATH_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\./\s]+$")

# Maximum lengths for various inputs
MAX_SESSION_NAME_LENGTH = 64
MAX_WINDOW_NAME_LENGTH = 64
MAX_MESSAGE_LENGTH = 10000
MAX_PATH_LENGTH = 1024
MAX_BRIEFING_LENGTH = 50000


def sanitize_session_name(name: str) -> str:
    """Sanitize tmux session name.

    Args:
        name: Session name to sanitize

    Returns:
        Sanitized session name

    Raises:
        ValidationError: If name is invalid
    """
    if not name:
        raise ValidationError("Session name cannot be empty")

    if len(name) > MAX_SESSION_NAME_LENGTH:
        raise ValidationError(f"Session name too long (max {MAX_SESSION_NAME_LENGTH} chars)")

    if not SAFE_SESSION_NAME_PATTERN.match(name):
        raise ValidationError(
            "Session name contains invalid characters. " "Only alphanumeric, underscore, hyphen, and dot allowed."
        )

    # Prevent special tmux session names
    if name.startswith(".") or name in ["0", "-", "="]:
        raise ValidationError("Invalid session name")

    return name


def sanitize_window_name(name: str) -> str:
    """Sanitize tmux window name.

    Args:
        name: Window name to sanitize

    Returns:
        Sanitized window name

    Raises:
        ValidationError: If name is invalid
    """
    if not name:
        raise ValidationError("Window name cannot be empty")

    if len(name) > MAX_WINDOW_NAME_LENGTH:
        raise ValidationError(f"Window name too long (max {MAX_WINDOW_NAME_LENGTH} chars)")

    if not SAFE_WINDOW_NAME_PATTERN.match(name):
        raise ValidationError(
            "Window name contains invalid characters. " "Only alphanumeric, underscore, hyphen, dot, and space allowed."
        )

    return name


def sanitize_target(target: str) -> str:
    """Sanitize tmux target (session:window format).

    Args:
        target: Target string to sanitize

    Returns:
        Sanitized target

    Raises:
        ValidationError: If target is invalid
    """
    if not target:
        raise ValidationError("Target cannot be empty")

    # Handle special cases
    if target.lower() == "all":
        return target.lower()

    # Validate session:window format
    if ":" not in target:
        raise ValidationError("Target must be in session:window format")

    if not SAFE_TARGET_PATTERN.match(target):
        raise ValidationError("Invalid target format")

    session, window = target.split(":", 1)

    # Validate session part
    sanitize_session_name(session)

    # Validate window part (must be numeric)
    try:
        window_idx = int(window)
        if window_idx < 0 or window_idx > 999:
            raise ValidationError("Window index out of range (0-999)")
    except ValueError:
        raise ValidationError("Window index must be numeric")

    return target


def sanitize_message(message: str) -> str:
    """Sanitize message content.

    Args:
        message: Message to sanitize

    Returns:
        Sanitized message

    Raises:
        ValidationError: If message is invalid
    """
    if not message:
        raise ValidationError("Message cannot be empty")

    if len(message) > MAX_MESSAGE_LENGTH:
        raise ValidationError(f"Message too long (max {MAX_MESSAGE_LENGTH} chars)")

    # Remove null bytes and other control characters
    cleaned = message.replace("\0", "")

    # Remove ANSI escape sequences that could manipulate terminal
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    cleaned = ansi_escape.sub("", cleaned)

    # Prevent tmux command injection via special sequences
    dangerous_patterns = [
        r"`[^`]*`",  # Backticks
        r"\$\([^)]*\)",  # Command substitution
        r"\$\{[^}]*\}",  # Variable expansion
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, cleaned):
            raise ValidationError("Message contains potentially dangerous patterns")

    return cleaned


def sanitize_path(path: str) -> str:
    """Sanitize file path.

    Args:
        path: Path to sanitize

    Returns:
        Sanitized path

    Raises:
        ValidationError: If path is invalid
    """
    if not path:
        raise ValidationError("Path cannot be empty")

    if len(path) > MAX_PATH_LENGTH:
        raise ValidationError(f"Path too long (max {MAX_PATH_LENGTH} chars)")

    # Normalize and resolve path
    try:
        resolved = Path(path).resolve()

        # Prevent directory traversal
        if ".." in str(resolved):
            raise ValidationError("Path contains directory traversal")

        # Check for suspicious path components
        suspicious_components = [
            "/etc/passwd",
            "/etc/shadow",
            "/.ssh/",
            "/.aws/",
            "/.config/gh/",
            "/private/",
            "/secrets/",
        ]

        path_str = str(resolved).lower()
        for component in suspicious_components:
            if component in path_str:
                raise ValidationError(f"Access to {component} is not allowed")

        return str(resolved)

    except Exception as e:
        raise ValidationError(f"Invalid path: {e}")


def sanitize_command_args(args: List[str]) -> List[str]:
    """Sanitize command line arguments.

    Args:
        args: List of arguments to sanitize

    Returns:
        Sanitized arguments

    Raises:
        ValidationError: If any argument is invalid
    """
    if not args:
        return []

    sanitized = []
    for arg in args:
        if not isinstance(arg, str):
            raise ValidationError(f"Argument must be string, got {type(arg)}")

        # Quote arguments to prevent shell interpretation
        sanitized.append(shlex.quote(arg))

    return sanitized


def sanitize_briefing(briefing: str) -> str:
    """Sanitize agent briefing content.

    Args:
        briefing: Briefing text to sanitize

    Returns:
        Sanitized briefing

    Raises:
        ValidationError: If briefing is invalid
    """
    if not briefing:
        return ""  # Empty briefing is allowed

    if len(briefing) > MAX_BRIEFING_LENGTH:
        raise ValidationError(f"Briefing too long (max {MAX_BRIEFING_LENGTH} chars)")

    # Apply same sanitization as messages
    return sanitize_message(briefing)


def sanitize_input(value: Any, input_type: str) -> Any:
    """Generic input sanitization dispatcher.

    Args:
        value: Value to sanitize
        input_type: Type of input ('session', 'window', 'target', 'message', 'path', 'briefing')

    Returns:
        Sanitized value

    Raises:
        ValidationError: If value is invalid for the given type
    """
    sanitizers = {
        "session": sanitize_session_name,
        "window": sanitize_window_name,
        "target": sanitize_target,
        "message": sanitize_message,
        "path": sanitize_path,
        "briefing": sanitize_briefing,
    }

    sanitizer = sanitizers.get(input_type)
    if not sanitizer:
        raise ValidationError(f"Unknown input type: {input_type}")

    return sanitizer(value)


def validate_agent_type(agent_type: str) -> str:
    """Validate agent type.

    Args:
        agent_type: Agent type to validate

    Returns:
        Validated agent type

    Raises:
        ValidationError: If agent type is invalid
    """
    valid_types = {
        "pm",
        "project-manager",
        "developer",
        "dev",
        "backend",
        "frontend",
        "qa",
        "qa-engineer",
        "tester",
        "devops",
        "ops",
        "reviewer",
        "code-reviewer",
        "researcher",
        "research",
        "docs",
        "documentation",
        "writer",
        "orchestrator",
        "orc",
    }

    if agent_type.lower() not in valid_types:
        raise ValidationError(f"Invalid agent type: {agent_type}. " f"Valid types: {', '.join(sorted(valid_types))}")

    return agent_type.lower()


def validate_team_type(team_type: str) -> str:
    """Validate team type.

    Args:
        team_type: Team type to validate

    Returns:
        Validated team type

    Raises:
        ValidationError: If team type is invalid
    """
    valid_types = ["frontend", "backend", "fullstack", "testing"]

    if team_type.lower() not in valid_types:
        raise ValidationError(f"Invalid team type: {team_type}. " f"Valid types: {', '.join(valid_types)}")

    return team_type.lower()


def validate_integer_range(value: Any, min_val: int, max_val: int, name: str) -> int:
    """Validate integer is within range.

    Args:
        value: Value to validate
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        name: Name of parameter for error messages

    Returns:
        Validated integer

    Raises:
        ValidationError: If value is invalid
    """
    try:
        int_val = int(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{name} must be an integer")

    if int_val < min_val or int_val > max_val:
        raise ValidationError(f"{name} must be between {min_val} and {max_val}")

    return int_val

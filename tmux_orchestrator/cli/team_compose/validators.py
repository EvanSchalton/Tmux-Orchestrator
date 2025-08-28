"""Input validation and sanitization for team composition."""

import html
import re
from pathlib import Path


def sanitize_for_template(value: str) -> str:
    """Sanitize user input for safe template replacement.

    Args:
        value: User input to sanitize

    Returns:
        Sanitized string safe for template replacement
    """
    # HTML escape to prevent injection
    safe_value = html.escape(str(value))
    # Remove potentially dangerous characters while preserving readability
    safe_value = re.sub(r'[<>"\'\\`$]', "", safe_value)
    # Limit length to prevent overflow attacks
    if len(safe_value) > 1000:
        safe_value = safe_value[:1000] + "..."
    return safe_value


def validate_project_name(project_name: str) -> bool:
    """Validate project name to prevent path traversal attacks.

    Args:
        project_name: Project name to validate

    Returns:
        True if valid, False if invalid
    """
    if not project_name:
        return False
    if ".." in project_name:
        return False
    if "/" in project_name or "\\" in project_name:
        return False
    return True


def validate_project_exists(project_name: str) -> tuple[bool, Path]:
    """Validate that project exists and return its directory.

    Args:
        project_name: Name of the project to validate

    Returns:
        Tuple of (exists, project_directory_path)
    """
    project_dir = Path.home() / "workspaces" / "Tmux-Orchestrator" / ".tmux_orchestrator" / "projects" / project_name
    return project_dir.exists(), project_dir


def validate_prd_path(prd: str | None) -> tuple[bool, Path | None]:
    """Validate PRD file path if provided.

    Args:
        prd: PRD file path to validate

    Returns:
        Tuple of (valid, path_object_or_none)
    """
    if not prd:
        return True, None

    prd_path = Path(prd)
    if not prd_path.exists():
        return False, None
    if not prd_path.is_file():
        return False, None
    if prd_path.suffix.lower() not in [".md", ".txt", ".rst"]:
        return False, None

    return True, prd_path

"""Context endpoints for standardized agent briefings."""

import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

# Contexts directory - using package data
try:
    import pkg_resources

    CONTEXTS_DIR = Path(pkg_resources.resource_filename("tmux_orchestrator", "data/contexts"))
except Exception:
    # Fallback for development
    CONTEXTS_DIR = Path(__file__).parent.parent.parent / "data" / "contexts"


class ContextResponse(BaseModel):
    """Response model for context data."""

    role: str
    content: str
    description: str


class ContextListResponse(BaseModel):
    """Response model for listing available contexts."""

    contexts: list[dict[str, str]]
    note: str = (
        "Only system roles (orchestrator, pm) have standard contexts. Other agents should have custom briefings."
    )


def _validate_role(role: str) -> str:
    """Validate and sanitize role input to prevent path traversal attacks.

    SECURITY: This function prevents path traversal vulnerabilities by:
    1. Validating that role contains only safe characters
    2. Ensuring it's a simple filename without path components
    3. Preventing directory traversal attempts

    Args:
        role: The role name to validate

    Returns:
        str: The validated role name

    Raises:
        HTTPException: If role is invalid or potentially dangerous
    """
    if not role:
        raise HTTPException(status_code=400, detail="Role cannot be empty")

    if not isinstance(role, str):
        raise HTTPException(status_code=400, detail="Role must be a string")

    # Remove any whitespace
    role = role.strip()

    # Check length limits (reasonable role names should be short)
    if len(role) > 50:
        raise HTTPException(status_code=400, detail="Role name too long")

    # Allow only alphanumeric characters, hyphens, and underscores
    # This prevents path traversal and other injection attacks
    if not re.match(r"^[a-zA-Z0-9_-]+$", role):
        raise HTTPException(
            status_code=400,
            detail="Role name contains invalid characters. Only letters, numbers, hyphens, and underscores are allowed.",
        )

    # Explicitly check for path traversal attempts
    dangerous_patterns = ["..", "/", "\\", ":", "*", "?", '"', "<", ">", "|"]
    for pattern in dangerous_patterns:
        if pattern in role:
            raise HTTPException(
                status_code=400,
                detail="Role name contains forbidden characters that could lead to security vulnerabilities",
            )

    return role


def _safe_path(role: str, contexts_dir: Path) -> Path:
    """Safely construct a path within the contexts directory.

    SECURITY: This function ensures the final path is within the contexts directory
    and prevents path traversal attacks.

    Args:
        role: Validated role name
        contexts_dir: The base contexts directory

    Returns:
        Path: Safe path within contexts directory

    Raises:
        HTTPException: If the resolved path is outside contexts directory
    """
    # Construct the path
    context_file = contexts_dir / f"{role}.md"

    # Resolve the path to handle any potential traversal
    try:
        resolved_file = context_file.resolve()
        resolved_contexts = contexts_dir.resolve()

        # Ensure the resolved path is within the contexts directory
        if not str(resolved_file).startswith(str(resolved_contexts)):
            raise HTTPException(status_code=400, detail="Path traversal detected. Access denied for security reasons.")

        return context_file  # Return the unresolved path for normal use

    except (OSError, ValueError) as e:
        raise HTTPException(status_code=400, detail="Invalid path specified") from e


@router.get("/list", response_model=ContextListResponse)
async def list_contexts():
    """List all available context templates.

    Returns:
        ContextListResponse: List of available contexts with descriptions
    """
    if not CONTEXTS_DIR.exists():
        return ContextListResponse(contexts=[])

    contexts = []
    for file in CONTEXTS_DIR.glob("*.md"):
        role = file.stem
        content = file.read_text()

        # Extract first meaningful line as description
        lines = content.strip().split("\n")
        description = next(
            (line.strip() for line in lines if line.strip() and not line.startswith("#")), "No description available"
        )

        contexts.append({"role": role, "description": description})

    return ContextListResponse(contexts=contexts)


@router.get("/{role}", response_model=ContextResponse)
async def get_context(role: str):
    """Get context briefing for a specific role.

    SECURITY: This endpoint has been hardened against path traversal attacks.
    All role inputs are validated and paths are safely constructed.

    Args:
        role: The role to get context for (must be alphanumeric with hyphens/underscores only)

    Returns:
        ContextResponse: The context content and metadata

    Raises:
        HTTPException: If role is invalid, context not found, or security violation detected
    """
    # SECURITY: Validate role input to prevent path traversal
    validated_role = _validate_role(role)

    # SECURITY: Safely construct path within contexts directory
    context_file = _safe_path(validated_role, CONTEXTS_DIR)

    if not context_file.exists():
        available = [f.stem for f in CONTEXTS_DIR.glob("*.md")] if CONTEXTS_DIR.exists() else []
        raise HTTPException(
            status_code=404, detail=f"Context '{validated_role}' not found. Available: {', '.join(available)}"
        )

    try:
        content = context_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise HTTPException(status_code=500, detail="Error reading context file") from e

    lines = content.strip().split("\n")
    description = next(
        (line.strip() for line in lines if line.strip() and not line.startswith("#")), "No description available"
    )

    return ContextResponse(role=validated_role, content=content, description=description)


@router.post("/spawn/{role}")
async def spawn_with_context(role: str, session: str, extend: str | None = None):
    """Spawn an agent with standardized context.

    Args:
        role: The system role (orchestrator or pm)
        session: Target session:window location
        extend: Additional project-specific context

    Returns:
        dict: Success status and message

    Raises:
        HTTPException: If context not found or spawn fails
    """
    from tmux_orchestrator.utils.tmux import TMUXManager

    # Load context
    context_file = CONTEXTS_DIR / f"{role}.md"
    if not context_file.exists():
        raise HTTPException(
            status_code=404, detail=f"Context '{role}' not found. Only system roles have standard contexts."
        )

    briefing = context_file.read_text()

    # Add extension if provided
    if extend:
        briefing += f"\n\n## Project-Specific Context\n\n{extend}"

    # Spawn agent
    tmux = TMUXManager()
    success = tmux.send_message(session, briefing)

    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to spawn {role} agent at {session}")

    return {"success": True, "message": f"Spawned {role} agent at {session}", "session": session, "role": role}

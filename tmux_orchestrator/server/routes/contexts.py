"""Context endpoints for standardized agent briefings."""

from pathlib import Path
from typing import Dict, List

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

    contexts: List[Dict[str, str]]
    note: str = (
        "Only system roles (orchestrator, pm) have standard contexts. Other agents should have custom briefings."
    )


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

    Args:
        role: The role to get context for (orchestrator or pm)

    Returns:
        ContextResponse: The context content and metadata

    Raises:
        HTTPException: If context not found
    """
    context_file = CONTEXTS_DIR / f"{role}.md"

    if not context_file.exists():
        available = [f.stem for f in CONTEXTS_DIR.glob("*.md")] if CONTEXTS_DIR.exists() else []
        raise HTTPException(status_code=404, detail=f"Context '{role}' not found. Available: {', '.join(available)}")

    content = context_file.read_text()
    lines = content.strip().split("\n")
    description = next(
        (line.strip() for line in lines if line.strip() and not line.startswith("#")), "No description available"
    )

    return ContextResponse(role=role, content=content, description=description)


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

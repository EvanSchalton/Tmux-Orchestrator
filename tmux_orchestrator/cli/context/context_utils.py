"""Context utilities and shared functions."""

import importlib.resources as resources
from pathlib import Path

try:
    # Try to use package data first (using importlib for modern Python)
    try:
        # Python 3.9+ with files() API
        contexts_ref = resources.files("tmux_orchestrator").joinpath("data/contexts")
        CONTEXTS_DIR = Path(str(contexts_ref))
    except AttributeError:
        # Python 3.7-3.8 fallback
        with resources.path("tmux_orchestrator.data", "contexts") as p:
            CONTEXTS_DIR = Path(p)
except Exception:
    # Fallback for development
    CONTEXTS_DIR = Path(__file__).parent.parent.parent / "data" / "contexts"


def get_available_contexts() -> dict[str, Path]:
    """Get list of available context files."""
    if not CONTEXTS_DIR.exists():
        return {}

    contexts = {}
    for file in CONTEXTS_DIR.glob("*.md"):
        role = file.stem
        contexts[role] = file

    return contexts


def load_context(role: str) -> str:
    """Load context from file."""
    contexts = get_available_contexts()
    if role not in contexts:
        return f"Context for role '{role}' not found"

    try:
        return contexts[role].read_text()
    except Exception as e:
        return f"Error loading context: {e}"

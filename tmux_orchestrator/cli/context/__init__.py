"""Context CLI module."""

from .context_core import context
from .context_spawn import spawn_context as spawn

__all__ = ["context", "spawn"]

"""Agent management commands - modular structure.

This module has been refactored following development-patterns.md:
- Business logic functions extracted to individual files in agent/ directory
- CLI command orchestration maintained in __init__.py
- Direct message sending without chunking in send_message.py
- Full backwards compatibility via re-exports
"""

# Re-export the main CLI group for backwards compatibility
from .agent import agent

__all__ = ["agent"]

"""TMUX Orchestrator CLI - Refactored into focused modules for maintainability.

This module maintains backwards compatibility while internally using a modular
architecture following SOLID principles and development patterns.
"""

# Import main CLI from core module for backwards compatibility
# Module-level exports for backwards compatibility
from rich.console import Console

from .core import cli

# Initialize console for CLI output (backwards compatibility)
console: Console = Console()

# Re-export main CLI and console for backwards compatibility
__all__ = ["cli", "console"]

# Entry point for command line execution
if __name__ == "__main__":
    cli()

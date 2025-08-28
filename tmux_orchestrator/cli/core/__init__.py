"""CLI core components - refactored for maintainability and SOLID principles."""

# Re-export main CLI for backwards compatibility
from .main_cli import cli

__all__ = ["cli"]

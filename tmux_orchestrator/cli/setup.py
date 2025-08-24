"""Setup commands - alias to setup_claude for import compatibility."""

# Import all functionality from setup_claude
from tmux_orchestrator.cli.setup_claude import *  # noqa: F401, F403

# Ensure the main setup command is available
from tmux_orchestrator.cli.setup_claude import setup

__all__ = ["setup"]

"""
CLI utility functions for tmux-orchestrator.

This module provides common utilities used across CLI commands following
the one-function-per-file pattern for business logic.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# Re-export utilities
from .console import console, create_panel, error_console
from .formatting import format_error, format_json, format_table
from .paths import ensure_directory, get_config_dir, get_log_dir
from .process import check_command_exists, run_command

__all__ = [
    "console",
    "error_console",
    "create_panel",
    "format_json",
    "format_table",
    "format_error",
    "run_command",
    "check_command_exists",
    "get_config_dir",
    "get_log_dir",
    "ensure_directory",
]

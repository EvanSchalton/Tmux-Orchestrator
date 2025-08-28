"""Path management utilities for CLI."""

import os
from pathlib import Path


def get_config_dir() -> Path:
    """Get the configuration directory path."""
    config_dir = os.environ.get("TMUX_ORC_CONFIG_DIR")
    if config_dir:
        return Path(config_dir)
    return Path.home() / ".config" / "tmux-orchestrator"


def get_log_dir() -> Path:
    """Get the log directory path."""
    log_dir = os.environ.get("TMUX_ORC_LOG_DIR")
    if log_dir:
        return Path(log_dir)
    return Path.home() / ".local" / "share" / "tmux-orchestrator" / "logs"


def ensure_directory(path: Path) -> Path:
    """Ensure a directory exists, creating it if necessary."""
    path.mkdir(parents=True, exist_ok=True)
    return path

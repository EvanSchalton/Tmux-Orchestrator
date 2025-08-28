"""Monitoring system exceptions."""

from pathlib import Path


class DaemonAlreadyRunningError(Exception):
    """Exception raised when trying to start a daemon that is already running."""

    def __init__(self, pid: int, pid_file: Path):
        self.pid = pid
        self.pid_file = pid_file
        super().__init__(
            f"Monitor daemon is already running with PID {pid}. "
            f"PID file: {pid_file}. "
            f"Use 'tmux-orc monitor stop' to stop the existing daemon first, "
            f"or 'tmux-orc monitor status' to check daemon status."
        )

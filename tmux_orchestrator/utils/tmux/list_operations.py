"""List operations for windows and sessions."""

import logging
import subprocess
from typing import Any


class TmuxListOperations:
    """Handles listing operations for TMUX windows and sessions."""

    def __init__(self, tmux_cmd: str = "tmux"):
        """Initialize list operations.

        Args:
            tmux_cmd: TMUX command to use (default: "tmux")
        """
        self.tmux_cmd = tmux_cmd
        self._logger = logging.getLogger(__name__)

    def list_windows(self, session: str) -> list[dict[str, Any]]:
        """List windows in a session.

        Args:
            session: Session name

        Returns:
            List of window dictionaries with index, name, and active status
        """
        try:
            cmd = [
                self.tmux_cmd,
                "list-windows",
                "-t",
                session,
                "-F",
                "#{window_index}:#{window_name}:#{window_active}",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
            if result.returncode != 0:
                return []

            windows = []
            for line in result.stdout.strip().split("\n"):
                if line and ":" in line:
                    parts = line.split(":", 2)
                    windows.append(
                        {
                            "index": int(parts[0]),
                            "name": parts[1] if len(parts) > 1 else "",
                            "active": parts[2] if len(parts) > 2 else "0",
                        }
                    )

            return windows

        except Exception as e:
            self._logger.error(f"Error listing windows for session {session}: {e}")
            return []

    def list_sessions(self) -> list[dict[str, str]]:
        """List all TMUX sessions.

        Returns:
            List of session dictionaries with name, created, and attached status
        """
        try:
            result = subprocess.run(
                [self.tmux_cmd, "list-sessions", "-F", "#{session_name}:#{session_created}:#{session_attached}"],
                capture_output=True,
                text=True,
                timeout=3,
            )

            if result.returncode != 0:
                return []

            sessions = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line.split(":")
                    sessions.append(
                        {
                            "name": parts[0],
                            "created": parts[1] if len(parts) > 1 else "",
                            "attached": parts[2] if len(parts) > 2 else "0",
                        }
                    )

            return sessions

        except Exception as e:
            self._logger.error(f"Error listing sessions: {e}")
            return []

"""Session and window management operations."""

import logging
import subprocess
from typing import Any, Optional


class SessionManager:
    """Handles TMUX session and window management operations."""

    def __init__(self, tmux_cmd: str = "tmux"):
        """Initialize session manager.

        Args:
            tmux_cmd: TMUX command to use (default: "tmux")
        """
        self.tmux_cmd = tmux_cmd
        self._logger = logging.getLogger(__name__)

    def list_sessions(self) -> list[dict[str, str]]:
        """List all tmux sessions."""
        sessions: list[dict[str, str]] = []
        try:
            result = subprocess.run(
                [self.tmux_cmd, "list-sessions", "-F", "#{session_name}:#{session_windows}:#{session_attached}"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if line:
                        parts = line.split(":")
                        if len(parts) >= 3:
                            sessions.append(
                                {
                                    "name": parts[0],
                                    "windows": parts[1],
                                    "attached": "true" if parts[2] == "1" else "false",
                                }
                            )
        except Exception as e:
            self._logger.error(f"Failed to list sessions: {e}")

        return sessions

    def list_sessions_cached(self) -> list[dict[str, str]]:
        """List sessions with basic caching."""
        # Simplified version without complex caching
        return self.list_sessions()

    def has_session_optimized(self, session_name: str) -> bool:
        """Check if session exists with optimization."""
        return self.has_session(session_name)

    def has_session(self, session_name: str) -> bool:
        """Check if a tmux session exists."""
        try:
            result = subprocess.run([self.tmux_cmd, "has-session", "-t", session_name], capture_output=True, timeout=1)
            return result.returncode == 0
        except Exception:
            return False

    def create_session_optimized(
        self, session_name: str, window_name: Optional[str] = None, start_directory: Optional[str] = None
    ) -> bool:
        """Create session with optimization."""
        return self.create_session(session_name, window_name, start_directory)

    def create_session(
        self, session_name: str, window_name: Optional[str] = None, start_directory: Optional[str] = None
    ) -> bool:
        """Create a new tmux session."""
        try:
            cmd = [self.tmux_cmd, "new-session", "-d", "-s", session_name]
            if window_name:
                cmd.extend(["-n", window_name])
            if start_directory:
                cmd.extend(["-c", start_directory])

            result = subprocess.run(cmd, capture_output=True, timeout=5)
            return result.returncode == 0
        except Exception as e:
            self._logger.error(f"Session creation failed: {e}")
            return False

    def create_window_optimized(
        self, session_name: str, window_name: str, start_directory: Optional[str] = None
    ) -> bool:
        """Create window with optimization."""
        return self.create_window(session_name, window_name, start_directory)

    def create_window(self, session_name: str, window_name: str, start_directory: Optional[str] = None) -> bool:
        """Create a new window in a session."""
        try:
            cmd = [self.tmux_cmd, "new-window", "-t", session_name, "-n", window_name]
            if start_directory:
                cmd.extend(["-c", start_directory])

            result = subprocess.run(cmd, capture_output=True, timeout=3)
            return result.returncode == 0
        except Exception as e:
            self._logger.error(f"Window creation failed: {e}")
            return False

    def list_windows(self, session: str) -> list[dict[str, Any]]:
        """List windows in a session."""
        windows = []
        try:
            result = subprocess.run(
                [
                    self.tmux_cmd,
                    "list-windows",
                    "-t",
                    session,
                    "-F",
                    "#{window_index}:#{window_name}:#{window_active}:#{window_last_flag}",
                ],
                capture_output=True,
                text=True,
                timeout=3,
            )

            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if line:
                        parts = line.split(":")
                        if len(parts) >= 4:
                            windows.append(
                                {
                                    "index": parts[0],
                                    "name": parts[1],
                                    "active": parts[2] == "1",
                                    "last": parts[3] == "1",
                                }
                            )
        except Exception as e:
            self._logger.error(f"Failed to list windows for session {session}: {e}")

        return windows

    def kill_window(self, target: str) -> bool:
        """Kill a specific tmux window."""
        result = subprocess.run([self.tmux_cmd, "kill-window", "-t", target], capture_output=True, text=True)
        return result.returncode == 0

    def kill_session(self, session_name: str) -> bool:
        """Kill a specific tmux session."""
        result = subprocess.run([self.tmux_cmd, "kill-session", "-t", session_name], capture_output=True, text=True)
        return result.returncode == 0

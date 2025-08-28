"""Agent discovery functionality for finding Claude agents across tmux sessions."""

import os

from tmux_orchestrator.core.config import Config
from tmux_orchestrator.utils.tmux import TMUXManager


class AgentDiscovery:
    """Handles discovery and identification of Claude agents across tmux sessions."""

    def __init__(self) -> None:
        """Initialize the agent discovery system."""
        pass

    def discover_agents(self, tmux: TMUXManager) -> list[str]:
        """Discover all active Claude agents across the tmux environment for monitoring.

        Systematically scans all tmux sessions and windows to identify Claude Code agents
        that should be monitored for health, activity, and responsiveness. Uses window
        name pattern matching rather than content analysis to detect agents that may
        be crashed, hung, or otherwise unresponsive.

        Args:
            tmux: TMUXManager instance for session and window enumeration

        Returns:
            list[str]: Agent target identifiers in format "session:window"
                      (e.g., ["dev-team:2", "qa-session:1", "pm-control:0"])
                      Empty list if no agents found or discovery fails
        """
        agents = []

        try:
            # Get all tmux sessions
            sessions = tmux.list_sessions()

            for session_info in sessions:
                session_name = session_info["name"]

                # Get windows for this session
                try:
                    windows = tmux.list_windows(session_name)
                    for window_info in windows:
                        # Fix: use 'index' not 'id' - window_info contains index/name/active
                        window_idx = window_info.get("index", "0")
                        target = f"{session_name}:{window_idx}"

                        # Check if window contains an active agent
                        if self.is_agent_window(tmux, target):
                            agents.append(target)

                except Exception:
                    # Skip this session if we can't list windows
                    continue

        except Exception:
            # Return empty list if we can't discover agents
            pass

        return agents

    def is_agent_window(self, tmux: TMUXManager, target: str) -> bool:
        """Check if a window should be monitored as an agent window.

        This checks window NAME patterns, not content, so we can track
        crashed agents that need recovery.

        Args:
            tmux: TMUXManager instance
            target: Target identifier in "session:window" format

        Returns:
            bool: True if this window should be monitored as an agent
        """
        try:
            session_name, window_idx = target.split(":")
            windows = tmux.list_windows(session_name)

            # Find the window info for this index
            for window in windows:
                if str(window.get("index", "")) == str(window_idx):
                    window_name = window.get("name", "").lower()

                    # Check if this is an agent window by name pattern
                    # Claude agent windows are named "Claude-{role}"
                    if window_name.startswith("claude-"):
                        return True

                    # Also check for common agent indicators in window name
                    agent_indicators = ["pm", "developer", "qa", "engineer", "devops", "backend", "frontend"]
                    if any(indicator in window_name for indicator in agent_indicators):
                        return True

            return False

        except Exception:
            return False

    def check_messaging_daemon_status(self) -> bool:
        """Check if the messaging daemon is running."""
        try:
            pid = self._get_messaging_daemon_pid()
            if pid and os.path.exists(f"/proc/{pid}"):
                return True
        except Exception:
            pass
        return False

    def _get_messaging_daemon_pid(self) -> int | None:
        """Get the PID of the messaging daemon."""
        try:
            # Check for messaging daemon PID file
            config = Config.load()
            messaging_pid_file = config.orchestrator_base_dir / "messaging-daemon.pid"

            if messaging_pid_file.exists():
                with open(messaging_pid_file) as f:
                    return int(f.read().strip())
        except (OSError, ValueError):
            pass
        return None

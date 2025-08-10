"""TMUX utility functions and manager."""

import re
import subprocess


class TMUXManager:
    """Manages tmux sessions and windows."""

    def __init__(self) -> None:
        self.tmux_cmd = "tmux"

    def _run_tmux(self, args: list[str], check: bool = True) -> subprocess.CompletedProcess:
        """Run a tmux command."""
        cmd = [self.tmux_cmd] + args
        return subprocess.run(cmd, capture_output=True, text=True, check=check)

    def has_session(self, session_name: str) -> bool:
        """Check if a session exists."""
        result = self._run_tmux(["has-session", "-t", session_name], check=False)
        return result.returncode == 0

    def create_session(
        self,
        session_name: str,
        window_name: str | None = None,
        start_directory: str | None = None,
    ) -> bool:
        """Create a new tmux session."""
        cmd = ["new-session", "-d", "-s", session_name]
        if window_name:
            cmd.extend(["-n", window_name])
        if start_directory:
            cmd.extend(["-c", start_directory])

        result = self._run_tmux(cmd, check=False)
        return result.returncode == 0

    def create_window(self, session_name: str, window_name: str, start_directory: str | None = None) -> bool:
        """Create a new window in a session."""
        cmd = ["new-window", "-t", session_name, "-n", window_name]
        if start_directory:
            cmd.extend(["-c", start_directory])

        result = self._run_tmux(cmd, check=False)
        return result.returncode == 0

    def send_keys(self, target: str, keys: str) -> bool:
        """Send keys to a tmux pane."""
        result = self._run_tmux(["send-keys", "-t", target, keys], check=False)
        return result.returncode == 0

    def send_message(self, target: str, message: str) -> bool:
        """Send a message to a Claude agent using the proven CLI method."""
        import time

        # Use the exact same method as the working CLI command
        try:
            delay = 0.5  # Standard delay from CLI

            # Clear any existing input first
            self.send_keys(target, "C-c")
            time.sleep(delay)

            # Clear the input line
            self.send_keys(target, "C-u")
            time.sleep(delay)

            # Send the actual message
            self.send_keys(target, message)
            time.sleep(max(delay * 6, 3.0))  # Ensure adequate time for message processing

            # Move to end and submit with Ctrl+Enter (Claude's required key combination)
            self.send_keys(target, "End")
            time.sleep(delay * 0.4)
            self.send_keys(target, "C-Enter")

            return True

        except Exception as e:
            import logging

            logging.error(f"Failed to send message to {target}: {e}")
            return False

    def _send_message_fallback(self, target: str, message: str) -> bool:
        """Original message sending implementation as fallback."""
        # Clear any existing input
        self.send_keys(target, "C-c")
        subprocess.run(["sleep", "0.5"])

        # Clear the input line
        self.send_keys(target, "C-u")
        subprocess.run(["sleep", "0.5"])

        # Send the message
        self.send_keys(target, message)
        subprocess.run(["sleep", "3.0"])

        # Move to end and submit
        self.send_keys(target, "End")
        subprocess.run(["sleep", "0.2"])
        self.send_keys(target, "Enter")
        subprocess.run(["sleep", "1.0"])
        self.send_keys(target, "Enter")

        return True

    def capture_pane(self, target: str, lines: int = 50) -> str:
        """Capture pane output."""
        result = self._run_tmux(["capture-pane", "-t", target, "-p"], check=False)
        if result.returncode == 0:
            output_lines = result.stdout.strip().split("\n")
            return "\n".join(output_lines[-lines:])
        return ""

    def list_sessions(self) -> list[dict[str, str]]:
        """List all tmux sessions."""
        result = self._run_tmux(
            [
                "list-sessions",
                "-F",
                "#{session_name}:#{session_created}:#{session_attached}",
            ],
            check=False,
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

    def list_windows(self, session: str) -> list[dict[str, str]]:
        """List windows in a session."""
        result = self._run_tmux(
            [
                "list-windows",
                "-t",
                session,
                "-F",
                "#{window_index}:#{window_name}:#{window_active}",
            ],
            check=False,
        )
        if result.returncode != 0:
            return []

        windows = []
        for line in result.stdout.strip().split("\n"):
            if line:
                parts = line.split(":")
                windows.append(
                    {
                        "index": parts[0],
                        "name": parts[1] if len(parts) > 1 else "",
                        "active": parts[2] if len(parts) > 2 else "0",
                    }
                )
        return windows

    def list_agents(self) -> list[dict[str, str]]:
        """List all active agents across sessions."""
        agents = []
        sessions = self.list_sessions()

        for session in sessions:
            windows = self.list_windows(session["name"])
            for window in windows:
                # Check if it's a Claude window
                if "Claude" in window["name"] or window["name"] in [
                    "pm",
                    "developer",
                    "qa",
                ]:
                    # Determine agent type
                    agent_type = "Unknown"
                    if "frontend" in session["name"]:
                        agent_type = "Frontend"
                    elif "backend" in session["name"]:
                        agent_type = "Backend"
                    elif "testing" in session["name"]:
                        agent_type = "QA"
                    elif "orchestrator" in session["name"]:
                        agent_type = "Orchestrator"
                    elif window["name"] == "pm" or "Claude-pm" in window["name"]:
                        agent_type = "PM"

                    # Check if idle
                    pane_content = self.capture_pane(f"{session['name']}:{window['index']}")
                    status = "Active"
                    if self._is_idle(pane_content):
                        status = "Idle"

                    agents.append(
                        {
                            "session": session["name"],
                            "window": window["index"],
                            "type": agent_type,
                            "status": status,
                        }
                    )

        return agents

    def _is_idle(self, pane_content: str) -> bool:
        """Check if pane content indicates idle state."""
        idle_patterns = [
            r"waiting for.*task",
            r"ready for.*assignment",
            r"awaiting.*instruction",
            r"standing by",
            r"idle",
            r"completed.*awaiting",
        ]

        for pattern in idle_patterns:
            if re.search(pattern, pane_content, re.IGNORECASE):
                return True

        # Check for Claude prompt with no recent activity
        if "│ >" in pane_content and pane_content.strip().endswith("│"):
            return True

        return False

    def kill_session(self, session_name: str) -> bool:
        """Kill a tmux session."""
        result = self._run_tmux(["kill-session", "-t", session_name], check=False)
        return result.returncode == 0

    def kill_project_sessions(self, project_name: str) -> int:
        """Kill all sessions for a project."""
        killed = 0
        sessions = self.list_sessions()

        for session in sessions:
            if project_name in session["name"] or session["name"] == "orchestrator":
                if self.kill_session(session["name"]):
                    killed += 1

        return killed

    def rename_window(self, target: str, new_name: str) -> bool:
        """Rename a tmux window."""
        result = self._run_tmux(["rename-window", "-t", target, new_name], check=False)
        return result.returncode == 0

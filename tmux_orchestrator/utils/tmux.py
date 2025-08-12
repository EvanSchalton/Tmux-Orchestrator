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

    def send_keys(self, target: str, keys: str, literal: bool = False) -> bool:
        """Send keys to a tmux pane.

        Args:
            target: Target pane (session:window)
            keys: Keys or text to send
            literal: If True, send as literal text with -l flag (escaped)
                    If False, send as command keys (Enter, C-c, etc.)
        """
        cmd = ["send-keys", "-t", target]
        if literal:
            cmd.append("-l")  # Literal mode for text
        cmd.append(keys)
        result = self._run_tmux(cmd, check=False)
        return result.returncode == 0

    def press_enter(self, target: str) -> bool:
        """Press Enter key in the target pane."""
        return self.send_keys(target, "Enter", literal=False)

    def press_ctrl_c(self, target: str) -> bool:
        """Press Ctrl+C in the target pane."""
        return self.send_keys(target, "C-c", literal=False)

    def press_ctrl_u(self, target: str) -> bool:
        """Press Ctrl+U (clear line) in the target pane."""
        return self.send_keys(target, "C-u", literal=False)

    def press_ctrl_e(self, target: str) -> bool:
        """Press Ctrl+E (end of line) in the target pane."""
        return self.send_keys(target, "C-e", literal=False)

    def press_ctrl_a(self, target: str) -> bool:
        """Press Ctrl+A (beginning of line) in the target pane."""
        return self.send_keys(target, "C-a", literal=False)

    def press_escape(self, target: str) -> bool:
        """Press Escape key in the target pane."""
        return self.send_keys(target, "Escape", literal=False)

    def send_text(self, target: str, text: str) -> bool:
        """Send literal text to the target pane (properly escaped)."""
        return self.send_keys(target, text, literal=True)

    def send_message(self, target: str, message: str) -> bool:
        """Send a message to a Claude agent using the proven CLI method."""
        import time

        # Use the exact same method as the working CLI command
        try:
            delay = 0.5  # Standard delay from CLI

            # Safety check: Wait if Claude is still initializing to prevent Ctrl+C interruption
            max_wait = 15  # Maximum wait time in seconds
            wait_count = 0
            while wait_count < max_wait:
                content = self.capture_pane(target)
                if content and ("│ >" in content or "Bypassing Permissions" in content):
                    # Claude is ready
                    break
                elif "Downloading" in content or "Installing" in content or content.strip() == "":
                    # Claude is still initializing
                    time.sleep(1)
                    wait_count += 1
                else:
                    # Claude appears ready
                    break

            # Clear any existing input first
            self.press_ctrl_c(target)
            time.sleep(delay)

            # Clear the input line
            self.press_ctrl_u(target)
            time.sleep(delay)

            # Send the actual message as literal text
            self.send_text(target, message)
            time.sleep(max(delay * 6, 3.0))  # Ensure adequate time for message processing

            # Submit with Enter (Claude Code uses Enter, not Ctrl+Enter)
            self.press_enter(target)

            return True

        except Exception as e:
            import logging

            logging.error(f"Failed to send message to {target}: {e}")
            return False

    def _send_message_fallback(self, target: str, message: str) -> bool:
        """Original message sending implementation as fallback."""
        # Clear any existing input
        self.press_ctrl_c(target)
        subprocess.run(["sleep", "0.5"])

        # Clear the input line
        self.press_ctrl_u(target)
        subprocess.run(["sleep", "0.5"])

        # Send the message as literal text
        self.send_text(target, message)
        subprocess.run(["sleep", "3.0"])

        # Submit with Enter (Claude Code uses Enter, not Ctrl+Enter)
        self.press_enter(target)

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
                    window_lower = window["name"].lower()

                    # Check session name first
                    if "frontend" in session["name"]:
                        agent_type = "Frontend"
                    elif "backend" in session["name"]:
                        agent_type = "Backend"
                    elif "testing" in session["name"]:
                        agent_type = "QA"
                    elif "orchestrator" in session["name"]:
                        agent_type = "Orchestrator"
                    # Then check window name for more specific types
                    elif "pm" in window_lower:
                        agent_type = "PM"
                    elif "developer" in window_lower:
                        agent_type = "Developer"
                    elif "devops" in window_lower:
                        agent_type = "DevOps"
                    elif "qa" in window_lower or "test" in window_lower:
                        agent_type = "QA"
                    elif "refactor" in window_lower:
                        agent_type = "Engineer"
                    elif "review" in window_lower:
                        agent_type = "Reviewer"

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

    def kill_window(self, target: str) -> bool:
        """Kill a specific tmux window.

        Args:
            target: Window target in format "session:window" or "session:window_index"

        Returns:
            True if window was successfully killed, False otherwise
        """
        result = self._run_tmux(["kill-window", "-t", target], check=False)
        return result.returncode == 0

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

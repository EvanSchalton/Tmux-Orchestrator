"""TMUX utility functions and manager."""

import logging
import re
import shlex
import subprocess
import time
from typing import Any


class TMUXManager:
    """Manages tmux sessions and windows."""

    def __init__(self) -> None:
        self.tmux_cmd = "tmux"
        self._last_command_time = 0.0
        self._min_command_interval = 0.05  # 50ms minimum between commands
        self._logger = logging.getLogger(__name__)

        # Performance optimization: Session caching
        self._session_cache: dict[str, Any] = {}
        self._session_cache_time = 0.0
        self._cache_ttl = 30.0  # Cache for 30 seconds

    def _validate_input(self, value: str, field_name: str = "input") -> str:
        """Validate input to prevent command injection vulnerabilities.

        This provides defense-in-depth validation without breaking tmux functionality.
        Since we use subprocess with list arguments (not shell=True), we focus on
        preventing the most dangerous injection patterns.

        Args:
            value: Input to validate
            field_name: Name of the field for error messages

        Returns:
            Validated input (unchanged if safe)

        Raises:
            ValueError: If input contains dangerous patterns
        """
        if not isinstance(value, str):
            raise ValueError(f"{field_name} must be string, got {type(value)}")

        # Check for null bytes (can cause issues with subprocess)
        if "\x00" in value:
            raise ValueError(f"{field_name} contains null byte")

        # For local CLI usage, only check for null bytes which can break subprocess
        # Newlines and carriage returns are safe in tmux literal mode (-l flag)
        # and this is a local developer tool, not a network service

        return value

    def _sanitize_input(self, value: str) -> str:
        """Sanitize input for shell contexts using shlex.quote().

        This should only be used when we need to pass arguments to shell contexts.
        For normal tmux commands using subprocess with lists, _validate_input is sufficient.

        Args:
            value: The input string to sanitize

        Returns:
            Safely quoted string for shell contexts
        """
        if not isinstance(value, str):
            raise ValueError(f"Input must be string, got {type(value)}")

        # Use shlex.quote for comprehensive protection in shell contexts
        return shlex.quote(value)

    def _check_tmux_server_health(self) -> bool:
        """Check if tmux server is responsive and healthy."""
        try:
            # Simple health check - list sessions should respond quickly
            result = subprocess.run(
                [self.tmux_cmd, "list-sessions"],
                capture_output=True,
                text=True,
                check=False,
                shell=False,
                timeout=2.0,  # 2 second timeout for health check
            )
            return result.returncode in [0, 1]  # 0=sessions exist, 1=no sessions (both healthy)
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            self._logger.warning("TMUX server health check failed - server may be overloaded")
            return False

    def _throttle_command(self) -> None:
        """Throttle tmux commands to prevent server overload."""
        current_time = time.time()
        elapsed = current_time - self._last_command_time

        if elapsed < self._min_command_interval:
            sleep_time = self._min_command_interval - elapsed
            time.sleep(sleep_time)

        self._last_command_time = time.time()

    def _run_tmux(self, args: list[str], check: bool = True) -> subprocess.CompletedProcess:
        """Run a tmux command with security safeguards and throttling.

        SECURITY: This method ensures all arguments are passed safely to subprocess
        without shell interpretation. Never use shell=True with user input.
        """
        # Throttle commands to prevent server overload
        self._throttle_command()

        # Validate that args is a list to prevent accidental string passing
        if not isinstance(args, list):
            raise ValueError("args must be a list")

        # Validate each argument
        validated_args = []
        for i, arg in enumerate(args):
            if not isinstance(arg, str):
                raise ValueError(f"Argument {i} must be string, got {type(arg)}")
            validated_args.append(self._validate_input(arg, f"argument {i}"))

        cmd = [self.tmux_cmd] + validated_args

        # SECURITY: Explicitly set shell=False to prevent shell injection
        # Add timeout to prevent hanging commands that could indicate server issues
        try:
            return subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=check,
                shell=False,  # CRITICAL: Never use shell=True with user input
                timeout=10.0,  # 10 second timeout to detect server issues
            )
        except subprocess.TimeoutExpired as e:
            self._logger.error(f"TMUX command timed out: {' '.join(cmd)} - server may be overloaded")
            if check:
                raise
            # Return a failed result for non-checking calls
            return subprocess.CompletedProcess(cmd, 1, "", f"Command timed out: {e}")

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

    def send_message(self, target: str, message: str, delay: float = 0.5) -> bool:
        """Send a message to a Claude agent using the proven CLI method.

        This implementation matches the working CLI agent send command.

        Args:
            target: Target pane (session:window or session:window.pane)
            message: Message text to send
            delay: Delay between operations (default 0.5s)

        Returns:
            bool: True if message was sent successfully
        """
        import time

        try:
            # Clear any existing input first
            # DISABLED: self.press_ctrl_c(target)  # This kills Claude when multiple messages arrive
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
        # DISABLED: self.press_ctrl_c(target)  # This kills Claude when multiple messages arrive
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
        """Capture pane output with defensive server health checking."""
        # Defensive check for frequent operations - don't overwhelm server
        if not hasattr(self, "_health_check_counter"):
            self._health_check_counter = 0

        # Check server health every 10 capture_pane calls
        self._health_check_counter += 1
        if self._health_check_counter % 10 == 0:
            if not self._check_tmux_server_health():
                self._logger.warning("TMUX server unhealthy during capture_pane - backing off")
                time.sleep(0.5)  # Brief backoff

        result = self._run_tmux(["capture-pane", "-t", target, "-p"], check=False)
        if result.returncode == 0:
            output_lines = result.stdout.strip().split("\n")
            return "\n".join(output_lines[-lines:])
        return ""

    def list_sessions(self) -> list[dict[str, str]]:
        """List all tmux sessions with caching for performance."""
        current_time = time.time()

        # Check cache
        if current_time - self._session_cache_time < self._cache_ttl and "sessions" in self._session_cache:
            from typing import cast

            return cast(list[dict[str, str]], self._session_cache["sessions"])

        # Cache miss - get fresh data
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

        # Update cache
        self._session_cache["sessions"] = sessions
        self._session_cache_time = current_time

        typed_sessions: list[dict[str, str]] = sessions
        return typed_sessions

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
                    # Determine agent type directly from window name
                    window_name = window["name"]

                    # Remove "claude-" prefix if present
                    if window_name.lower().startswith("claude-"):
                        window_name = window_name[7:]  # Remove "claude-" (7 chars)

                    # Use window name directly, capitalizing appropriately
                    agent_type = window_name.replace("-", " ").replace("_", " ").title()

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

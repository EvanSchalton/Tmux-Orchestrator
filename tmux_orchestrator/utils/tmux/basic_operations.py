"""Basic TMUX operations for sessions, windows, and key sending."""

import logging
import subprocess
from typing import Optional


class BasicTmuxOperations:
    """Core TMUX operations without performance optimizations."""

    def __init__(self, tmux_cmd: str = "tmux"):
        """Initialize basic TMUX operations.

        Args:
            tmux_cmd: TMUX command to use (default: "tmux")
        """
        self.tmux_cmd = tmux_cmd
        self._logger = logging.getLogger(__name__)

    def has_session(self, session_name: str) -> bool:
        """Check if a tmux session exists."""
        try:
            cmd = [self.tmux_cmd, "has-session", "-t", session_name]
            self._logger.debug(f"Checking session existence: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, timeout=1, text=True)
            success = result.returncode == 0
            self._logger.debug(f"Session '{session_name}' exists: {success}")
            if not success and result.stderr:
                self._logger.debug(f"has-session stderr: {result.stderr.strip()}")
            return success
        except Exception as e:
            self._logger.error(f"Exception checking session '{session_name}': {e}")
            return False

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

            self._logger.info(f"Creating session '{session_name}': {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, timeout=5, text=True)
            success = result.returncode == 0

            if success:
                self._logger.info(f"Session '{session_name}' created successfully")
            else:
                self._logger.error(f"Session creation failed - return code: {result.returncode}")
                if result.stdout:
                    self._logger.error(f"create-session stdout: {result.stdout.strip()}")
                if result.stderr:
                    self._logger.error(f"create-session stderr: {result.stderr.strip()}")

            return success
        except Exception as e:
            self._logger.error(f"Exception during session creation '{session_name}': {e}")
            return False

    def create_window(self, session_name: str, window_name: str, start_directory: Optional[str] = None) -> bool:
        """Create a new window in a session."""
        try:
            cmd = [self.tmux_cmd, "new-window", "-t", session_name, "-n", window_name]
            if start_directory:
                cmd.extend(["-c", start_directory])

            self._logger.info(f"Creating window '{window_name}' in session '{session_name}': {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, timeout=3, text=True)
            success = result.returncode == 0

            if success:
                self._logger.info(f"Window '{window_name}' created successfully in session '{session_name}'")
            else:
                self._logger.error(f"Window creation failed - return code: {result.returncode}")
                if result.stdout:
                    self._logger.error(f"new-window stdout: {result.stdout.strip()}")
                if result.stderr:
                    self._logger.error(f"new-window stderr: {result.stderr.strip()}")
                self._logger.error(f"Failed command: {' '.join(cmd)}")

            return success
        except Exception as e:
            self._logger.error(f"Exception during window creation '{window_name}' in '{session_name}': {e}")
            return False

    def send_keys(self, target: str, keys: str, literal: bool = False) -> bool:
        """Send keys to a tmux target."""
        try:
            cmd = [self.tmux_cmd, "send-keys", "-t", target]
            if literal:
                cmd.append("-l")
            cmd.append(keys)

            self._logger.debug(f"Sending keys to '{target}': {repr(keys)} (literal={literal})")
            result = subprocess.run(cmd, capture_output=True, timeout=2, text=True)
            success = result.returncode == 0

            if not success:
                self._logger.error(f"Send keys failed - return code: {result.returncode}")
                if result.stdout:
                    self._logger.error(f"send-keys stdout: {result.stdout.strip()}")
                if result.stderr:
                    self._logger.error(f"send-keys stderr: {result.stderr.strip()}")
                self._logger.error(f"Failed command: {' '.join(cmd)}")
            else:
                self._logger.debug(f"Keys sent successfully to '{target}'")

            return success
        except Exception as e:
            self._logger.error(f"Exception during send_keys to '{target}': {e}")
            return False

    def press_enter(self, target: str) -> bool:
        """Press Enter key in the target pane."""
        return self.send_keys(target, "Enter", literal=False)

    def press_ctrl_u(self, target: str) -> bool:
        """Press Ctrl+U (clear line) in the target pane."""
        return self.send_keys(target, "C-u", literal=False)

    def press_escape(self, target: str) -> bool:
        """Press Escape key in the target pane."""
        return self.send_keys(target, "Escape", literal=False)

    def press_ctrl_e(self, target: str) -> bool:
        """Press Ctrl+E (end of line) in the target pane."""
        return self.send_keys(target, "C-e", literal=False)

    def capture_pane(self, target: str, lines: int = 50) -> str:
        """Capture pane output."""
        try:
            cmd = [self.tmux_cmd, "capture-pane", "-t", target, "-p"]
            if lines > 0:
                cmd.extend(["-S", f"-{lines}"])

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                return result.stdout
            else:
                self._logger.error(f"Failed to capture pane {target}: {result.stderr}")
                return ""
        except Exception as e:
            self._logger.error(f"Error capturing pane {target}: {e}")
            return ""

    def kill_window(self, target: str) -> bool:
        """Kill a specific tmux window."""
        self._logger.warning(f"🔪 TMUX KILL_WINDOW: Killing window {target}")
        self._logger.warning("🔪 CALLER: BasicTmuxOperations.kill_window() called")
        import traceback

        stack = traceback.format_stack()
        # Log the last few stack frames to see who called this
        self._logger.warning(f"🔪 CALL STACK: {stack[-3].strip()}")
        self._logger.warning(f"🔪 CALL STACK: {stack[-2].strip()}")

        result = subprocess.run([self.tmux_cmd, "kill-window", "-t", target], capture_output=True, text=True)
        success = result.returncode == 0

        if success:
            self._logger.warning(f"🔪 KILL SUCCESS: Window {target} killed successfully")
        else:
            self._logger.error(f"🔪 KILL FAILED: Window {target} kill failed - return code: {result.returncode}")
            if result.stderr:
                self._logger.error(f"🔪 KILL ERROR: {result.stderr.strip()}")

        return success

    def kill_session(self, session_name: str) -> bool:
        """Kill a specific tmux session."""
        self._logger.warning(f"🔪 TMUX KILL_SESSION: Killing session {session_name}")
        self._logger.warning("🔪 CALLER: BasicTmuxOperations.kill_session() called")
        import traceback

        stack = traceback.format_stack()
        self._logger.warning(f"🔪 CALL STACK: {stack[-3].strip()}")
        self._logger.warning(f"🔪 CALL STACK: {stack[-2].strip()}")

        result = subprocess.run([self.tmux_cmd, "kill-session", "-t", session_name], capture_output=True, text=True)
        success = result.returncode == 0

        if success:
            self._logger.warning(f"🔪 KILL SUCCESS: Session {session_name} killed successfully")
        else:
            self._logger.error(f"🔪 KILL FAILED: Session {session_name} kill failed - return code: {result.returncode}")
            if result.stderr:
                self._logger.error(f"🔪 KILL ERROR: {result.stderr.strip()}")

        return success

    def run(self, command: str) -> bool:
        """Execute a raw tmux command."""
        try:
            result = subprocess.run([self.tmux_cmd] + command.split(), capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except Exception:
            return False

"""Message sending and text operations for TMUX panes."""

import logging
import subprocess


class MessageOperations:
    """Handles TMUX message sending and text operations."""

    def __init__(self, tmux_cmd: str = "tmux"):
        """Initialize message operations.

        Args:
            tmux_cmd: TMUX command to use (default: "tmux")
        """
        self.tmux_cmd = tmux_cmd
        self._logger = logging.getLogger(__name__)

    def send_keys_optimized(self, target: str, keys: str, literal: bool = False) -> bool:
        """Send keys with optimization."""
        return self.send_keys(target, keys, literal)

    def send_keys(self, target: str, keys: str, literal: bool = False) -> bool:
        """Send keys to a tmux target."""
        try:
            cmd = [self.tmux_cmd, "send-keys", "-t", target]
            if literal:
                cmd.append("-l")
            cmd.append(keys)

            result = subprocess.run(cmd, capture_output=True, timeout=2)
            return result.returncode == 0
        except Exception as e:
            self._logger.error(f"Send keys failed: {e}")
            return False

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

    # Chunking removed - messages sent directly

    def send_text(self, target: str, text: str, **kwargs) -> bool:
        """Send text directly to target. Ignores legacy chunking params.

        Args:
            target: TMUX target (session:window format)
            text: Text to send
            **kwargs: Ignored legacy parameters

        Returns:
            True if successful
        """
        try:
            # Send entire message directly - tmux handles 4000+ chars
            return self.send_keys(target, text, literal=True)
        except Exception as e:
            self._logger.error(f"Failed to send text to {target}: {e}")
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

    def send_message(self, target: str, message: str, delay: float = 0.5) -> bool:
        """Send a message with Enter key press.

        Args:
            target: TMUX target
            message: Message to send
            delay: Delay before pressing Enter

        Returns:
            True if successful
        """
        try:
            # Send the message text
            if not self.send_text(target, message):
                return False

            # Brief delay before pressing Enter
            if delay > 0:
                import time

                time.sleep(delay)

            # Press Enter to submit
            return self.press_enter(target)

        except Exception as e:
            self._logger.error(f"Failed to send message to {target}: {e}")
            return False

    def _is_idle(self, pane_content: str) -> bool:
        """Determine if pane content indicates an idle session."""
        if not pane_content.strip():
            return True

        idle_indicators = [
            "bash-",
            "$ ",
            "# ",
            "waiting",
            "idle",
            "ready",
            ">>>",  # Python prompt
            "claude>",
        ]

        last_lines = pane_content.split("\n")[-3:]  # Check last 3 lines
        content_check = " ".join(last_lines).lower()

        return any(indicator in content_check for indicator in idle_indicators)

    def _validate_input(self, value: str, field_name: str = "input") -> str:
        """Validate and sanitize input string."""
        if not isinstance(value, str):
            raise ValueError(f"{field_name} must be a string")

        # Remove any null bytes or other problematic characters
        sanitized = value.replace("\x00", "").strip()

        if not sanitized:
            raise ValueError(f"{field_name} cannot be empty")

        return sanitized

    def run(self, command: str) -> bool:
        """Execute a raw tmux command."""
        try:
            result = subprocess.run([self.tmux_cmd] + command.split(), capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except Exception:
            return False

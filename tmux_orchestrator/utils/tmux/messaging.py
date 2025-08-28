"""Message handling for TMUX - direct sending without chunking."""

import logging
import re
import subprocess
from typing import Optional

from .basic_operations import BasicTmuxOperations


class TmuxMessaging:
    """Handles message sending directly without chunking."""

    def __init__(self, basic_ops: Optional[BasicTmuxOperations] = None):
        """Initialize messaging operations."""
        self.basic_ops = basic_ops or BasicTmuxOperations()
        self._logger = logging.getLogger(__name__)

    def send_text(self, target: str, text: str, **kwargs) -> bool:
        """Send literal text to the target pane directly. Ignores legacy chunking params."""
        try:
            result = subprocess.run(["tmux", "send-keys", "-t", target, "-l", text], capture_output=True)
            return result.returncode == 0
        except Exception:
            return False

    def send_message(self, target: str, message: str, delay: float = 0.5) -> bool:
        """Send a message to an agent (text + Enter)."""
        try:
            self._logger.info(f"TmuxMessaging.send_message: to '{target}' ({len(message)} chars)")

            # Send message text literally
            cmd1 = ["tmux", "send-keys", "-t", target, "-l", message]
            self._logger.debug(f"Sending message text: {' '.join(cmd1)}")
            result = subprocess.run(cmd1, capture_output=True, text=True)

            if result.returncode != 0:
                self._logger.error(f"Failed to send message text - return code: {result.returncode}")
                if result.stderr:
                    self._logger.error(f"send-keys stderr: {result.stderr.strip()}")
                return False

            self._logger.debug("Message text sent successfully, now sending Enter")

            # Send Enter to submit
            cmd2 = ["tmux", "send-keys", "-t", target, "Enter"]
            self._logger.debug(f"Sending Enter: {' '.join(cmd2)}")
            result = subprocess.run(cmd2, capture_output=True, text=True)

            success = result.returncode == 0
            if success:
                self._logger.info(f"Message sent successfully to '{target}'")
            else:
                self._logger.error(f"Failed to send Enter - return code: {result.returncode}")
                if result.stderr:
                    self._logger.error(f"send-keys Enter stderr: {result.stderr.strip()}")

            return success
        except Exception as e:
            self._logger.error(f"Exception in send_message to '{target}': {e}", exc_info=True)
            return False

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

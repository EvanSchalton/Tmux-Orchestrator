"""Claude-specific interface handling for tmux sessions."""

import logging
import subprocess
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# Use secure project directory instead of /tmp
PROJECT_DIR = Path.cwd() / ".tmux_orchestrator"
PROJECT_DIR.mkdir(exist_ok=True)
BRIEFINGS_DIR = PROJECT_DIR / "briefings"
BRIEFINGS_DIR.mkdir(exist_ok=True)


class ClaudeInterface:
    """Handles Claude-specific terminal interface quirks."""

    @staticmethod
    def send_message_to_claude(tmux_session: str, message: str, timeout: float = 10.0) -> tuple[bool, str]:
        """
        Send a message to Claude and ensure it's actually submitted.

        Claude's interface requires special handling:
        1. Text appears in input box but Enter doesn't submit
        2. Might need specific key sequences or timing
        3. May require detecting UI state before sending

        Args:
            tmux_session: Target session in format "session:window"
            message: Message to send
            timeout: Maximum time to wait for submission

        Returns:
            Tuple of (success, error_message)
        """
        try:
            # First, check if Claude interface is ready
            pane_content = ClaudeInterface._get_pane_content(tmux_session)
            if not ClaudeInterface._is_claude_ready(pane_content):
                return False, "Claude interface not ready or not found"

            # Clear any existing input with multiple methods
            ClaudeInterface._clear_input(tmux_session)
            time.sleep(0.5)

            # Try multiple submission methods
            methods = [
                ClaudeInterface._method_standard_submit,
                ClaudeInterface._method_paste_and_submit,
                ClaudeInterface._method_literal_keys,
                ClaudeInterface._method_multiple_enters,
                ClaudeInterface._method_escape_sequence,
            ]

            for method in methods:
                if method(tmux_session, message):
                    # Verify submission worked
                    time.sleep(2.0)
                    new_content = ClaudeInterface._get_pane_content(tmux_session)
                    if ClaudeInterface._message_was_submitted(pane_content, new_content, message):
                        return True, ""

            return False, "All submission methods failed"

        except Exception as e:
            logger.error(f"Error sending message to Claude: {e}")
            return False, str(e)

    @staticmethod
    def _get_pane_content(target: str) -> str:
        """Get current pane content."""
        try:
            result = subprocess.run(
                ["tmux", "capture-pane", "-t", target, "-p", "-S", "-100"],
                capture_output=True,
                text=True,
                check=True,
                timeout=30,
            )
            return result.stdout
        except Exception:
            return ""

    @staticmethod
    def _is_claude_ready(content: str) -> bool:
        """Check if Claude interface is ready for input."""
        # Look for Claude's prompt indicator
        indicators = [
            "> ",  # Common prompt
            "│ >",  # Box prompt
            "Type a message",  # Input placeholder
            "Claude",  # Interface loaded
        ]
        return any(indicator in content for indicator in indicators)

    @staticmethod
    def _clear_input(target: str) -> None:
        """Clear any existing input in multiple ways."""
        # Try various clear methods
        subprocess.run(["tmux", "send-keys", "-t", target, "C-c"], check=False, timeout=10)
        time.sleep(0.2)
        subprocess.run(["tmux", "send-keys", "-t", target, "C-u"], check=False, timeout=10)
        time.sleep(0.2)
        subprocess.run(["tmux", "send-keys", "-t", target, "Escape"], check=False, timeout=10)
        time.sleep(0.2)
        # Select all and delete
        subprocess.run(["tmux", "send-keys", "-t", target, "C-a"], check=False, timeout=10)
        time.sleep(0.1)
        subprocess.run(["tmux", "send-keys", "-t", target, "C-k"], check=False, timeout=10)

    @staticmethod
    def _method_standard_submit(target: str, message: str) -> bool:
        """Standard submission: type and press Ctrl+Enter (Claude's required key)."""
        try:
            # Type the message
            subprocess.run(["tmux", "send-keys", "-t", target, message], check=True, timeout=15)
            time.sleep(0.5)
            # Use Ctrl+Enter for Claude submission
            subprocess.run(["tmux", "send-keys", "-t", target, "C-Enter"], check=True, timeout=10)
            return True
        except Exception:
            return False

    @staticmethod
    def _method_paste_and_submit(target: str, message: str) -> bool:
        """Use tmux paste buffer."""
        try:
            # Set buffer
            subprocess.run(["tmux", "set-buffer", message], check=True, timeout=10)
            # Paste it
            subprocess.run(["tmux", "paste-buffer", "-t", target], check=True, timeout=15)
            time.sleep(0.5)
            # Submit with Ctrl+Enter
            subprocess.run(["tmux", "send-keys", "-t", target, "C-Enter"], check=True, timeout=10)
            return True
        except Exception:
            return False

    @staticmethod
    def _method_literal_keys(target: str, message: str) -> bool:
        """Send keys with -l flag for literal interpretation."""
        try:
            subprocess.run(["tmux", "send-keys", "-t", target, "-l", message], check=True, timeout=15)
            time.sleep(0.5)
            subprocess.run(["tmux", "send-keys", "-t", target, "C-Enter"], check=True, timeout=10)
            return True
        except Exception:
            return False

    @staticmethod
    def _method_multiple_enters(target: str, message: str) -> bool:
        """Try multiple Enter key variations."""
        try:
            subprocess.run(["tmux", "send-keys", "-t", target, message], check=True, timeout=15)
            time.sleep(0.5)
            # Use Ctrl+Enter which is the proven working method
            subprocess.run(["tmux", "send-keys", "-t", target, "C-Enter"], check=True, timeout=10)
            return True
        except Exception:
            return False

    @staticmethod
    def _method_escape_sequence(target: str, message: str) -> bool:
        """Try with escape sequences."""
        try:
            # Send with newline
            full_message = f"{message}\n"
            subprocess.run(["tmux", "send-keys", "-t", target, full_message], check=True, timeout=15)
            time.sleep(0.5)
            # Also try carriage return
            subprocess.run(["tmux", "send-keys", "-t", target, "\r"], check=True, timeout=10)
            return True
        except Exception:
            return False

    @staticmethod
    def _message_was_submitted(old_content: str, new_content: str, message: str) -> bool:
        """Check if message was actually submitted."""
        # Look for signs the message was processed
        if message not in new_content:
            return False  # Message disappeared (good sign)

        # Check for Claude's response indicators
        response_indicators = [
            "Claude:",
            "I'll",
            "I will",
            "Let me",
            "Sure,",
            "●",  # Typing indicator
        ]

        # Check if new content appeared after our message
        old_lines = len(old_content.splitlines())
        new_lines = len(new_content.splitlines())

        return new_lines > old_lines + 2 or any(ind in new_content for ind in response_indicators)


class ClaudeAgentManager:
    """Manages Claude agents in tmux sessions."""

    @staticmethod
    def initialize_agent(session: str, window: str, briefing: str) -> bool:
        """
        Initialize a Claude agent with a briefing message.

        This handles the special case where agents are spawned but
        the initial briefing doesn't get delivered.
        """
        target = f"{session}:{window}"

        # Wait for Claude to be ready
        max_attempts = 30  # 30 seconds
        for i in range(max_attempts):
            content = ClaudeInterface._get_pane_content(target)
            if ClaudeInterface._is_claude_ready(content):
                break
            time.sleep(1.0)
        else:
            logger.error(f"Claude not ready after {max_attempts} seconds in {target}")
            return False

        # Send the briefing
        success, error = ClaudeInterface.send_message_to_claude(target, briefing)
        if not success:
            logger.error(f"Failed to deliver briefing to {target}: {error}")
            # Try alternate delivery method - write to file
            try:
                briefing_file = BRIEFINGS_DIR / f"briefing_{session}_{window}.txt"
                with open(briefing_file, "w") as f:
                    f.write(f"BRIEFING: {briefing}\n")
                # Try to make agent read the file
                read_cmd = f"Please read the briefing at {briefing_file}"
                ClaudeInterface.send_message_to_claude(target, read_cmd)
            except Exception as e:
                logger.error(f"Failed to deliver briefing via file: {e}")

        return success

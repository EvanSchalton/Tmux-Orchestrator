"""
Context-aware crash detection for agents and PMs.

This module provides sophisticated crash detection that prevents false positives
when agents are discussing failures, errors, or killed processes in normal conversation.
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from tmux_orchestrator.utils.tmux import TMUXManager

from .interfaces import CrashDetectorInterface
from .types import AgentInfo


class CrashDetector(CrashDetectorInterface):
    """Context-aware crash detection system."""

    def __init__(self, tmux: TMUXManager, logger: logging.Logger):
        """Initialize crash detector.

        Args:
            tmux: TMux manager instance
            logger: Logger instance
        """
        self.tmux = tmux
        self.logger = logger

        # Observation tracking for confirmation-based detection
        self._crash_observations: Dict[str, List[datetime]] = {}
        self._crash_observation_window = 30  # seconds

        # Focused crash indicators - only actual process crashes
        self._crash_indicators = [
            "claude: command not found",  # Claude binary missing
            "segmentation fault",  # Process crash
            "core dumped",  # Process crash
            "killed",  # Process killed
            "terminated",  # Process terminated
            "panic:",  # System panic
            "bash-",  # Shell prompt (Claude gone)
            "zsh:",  # Shell prompt (Claude gone)
            # Removed "$ " as it causes too many false positives
            "traceback (most recent call last)",  # Python crash
            "modulenotfounderror",  # Import failure
            "process finished with exit code",  # Process died
            "[process completed]",  # Process ended
            "process does not exist",  # Process killed
            "no process found",  # Process terminated
            "broken pipe",  # Communication failure
            "connection lost",  # Connection failure (not tool output)
        ]

        # Regex patterns that indicate normal agent output, not crashes
        self._regex_ignore_contexts = [
            r"test.*failed",
            r"tests?\s+failed",
            r"check.*failed",
            r"Tests failed:",
            r"Build failed:",
            r"unit\s+test.*failed",
            r"integration\s+test.*failed",
            r"test\s+suite.*failed",
            r"failing\s+test",
            r"deployment.*failed",
            r"pipeline.*failed",
            r"job.*failed",
            r"Task failed:",
            r"Failed:",
            r"FAILED:",
            r"\d+\s+tests?\s+failed",  # "3 tests failed"
            r"failed\s+\d+\s+tests?",  # "failed 3 tests"
        ]

        # Additional substring patterns for non-regex matches
        self._safe_contexts = [
            # PM analyzing or reporting errors
            "error occurred",
            "error was",
            "error has been",
            "previous error",
            "fixed the error",
            "resolving error",
            "error in the",
            # Status reports and discussions
            "reported killed",
            "was killed by",
            "process was terminated",
            "has been terminated",
            "connection was lost",
            # Historical references
            "previously failed",
            "had failed",
            "which failed",
            "that failed",
            # Tool output patterns
            "⎿",  # Tool output boundary
            "│",  # Tool output formatting
            "└",  # Tool output formatting
            "├",  # Tool output formatting
        ]

    def detect_crash(self, agent: AgentInfo, content: str) -> Tuple[bool, Optional[str]]:
        """Detect if an agent has crashed based on content analysis.

        Args:
            agent: Agent information
            content: Terminal content to analyze

        Returns:
            Tuple of (crashed: bool, crash_reason: str | None)
        """
        content_lower = content.lower()

        # PRIORITY 1: Check for shell prompt at the end of content (immediate crash detection)
        if self._check_shell_prompt_at_end(content):
            self.logger.warning(f"Agent {agent.target} shows shell prompt at end - likely crashed")
            return True, "Shell prompt detected at terminal end"

        # PRIORITY 2: Check for crash indicators
        for indicator in self._crash_indicators:
            if indicator in content_lower:
                # Use context-aware check to prevent false positives
                if self._should_ignore_crash_indicator(indicator, content, content_lower):
                    self.logger.debug(
                        f"Ignoring crash indicator '{indicator}' in {agent.target} - " "appears to be normal output"
                    )
                    continue

                self.logger.warning(f"Crash indicator found: '{indicator}' in {agent.target}")

                # Use observation period for confirmation
                if self._confirm_crash_with_observation(agent.target, indicator):
                    return True, f"Confirmed crash: {indicator}"
                else:
                    # Still observing, not confirmed yet
                    return False, None

        # PRIORITY 3: Check if Claude interface is present (only for extremely minimal content)
        # Only flag as crash if content is very short and empty-looking
        # This prevents false positives on normal conversation content
        if len(content.strip()) < 10 and not self._is_claude_interface_present(content):
            self.logger.warning(f"Agent {agent.target} missing Claude interface in minimal content - likely crashed")
            return True, "Missing Claude interface"

        return False, None

    def _should_ignore_crash_indicator(self, indicator: str, content: str, content_lower: str) -> bool:
        """Determine if a crash indicator should be ignored based on context.

        This prevents false positives when agents are discussing failures/errors
        in normal conversation or reporting status.

        Args:
            indicator: The crash indicator that was found
            content: Full terminal content (original case)
            content_lower: Lowercase version of content

        Returns:
            True if the indicator should be ignored (false positive)
        """
        # Check regex patterns for more flexible matching
        for pattern in self._regex_ignore_contexts:
            if re.search(pattern, content, re.IGNORECASE):
                return True

        # Check if indicator appears in a safe context
        for safe_context in self._safe_contexts:
            if safe_context.lower() in content_lower:
                # Found in safe context - this is likely normal agent output
                return True

        # Additional checks for specific indicators
        if indicator == "killed":
            # Check if it's discussing a killed process vs being killed itself
            kill_contexts = ["process killed", "killed the", "killed by", "was killed", "been killed"]
            for context in kill_contexts:
                if context in content_lower:
                    return True

        if indicator == "terminated":
            # Check if discussing termination vs being terminated
            term_contexts = ["was terminated", "been terminated", "process terminated", "terminated the"]
            for context in term_contexts:
                if context in content_lower:
                    return True

        # FIRST: Check for shell prompts at the very end of content (indicates actual crash)
        # This takes precedence over other patterns
        lines = content.strip().split("\n")
        if lines:
            last_line = lines[-1].strip()
            # Shell prompts that indicate actual crashes
            shell_prompt_patterns = [
                ("bash-", True),  # bash-5.1$ format
                ("zsh:", True),  # zsh: format
                ("$", False),  # Generic $ prompt (check if standalone)
                ("%", False),  # Generic % prompt
                ("#", False),  # Root prompt
                ("➜", False),  # Zsh fancy prompt
                ("❯", False),  # Fish/starship prompt
            ]

            for pattern, prefix_check in shell_prompt_patterns:
                if prefix_check:
                    # Check if line starts with this pattern (e.g., "bash-5.1$")
                    if last_line.startswith(pattern) and ("$" in last_line or pattern == "zsh:"):
                        return False  # This is a crash
                else:
                    # Check if it's just the prompt character or starts with it
                    if last_line == pattern or last_line.startswith(pattern):
                        return False  # This is a crash

                # Also check if the specific crash indicator is in a crash line
                if indicator == "bash-" and last_line.startswith("bash-") and "$" in last_line:
                    return False  # bash prompt after crash

        # Default: assume it's normal conversation about failures
        return True

    def _confirm_crash_with_observation(self, target: str, indicator: str) -> bool:
        """Use observation period to confirm crashes before taking action.

        Args:
            target: Agent target identifier
            indicator: The crash indicator found

        Returns:
            True if crash is confirmed after observation period
        """
        current_time = datetime.now()

        # Initialize observation list if needed
        if target not in self._crash_observations:
            self._crash_observations[target] = []

        # Clean up old observations outside the window
        self._crash_observations[target] = [
            obs
            for obs in self._crash_observations[target]
            if current_time - obs < timedelta(seconds=self._crash_observation_window)
        ]

        # Add current observation
        self._crash_observations[target].append(current_time)

        # Check if we have multiple observations within the window
        observation_count = len(self._crash_observations[target])

        if observation_count < 3:  # Require 3 observations before declaring crash
            self.logger.info(
                f"Crash indicator '{indicator}' observed ({observation_count}/3) "
                f"in {target} - monitoring for {self._crash_observation_window}s"
            )
            return False  # Don't declare crash yet
        else:
            self.logger.error(
                f"Crash confirmed after {observation_count} observations "
                f"within {self._crash_observation_window}s window"
            )
            # Clear observations for this target
            del self._crash_observations[target]
            return True

    def _is_claude_interface_present(self, content: str) -> bool:
        """Check if Claude interface markers are present in content.

        Args:
            content: Terminal content to check

        Returns:
            True if Claude interface appears to be present
        """
        claude_markers = [
            "Human:",
            "Assistant:",
            "claude-3",
            "claude-opus",
            "claude-sonnet",
            "claude-haiku",
            "Claude Code",
            "thinking...",
            "⎿",  # Tool output marker
            "Tool Result:",
        ]

        content_lower = content.lower()
        for marker in claude_markers:
            if marker.lower() in content_lower:
                return True

        return False

    def _check_shell_prompt_at_end(self, content: str) -> bool:
        """Check if content ends with a shell prompt indicating crash.

        Args:
            content: Terminal content to check

        Returns:
            True if shell prompt detected at end indicating crash
        """
        lines = content.strip().split("\n")
        if not lines:
            return False

        # Check last few lines for shell prompt patterns
        last_lines = lines[-3:]  # Check last 3 lines

        for line in reversed(last_lines):
            line = line.strip()
            if not line:
                continue

            # Common shell prompt patterns that indicate Claude has exited
            shell_patterns = [
                (r"^bash-\d+\.\d+\$$", True),  # bash-5.1$
                (r"^bash-.*\$$", True),  # bash-anything$
                (r"^zsh:\s*\$$", True),  # zsh: $
                (r"^zsh:\s*$", True),  # zsh: (without $)
                (r"^\[.+\]\$$", True),  # [user@host]$
                (r"^.+@.+[:#~]\s*\$$", True),  # user@host:~ $
                (r"^➜.*", True),  # zsh prompt
                (r"^❯.*", True),  # fish/starship prompt
                (r"^\$$", True),  # Just $ on its own line
                (r"^\$ $", True),  # $ with trailing space
                (r"^#$", True),  # Just # (root)
                (r"^%$", True),  # Just % (csh/tcsh)
            ]

            for pattern, is_regex in shell_patterns:
                if is_regex:
                    if re.match(pattern, line):
                        self.logger.debug(f"Shell prompt pattern '{pattern}' matched: '{line}'")
                        return True
                else:
                    if line == pattern:
                        self.logger.debug(f"Shell prompt exact match: '{line}'")
                        return True

            # If we found a non-empty line that's not a prompt, probably not crashed
            if len(line) > 5:  # Arbitrary threshold for "real content"
                return False

        return False

    def detect_pm_crash(self, session_name: str) -> Tuple[bool, Optional[str]]:
        """Detect if PM has crashed in the given session.

        Args:
            session_name: Session to check for PM

        Returns:
            Tuple of (crashed: bool, pm_target: str | None)
            - crashed: True if PM crashed or is unhealthy
            - pm_target: The target string if PM window exists (crashed or healthy)
        """
        try:
            self.logger.debug(f"Detecting PM crash in session {session_name}")

            # First, check if there's any PM window
            pm_window = self._find_pm_window(session_name)

            if not pm_window:
                self.logger.info(f"No PM window found in session {session_name}")
                return (True, None)  # PM is missing entirely

            self.logger.debug(f"Found PM window at {pm_window}, checking health...")

            # Check if PM has Claude interface
            content = self.tmux.capture_pane(pm_window, lines=20)

            # Create a temporary AgentInfo for the PM
            pm_agent = AgentInfo(
                target=pm_window,
                session=session_name,
                window=pm_window.split(":")[1],
                name="Project Manager",
                type="pm",
                status="unknown",
            )

            # Use the main crash detection logic
            crashed, reason = self.detect_crash(pm_agent, content)

            if crashed:
                self.logger.error(f"PM crash detected in {pm_window}: {reason}")
                return (True, pm_window)
            else:
                self.logger.debug(f"PM at {pm_window} appears healthy")
                return (False, pm_window)

        except Exception as e:
            self.logger.error(f"Error detecting PM crash in session {session_name}: {e}")
            return (True, None)

    def _find_pm_window(self, session_name: str) -> Optional[str]:
        """Find PM window in the given session.

        Args:
            session_name: Session to search

        Returns:
            PM target identifier or None if not found
        """
        try:
            windows = self.tmux.list_windows(session_name)
            for window_info in windows:
                window_name = window_info.get("name", "").lower()
                window_idx = window_info.get("index", "0")

                # Check for PM indicators in window name
                if "pm" in window_name or "project-manager" in window_name:
                    return f"{session_name}:{window_idx}"

        except Exception as e:
            self.logger.error(f"Error finding PM in session {session_name}: {e}")

        return None

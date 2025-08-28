"""Idle detection functionality for monitoring agent activity."""

import time
from typing import TYPE_CHECKING

from tmux_orchestrator.core.monitor.terminal_cache import TerminalCache
from tmux_orchestrator.utils.tmux import TMUXManager

if TYPE_CHECKING:
    pass


class IdleDetector:
    """Handles agent idle detection and activity monitoring."""

    def __init__(self) -> None:
        """Initialize the idle detector."""
        pass

    def is_agent_idle(self, tmux: TMUXManager, target: str) -> bool:
        """Check if agent is idle using the improved 4-snapshot method.

        Args:
            tmux: TMUXManager instance for terminal capture
            target: Agent target identifier in "session:window" format

        Returns:
            bool: True if agent is idle, False if active
        """
        try:
            session, window = target.split(":")

            # Take 4 snapshots of the last line at 300ms intervals
            snapshots = []
            for _ in range(4):
                content = tmux.capture_pane(target, lines=1)
                last_line = content.strip().split("\n")[-1] if content else ""
                snapshots.append(last_line)
                time.sleep(0.3)

            # If all snapshots are identical, agent is idle
            return all(line == snapshots[0] for line in snapshots)

        except Exception:
            return False  # If we can't check, assume active

    def detect_idle_type(self, target: str, current_content: str, terminal_caches: dict[str, "TerminalCache"]) -> str:
        """Detect if agent is newly idle (just finished work) or continuously idle.

        Uses TerminalCache class for efficient change detection to distinguish between:
        - newly_idle: Agent just completed work and became idle (notify immediately)
        - continuously_idle: Agent has been idle with no activity (use cooldown)

        Args:
            target: Agent target identifier
            current_content: Current terminal content
            terminal_caches: Dictionary of terminal caches by target

        Returns:
            "newly_idle", "continuously_idle", or "unknown"
        """
        try:
            # Performance optimization: configurable line count for terminal sampling
            terminal_sample_lines = 10  # Reduced from 100 for better performance

            # Get last N lines for efficiency (terminal activity usually at the end)
            current_lines = current_content.strip().split("\n")
            current_sample = (
                "\n".join(current_lines[-terminal_sample_lines:])
                if len(current_lines) >= terminal_sample_lines
                else current_content
            )

            # Get or create terminal cache for this agent
            if target not in terminal_caches:
                terminal_caches[target] = TerminalCache()

            cache = terminal_caches[target]

            # Update cache with current content
            cache.update(current_sample)

            # Get intelligent status from cache
            status = cache.status

            return status

        except Exception:
            # Fallback to unknown on error
            return "unknown"

    def is_terminal_actively_changing(self, snapshots: list[str]) -> bool:
        """Detect if terminal content is actively changing.

        Args:
            snapshots: List of terminal content snapshots taken over time

        Returns:
            bool: True if terminal is actively changing, False if static
        """
        if len(snapshots) < 2:
            return False

        for i in range(1, len(snapshots)):
            # Simple change detection - if content changed significantly, it's active
            if snapshots[i - 1] != snapshots[i]:
                # Check if change is meaningful (not just cursor blink)
                changes = sum(1 for a, b in zip(snapshots[i - 1], snapshots[i]) if a != b)
                if changes > 1:
                    return True

        return False

    def detect_processing_indicators(self, content: str) -> bool:
        """Detect if agent is actively processing based on content indicators.

        Args:
            content: Terminal content to analyze

        Returns:
            bool: True if processing indicators found, False otherwise
        """
        content_lower = content.lower()

        # Check for compaction (robust across Claude Code versions)
        if "compacting conversation" in content_lower:
            return True

        # Check for active processing (ellipsis indicates ongoing work)
        if "…" in content and any(
            word in content_lower for word in ["thinking", "pondering", "divining", "musing", "elucidating"]
        ):
            return True

        return False

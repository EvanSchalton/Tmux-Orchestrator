"""Agent health checking functionality for the monitoring system."""

import logging
import time
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from tmux_orchestrator.core.monitor_helpers import (
    AgentState,
    detect_claude_state,
    is_claude_interface_present,
    should_notify_continuously_idle,
    should_notify_pm,
)
from tmux_orchestrator.utils.tmux import TMUXManager

if TYPE_CHECKING:
    from tmux_orchestrator.core.monitor.terminal_cache import TerminalCache


class HealthChecker:
    """Handles agent health status checking and monitoring."""

    def __init__(self) -> None:
        """Initialize the health checker."""
        self._idle_agents: dict[str, datetime] = {}
        self._submission_attempts: dict[str, int] = {}
        self._last_submission_time: dict[str, float] = {}
        self._idle_notifications: dict[str, datetime] = {}
        self._restart_attempts: dict[str, datetime] = {}
        self._terminal_caches: dict[str, "TerminalCache"] = {}

    def check_agent_status(
        self, tmux: TMUXManager, target: str, logger: logging.Logger, pm_notifications: dict[str, list[str]]
    ) -> None:
        """Check agent status using improved detection algorithm."""
        try:
            # Get session-specific logger
            session_name = target.split(":")[0]
            session_logger = self._get_session_logger(session_name)

            session_logger.debug(f"Checking status for agent {target}")

            # Step 1: Use polling-based active detection (NEW METHOD)
            snapshots = []
            poll_interval = 0.3  # 300ms
            poll_count = 4  # 1.2s total

            # Take snapshots for change detection
            for i in range(poll_count):
                content = tmux.capture_pane(target, lines=50)
                snapshots.append(content)
                if i < poll_count - 1:
                    time.sleep(poll_interval)

            # Use last snapshot for state detection
            content = snapshots[-1]

            # Step 2: Detect if terminal is actively changing
            is_active = False
            for i in range(1, len(snapshots)):
                # Simple change detection - if content changed significantly, it's active
                if snapshots[i - 1] != snapshots[i]:
                    # Check if change is meaningful (not just cursor blink)
                    changes = sum(1 for a, b in zip(snapshots[i - 1], snapshots[i]) if a != b)
                    session_logger.debug(f"Agent {target} snapshot {i} has {changes} character changes")
                    if changes > 1:
                        is_active = True
                        break

            if not is_active:
                session_logger.debug(f"Agent {target} determined to be idle - no significant changes")

            # Simple activity detection (minimal coupling to Claude Code implementation)
            if not is_active:
                content_lower = content.lower()

                # Check for compaction (robust across Claude Code versions)
                if "compacting conversation" in content_lower:
                    session_logger.debug(f"Agent {target} is compacting conversation")
                    session_logger.debug(f"Agent {target} found thinking indicator: 'Compacting conversation'")
                    session_logger.info(f"Agent {target} appears idle but is compacting - will not mark as idle")
                    is_active = True

                # Check for active processing (ellipsis indicates ongoing work)
                elif "…" in content and any(
                    word in content_lower for word in ["thinking", "pondering", "divining", "musing", "elucidating"]
                ):
                    session_logger.debug(f"Agent {target} is actively processing")
                    is_active = True

            # Step 3: Detect base state from content
            if not is_claude_interface_present(content):
                # No Claude interface - check if crashed
                lines = content.strip().split("\n")
                last_few_lines = [line for line in lines[-5:] if line.strip()]

                # Check for bash prompt
                for line in last_few_lines:
                    if line.strip().endswith(("$", "#", ">", "%")):
                        state = AgentState.CRASHED
                        session_logger.error(f"Agent {target} has crashed - attempting auto-restart")
                        success = self.attempt_agent_restart(tmux, target, session_logger)
                        if not success:
                            session_logger.error(f"Auto-restart failed for {target} - notifying PM")
                            self._notify_crash(tmux, target, logger, pm_notifications)
                        return

                # Otherwise it's an error state
                state = AgentState.ERROR
                session_logger.error(f"Agent {target} in error state - needs recovery")
                self._notify_recovery_needed(tmux, target, session_logger)
                return

            # Step 4: Check Claude state (fresh vs unsubmitted vs active)
            claude_state = detect_claude_state(content)

            if claude_state == "fresh":
                state = AgentState.FRESH
                session_logger.info(f"Agent {target} is FRESH - needs context/briefing")
                # Check if should notify PM about fresh agent
                if should_notify_pm(state, target, self._idle_notifications):
                    self._notify_fresh_agent(tmux, target, session_logger, pm_notifications)
                    # Track notification time with fresh prefix
                    self._idle_notifications[f"fresh_{target}"] = datetime.now()
                return
            elif claude_state == "unsubmitted":
                state = AgentState.MESSAGE_QUEUED
                session_logger.info(f"Agent {target} has unsubmitted message - attempting auto-submit")
                self.try_auto_submit(tmux, target, session_logger)
                return

            # Step 5: Determine if idle or active
            if is_active:
                state = AgentState.ACTIVE
                session_logger.info(f"Agent {target} is ACTIVE")
                # Reset tracking for active agents
                self._reset_agent_tracking(target)
            else:
                state = AgentState.IDLE

                # Intelligent idle detection: newly idle vs continuously idle
                idle_type = self._detect_idle_type(target, content, session_logger)

                if idle_type == "newly_idle":
                    session_logger.info(f"Agent {target} is NEWLY IDLE (just completed work) - notifying PM")
                    # Always notify PM about newly idle agents (they just finished work)
                    self._check_idle_notification(tmux, target, session_logger, pm_notifications)
                    self._idle_notifications[target] = datetime.now()
                elif idle_type == "continuously_idle":
                    session_logger.debug(f"Agent {target} is CONTINUOUSLY IDLE (no recent activity)")
                    # Use cooldown logic for continuously idle agents to prevent spam

                    if should_notify_continuously_idle(target, self._idle_notifications):
                        session_logger.info(f"Agent {target} continuously idle - notifying PM (with 5min cooldown)")
                        self._check_idle_notification(tmux, target, session_logger, pm_notifications)
                        self._idle_notifications[target] = datetime.now()
                    else:
                        session_logger.debug(f"Agent {target} continuously idle - notification in cooldown")
                else:  # "unknown" fallback
                    session_logger.info(f"Agent {target} is IDLE (type unknown) - notifying PM")
                    self._check_idle_notification(tmux, target, session_logger, pm_notifications)
                    self._idle_notifications[target] = datetime.now()

        except Exception as e:
            # Use the main logger if session logger is not available
            try:
                session_logger.error(f"Failed to check agent {target}: {e}")
            except NameError:
                logger.error(f"Failed to check agent {target}: {e}")

    def capture_snapshots(self, tmux: TMUXManager, target: str, count: int, interval: float) -> list[str]:
        """Capture multiple snapshots of terminal content."""
        snapshots = []
        for i in range(count):
            content = tmux.capture_pane(target, lines=50)
            snapshots.append(content)
            if i < count - 1:
                time.sleep(interval)
        return snapshots

    def try_auto_submit(self, tmux: TMUXManager, target: str, logger: logging.Logger) -> None:
        """Try auto-submitting stuck messages with cooldown.

        CRITICAL: Never auto-submit on fresh Claude instances to prevent breaking them.
        """
        current_time = time.time()
        last_attempt = self._last_submission_time.get(target, 0)

        # Check if we've already tried too many times
        attempts = self._submission_attempts.get(target, 0)
        if attempts >= 5:
            logger.debug(f"Skipping auto-submit for {target} - already tried {attempts} times")
            return

        if current_time - last_attempt >= 10:  # 10 second cooldown
            # SAFETY CHECK: Verify this isn't a fresh Claude instance before submitting
            content = tmux.capture_pane(target, lines=50)
            claude_state = detect_claude_state(content)

            if claude_state == "fresh":
                logger.warning(f"PREVENTED auto-submit on fresh Claude instance at {target}")
                return

            logger.info(f"Auto-submitting stuck message for {target} (attempt #{attempts + 1})")

            # Try different submission methods
            if attempts == 0:
                # First try: Just Enter (Claude Code submits with Enter, not Ctrl+Enter)
                tmux.press_enter(target)
            elif attempts == 1:
                # Second try: Move to end of line then Enter
                tmux.press_ctrl_e(target)
                time.sleep(0.1)
                tmux.press_enter(target)
            elif attempts == 2:
                # Third try: Escape (to exit any mode) then Enter
                tmux.press_escape(target)
                time.sleep(0.1)
                tmux.press_enter(target)
            else:
                # Later attempts: Just Enter
                tmux.press_enter(target)

            self._submission_attempts[target] = attempts + 1
            self._last_submission_time[target] = current_time

    def attempt_agent_restart(self, tmux: TMUXManager, target: str, logger: logging.Logger) -> bool:
        """Detect agent failure and notify PM with one-command restart solution."""
        try:
            # Get restart cooldown tracking
            restart_key = f"restart_{target}"
            now = datetime.now()

            # Check cooldown (5 minutes between notifications)
            if hasattr(self, "_restart_attempts"):
                last_restart = self._restart_attempts.get(restart_key)
                if last_restart and (now - last_restart) < timedelta(minutes=5):
                    logger.debug(f"Restart notification for {target} in cooldown")
                    return False
            else:
                self._restart_attempts = {}

            # Step 1: Detect API error patterns and failure type
            current_content = tmux.capture_pane(target, lines=50)
            api_error_detected = self._detect_api_error_patterns(current_content)

            if api_error_detected:
                error_type = self._identify_error_type(current_content)
                logger.info(f"API error detected for {target}: {error_type}. Notifying PM with one-command fix.")
                failure_reason = f"API error ({error_type})"
            else:
                logger.info(f"Agent failure detected for {target}. Notifying PM with one-command fix.")
                failure_reason = "Agent crash/failure"

            # Step 2: Kill the crashed window to clean up resources
            try:
                logger.warning(f"🔪 WINDOW KILL: HealthChecker killing crashed agent window: {target}")
                logger.warning("🔪 KILL REASON: Crashed agent cleanup before PM notification")
                logger.warning("🔪 CALL STACK: HealthChecker.handle_crashed_agent() -> tmux.kill_window()")
                logger.info(f"Killing crashed window {target} before notifying PM")
                tmux.kill_window(target)
                logger.info(f"Successfully killed crashed window {target}")
            except Exception as kill_error:
                logger.error(f"Failed to kill crashed window {target}: {kill_error}")
                # Continue with notification even if kill fails

            # Step 3: Send PM notification with ready-to-copy-paste command
            self._send_simple_restart_notification(tmux, target, failure_reason, logger)

            # Track notification time
            self._restart_attempts[restart_key] = now

            return True

        except Exception as e:
            logger.error(f"Error attempting to restart agent {target}: {e}")
            return False

    def _reset_agent_tracking(self, target: str) -> None:
        """Reset tracking for active agents."""
        if target in self._idle_agents:
            del self._idle_agents[target]
        if target in self._submission_attempts:
            self._submission_attempts[target] = 0
        if target in self._last_submission_time:
            del self._last_submission_time[target]
        # Reset terminal cache when agent becomes active (fresh start)
        if target in self._terminal_caches:
            del self._terminal_caches[target]

    def _detect_idle_type(self, target: str, current_content: str, logger: logging.Logger) -> str:
        """Detect if agent is newly idle (just finished work) or continuously idle.

        Uses TerminalCache class for efficient change detection to distinguish between:
        - newly_idle: Agent just completed work and became idle (notify immediately)
        - continuously_idle: Agent has been idle with no activity (use cooldown)

        Args:
            target: Agent target identifier
            current_content: Current terminal content
            logger: Logger instance

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
            if target not in self._terminal_caches:
                self._terminal_caches[target] = TerminalCache()
                logger.debug(f"Created new terminal cache for {target}")

            cache = self._terminal_caches[target]

            # Update cache with current content
            cache.update(current_sample)

            # Get intelligent status from cache
            status = cache.status
            logger.debug(f"Terminal cache status for {target}: {status}")

            return status

        except Exception as e:
            logger.error(f"Error in idle type detection for {target}: {e}")
            # Fallback to unknown on error
            return "unknown"

    def _detect_api_error_patterns(self, content: str) -> bool:
        """Detect API error patterns in terminal content."""
        error_patterns = [
            "api key",
            "unauthorized",
            "401",
            "403",
            "rate limit",
            "quota exceeded",
            "connection failed",
            "timeout",
            "network error",
            "service unavailable",
            "502",
            "503",
        ]

        content_lower = content.lower()
        return any(pattern in content_lower for pattern in error_patterns)

    def _identify_error_type(self, content: str) -> str:
        """Identify the specific type of error from content."""
        content_lower = content.lower()

        if "api key" in content_lower or "unauthorized" in content_lower or "401" in content_lower:
            return "Authentication Error"
        elif "rate limit" in content_lower or "quota exceeded" in content_lower:
            return "Rate Limit"
        elif "timeout" in content_lower or "connection failed" in content_lower:
            return "Network Timeout"
        elif "503" in content_lower or "service unavailable" in content_lower:
            return "Service Unavailable"
        else:
            return "Unknown Error"

    def _get_session_logger(self, session_name: str) -> logging.Logger:
        """Get or create session-specific logger."""
        logger = logging.getLogger(f"monitor.{session_name}")
        return logger

    # Placeholder methods that will need to be connected to notification system
    def _notify_crash(
        self, tmux: TMUXManager, target: str, logger: logging.Logger, pm_notifications: dict[str, list[str]]
    ) -> None:
        """Placeholder for crash notification."""
        pass

    def _notify_recovery_needed(self, tmux: TMUXManager, target: str, logger: logging.Logger) -> None:
        """Placeholder for recovery notification."""
        pass

    def _notify_fresh_agent(
        self, tmux: TMUXManager, target: str, logger: logging.Logger, pm_notifications: dict[str, list[str]]
    ) -> None:
        """Placeholder for fresh agent notification."""
        pass

    def _check_idle_notification(
        self, tmux: TMUXManager, target: str, logger: logging.Logger, pm_notifications: dict[str, list[str]]
    ) -> None:
        """Placeholder for idle notification."""
        pass

    def _send_simple_restart_notification(
        self, tmux: TMUXManager, target: str, failure_reason: str, logger: logging.Logger
    ) -> None:
        """Placeholder for restart notification."""
        pass

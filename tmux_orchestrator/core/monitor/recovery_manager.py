"""Recovery management functionality for handling PM and agent failures."""

import logging
import time
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from tmux_orchestrator.utils.tmux import TMUXManager

if TYPE_CHECKING:
    from tmux_orchestrator.core.monitor.agent_discovery import AgentDiscovery
    from tmux_orchestrator.core.monitor_helpers import is_claude_interface_present


class RecoveryManager:
    """Handles recovery operations for crashed or failed agents and project managers."""

    def __init__(self, grace_period_minutes: int = 3, recovery_cooldown_minutes: int = 5) -> None:
        """Initialize the recovery manager.

        Args:
            grace_period_minutes: Grace period after PM recovery before health checks resume
            recovery_cooldown_minutes: Cooldown between recovery attempts
        """
        self._grace_period_minutes = grace_period_minutes
        self._recovery_cooldown_minutes = recovery_cooldown_minutes
        self._pm_recovery_timestamps: dict[str, datetime] = {}
        self._last_recovery_attempt: dict[str, datetime] = {}

    def check_pm_recovery(
        self, tmux: TMUXManager, agents: list[str], agent_discovery: "AgentDiscovery", logger: logging.Logger
    ) -> None:
        """Check if PM needs to be auto-spawned when other agents exist but PM is missing or unhealthy."""
        try:
            # Skip if no agents exist
            if not agents:
                return

            # Group agents by session to focus recovery
            session_counts: dict[str, int] = {}
            for agent in agents:
                session_name = agent.split(":")[0]
                session_counts[session_name] = session_counts.get(session_name, 0) + 1

            # Check each session with agents for PM health
            for session_name, agent_count in session_counts.items():
                session_logger = self._get_session_logger(session_name)
                session_logger.debug(f"🔍 Checking PM health in session {session_name} with {agent_count} agents")

                # Check if any PM in this session is in grace period
                pm_in_grace_period = False
                for pm_target_key, recovery_time in list(self._pm_recovery_timestamps.items()):
                    if pm_target_key.startswith(session_name + ":"):
                        time_since_recovery = datetime.now() - recovery_time
                        if time_since_recovery < timedelta(minutes=self._grace_period_minutes):
                            session_logger.debug(
                                f"PM {pm_target_key} in grace period ({time_since_recovery.total_seconds():.0f}s since recovery)"
                            )
                            pm_in_grace_period = True
                            break
                        else:
                            # Grace period expired, remove from tracking
                            del self._pm_recovery_timestamps[pm_target_key]
                            session_logger.debug(f"Grace period expired for PM {pm_target_key}")

                # Skip health checks if PM is in grace period
                if pm_in_grace_period:
                    session_logger.debug(f"Skipping PM health check for session {session_name} - in grace period")
                    continue

                # Use the crash detection method
                crashed, pm_target = self.detect_pm_crash(tmux, session_name, session_logger)

                if not crashed:
                    session_logger.debug(f"✅ PM in session {session_name} is healthy, no recovery needed")
                    continue

                # PM has crashed or is missing - trigger recovery
                session_logger.warning(f"🚨 PM crash detected in session {session_name}")

                # Log detailed recovery context with timestamps
                session_logger.info("🔧 Initiating PM recovery process:")
                session_logger.info(f"   - Crashed PM target: {pm_target or 'Missing entirely'}")
                session_logger.info(f"   - Active agents requiring coordination: {agent_count}")
                session_logger.info("   - Recovery mode: Automatic with enhanced retry logic")
                session_logger.info(f"   - Recovery initiated at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info(f"Session has {agent_count} agents that need a PM")

                # Check recovery cooldown to prevent rapid recovery loops
                if session_name in self._last_recovery_attempt:
                    time_since_last_attempt = datetime.now() - self._last_recovery_attempt[session_name]
                    cooldown_period = timedelta(minutes=self._recovery_cooldown_minutes)

                    if time_since_last_attempt < cooldown_period:
                        remaining_cooldown = cooldown_period - time_since_last_attempt
                        logger.warning(
                            f"Recovery cooldown active for session {session_name}. "
                            f"Waiting {remaining_cooldown.total_seconds():.0f}s before next attempt."
                        )
                        return

                # Record this recovery attempt
                self._last_recovery_attempt[session_name] = datetime.now()

                # Use the recovery orchestration method
                recovery_success = self.recover_crashed_pm(
                    tmux=tmux,
                    session_name=session_name,
                    crashed_pm_target=pm_target,
                    agent_discovery=agent_discovery,
                    logger=session_logger,
                    max_retries=3,
                    retry_delay=2,
                )

                if recovery_success:
                    session_logger.info(f"🎉 Successfully recovered PM for session {session_name}")
                    session_logger.info("📈 Recovery metrics:")
                    session_logger.info(f"   - Session agents preserved: {agent_count}")
                    session_logger.info("   - Recovery process completed successfully")
                    session_logger.info("   - PM is healthy and ready for coordination")
                else:
                    logger.error(f"Failed to recover PM for session {session_name} - manual intervention required")

        except Exception as e:
            logger.error(f"Failed to auto-spawn PM: {e}")

    def recover_crashed_pm(
        self,
        tmux: TMUXManager,
        session_name: str,
        crashed_pm_target: str | None,
        agent_discovery: "AgentDiscovery",
        logger: logging.Logger,
        max_retries: int = 3,
        retry_delay: int = 2,
    ) -> bool:
        """Orchestrate PM recovery with retries and comprehensive error handling.

        Args:
            tmux: TMUXManager instance
            session_name: Session where PM crashed
            crashed_pm_target: Target of crashed PM window (if exists)
            agent_discovery: Agent discovery instance for finding active agents
            logger: Logger instance
            max_retries: Maximum recovery attempts
            retry_delay: Delay between retries in seconds

        Returns:
            bool: True if recovery successful, False otherwise
        """
        logger.info(f"Starting PM recovery for session {session_name}")
        logger.info(f"Crashed PM target: {crashed_pm_target or 'None (missing entirely)'}")

        # Step 1: Clean up crashed PM if it exists
        if crashed_pm_target:
            logger.info(f"Cleaning up crashed PM at {crashed_pm_target}")
            try:
                logger.warning(
                    f"🔪 WINDOW KILL: RecoveryManager.recover_pm() killing crashed PM window: {crashed_pm_target}"
                )
                logger.warning("🔪 KILL REASON: Crashed PM cleanup in recovery process")
                logger.warning("🔪 CALL STACK: RecoveryManager.recover_pm() -> tmux.kill_window()")
                tmux.kill_window(crashed_pm_target)
                logger.info(f"Successfully killed crashed PM window {crashed_pm_target}")
                time.sleep(1)  # Allow cleanup to complete
            except Exception as e:
                logger.error(f"Failed to kill crashed PM: {e}")
                # Continue with recovery attempt anyway

        # Step 2: Find suitable window index for new PM
        try:
            windows = tmux.list_windows(session_name)
            used_indices = {int(w["index"]) for w in windows}
            new_window_index = 1
            while new_window_index in used_indices:
                new_window_index += 1
            logger.info(f"Selected window index {new_window_index} for new PM")
        except Exception as e:
            logger.error(f"Failed to find suitable window index: {e}")
            return False

        # Step 3: Attempt recovery with enhanced retry logic and progressive delays
        progressive_delays = [2, 5, 10]  # Progressive backoff

        for attempt in range(1, max_retries + 1):
            logger.info(f"PM recovery attempt {attempt}/{max_retries}")

            try:
                # Get active agents for context with enhanced session analysis
                agents = agent_discovery.discover_agents(tmux)
                session_agents = [a for a in agents if a.startswith(f"{session_name}:")]

                # Enhanced recovery context with more detail
                recovery_context = f"""🔄 PM RECOVERY NOTIFICATION:
You are being spawned as the Project Manager after a PM failure was detected and resolved.

📊 SESSION STATUS:
- Session: {session_name}
- Active agents in session: {len(session_agents)}
- Agent targets: {", ".join(session_agents) if session_agents else "None"}
- Recovery attempt: {attempt}/{max_retries}

🎯 YOUR MISSION:
1. Verify the status of all active agents in this session
2. Check for any pending tasks or blockers
3. Resume project coordination and maintain team momentum
4. Report any issues that need immediate attention

The monitoring daemon has automatically handled the technical recovery.
Please focus on project continuity and team coordination."""

                # Spawn new PM with better error handling
                pm_target = self.spawn_pm(tmux, session_name, new_window_index, logger, recovery_context)

                if pm_target:
                    logger.info(f"PM spawned at {pm_target}, verifying health...")

                    # Give PM extra time to fully initialize before health checks
                    init_wait = min(5 + (attempt - 1) * 2, 12)  # 5s to 12s based on attempt
                    logger.info(f"Waiting {init_wait}s for PM initialization...")
                    time.sleep(init_wait)

                    # Single health check with internal retry logic (more efficient)
                    health_verified = self.check_pm_health(tmux, pm_target, logger, retry_for_new_pm=True)

                    if health_verified:
                        logger.info(f"✅ PM recovery SUCCESSFUL at {pm_target} after {attempt} attempts")

                        # Record recovery timestamp for grace period
                        self._pm_recovery_timestamps[pm_target] = datetime.now()
                        logger.info(f"PM {pm_target} entered {self._grace_period_minutes}-minute grace period")

                        # Enhanced team notification
                        try:
                            self.notify_team_of_pm_recovery(session_name, pm_target)
                            logger.info(f"Team notification sent for recovered PM at {pm_target}")
                        except Exception as notify_error:
                            logger.warning(f"Team notification failed: {notify_error}")

                        return True

                    else:
                        logger.warning(f"PM health verification failed for {pm_target} (attempt {attempt})")
                        # Kill unhealthy PM before retry
                        try:
                            logger.warning(
                                f"🔪 WINDOW KILL: RecoveryManager PM health check killing unhealthy PM: {pm_target}"
                            )
                            logger.warning(f"🔪 KILL REASON: PM health verification failed, retry attempt {attempt}")
                            logger.warning(
                                "🔪 CALL STACK: RecoveryManager.recover_pm() -> health check retry -> tmux.kill_window()"
                            )
                            tmux.kill_window(pm_target)
                            logger.info(f"Killed unhealthy PM {pm_target} before retry")
                        except Exception as kill_error:
                            logger.error(f"Failed to kill unhealthy PM: {kill_error}")

                else:
                    logger.error(f"Failed to spawn PM in attempt {attempt}")

                # Progressive delay before retry
                if attempt < max_retries:
                    delay_index = min(attempt - 1, len(progressive_delays) - 1)
                    delay = progressive_delays[delay_index]
                    logger.info(f"Waiting {delay}s before retry...")
                    time.sleep(delay)

            except Exception as e:
                logger.error(f"PM recovery attempt {attempt} failed with exception: {e}")
                if attempt < max_retries:
                    delay_index = min(attempt - 1, len(progressive_delays) - 1)
                    delay = progressive_delays[delay_index]
                    time.sleep(delay)

        logger.error(f"All {max_retries} PM recovery attempts failed for session {session_name}")
        return False

    def detect_pm_crash(self, tmux: TMUXManager, session_name: str, logger: logging.Logger) -> tuple[bool, str | None]:
        """Detect if PM has crashed in the given session.

        Args:
            tmux: TMUXManager instance
            session_name: Session name to check
            logger: Logger instance

        Returns:
            tuple[bool, str | None]: (crashed, pm_target) - crashed is True if PM crashed,
                                   pm_target is the target if found (may be None)
        """
        try:
            # Find PM window in session
            pm_target = self.find_pm_in_session(tmux, session_name)

            if not pm_target:
                logger.debug(f"No PM found in session {session_name}")
                return True, None  # No PM = needs recovery

            # Check PM health
            is_healthy = self.check_pm_health(tmux, pm_target, logger)

            if not is_healthy:
                logger.warning(f"PM {pm_target} failed health check")
                return True, pm_target

            return False, pm_target

        except Exception as e:
            logger.error(f"Error detecting PM crash in session {session_name}: {e}")
            return True, None  # Assume crashed on error

    def find_pm_in_session(self, tmux: TMUXManager, session: str) -> str | None:
        """Find PM agent in a specific session.

        Args:
            tmux: TMUXManager instance
            session: Session name

        Returns:
            str | None: PM target if found, None otherwise
        """
        try:
            windows = tmux.list_windows(session)
            for window in windows:
                target = f"{session}:{window.get('index', '0')}"
                if self.is_pm_agent(tmux, target):
                    return target
        except Exception:
            pass
        return None

    def is_pm_agent(self, tmux: TMUXManager, target: str) -> bool:
        """Check if the target is a PM agent.

        Args:
            tmux: TMUXManager instance
            target: Target identifier

        Returns:
            bool: True if target is a PM agent
        """
        try:
            session_name, window_idx = target.split(":")
            windows = tmux.list_windows(session_name)

            for window in windows:
                if str(window.get("index", "")) == str(window_idx):
                    window_name = window.get("name", "").lower()
                    # Check for PM indicators
                    if "pm" in window_name or "project-manager" in window_name or "manager" in window_name:
                        return True
                    # Check for Claude-PM pattern
                    if window_name.startswith("claude-pm") or "claude-project-manager" in window_name:
                        return True
        except Exception:
            pass
        return False

    def check_pm_health(
        self, tmux: TMUXManager, pm_target: str, logger: logging.Logger, retry_for_new_pm: bool = False
    ) -> bool:
        """Check if PM is healthy and responsive.

        Args:
            tmux: TMUXManager instance
            pm_target: PM target identifier
            logger: Logger instance
            retry_for_new_pm: Whether this is checking a newly spawned PM

        Returns:
            bool: True if PM is healthy, False otherwise
        """
        try:
            # Capture PM terminal content
            content = tmux.capture_pane(pm_target, lines=50)

            # Basic health checks
            if not content or len(content.strip()) < 10:
                logger.debug(f"PM {pm_target} has insufficient content")
                return False

            # Check for crash indicators
            crash_indicators = ["command not found", "bash:", "zsh:", "$", "#"]
            content_lower = content.lower()

            for indicator in crash_indicators:
                if indicator in content_lower:
                    logger.debug(f"PM {pm_target} shows crash indicator: {indicator}")
                    return False

            # Check for Claude interface presence

            if not is_claude_interface_present(content):
                logger.debug(f"PM {pm_target} lacks Claude interface")
                return False

            return True

        except Exception as e:
            logger.error(f"Error checking PM health for {pm_target}: {e}")
            return False

    # Placeholder methods that need to be implemented or connected
    def spawn_pm(
        self, tmux: TMUXManager, session_name: str, window_index: int, logger: logging.Logger, recovery_context: str
    ) -> str | None:
        """Placeholder for PM spawning functionality."""
        # This would need to be implemented or connected to the actual spawning logic
        logger.info(f"Spawning PM in session {session_name} at window {window_index}")
        return None

    def notify_team_of_pm_recovery(self, session_name: str, pm_target: str) -> None:
        """Placeholder for team notification functionality."""
        pass

    def _get_session_logger(self, session_name: str) -> logging.Logger:
        """Get or create session-specific logger."""
        logger = logging.getLogger(f"recovery.{session_name}")
        return logger

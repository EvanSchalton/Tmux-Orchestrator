"""
PM Recovery Manager for handling Project Manager crashes and recovery.

This module extracts PM-specific recovery logic from the monolithic monitor.py,
providing a focused component for PM health monitoring and recovery actions.
"""

import logging
import time
from datetime import datetime, timedelta
from pathlib import Path

from tmux_orchestrator.core.config import Config
from tmux_orchestrator.utils.tmux import TMUXManager

from .crash_detector import CrashDetector
from .interfaces import CrashDetectorInterface, PMRecoveryManagerInterface


class PMRecoveryState:
    """Track PM recovery state and history."""

    def __init__(self):
        self.recovery_attempts: dict[str, list[datetime]] = {}
        self.recovery_in_progress: dict[str, datetime] = {}
        self.last_recovery: dict[str, datetime] = {}
        self.recovery_grace_period = timedelta(minutes=3)  # 3-minute grace after recovery
        self.recovery_cooldown = timedelta(minutes=5)  # 5-minute cooldown between attempts


class PMRecoveryManager(PMRecoveryManagerInterface):
    """Manages PM crash detection and recovery operations."""

    def __init__(
        self,
        tmux: TMUXManager,
        config: Config,
        logger: logging.Logger,
        crash_detector: CrashDetectorInterface | None = None,
    ):
        """Initialize PM Recovery Manager.

        Args:
            tmux: TMux manager instance
            config: Configuration object
            logger: Logger instance
            crash_detector: Optional crash detector instance (will create if not provided)
        """
        self.tmux = tmux
        self.config = config
        self.logger = logger
        self.crash_detector = crash_detector or CrashDetector(tmux, logger)
        self.recovery_state = PMRecoveryState()

        # Recovery configuration
        self.max_recovery_attempts = 3
        self.recovery_window = timedelta(hours=1)

        # Progressive delay configuration for recovery retries
        self.base_recovery_delay = 2  # seconds
        self.max_recovery_delay = 10  # seconds

        # File paths for state persistence
        self.recovery_state_dir = config.orchestrator_base_dir / "recovery"
        self.recovery_state_dir.mkdir(parents=True, exist_ok=True)

    def initialize(self) -> bool:
        """Initialize the PM recovery manager.

        Returns:
            True if initialization successful
        """
        try:
            # Resume any incomplete recoveries
            self._resume_incomplete_recoveries()
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize PM Recovery Manager: {e}")
            return False

    def cleanup(self) -> None:
        """Clean up resources."""
        # Clear in-memory state
        self.recovery_state = PMRecoveryState()

    def check_pm_health(self, session_name: str) -> tuple[bool, str | None, str | None]:
        """Check PM health in a session with grace period protection.

        Args:
            session_name: Session to check

        Returns:
            Tuple of (is_healthy, pm_target, issue_description)
        """
        try:
            # Check if PM is in recovery grace period
            if self._is_in_grace_period(session_name):
                self.logger.debug(f"PM in session {session_name} is in grace period - skipping health check")
                return (True, None, None)

            # Use crash detector to check PM health
            crashed, pm_target = self.crash_detector.detect_pm_crash(session_name)

            if crashed:
                issue = "PM crashed" if pm_target else "PM missing"
                return (False, pm_target, issue)
            else:
                return (True, pm_target, None)

        except Exception as e:
            self.logger.error(f"Error checking PM health in {session_name}: {e}")
            return (False, None, f"Health check error: {e}")

    def should_attempt_recovery(self, session_name: str) -> bool:
        """Determine if recovery should be attempted for a session.

        Args:
            session_name: Session to check

        Returns:
            True if recovery should be attempted
        """
        # Check if already recovering
        if session_name in self.recovery_state.recovery_in_progress:
            self.logger.info(f"Recovery already in progress for {session_name}")
            return False

        # Check cooldown period
        if session_name in self.recovery_state.last_recovery:
            time_since_recovery = datetime.now() - self.recovery_state.last_recovery[session_name]
            if time_since_recovery < self.recovery_state.recovery_cooldown:
                remaining = self.recovery_state.recovery_cooldown - time_since_recovery
                self.logger.info(
                    f"Recovery cooldown active for {session_name} ({remaining.total_seconds():.0f}s remaining)"
                )
                return False

        # Check recovery attempt limits
        attempts = self._get_recent_recovery_attempts(session_name)
        if len(attempts) >= self.max_recovery_attempts:
            self.logger.error(f"Max recovery attempts ({self.max_recovery_attempts}) reached for {session_name}")
            return False

        return True

    def recover_pm(self, session_name: str, crashed_target: str | None = None) -> bool:
        """Recover a crashed or missing PM.

        Args:
            session_name: Session needing PM recovery
            crashed_target: Target of crashed PM (if known)

        Returns:
            True if recovery successful
        """
        try:
            self.logger.info(f"Starting PM recovery for session {session_name}")

            # Mark recovery in progress
            self.recovery_state.recovery_in_progress[session_name] = datetime.now()
            self._record_recovery_attempt(session_name)

            # Write recovery state file for persistence
            state_file = self._write_recovery_state(session_name, crashed_target)

            # Calculate recovery delay based on attempt count
            attempts = len(self._get_recent_recovery_attempts(session_name))
            delay = min(self.base_recovery_delay * attempts, self.max_recovery_delay)

            self.logger.info(f"Waiting {delay}s before spawning PM (attempt {attempts})")
            time.sleep(delay)

            # Spawn new PM
            success = self._spawn_replacement_pm(session_name, crashed_target)

            if success:
                # Update recovery state
                self.recovery_state.last_recovery[session_name] = datetime.now()
                del self.recovery_state.recovery_in_progress[session_name]

                # Notify team of recovery
                self._notify_team_of_recovery(session_name)

                # Clean up state file
                if state_file.exists():
                    state_file.unlink()

                self.logger.info(f"PM recovery successful for session {session_name}")
                return True
            else:
                self.logger.error(f"PM recovery failed for session {session_name}")
                del self.recovery_state.recovery_in_progress[session_name]
                return False

        except Exception as e:
            self.logger.error(f"Error during PM recovery for {session_name}: {e}")
            if session_name in self.recovery_state.recovery_in_progress:
                del self.recovery_state.recovery_in_progress[session_name]
            return False

    def _is_in_grace_period(self, session_name: str) -> bool:
        """Check if PM is in post-recovery grace period.

        Args:
            session_name: Session to check

        Returns:
            True if in grace period
        """
        if session_name not in self.recovery_state.last_recovery:
            return False

        time_since_recovery = datetime.now() - self.recovery_state.last_recovery[session_name]
        return time_since_recovery < self.recovery_state.recovery_grace_period

    def _get_recent_recovery_attempts(self, session_name: str) -> list[datetime]:
        """Get recent recovery attempts within the recovery window.

        Args:
            session_name: Session to check

        Returns:
            List of recent recovery attempt timestamps
        """
        if session_name not in self.recovery_state.recovery_attempts:
            return []

        current_time = datetime.now()
        recent_attempts = [
            attempt
            for attempt in self.recovery_state.recovery_attempts[session_name]
            if current_time - attempt < self.recovery_window
        ]

        # Update the list to only keep recent attempts
        self.recovery_state.recovery_attempts[session_name] = recent_attempts
        return recent_attempts

    def _record_recovery_attempt(self, session_name: str) -> None:
        """Record a recovery attempt for tracking.

        Args:
            session_name: Session being recovered
        """
        if session_name not in self.recovery_state.recovery_attempts:
            self.recovery_state.recovery_attempts[session_name] = []

        self.recovery_state.recovery_attempts[session_name].append(datetime.now())

    def _write_recovery_state(self, session_name: str, crashed_target: str | None) -> Path:
        """Write recovery state to disk for persistence.

        Args:
            session_name: Session being recovered
            crashed_target: Target of crashed PM

        Returns:
            Path to state file
        """
        state_file = self.recovery_state_dir / f"pm_recovery_{session_name}.json"

        state_data = {
            "session": session_name,
            "crashed_target": crashed_target,
            "start_time": datetime.now().isoformat(),
            "attempts": len(self._get_recent_recovery_attempts(session_name)),
        }

        import json

        state_file.write_text(json.dumps(state_data, indent=2))
        return state_file

    def _spawn_replacement_pm(self, session_name: str, crashed_target: str | None) -> bool:
        """Spawn a replacement PM for the session.

        Args:
            session_name: Session needing PM
            crashed_target: Target of crashed PM (for cleanup)

        Returns:
            True if PM spawned successfully
        """
        try:
            # Determine window index for new PM
            window_idx = 0  # Default to window 0
            if crashed_target and ":" in crashed_target:
                try:
                    window_idx = int(crashed_target.split(":")[1])
                except ValueError:
                    pass

            target = f"{session_name}:{window_idx}"

            # Check if window exists
            try:
                windows = self.tmux.list_windows(session_name)
                window_exists = any(w.get("index") == str(window_idx) for w in windows)

                if not window_exists:
                    # Create window first
                    self.tmux.run(f"new-window -t '{session_name}:{window_idx}' -n 'pm'")
                    time.sleep(0.5)
            except Exception as e:
                self.logger.warning(f"Error checking/creating window: {e}")

            # Spawn PM using tmux-orc CLI
            from tmux_orchestrator.cli.spawn_orc import run_spawn_command

            # Create spawn arguments
            spawn_args = {
                "agent_type": "pm",
                "session": target,
                "briefing": None,
                "extend": f"Recovery: PM crashed in session {session_name}. Resume coordination of ongoing work.",
                "model": self.config.default_model or "claude-3-5-sonnet-20241022",
                "attach": False,
                "api_key": self.config.api_key,
                "base_url": self.config.base_url,
            }

            success = run_spawn_command(**spawn_args)

            if success:
                self.logger.info(f"Successfully spawned replacement PM at {target}")
                return True
            else:
                self.logger.error(f"Failed to spawn replacement PM at {target}")
                return False

        except Exception as e:
            self.logger.error(f"Error spawning replacement PM: {e}")
            return False

    def _notify_team_of_recovery(self, session_name: str) -> None:
        """Notify team agents about PM recovery.

        Args:
            session_name: Session where PM was recovered
        """
        try:
            message = f"PM Recovery: A new Project Manager has been spawned in session {session_name}. The PM will resume coordination shortly."

            # Find all agents in session
            windows = self.tmux.list_windows(session_name)
            for window in windows:
                window_idx = window.get("index", "0")
                window_name = window.get("name", "").lower()

                # Skip PM window
                if "pm" in window_name or window_idx == "0":
                    continue

                target = f"{session_name}:{window_idx}"

                try:
                    # Send notification
                    self.tmux.send_keys(target, message)
                    self.tmux.send_keys(target, "Enter")
                    self.logger.debug(f"Notified agent at {target} about PM recovery")
                except Exception as e:
                    self.logger.warning(f"Failed to notify agent at {target}: {e}")

        except Exception as e:
            self.logger.error(f"Error notifying team of PM recovery: {e}")

    def _resume_incomplete_recoveries(self) -> None:
        """Resume any incomplete PM recoveries from previous daemon runs."""
        try:
            if not self.recovery_state_dir.exists():
                return

            import json

            for state_file in self.recovery_state_dir.glob("pm_recovery_*.json"):
                try:
                    state_data = json.loads(state_file.read_text())
                    session_name = state_data.get("session")

                    if not session_name:
                        continue

                    # Check if recovery is still needed
                    is_healthy, pm_target, issue = self.check_pm_health(session_name)

                    if not is_healthy:
                        self.logger.info(f"Resuming incomplete PM recovery for {session_name}")
                        self.recover_pm(session_name, state_data.get("crashed_target"))
                    else:
                        # Clean up stale state file
                        state_file.unlink()

                except Exception as e:
                    self.logger.error(f"Error processing recovery state file {state_file}: {e}")

        except Exception as e:
            self.logger.error(f"Error resuming incomplete recoveries: {e}")

    def get_recovery_status(self) -> dict[str, any]:
        """Get current recovery status information.

        Returns:
            Dictionary with recovery status details
        """
        return {
            "in_progress": list(self.recovery_state.recovery_in_progress.keys()),
            "recent_recoveries": {
                session: recovery_time.isoformat()
                for session, recovery_time in self.recovery_state.last_recovery.items()
            },
            "attempt_counts": {
                session: len(self._get_recent_recovery_attempts(session))
                for session in self.recovery_state.recovery_attempts.keys()
            },
        }

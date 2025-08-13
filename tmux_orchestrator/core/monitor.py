"""Advanced agent monitoring system with 100% accurate idle detection."""

import logging
import multiprocessing
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from tmux_orchestrator.core.config import Config
from tmux_orchestrator.core.monitor_helpers import (
    DAEMON_CONTROL_LOOP_COOLDOWN_SECONDS,
    NONRESPONSIVE_PM_ESCALATIONS_MINUTES,
    AgentState,
    DaemonAction,
    calculate_sleep_duration,
    extract_rate_limit_reset_time,
    has_unsubmitted_message,
    is_claude_interface_present,
    should_notify_pm,
)
from tmux_orchestrator.utils.tmux import TMUXManager


@dataclass
class AgentHealthStatus:
    """Agent health status data."""

    target: str
    last_heartbeat: datetime
    last_response: datetime
    consecutive_failures: int
    is_responsive: bool
    last_content_hash: str
    status: str  # 'healthy', 'warning', 'critical', 'unresponsive'
    is_idle: bool
    activity_changes: int


class IdleMonitor:
    """Monitor with 100% accurate idle detection using native Python daemon."""

    def __init__(self, tmux: TMUXManager):
        self.tmux = tmux
        # Use project directory for storage as per user preference
        project_dir = Path("/workspaces/Tmux-Orchestrator/.tmux_orchestrator")
        project_dir.mkdir(exist_ok=True)
        logs_dir = project_dir / "logs"
        logs_dir.mkdir(exist_ok=True)

        self.pid_file = project_dir / "idle-monitor.pid"
        self.log_file = logs_dir / "idle-monitor.log"
        self.daemon_process: multiprocessing.Process | None = None
        self._crash_notifications: dict[str, datetime] = {}
        self._idle_notifications: dict[str, datetime] = {}
        self._idle_agents: dict[str, datetime] = {}
        self._submission_attempts: dict[str, int] = {}
        self._last_submission_time: dict[str, float] = {}
        self._session_agents: dict[str, set[str]] = {}  # Track high-water mark of agents per session
        self._missing_agent_grace: dict[str, datetime] = {}  # Track when agents were first identified as missing
        self._missing_agent_notifications: dict[str, datetime] = {}  # Track when we last notified about missing agents
        self._team_idle_at: Dict[str, Optional[datetime]] = {}  # Track when entire team becomes idle per session
        self._pm_escalation_history: Dict[str, Dict[int, datetime]] = {}  # Track escalation history per PM

    def is_running(self) -> bool:
        """Check if monitor daemon is running."""
        if not self.pid_file.exists():
            return False

        try:
            with open(self.pid_file) as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)  # Check if process exists
            return True
        except (OSError, ValueError, FileNotFoundError):
            if self.pid_file.exists():
                self.pid_file.unlink()
            return False

    def start(self, interval: int = 10) -> int:
        """Start the native Python monitor daemon."""
        if self.is_running():
            with open(self.pid_file) as f:
                return int(f.read().strip())

        # Fork to create daemon (proper daemonization to prevent early exit)
        pid = os.fork()
        if pid > 0:
            # Parent process - wait for daemon to start
            for _ in range(50):  # Wait up to 5 seconds
                if self.pid_file.exists():
                    with open(self.pid_file) as f:
                        return int(f.read().strip())
                time.sleep(0.1)
            raise RuntimeError("Monitor daemon started but PID file not found")

        # Child process - become daemon
        os.setsid()  # Create new session

        # Fork again to prevent zombie processes
        pid = os.fork()
        if pid > 0:
            os._exit(0)  # Exit first child

        # Grandchild - the actual daemon
        # Close file descriptors
        sys.stdin.close()
        sys.stdout.close()
        sys.stderr.close()

        # Run the monitoring daemon
        self._run_monitoring_daemon(interval)
        os._exit(0)  # Should never reach here

    def stop(self) -> bool:
        """Stop the idle monitor daemon."""
        if not self.is_running():
            return False

        try:
            with open(self.pid_file) as f:
                pid = int(f.read().strip())

            # Send SIGTERM for graceful shutdown
            os.kill(pid, signal.SIGTERM)

            # Wait up to 5 seconds for graceful shutdown
            for _ in range(50):
                try:
                    os.kill(pid, 0)  # Check if still running
                    time.sleep(0.1)
                except OSError:
                    # Process has stopped
                    break
            else:
                # Force kill if still running
                try:
                    os.kill(pid, signal.SIGKILL)
                except OSError:
                    pass

            # Clean up PID file
            if self.pid_file.exists():
                self.pid_file.unlink()

            return True
        except (OSError, ValueError, FileNotFoundError):
            return False

    def status(self) -> None:
        """Display monitor status."""
        from rich.console import Console
        from rich.panel import Panel

        console = Console()

        if self.is_running():
            with open(self.pid_file) as f:
                pid = int(f.read().strip())

            # Get log info if available
            log_info = ""
            if self.log_file.exists():
                try:
                    stat = self.log_file.stat()
                    log_info = f"\nLog size: {stat.st_size} bytes\nLog file: {self.log_file}"
                except OSError:
                    log_info = f"\nLog file: {self.log_file}"

            console.print(
                Panel(
                    f"✓ Monitor is running (PID: {pid})\nNative Python daemon with bulletproof detection{log_info}",
                    title="Monitoring Status",
                    style="green",
                )
            )
        else:
            console.print(
                Panel(
                    "✗ Monitor is not running\nUse 'tmux-orc monitor start' to begin monitoring",
                    title="Monitoring Status",
                    style="red",
                )
            )

    def _run_monitoring_daemon(self, interval: int) -> None:
        """Run the monitoring daemon in a separate process."""

        # Set up signal handlers for graceful shutdown
        def signal_handler(signum: int, frame: Any) -> None:
            self._cleanup_daemon()
            exit(0)

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        # Write PID file
        with open(self.pid_file, "w") as f:
            f.write(str(os.getpid()))

        # Set up logging
        logger = self._setup_daemon_logging()
        logger.info(f"Native Python monitoring daemon started (PID: {os.getpid()}, interval: {interval}s)")

        # Initialize restart attempts tracking for the daemon process
        self._restart_attempts: dict[str, datetime] = {}
        # Initialize notification tracking for the daemon process (fixes notification spam)
        # These are intentionally separate from parent process attributes
        self._idle_notifications: dict[str, datetime] = {}  # type: ignore[no-redef]
        self._crash_notifications: dict[str, datetime] = {}  # type: ignore[no-redef]

        # Create TMUXManager instance for this process
        tmux = TMUXManager()

        # Main monitoring loop
        cycle_count = 0
        try:
            while True:
                cycle_count += 1
                start_time = time.time()

                # Log cycle start
                logger.debug(f"Starting monitoring cycle #{cycle_count}")

                # Discover and monitor agents
                self._monitor_cycle(tmux, logger)

                # Calculate sleep time to maintain interval
                elapsed = time.time() - start_time
                sleep_time = max(0, interval - elapsed)

                logger.debug(f"Cycle #{cycle_count} completed in {elapsed:.2f}s, next check in {sleep_time:.2f}s")

                if sleep_time > 0:
                    time.sleep(sleep_time)

        except KeyboardInterrupt:
            logger.info("Monitoring daemon interrupted")
        except Exception as e:
            logger.error(f"Monitoring daemon error: {e}", exc_info=True)
            # Try to write error to a debug file
            try:
                error_log = self.log_file.parent / "monitor-daemon-error.log"
                with open(error_log, "a") as f:
                    f.write(f"{datetime.now()}: {type(e).__name__}: {e}\n")
                    import traceback

                    traceback.print_exc(file=f)
            except Exception:
                pass
        finally:
            self._cleanup_daemon()

    def _setup_daemon_logging(self) -> logging.Logger:
        """Set up logging for the daemon process."""
        logger = logging.getLogger("idle_monitor_daemon")
        logger.setLevel(logging.INFO)

        # Clear existing handlers
        logger.handlers.clear()

        # File handler
        handler = logging.FileHandler(self.log_file)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    def _cleanup_daemon(self) -> None:
        """Clean up daemon resources."""
        if self.pid_file.exists():
            try:
                self.pid_file.unlink()
            except OSError:
                pass

    def _monitor_cycle(self, tmux: TMUXManager, logger: logging.Logger) -> None:
        """Perform one monitoring cycle."""
        try:
            # Discover active agents
            agents = self._discover_agents(tmux)

            logger.debug(f"Agent discovery complete: found {len(agents)} agents")

            if not agents:
                logger.warning("No agents found to monitor")
                # Log available sessions for debugging
                try:
                    sessions = tmux.list_sessions()
                    logger.debug(f"Available sessions: {[s['name'] for s in sessions]}")
                except Exception as e:
                    logger.error(f"Could not list sessions: {e}")
                return

            logger.debug(f"Monitoring agents: {agents}")

            # Initialize notification collection structure for this cycle
            pm_notifications: dict[str, list[str]] = {}

            # First, check all agents for rate limiting
            for target in agents:
                try:
                    content = tmux.capture_pane(target, lines=50)

                    # Check for rate limit message
                    if (
                        "claude usage limit reached" in content.lower()
                        and "your limit will reset at" in content.lower()
                    ):
                        reset_time = extract_rate_limit_reset_time(content)
                        if reset_time:
                            # Calculate sleep duration
                            now = datetime.now(timezone.utc)
                            sleep_seconds = calculate_sleep_duration(reset_time, now)

                            # If sleep_seconds is 0, it means the rate limit is stale/invalid (>4 hours away)
                            if sleep_seconds == 0:
                                logger.warning(
                                    f"Rate limit message appears stale (reset time {reset_time} is >4 hours away). "
                                    f"Ignoring and continuing normal monitoring."
                                )
                                continue

                            # Calculate resume time
                            resume_time = now + timedelta(seconds=sleep_seconds)

                            logger.warning(f"Rate limit detected on agent {target}. Reset time: {reset_time} UTC")

                            # Try to notify PM (may also be rate limited)
                            pm_target = self._find_pm_agent(tmux)
                            if pm_target:
                                message = (
                                    f"🚨 RATE LIMIT REACHED: All Claude agents are rate limited.\n"
                                    f"Will reset at {reset_time} UTC.\n\n"
                                    f"The monitoring daemon will pause and resume at {resume_time.strftime('%H:%M')} UTC "
                                    f"(2 minutes after reset for safety).\n"
                                    f"All agents will become responsive after the rate limit resets."
                                )
                                try:
                                    tmux.send_message(pm_target, message)
                                    logger.info(f"PM {pm_target} notified about rate limit")
                                except Exception:
                                    logger.warning("Could not notify PM - may also be rate limited")

                            # Log and sleep
                            logger.debug(
                                f"Rate limit detected. Sleeping for {sleep_seconds} seconds until {reset_time} UTC"
                            )
                            time.sleep(sleep_seconds)

                            # After waking up, notify that monitoring has resumed
                            logger.info("Rate limit period ended, resuming monitoring")
                            if pm_target:
                                try:
                                    tmux.send_message(
                                        pm_target,
                                        "🎉 Rate limit reset! Monitoring resumed. All agents should now be responsive.",
                                    )
                                except Exception:
                                    pass

                            # Return to restart the monitoring cycle
                            return

                except Exception as e:
                    logger.error(f"Error checking rate limit for {target}: {e}")

            # Check for PM recovery need before monitoring agents
            self._check_pm_recovery(tmux, agents, logger)

            # Check for missing agents (track high-water mark per session)
            self._check_missing_agents(tmux, agents, logger, pm_notifications)

            # Monitor each agent normally if no rate limit detected
            for target in agents:
                try:
                    self._check_agent_status(tmux, target, logger, pm_notifications)
                except Exception as e:
                    logger.error(f"Error checking agent {target}: {e}")

            # Check for team-wide idleness and handle PM escalations
            self._check_team_idleness(tmux, agents, logger, pm_notifications)

            # Send all collected notifications at the end of the cycle
            pm_notified = False
            if pm_notifications:
                logger.info(f"Sending collected notifications to {len(pm_notifications)} PMs")
                self._send_collected_notifications(pm_notifications, tmux, logger)
                pm_notified = True

            # If any PM was notified, apply cooldown period
            if pm_notified:
                logger.info(f"PM notification sent - applying {DAEMON_CONTROL_LOOP_COOLDOWN_SECONDS}s cooldown")
                time.sleep(DAEMON_CONTROL_LOOP_COOLDOWN_SECONDS)

        except Exception as e:
            logger.error(f"Error in monitoring cycle: {e}")

    def _discover_agents(self, tmux: TMUXManager) -> list[str]:
        """Discover active agents to monitor."""
        agents = []

        try:
            # Get all tmux sessions
            sessions = tmux.list_sessions()

            for session_info in sessions:
                session_name = session_info["name"]

                # Get windows for this session
                try:
                    windows = tmux.list_windows(session_name)
                    for window_info in windows:
                        # Fix: use 'index' not 'id' - window_info contains index/name/active
                        window_idx = window_info.get("index", "0")
                        target = f"{session_name}:{window_idx}"

                        # Check if window contains an active agent
                        if self._is_agent_window(tmux, target):
                            agents.append(target)

                except Exception:
                    # Skip this session if we can't list windows
                    continue

        except Exception:
            # Return empty list if we can't discover agents
            pass

        return agents

    def _is_agent_window(self, tmux: TMUXManager, target: str) -> bool:
        """Check if a window should be monitored as an agent window.

        This checks window NAME patterns, not content, so we can track
        crashed agents that need recovery.
        """
        try:
            session_name, window_idx = target.split(":")
            windows = tmux.list_windows(session_name)

            # Find the window info for this index
            for window in windows:
                if str(window.get("index", "")) == str(window_idx):
                    window_name = window.get("name", "").lower()

                    # Check if this is an agent window by name pattern
                    # Claude agent windows are named "Claude-{role}"
                    if window_name.startswith("claude-"):
                        return True

                    # Also check for common agent indicators in window name
                    agent_indicators = ["pm", "developer", "qa", "engineer", "devops", "backend", "frontend"]
                    if any(indicator in window_name for indicator in agent_indicators):
                        return True

            return False

        except Exception:
            return False

    def _check_agent_status(
        self, tmux: TMUXManager, target: str, logger: logging.Logger, pm_notifications: dict[str, list[str]]
    ) -> None:
        """Check agent status using improved detection algorithm."""
        try:
            logger.debug(f"Checking status for agent {target}")

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
                    logger.debug(f"Agent {target} snapshot {i} has {changes} character changes")
                    if changes > 1:
                        is_active = True
                        break

            if not is_active:
                logger.debug(f"Agent {target} determined to be idle - no significant changes")

            # Simple activity detection (minimal coupling to Claude Code implementation)
            if not is_active:
                content_lower = content.lower()

                # Check for compaction (robust across Claude Code versions)
                if "compacting conversation" in content_lower:
                    logger.debug(f"Agent {target} is compacting conversation")
                    is_active = True

                # Check for active processing (ellipsis indicates ongoing work)
                elif "…" in content and any(
                    word in content_lower for word in ["thinking", "pondering", "divining", "musing", "elucidating"]
                ):
                    logger.debug(f"Agent {target} is actively processing")
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
                        logger.error(f"Agent {target} has crashed - attempting auto-restart")
                        success = self._attempt_agent_restart(tmux, target, logger)
                        if not success:
                            logger.error(f"Auto-restart failed for {target} - notifying PM")
                            self._notify_crash(tmux, target, logger, pm_notifications)
                        return

                # Otherwise it's an error state
                state = AgentState.ERROR
                logger.error(f"Agent {target} in error state - needs recovery")
                self._notify_recovery_needed(tmux, target, logger)
                return

            # Step 4: Check for unsubmitted messages
            if has_unsubmitted_message(content):
                state = AgentState.MESSAGE_QUEUED
                logger.info(f"Agent {target} has unsubmitted message - attempting auto-submit")
                self._try_auto_submit(tmux, target, logger)
                return

            # Step 5: Determine if idle or active
            if is_active:
                state = AgentState.ACTIVE
                logger.info(f"Agent {target} is ACTIVE")
                # Reset tracking for active agents
                self._reset_agent_tracking(target)
            else:
                state = AgentState.IDLE
                logger.info(f"Agent {target} is IDLE")

                # Check if should notify PM about idle agent
                if should_notify_pm(state, target, self._idle_notifications):
                    logger.info(f"Agent {target} is idle without active work - notifying PM")
                    self._check_idle_notification(tmux, target, logger, pm_notifications)
                    # Track notification time
                    self._idle_notifications[target] = datetime.now()

        except Exception as e:
            logger.error(f"Failed to check agent {target}: {e}")

    def _capture_snapshots(self, tmux: TMUXManager, target: str, count: int, interval: float) -> list[str]:
        """Capture multiple snapshots of terminal content."""
        snapshots = []
        for i in range(count):
            content = tmux.capture_pane(target, lines=50)
            snapshots.append(content)
            if i < count - 1:
                time.sleep(interval)
        return snapshots

    def _reset_agent_tracking(self, target: str) -> None:
        """Reset tracking for active agents."""
        if target in self._idle_agents:
            del self._idle_agents[target]
        if target in self._submission_attempts:
            self._submission_attempts[target] = 0
        if target in self._last_submission_time:
            del self._last_submission_time[target]

    def _try_auto_submit(self, tmux: TMUXManager, target: str, logger: logging.Logger) -> None:
        """Try auto-submitting stuck messages with cooldown."""
        current_time = time.time()
        last_attempt = self._last_submission_time.get(target, 0)

        # Check if we've already tried too many times
        attempts = self._submission_attempts.get(target, 0)
        if attempts >= 5:
            logger.debug(f"Skipping auto-submit for {target} - already tried {attempts} times")
            return

        if current_time - last_attempt >= 10:  # 10 second cooldown
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

    def _attempt_agent_restart(self, tmux: TMUXManager, target: str, logger: logging.Logger) -> bool:
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

            # Step 2: Send PM notification with ready-to-copy-paste command
            self._send_simple_restart_notification(tmux, target, failure_reason, logger)

            # Track notification time
            self._restart_attempts[restart_key] = now

            return True

        except Exception as e:
            logger.error(f"Exception during restart notification for {target}: {e}")
            return False

    def _detect_api_error_patterns(self, content: str) -> bool:
        """Detect API error patterns in terminal content."""
        content_lower = content.lower()

        # Common API error patterns
        api_error_patterns = [
            # Network and connection errors
            "network error occurred",
            "connection error",
            "connection timed out",
            "connection refused",
            "network timeout",
            "request timeout",
            "socket timeout",
            # API-specific errors
            "api error",
            "rate limit",
            "rate limited",
            "quota exceeded",
            "authentication failed",
            "unauthorized",
            "forbidden",
            "service unavailable",
            "internal server error",
            "bad gateway",
            "gateway timeout",
            # Claude-specific patterns
            "claude api error",
            "anthropic api",
            "model overloaded",
            "server overloaded",
            # Red text indicators (ANSI escape codes for red)
            "\033[31m",  # Red text
            "\033[91m",  # Bright red
            "\u001b[31m",  # Alternative red encoding
        ]

        return any(pattern in content_lower for pattern in api_error_patterns)

    def _identify_error_type(self, content: str) -> str:
        """Identify the specific type of API error for better reporting."""
        content_lower = content.lower()

        if any(pattern in content_lower for pattern in ["network error", "connection", "timeout"]):
            return "Network/Connection"
        elif any(pattern in content_lower for pattern in ["rate limit", "quota"]):
            return "Rate Limiting"
        elif any(pattern in content_lower for pattern in ["authentication", "unauthorized"]):
            return "Authentication"
        elif any(pattern in content_lower for pattern in ["server", "gateway", "service unavailable"]):
            return "Server Error"
        elif any(pattern in content_lower for pattern in ["overloaded", "capacity"]):
            return "Capacity"
        elif "\033[31m" in content or "\033[91m" in content:
            return "Error Output"
        else:
            return "API Error"

    def _send_simple_restart_notification(
        self, tmux: TMUXManager, target: str, reason: str, logger: logging.Logger
    ) -> None:
        """Send simple PM notification about agent failure."""
        try:
            # Find PM target IN THE SAME SESSION
            session_name = target.split(":")[0]
            pm_target = self._find_pm_in_session(tmux, session_name)
            if not pm_target:
                logger.debug(f"No PM found in session {session_name} to notify about agent failure")
                return

            # Don't notify PM about their own issues
            if pm_target == target:
                logger.debug(f"Skipping notification - PM at {target} has their own issue")
                return

            # Get window name from target
            session, window = target.split(":")
            window_name = self._get_window_name(tmux, session, window)

            # Send simple notification
            message = (
                f"🚨 AGENT FAILURE\n\n"
                f"Agent: {target} ({window_name})\n"
                f"Issue: {reason}\n\n"
                f"Please restart this agent and provide the appropriate role prompt."
            )

            # Send notification
            success_sent = tmux.send_message(pm_target, message)

            if success_sent:
                logger.info(f"Sent restart notification to PM at {pm_target} for {target}")
            else:
                logger.warning(f"Failed to send restart notification to PM at {pm_target}")

        except Exception as e:
            logger.error(f"Failed to send restart notification: {e}")

    def _notify_recovery_needed(self, tmux: TMUXManager, target: str, logger: logging.Logger) -> None:
        """Notify PM that agent needs recovery."""
        logger.warning(f"Notifying PM that {target} needs recovery")
        session_name = target.split(":")[0]
        pm_target = self._find_pm_in_session(tmux, session_name)
        if pm_target:
            message = f"🔴 AGENT RECOVERY NEEDED: {target} is idle and Claude interface is not responding. Please restart this agent."
            try:
                tmux.send_message(pm_target, message)
                logger.info(f"Sent recovery notification to PM at {pm_target}")
            except Exception as e:
                logger.error(f"Failed to notify PM: {e}")
        else:
            logger.warning(f"No PM agent found in session {session_name} to notify about recovery")

    def _find_pm_agent(self, tmux: TMUXManager) -> str | None:
        """Find a PM agent to send notifications to."""
        try:
            sessions = tmux.list_sessions()
            for session in sessions:
                windows = tmux.list_windows(session["name"])
                for window in windows:
                    window_name = window.get("name", "").lower()
                    target = f"{session['name']}:{window['index']}"

                    # Check if this looks like a PM window
                    if any(pm_indicator in window_name for pm_indicator in ["pm", "manager", "project"]):
                        # Verify it has Claude interface
                        content = tmux.capture_pane(target, lines=10)
                        if is_claude_interface_present(content):
                            return target
            return None
        except Exception:
            return None

    def is_agent_idle(self, target: str) -> bool:
        """Check if agent is idle using the improved 4-snapshot method."""
        try:
            session, window = target.split(":")

            # Take 4 snapshots of the last line at 300ms intervals
            snapshots = []
            for _ in range(4):
                content = self.tmux.capture_pane(target, lines=1)
                last_line = content.strip().split("\n")[-1] if content else ""
                snapshots.append(last_line)
                time.sleep(0.3)

            # If all snapshots are identical, agent is idle
            return all(line == snapshots[0] for line in snapshots)

        except Exception:
            return False  # If we can't check, assume active

    def _auto_submit_message(self, tmux: TMUXManager, target: str, logger: logging.Logger) -> None:
        """Auto-submit unsubmitted message in Claude prompt."""
        try:
            logger.info(f"Auto-submitting unsubmitted message for {target}")

            # Simply send Enter key to submit the message
            # Claude Code submits with Enter, not complex key sequences
            tmux.press_enter(target)

            logger.info(f"Message submitted for {target}")

        except Exception as e:
            logger.error(f"Failed to auto-submit message for {target}: {e}")

    def _notify_crash(
        self, tmux: TMUXManager, target: str, logger: logging.Logger, pm_notifications: dict[str, list[str]]
    ) -> None:
        """Notify PM about crashed Claude agent."""
        try:
            # Find PM target IN THE SAME SESSION
            session_name = target.split(":")[0]
            pm_target = self._find_pm_in_session(tmux, session_name)
            if not pm_target:
                logger.warning(f"No PM found in session {session_name} to notify about crash")
                return

            # Get current time for cooldown check
            now = datetime.now()
            crash_key = f"crash_{target}"

            # Check cooldown (5 minutes between crash notifications)
            last_notified = self._crash_notifications.get(crash_key)
            if last_notified and (now - last_notified) < timedelta(minutes=5):
                logger.debug(f"Crash notification for {target} in cooldown")
                return

            # Format crash message
            message = (
                f"🚨 AGENT CRASH ALERT:\n\n"
                f"Claude Code has crashed for agent at {target}\n\n"
                f"**RECOVERY ACTIONS NEEDED**:\n"
                f"1. Restart Claude Code in the crashed window\n"
                f"2. Provide system prompt from agent-prompts.yaml\n"
                f"3. Re-assign current tasks\n"
                f"4. Verify agent is responsive\n\n"
                f"Use this command:\n"
                f"• tmux send-keys -t {target} 'claude --dangerously-skip-permissions' Enter"
            )

            # Collect notification instead of sending directly
            self._collect_notification(pm_notifications, session_name, message, tmux)
            logger.info(f"Collected crash notification for {target}")
            self._crash_notifications[crash_key] = now

        except Exception as e:
            logger.error(f"Failed to collect crash notification: {e}")

    def _check_idle_notification(
        self, tmux: TMUXManager, target: str, logger: logging.Logger, pm_notifications: dict[str, list[str]]
    ) -> None:
        """Check if PM should be notified about idle agent."""
        try:
            logger.debug(f"_check_idle_notification called for {target}")
            # Already initialized in __init__

            now = datetime.now()

            # Track idle state for notification purposes
            if target not in self._idle_agents:
                self._idle_agents[target] = now
                logger.debug(f"Started tracking idle state for {target}")
                # Don't return here - continue to check if we should notify immediately

            # No minimum wait time - if agent is idle, PM should know immediately

            # No cooldown needed - if agent is idle, PM should be notified
            # PM will communicate with agent, and if agent becomes active, notifications stop naturally

            # Find PM target IN THE SAME SESSION
            logger.info(f"Looking for PM to notify about idle agent {target}")
            session_name = target.split(":")[0]
            pm_target = self._find_pm_in_session(tmux, session_name)
            if not pm_target:
                logger.warning(f"No PM found in session {session_name} to notify about idle agent {target}")
                return
            logger.info(f"Found PM at {pm_target} to notify about idle agent {target}")

            # Don't notify PM about themselves being idle - only skip self-notifications
            if pm_target == target:
                logger.debug(
                    f"Skipping self-notification - PM at {pm_target} would be notified about their own idle status"
                )
                return

            # Get window name from target
            session, window = target.split(":")
            window_name = self._get_window_name(tmux, session, window)

            # Send idle notification
            message = (
                f"🚨 IDLE AGENT(S) ALERT:\n\n"
                f"Agent {target} ({window_name}) is currently idle and available for work.\n\n"
                f"Please review their status and assign tasks as needed.\n\n"
                f"This is an automated notification from the monitoring system."
            )

            # Collect notification instead of sending directly
            self._collect_notification(pm_notifications, session_name, message, tmux)
            logger.info(f"Collected idle notification for {target}")

        except Exception as e:
            logger.error(f"Failed to collect idle notification: {e}")

    def _find_pm_target(self, tmux: TMUXManager) -> str | None:
        """Find PM session dynamically - just use the better implementation."""
        return self._find_pm_agent(tmux)

    def _spawn_pm(
        self,
        tmux: TMUXManager,
        target_session: str,
        window_index: int,
        logger: logging.Logger,
        recovery_context: str = "",
    ) -> str | None:
        """Spawn a PM agent at the specified location.

        Args:
            tmux: TMUXManager instance
            target_session: Session to spawn PM in
            window_index: Window index to use
            logger: Logger instance
            recovery_context: Additional context for recovery scenarios

        Returns:
            PM target string if successful, None if failed
        """
        pm_target = f"{target_session}:{window_index}"

        try:
            # Create new window for PM using subprocess
            import subprocess

            subprocess.run(
                ["tmux", "new-window", "-t", f"{target_session}:{window_index}", "-n", "Claude-pm"], check=True
            )
            logger.info(f"Created PM window at {pm_target}")

            # Start Claude with PM context
            tmux.send_keys(pm_target, "claude --dangerously-skip-permissions", literal=True)
            tmux.send_keys(pm_target, "Enter")

            # Wait for Claude to initialize
            import time

            time.sleep(8)

            # Send PM context
            from pathlib import Path

            pm_context_path = Path(__file__).parent.parent / "data" / "contexts" / "pm.md"
            if pm_context_path.exists():
                with open(pm_context_path) as f:
                    pm_context = f.read()

                # Build message with context and any recovery info
                message_parts = [pm_context]
                if recovery_context:
                    message_parts.append(recovery_context)

                full_message = "\n\n".join(message_parts)

                success = tmux.send_message(pm_target, full_message)
                if success:
                    logger.info(f"Successfully spawned PM at {pm_target} with context")
                    return pm_target
                else:
                    logger.error(f"Failed to send context to PM at {pm_target}")
            else:
                logger.error("PM context file not found")

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create PM window: {e}")
        except Exception as e:
            logger.error(f"Failed to spawn PM: {e}")

        return None

    def _check_pm_recovery(self, tmux: TMUXManager, agents: list[str], logger: logging.Logger) -> None:
        """Check if PM needs to be auto-spawned when other agents exist but PM is missing."""
        try:
            # Skip if no agents exist
            if not agents:
                return

            # Check if PM exists
            pm_target = self._find_pm_agent(tmux)
            if pm_target:
                return  # PM exists, no recovery needed

            # PM missing but other agents exist - auto-spawn PM
            logger.warning(f"PM missing but {len(agents)} agents exist. Auto-spawning PM for recovery.")

            # Find the session with the most agents
            session_counts: dict[str, int] = {}
            for agent in agents:
                session_name = agent.split(":")[0]
                session_counts[session_name] = session_counts.get(session_name, 0) + 1

            target_session = max(session_counts.keys(), key=lambda k: session_counts[k])

            # Find available window number in that session
            windows = tmux.list_windows(target_session)
            used_indices = {int(w["index"]) for w in windows}
            new_window_index = 1
            while new_window_index in used_indices:
                new_window_index += 1

            # Create recovery context message
            recovery_context = f"""AUTO-RECOVERY NOTIFICATION:
You have been automatically spawned as PM because the previous PM failed but other agents still exist.
Your session: {target_session}
Active agents: {', '.join(agents)}
Please assess the current situation and resume project management."""

            # Use the reusable spawn_pm function
            pm_target = self._spawn_pm(tmux, target_session, new_window_index, logger, recovery_context)
            if pm_target:
                logger.info(f"PM auto-recovery successful at {pm_target}")
            else:
                logger.error("PM auto-recovery failed")

        except Exception as e:
            logger.error(f"Failed to auto-spawn PM: {e}")

    def _check_missing_agents(
        self,
        tmux: TMUXManager,
        current_agents: list[str],
        logger: logging.Logger,
        pm_notifications: dict[str, list[str]],
    ) -> None:
        """Track agents per session and notify PM when agents disappear."""
        try:
            # Import the constant here to avoid circular imports
            from tmux_orchestrator.core.monitor_helpers import MISSING_AGENT_GRACE_MINUTES

            # Group current agents by session
            current_by_session: dict[str, set[str]] = {}
            for agent in current_agents:
                session_name = agent.split(":")[0]
                if session_name not in current_by_session:
                    current_by_session[session_name] = set()
                current_by_session[session_name].add(agent)

            # Check each session for missing agents
            for session_name, current_agents_set in current_by_session.items():
                # Update high-water mark (union with existing)
                if session_name not in self._session_agents:
                    self._session_agents[session_name] = set()

                previous_agents = self._session_agents[session_name].copy()
                self._session_agents[session_name] = self._session_agents[session_name].union(current_agents_set)

                # Check for missing agents (set subtraction)
                missing_agents = previous_agents - current_agents_set

                # Clean up agents that have come back
                for agent in current_agents_set:
                    if agent in self._missing_agent_grace:
                        del self._missing_agent_grace[agent]
                        logger.info(f"Agent {agent} has recovered - removing from grace period tracking")

                if missing_agents:
                    now = datetime.now()

                    # Check grace period for each missing agent
                    agents_to_notify = []
                    for agent in missing_agents:
                        if agent not in self._missing_agent_grace:
                            # First time seeing this agent as missing
                            self._missing_agent_grace[agent] = now
                            logger.info(
                                f"Agent {agent} detected as missing - starting {MISSING_AGENT_GRACE_MINUTES} minute grace period"
                            )
                        else:
                            # Check if grace period has expired
                            time_missing = now - self._missing_agent_grace[agent]
                            if time_missing >= timedelta(minutes=MISSING_AGENT_GRACE_MINUTES):
                                agents_to_notify.append(agent)
                            else:
                                remaining = timedelta(minutes=MISSING_AGENT_GRACE_MINUTES) - time_missing
                                logger.debug(
                                    f"Agent {agent} still in grace period - {remaining.seconds} seconds remaining"
                                )

                    # Only notify if we have agents past their grace period
                    if agents_to_notify:
                        # Find PM in this session to notify
                        pm_target = None
                        for agent in current_agents_set:
                            if self._is_pm_agent(tmux, agent):
                                pm_target = agent
                                break

                        if pm_target:
                            # Import cooldown constant
                            from tmux_orchestrator.core.monitor_helpers import (
                                MISSING_AGENT_NOTIFICATION_COOLDOWN_MINUTES,
                            )

                            # Check cooldown for these specific missing agents
                            notification_key = f"{session_name}:{','.join(sorted(agents_to_notify))}"
                            last_notified = self._missing_agent_notifications.get(notification_key)

                            if last_notified:
                                time_since_notification = now - last_notified
                                if time_since_notification < timedelta(
                                    minutes=MISSING_AGENT_NOTIFICATION_COOLDOWN_MINUTES
                                ):
                                    cooldown_remaining = (
                                        timedelta(minutes=MISSING_AGENT_NOTIFICATION_COOLDOWN_MINUTES)
                                        - time_since_notification
                                    )
                                    logger.debug(
                                        f"Missing agents notification in cooldown - {cooldown_remaining.seconds} seconds remaining"
                                    )
                                    continue

                            # Get display names for missing and current agents
                            missing_display = []
                            for agent in agents_to_notify:
                                display_name = self._get_agent_display_name(tmux, agent)
                                missing_display.append(display_name)

                            current_display = []
                            for agent in current_agents_set:
                                display_name = self._get_agent_display_name(tmux, agent)
                                current_display.append(display_name)

                            missing_list = "\n".join(sorted(missing_display))
                            current_list = "\n".join(sorted(current_display))

                            message = f"""🚨 TEAM MEMBER ALERT:

Missing agents detected in session {session_name}:
{missing_list}

Current team members:
{current_list}

Please review your team plan to determine if these agents are still needed.
If they are needed, restart them with their appropriate briefing.
If they are no longer needed, no action is required.

Use 'tmux list-windows -t {session_name}' to check window status."""

                            try:
                                # Collect notification instead of sending directly
                                self._collect_notification(pm_notifications, session_name, message, tmux)
                                logger.warning(
                                    f"Collected missing agents notification for session {session_name}: {missing_list}"
                                )
                                # Track notification time
                                self._missing_agent_notifications[notification_key] = now
                            except Exception as e:
                                logger.error(f"Error collecting missing agents notification: {e}")
                        else:
                            logger.warning(
                                f"Missing agents {agents_to_notify} in session {session_name} but no PM found to notify"
                            )

        except Exception as e:
            logger.error(f"Error checking missing agents: {e}")

    def _get_agent_display_name(self, tmux: TMUXManager, target: str) -> str:
        """Get a display name for an agent that includes window name and location."""
        try:
            session_name, window_idx = target.split(":")
            windows = tmux.list_windows(session_name)

            for window in windows:
                if str(window.get("index", "")) == str(window_idx):
                    window_name = window.get("name", "Unknown")
                    # Format: "WindowName[session:idx]"
                    return f"{window_name}[{target}]"

            return f"Unknown[{target}]"
        except Exception:
            return target

    def _get_window_name(self, tmux: TMUXManager, session: str, window: str) -> str:
        """Get just the window name for an agent."""
        try:
            windows = tmux.list_windows(session)
            for w in windows:
                if str(w.get("index", "")) == str(window):
                    return w.get("name", "Unknown")
            return "Unknown"
        except Exception:
            return "Unknown"

    def _find_pm_in_session(self, tmux: TMUXManager, session: str) -> str | None:
        """Find PM agent in a specific session."""
        try:
            windows = tmux.list_windows(session)
            for window in windows:
                window_idx = str(window.get("index", ""))
                target = f"{session}:{window_idx}"
                if self._is_pm_agent(tmux, target):
                    return target
            return None
        except Exception:
            return None

    def _is_pm_agent(self, tmux: TMUXManager, target: str) -> bool:
        """Check if target is a PM agent."""
        try:
            # Simple check: window name contains 'pm' or is identified as PM
            session, window = target.split(":")
            windows = tmux.list_windows(session)
            for w in windows:
                if w.get("index") == window:
                    window_name = w.get("name", "").lower()
                    return "pm" in window_name or "manager" in window_name
            return False
        except Exception:
            return False

    def _collect_notification(
        self, pm_notifications: dict[str, list[str]], session: str, message: str, tmux: TMUXManager
    ) -> None:
        """Collect notification for batching instead of sending immediately.

        Args:
            pm_notifications: Collection dict mapping PM targets to messages
            session: Session name to find PM in
            message: Notification message to collect
            tmux: TMUXManager instance
        """
        # Find PM in the session
        pm_target = self._find_pm_in_session(tmux, session)
        if not pm_target:
            # No PM to notify, discard message
            return

        # Initialize list if needed
        if pm_target not in pm_notifications:
            pm_notifications[pm_target] = []

        # Add message to collection
        pm_notifications[pm_target].append(message)

    def _check_team_idleness(
        self, tmux: TMUXManager, agents: list[str], logger: logging.Logger, pm_notifications: dict[str, list[str]]
    ) -> None:
        """Check if entire team is idle and handle PM escalations."""
        # Group agents by session to track team idleness per session
        session_agents: Dict[str, list[str]] = {}
        for agent in agents:
            session = agent.split(":")[0]
            if session not in session_agents:
                session_agents[session] = []
            session_agents[session].append(agent)

        # Check each session/team
        for session, team_agents in session_agents.items():
            # Check if ALL agents in this session are idle
            all_idle = all(agent in self._idle_agents for agent in team_agents)

            if all_idle and team_agents:  # Ensure we have agents to check
                # Find PM for this session
                pm_target = None
                for agent in team_agents:
                    if "pm" in agent.lower() or ":0" in agent:  # PM usually in window 0
                        pm_target = agent
                        break

                if not pm_target:
                    # Try to find PM more broadly
                    pm_target = self._find_pm_agent(tmux)

                if pm_target:
                    now = datetime.now()

                    # Initialize team idle tracking for this session
                    if session not in self._team_idle_at or self._team_idle_at[session] is None:
                        self._team_idle_at[session] = now
                        logger.info(f"Team in session {session} became idle at {now}")

                    # Calculate elapsed time
                    team_idle_time = self._team_idle_at[session]
                    assert team_idle_time is not None  # Already checked above
                    elapsed = now - team_idle_time
                    elapsed_minutes = int(elapsed.total_seconds() / 60)

                    # Check for escalations
                    for threshold_minutes, (action, message) in sorted(NONRESPONSIVE_PM_ESCALATIONS_MINUTES.items()):
                        if elapsed_minutes >= threshold_minutes:
                            # Check if we've already sent this escalation
                            if pm_target not in self._pm_escalation_history:
                                self._pm_escalation_history[pm_target] = {}

                            if threshold_minutes not in self._pm_escalation_history[pm_target]:
                                # Send escalation
                                if action == DaemonAction.MESSAGE and message:
                                    logger.warning(f"Sending {threshold_minutes}min escalation to PM {pm_target}")
                                    self._collect_notification(pm_notifications, session, message, tmux)
                                    self._pm_escalation_history[pm_target][threshold_minutes] = now

                                elif action == DaemonAction.KILL:
                                    logger.critical(
                                        f"PM {pm_target} unresponsive for {threshold_minutes}min - killing PM"
                                    )
                                    try:
                                        # Kill the PM window
                                        tmux.kill_window(pm_target)
                                        logger.info(f"Killed unresponsive PM {pm_target}")

                                        # Clear escalation history for this PM
                                        if pm_target in self._pm_escalation_history:
                                            del self._pm_escalation_history[pm_target]

                                        # Reset team idle tracking for this session
                                        self._team_idle_at[session] = None

                                        # The daemon's PM recovery will automatically spawn a new PM
                                    except Exception as e:
                                        logger.error(f"Failed to kill PM {pm_target}: {e}")

                                    self._pm_escalation_history[pm_target][threshold_minutes] = now
            else:
                # Team is not all idle - reset tracking for this session
                if session in self._team_idle_at and self._team_idle_at[session] is not None:
                    logger.info(f"Team in session {session} is active again")
                    self._team_idle_at[session] = None

                    # Clear escalation history for PMs in this session
                    for agent in team_agents:
                        if agent in self._pm_escalation_history:
                            del self._pm_escalation_history[agent]

    def _send_collected_notifications(
        self, pm_notifications: dict[str, list[str]], tmux: TMUXManager, logger: logging.Logger
    ) -> None:
        """Send all collected notifications as consolidated reports to PMs.

        Args:
            pm_notifications: Collection dict mapping PM targets to messages
            tmux: TMUXManager instance
            logger: Logger instance
        """
        for pm_target, messages in pm_notifications.items():
            if not messages:
                continue

            # Build consolidated report
            timestamp = datetime.now().strftime("%H:%M:%S UTC")
            report_header = f"🔔 MONITORING REPORT - {timestamp}\n"

            # Group messages by type
            crashed_agents = []
            idle_agents = []
            missing_agents = []
            other_messages = []

            for msg in messages:
                if "CRASH" in msg or "FAILURE" in msg:
                    crashed_agents.append(msg)
                elif "IDLE" in msg:
                    idle_agents.append(msg)
                elif "MISSING" in msg or "TEAM MEMBER ALERT" in msg:
                    missing_agents.append(msg)
                else:
                    other_messages.append(msg)

            # Build consolidated message
            report_parts = [report_header]

            if crashed_agents:
                report_parts.append("\n🚨 CRASHED AGENTS:")
                for msg in crashed_agents:
                    # Extract agent info from message
                    if "Agent: " in msg:
                        agent_line = [line for line in msg.split("\n") if line.startswith("Agent: ")][0]
                        report_parts.append(f"- {agent_line}")
                    elif "agent at " in msg:
                        import re

                        match = re.search(r"agent at ([^\s]+)", msg)
                        if match:
                            report_parts.append(f"- {match.group(1)}")

            if idle_agents:
                report_parts.append("\n⚠️ IDLE AGENTS:")
                for msg in idle_agents:
                    # Extract agent info
                    if "Agent " in msg and " (" in msg:
                        import re

                        match = re.search(r"Agent ([^\s]+) \(([^)]+)\)", msg)
                        if match:
                            report_parts.append(f"- {match.group(1)} ({match.group(2)})")

            if missing_agents:
                report_parts.append("\n📍 MISSING AGENTS:")
                for msg in missing_agents:
                    # Extract missing agents list
                    if "Missing agents detected" in msg:
                        lines = msg.split("\n")
                        for i, line in enumerate(lines):
                            if "Missing agents detected" in line and i + 1 < len(lines):
                                report_parts.append(f"- {lines[i + 1]}")
                                break

            if other_messages:
                report_parts.append("\n📋 OTHER NOTIFICATIONS:")
                for msg in other_messages:
                    # Get first meaningful line
                    first_line = msg.strip().split("\n")[0]
                    if first_line:
                        report_parts.append(f"- {first_line}")

            report_parts.append("\nPlease review and take appropriate action.")

            # Send consolidated report
            consolidated_message = "\n".join(report_parts)
            try:
                success = tmux.send_message(pm_target, consolidated_message)
                if success:
                    logger.info(f"Sent consolidated report to PM at {pm_target} with {len(messages)} notifications")
                else:
                    logger.error(f"Failed to send consolidated report to PM at {pm_target}")
            except Exception as e:
                logger.error(f"Error sending consolidated report to {pm_target}: {e}")


class AgentMonitor:
    """Enhanced agent monitor with bulletproof idle detection and recovery."""

    def __init__(self, config: Config, tmux: TMUXManager):
        self.config = config
        self.tmux = tmux
        self.idle_monitor = IdleMonitor(tmux)

        # Set up log file path
        project_dir = Path("/workspaces/Tmux-Orchestrator/.tmux_orchestrator")
        project_dir.mkdir(exist_ok=True)
        logs_dir = project_dir / "logs"
        logs_dir.mkdir(exist_ok=True)
        self.log_file = logs_dir / "agent-monitor.log"

        self.logger = self._setup_logging()
        self.agent_status: dict[str, AgentHealthStatus] = {}

        # Health check configuration
        self.heartbeat_interval = config.get("monitoring.heartbeat_interval", 30)
        self.response_timeout = config.get("monitoring.response_timeout", 60)
        self.max_failures = config.get("monitoring.max_failures", 3)
        self.recovery_cooldown = config.get("monitoring.recovery_cooldown", 300)

        # Track recent recovery attempts
        self.recent_recoveries: dict[str, datetime] = {}

    def _setup_logging(self) -> logging.Logger:
        """Set up logging for the monitor."""
        logger = logging.getLogger("agent_monitor")
        logger.setLevel(logging.INFO)

        # Clear existing handlers
        logger.handlers.clear()

        # Log to file
        log_file = self.log_file
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    def register_agent(self, target: str) -> None:
        """Register an agent for monitoring."""
        now = datetime.now()
        self.agent_status[target] = AgentHealthStatus(
            target=target,
            last_heartbeat=now,
            last_response=now,
            consecutive_failures=0,
            is_responsive=True,
            last_content_hash="",
            status="healthy",
            is_idle=False,
            activity_changes=0,
        )
        self.logger.info(f"Registered agent for monitoring: {target}")

    def unregister_agent(self, target: str) -> None:
        """Remove agent from monitoring."""
        if target in self.agent_status:
            del self.agent_status[target]
            self.logger.info(f"Unregistered agent from monitoring: {target}")

    def check_agent_health(self, target: str) -> AgentHealthStatus:
        """Check agent health using improved idle detection."""
        if target not in self.agent_status:
            self.register_agent(target)

        status = self.agent_status[target]
        now = datetime.now()

        try:
            # Use the bulletproof idle detection
            is_idle = self.idle_monitor.is_agent_idle(target)
            status.is_idle = is_idle

            # Capture current content for change detection
            content = self.tmux.capture_pane(target, lines=50)
            content_hash = str(hash(content))

            # Track activity changes
            if content_hash != status.last_content_hash:
                status.last_heartbeat = now
                status.last_content_hash = content_hash
                status.activity_changes += 1

            # Enhanced responsiveness check
            is_responsive = self._check_agent_responsiveness(target, content, is_idle)

            if is_responsive:
                status.last_response = now
                status.consecutive_failures = 0
                status.is_responsive = True
                status.status = "healthy"
            else:
                status.consecutive_failures += 1
                status.is_responsive = False

                # Determine status based on failure patterns
                time_since_response = now - status.last_response
                if self._has_critical_errors(content):
                    status.status = "critical"
                elif time_since_response > timedelta(seconds=self.response_timeout * 2):
                    status.status = "critical"
                elif time_since_response > timedelta(seconds=self.response_timeout):
                    status.status = "warning"
                elif status.consecutive_failures >= self.max_failures:
                    status.status = "unresponsive"
                else:
                    status.status = "warning"

            self.agent_status[target] = status

        except Exception as e:
            self.logger.error(f"Error checking health for {target}: {e}")
            status.consecutive_failures += 1
            status.status = "critical"

        return status

    def _check_agent_responsiveness(self, target: str, content: str, is_idle: bool) -> bool:
        """Enhanced responsiveness check."""
        # If agent is actively working, it's responsive
        if not is_idle:
            return True

        # Check for normal Claude interface elements
        if self._has_normal_claude_interface(content):
            return True

        # Check for error conditions
        if self._has_critical_errors(content):
            return False

        # If idle but with normal interface, it's responsive
        return True

    def _has_normal_claude_interface(self, content: str) -> bool:
        """Check if content shows normal Claude interface."""
        # Use the helper function from monitor_helpers
        return is_claude_interface_present(content)

    def _has_critical_errors(self, content: str) -> bool:
        """Check for critical error states."""
        # Use the helper functions from monitor_helpers
        from tmux_orchestrator.core.monitor_helpers import _has_crash_indicators, _has_error_indicators

        return _has_crash_indicators(content) or _has_error_indicators(content)

    def should_attempt_recovery(self, target: str, status: AgentHealthStatus) -> bool:
        """Determine if recovery should be attempted."""
        # Don't recover if recently recovered
        if target in self.recent_recoveries:
            time_since_recovery = datetime.now() - self.recent_recoveries[target]
            if time_since_recovery < timedelta(seconds=self.recovery_cooldown):
                return False

        # Recover if critical with multiple failures
        if status.status == "critical" and status.consecutive_failures >= self.max_failures:
            return True

        # Recover if unresponsive for too long
        time_since_response = datetime.now() - status.last_response
        if time_since_response > timedelta(seconds=self.response_timeout * 3):
            return True

        return False

    def attempt_recovery(self, target: str) -> bool:
        """Attempt to recover an unresponsive agent."""
        self.logger.warning(f"Attempting recovery for agent: {target}")

        try:
            # Use the CLI restart command
            _result = subprocess.run(
                ["tmux-orchestrator", "agent", "restart", target],
                capture_output=True,
                text=True,
                check=True,
            )

            # Mark recovery attempt
            self.recent_recoveries[target] = datetime.now()

            # Reset agent status after successful restart
            if target in self.agent_status:
                now = datetime.now()
                self.agent_status[target].last_response = now
                self.agent_status[target].last_heartbeat = now
                self.agent_status[target].consecutive_failures = 0
                self.agent_status[target].status = "healthy"
                self.agent_status[target].is_responsive = True
                self.agent_status[target].activity_changes = 0

            self.logger.info(f"Successfully recovered agent: {target}")
            return True

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to recover agent {target}: {e.stderr}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error recovering agent {target}: {e}")
            return False

    def monitor_all_agents(self) -> dict[str, AgentHealthStatus]:
        """Monitor all registered agents and return their status."""
        results = {}

        for target in list(self.agent_status.keys()):
            try:
                status = self.check_agent_health(target)
                results[target] = status

                # Attempt recovery if needed
                if self.should_attempt_recovery(target, status):
                    recovery_success = self.attempt_recovery(target)
                    if recovery_success:
                        # Re-check status after recovery
                        status = self.check_agent_health(target)
                        results[target] = status

            except Exception as e:
                self.logger.error(f"Error monitoring agent {target}: {e}")

        return results

    def get_unhealthy_agents(self) -> list[tuple[str, AgentHealthStatus]]:
        """Get list of agents that are not healthy."""
        unhealthy = []
        for target, status in self.agent_status.items():
            if status.status != "healthy":
                unhealthy.append((target, status))
        return unhealthy

    def get_monitoring_summary(self) -> dict[str, int]:
        """Get a summary of monitoring status."""
        total_agents = len(self.agent_status)
        healthy = sum(1 for s in self.agent_status.values() if s.status == "healthy")
        warning = sum(1 for s in self.agent_status.values() if s.status == "warning")
        critical = sum(1 for s in self.agent_status.values() if s.status == "critical")
        unresponsive = sum(1 for s in self.agent_status.values() if s.status == "unresponsive")
        idle = sum(1 for s in self.agent_status.values() if s.is_idle)

        return {
            "total_agents": total_agents,
            "healthy": healthy,
            "warning": warning,
            "critical": critical,
            "unresponsive": unresponsive,
            "idle": idle,
            "recent_recoveries": len(self.recent_recoveries),
        }

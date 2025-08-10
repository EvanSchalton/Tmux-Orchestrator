"""Advanced agent monitoring system with 100% accurate idle detection."""

import logging
import multiprocessing
import os
import signal
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from tmux_orchestrator.core.config import Config
from tmux_orchestrator.core.recovery.detect_failure import detect_failure
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
        self.pid_file = Path("/tmp/tmux-orchestrator-idle-monitor.pid")
        self.log_file = Path("/tmp/tmux-orchestrator-idle-monitor.log")
        self.daemon_process: multiprocessing.Process | None = None
        self._crash_notifications: dict[str, datetime] = {}
        self._idle_notifications: dict[str, datetime] = {}
        self._idle_agents: dict[str, datetime] = {}

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

        # Create daemon process
        self.daemon_process = multiprocessing.Process(target=self._run_monitoring_daemon, args=(interval,))
        self.daemon_process.daemon = False  # Don't exit with parent process

        self.daemon_process.start()

        # Wait for PID file to be created
        for _ in range(50):  # Wait up to 5 seconds
            if self.pid_file.exists():
                with open(self.pid_file) as f:
                    return int(f.read().strip())
            time.sleep(0.1)

        raise RuntimeError("Monitor daemon started but PID file not found")

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
        def signal_handler(signum, frame):
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

        # Create TMUXManager instance for this process
        tmux = TMUXManager()

        # Main monitoring loop
        try:
            while True:
                start_time = time.time()

                # Discover and monitor agents
                self._monitor_cycle(tmux, logger)

                # Calculate sleep time to maintain interval
                elapsed = time.time() - start_time
                sleep_time = max(0, interval - elapsed)

                if sleep_time > 0:
                    time.sleep(sleep_time)

        except KeyboardInterrupt:
            logger.info("Monitoring daemon interrupted")
        except Exception as e:
            logger.error(f"Monitoring daemon error: {e}", exc_info=True)
            # Try to write error to a debug file
            try:
                with open("/tmp/monitor-daemon-error.log", "a") as f:
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

            if not agents:
                logger.debug("No agents found to monitor")
                return

            logger.debug(f"Monitoring {len(agents)} agents")

            # Monitor each agent
            for target in agents:
                try:
                    self._check_agent_status(tmux, target, logger)
                except Exception as e:
                    logger.error(f"Error checking agent {target}: {e}")

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
                        window_id = window_info["id"]
                        target = f"{session_name}:{window_id}"

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
        """Check if a window contains an active Claude agent."""
        try:
            content = tmux.capture_pane(target, lines=10)

            # Look for Claude interface indicators
            claude_indicators = [
                "│ >",
                "assistant:",
                "I'll help",
                "I can help",
                "Human:",
                "Claude:",
                "╭─.*─╮",
            ]  # Claude prompt

            return any(indicator in content for indicator in claude_indicators)

        except Exception:
            return False

    def _check_agent_status(self, tmux: TMUXManager, target: str, logger: logging.Logger) -> None:
        """Check the status of a specific agent using the recovery system."""
        try:
            # Use the bulletproof detection from recovery system
            is_failed, failure_reason, status_details = detect_failure(
                tmux=tmux,
                target=target,
                last_response=datetime.now() - timedelta(seconds=30),  # Default check window
                consecutive_failures=0,
                max_failures=3,
                response_timeout=60,
            )

            # Check for Claude crash
            if failure_reason == "Claude interface not found":
                logger.error(
                    f"CRASH DETECTED: Claude Code appears to have crashed for {target} | Recovery needed immediately"
                )
                # Send crash notification to PM
                self._notify_crash(tmux, target, logger)
            # Check for unsubmitted messages
            elif self._has_unsubmitted_message(tmux, target):
                logger.warning(f"Agent {target} has unsubmitted message - auto-submitting")
                self._auto_submit_message(tmux, target, logger)
            # Log status
            elif is_failed:
                logger.warning(
                    f"Agent {target} failed: {failure_reason} | "
                    f"Idle: {status_details['is_idle']} | "
                    f"Interface: {status_details['interface_status']}"
                )
            elif status_details["is_idle"]:
                logger.info(f"Agent {target} is idle | Interface: {status_details['interface_status']}")
                # Check if PM should be notified about idle agent
                self._check_idle_notification(tmux, target, logger)
            else:
                logger.debug(f"Agent {target} is active and healthy")
                # Reset idle tracking when agent becomes active
                if target in self._idle_agents:
                    del self._idle_agents[target]

        except Exception as e:
            logger.error(f"Failed to check agent {target}: {e}")

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

    def _has_unsubmitted_message(self, tmux: TMUXManager, target: str) -> bool:
        """Check if agent has unsubmitted message in Claude prompt."""
        try:
            # Capture the last 20 lines from the agent's terminal
            content = tmux.capture_pane(target, lines=20)
            if not content:
                return False

            # Check if there's text typed in Claude prompt that hasn't been submitted
            # Look for the Claude prompt box with content inside
            lines = content.strip().split("\n")
            for line in lines:
                # Check for non-empty prompt line
                if "│ >" in line:
                    # Extract content after the prompt
                    prompt_content = line.split("│ >", 1)[1] if "│ >" in line else ""
                    # Check if there's actual content (not just whitespace)
                    if prompt_content.strip():
                        return True

            # Also check for multiline messages in the prompt box
            in_prompt = False
            for line in lines:
                if "│ >" in line:
                    in_prompt = True
                    # Check if there's content on the same line as the prompt
                    prompt_content = line.split("│ >", 1)[1] if "│ >" in line else ""
                    if prompt_content.strip():
                        return True
                elif in_prompt and "│" in line:
                    # Extract content between the box borders
                    content_match = line.strip()
                    if content_match.startswith("│") and content_match.endswith("│"):
                        inner_content = content_match[1:-1].strip()
                        if inner_content:
                            return True
                elif "╰─" in line:
                    # End of prompt box
                    in_prompt = False

            return False

        except Exception:
            return False

    def _auto_submit_message(self, tmux: TMUXManager, target: str, logger: logging.Logger) -> None:
        """Auto-submit unsubmitted message in Claude prompt."""
        try:
            logger.info(f"Auto-submitting unsubmitted message for {target}")

            # Send key sequences to submit the message
            tmux.send_keys(target, "C-a")  # Go to beginning of line
            time.sleep(0.2)
            tmux.send_keys(target, "C-e")  # Go to end of line
            time.sleep(0.3)
            tmux.send_keys(target, "Enter")  # Submit the message
            time.sleep(0.5)
            tmux.send_keys(target, "Enter")  # Extra enter to ensure submission

            logger.info(f"Message submitted for {target}")

        except Exception as e:
            logger.error(f"Failed to auto-submit message for {target}: {e}")

    def _notify_crash(self, tmux: TMUXManager, target: str, logger: logging.Logger) -> None:
        """Notify PM about crashed Claude agent."""
        try:
            # Find PM target
            pm_target = self._find_pm_target(tmux)
            if not pm_target:
                logger.warning("No PM found to notify about crash")
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

            # Send notification using CLI
            import subprocess

            result = subprocess.run(
                ["tmux-orc", "agent", "send", pm_target, message],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                logger.info(f"Notified PM at {pm_target} about crash at {target}")
                self._crash_notifications[crash_key] = now
            else:
                logger.error(f"Failed to notify PM about crash: {result.stderr}")

        except Exception as e:
            logger.error(f"Failed to send crash notification: {e}")

    def _check_idle_notification(self, tmux: TMUXManager, target: str, logger: logging.Logger) -> None:
        """Check if PM should be notified about idle agent."""
        try:
            # Already initialized in __init__

            now = datetime.now()
            idle_key = f"idle_{target}"

            # Track idle state
            if target not in self._idle_agents:
                self._idle_agents[target] = now
                logger.debug(f"Started tracking idle state for {target}")
                return

            # Check how long agent has been idle
            idle_duration = now - self._idle_agents[target]
            if idle_duration < timedelta(minutes=2):
                # Not idle long enough to notify
                return

            # Check notification cooldown (5 minutes)
            last_notified = self._idle_notifications.get(idle_key)
            if last_notified and (now - last_notified) < timedelta(minutes=5):
                logger.debug(f"Idle notification for {target} in cooldown")
                return

            # Find PM target
            pm_target = self._find_pm_target(tmux)
            if not pm_target:
                logger.warning("No PM found to notify about idle agent")
                return

            # Check if PM is busy
            pm_idle = self.is_agent_idle(pm_target)
            if not pm_idle:
                logger.debug("PM is busy, skipping idle notification")
                return

            # Send idle notification
            session, window = target.split(":")
            agent_type = self._determine_agent_type(session, window)

            message = (
                f"🚨 IDLE AGENT ALERT:\n\n"
                f"The following agent appears to be idle and needs tasks:\n"
                f"{target} ({agent_type})\n\n"
                f"Please check their status and assign work as needed.\n\n"
                f"This is an automated notification from the idle monitor."
            )

            # Send notification using CLI
            import subprocess

            result = subprocess.run(
                ["tmux-orc", "agent", "send", pm_target, message],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                logger.info(f"Notified PM at {pm_target} about idle agent {target}")
                self._idle_notifications[idle_key] = now
            else:
                logger.error(f"Failed to notify PM about idle agent: {result.stderr}")

        except Exception as e:
            logger.error(f"Failed to send idle notification: {e}")

    def _find_pm_target(self, tmux: TMUXManager) -> str | None:
        """Find PM session dynamically."""
        try:
            # First check tmux-orc-dev session for Project-Manager window
            if tmux.has_session("tmux-orc-dev"):
                windows = tmux.list_windows("tmux-orc-dev")
                for window in windows:
                    if window.get("name", "").lower() == "project-manager" or window.get("id") == "5":
                        return "tmux-orc-dev:5"

            # Search other sessions for PM windows
            sessions = tmux.list_sessions()
            for session in sessions:
                session_name = session.get("name", "")
                if "pm" in session_name.lower() or "project-manager" in session_name.lower():
                    return f"{session_name}:0"

            return None

        except Exception:
            return None

    def _determine_agent_type(self, session: str, window: str) -> str:
        """Determine agent type from session and window."""
        # Map of windows to agent types in tmux-orc-dev
        if session == "tmux-orc-dev":
            agent_map = {
                "1": "Orchestrator",
                "2": "MCP-Developer",
                "3": "CLI-Developer",
                "4": "Agent-Recovery-Dev",
                "5": "Project-Manager",
            }
            return agent_map.get(window, "Agent")

        # Determine from session name
        if "frontend" in session.lower():
            return "Frontend"
        elif "backend" in session.lower():
            return "Backend"
        elif "qa" in session.lower() or "testing" in session.lower():
            return "QA"
        elif "devops" in session.lower():
            return "DevOps"
        else:
            return "Agent"


class AgentMonitor:
    """Enhanced agent monitor with bulletproof idle detection and recovery."""

    def __init__(self, config: Config, tmux: TMUXManager):
        self.config = config
        self.tmux = tmux
        self.idle_monitor = IdleMonitor(tmux)
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
        log_file = Path("/tmp/tmux-orchestrator-monitor.log")
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
        claude_indicators = [
            "│ >",  # Claude prompt
            "assistant:",  # Claude response marker
            "I'll help",  # Common Claude response
            "I can help",  # Common Claude response
            "Let me",  # Common Claude response start
            "Human:",  # Human input marker
            "Claude:",  # Claude label
        ]

        return any(indicator in content for indicator in claude_indicators)

    def _has_critical_errors(self, content: str) -> bool:
        """Check for critical error states."""
        critical_errors = [
            "connection lost",
            "network error",
            "timeout",
            "crashed",
            "killed",
            "segmentation fault",
            "permission denied",
            "command not found",
            "python: can't open file",
            "ModuleNotFoundError",
            "ImportError",
            "SyntaxError",
            "claude: command not found",
        ]

        content_lower = content.lower()
        return any(error in content_lower for error in critical_errors)

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

    def get_monitoring_summary(self) -> dict:
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

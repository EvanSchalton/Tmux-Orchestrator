"""Recovery daemon for continuous agent monitoring and automatic recovery.

Integrates with existing monitoring systems to provide continuous health
monitoring and automatic recovery of failed agents. Designed to work
alongside the existing idle-monitor-daemon.sh or replace it entirely.
"""

import asyncio
import logging
import signal
from datetime import datetime
from typing import Any

from tmux_orchestrator.core.recovery.detect_failure import detect_failure
from tmux_orchestrator.core.recovery.recovery_coordinator import (
    coordinate_agent_recovery,
)
from tmux_orchestrator.core.recovery.recovery_logger import setup_recovery_logger
from tmux_orchestrator.utils.tmux import TMUXManager


class RecoveryDaemon:
    """Continuous agent monitoring and recovery daemon."""

    def __init__(
        self,
        monitor_interval: int = 30,
        recovery_enabled: bool = True,
        max_concurrent_recoveries: int = 3,
        failure_threshold: int = 3,
        recovery_cooldown: int = 300,  # 5 minutes
        log_level: int = logging.INFO,
    ) -> None:
        """
        Initialize recovery daemon.

        Args:
            monitor_interval: Seconds between monitoring cycles (default: 30)
            recovery_enabled: Whether to automatically trigger recovery (default: True)
            max_concurrent_recoveries: Max simultaneous recoveries (default: 3)
            failure_threshold: Failures before triggering recovery (default: 3)
            recovery_cooldown: Seconds between recovery attempts per agent (default: 300)
            log_level: Logging level (default: INFO)
        """
        self.monitor_interval = monitor_interval
        self.recovery_enabled = recovery_enabled
        self.max_concurrent_recoveries = max_concurrent_recoveries
        self.failure_threshold = failure_threshold
        self.recovery_cooldown = recovery_cooldown

        # Initialize components
        self.tmux = TMUXManager()
        self.logger = setup_recovery_logger(log_level=log_level)

        # State tracking
        self.agent_states: dict[str, dict[str, Any]] = {}
        self.active_recoveries: set[str] = set()
        self.last_recovery_attempts: dict[str, datetime] = {}
        self.shutdown_requested = False

        # Performance tracking
        self.cycle_count = 0
        self.total_recoveries_attempted = 0
        self.total_recoveries_successful = 0

        self.logger.info(f"Recovery daemon initialized - Interval: {monitor_interval}s, Recovery: {recovery_enabled}")

    async def start(self) -> None:
        """Start the recovery daemon main loop."""
        self.logger.info("Starting recovery daemon...")

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        try:
            while not self.shutdown_requested:
                cycle_start = datetime.now()

                await self._monitoring_cycle()

                # Calculate cycle performance
                cycle_duration = (datetime.now() - cycle_start).total_seconds()
                self.cycle_count += 1

                if self.cycle_count % 20 == 0:  # Log stats every 20 cycles
                    self._log_daemon_stats(cycle_duration)

                # Wait for next cycle
                if not self.shutdown_requested:
                    await asyncio.sleep(self.monitor_interval)

        except Exception as e:
            self.logger.error(f"Recovery daemon error: {str(e)}")
            raise
        finally:
            await self._shutdown()

    async def _monitoring_cycle(self) -> None:
        """Execute one monitoring and recovery cycle."""
        try:
            # Discover agents
            agents = await self._discover_agents()
            self.logger.debug(f"Monitoring {len(agents)} agents")

            # Check health of all agents
            health_results = await self._check_all_agents_health(agents)

            # Identify agents needing recovery
            recovery_candidates = self._identify_recovery_candidates(health_results)

            # Execute recoveries (respecting concurrency limits)
            if recovery_candidates and self.recovery_enabled:
                await self._execute_recoveries(recovery_candidates)

            # Update agent states
            self._update_agent_states(health_results)

        except Exception as e:
            self.logger.error(f"Monitoring cycle error: {str(e)}")

    async def _discover_agents(self) -> list[dict[str, str]]:
        """Discover all monitorable agents."""
        agents: list[dict[str, str]] = []

        try:
            # Check tmux-orc-dev session (primary development session)
            if self.tmux.has_session("tmux-orc-dev"):
                dev_agents = [
                    {
                        "target": "tmux-orc-dev:1",
                        "role": "orchestrator",
                        "session": "tmux-orc-dev",
                        "window": "1",
                    },
                    {
                        "target": "tmux-orc-dev:2",
                        "role": "developer",
                        "session": "tmux-orc-dev",
                        "window": "2",
                    },
                    {
                        "target": "tmux-orc-dev:3",
                        "role": "developer",
                        "session": "tmux-orc-dev",
                        "window": "3",
                    },
                    {
                        "target": "tmux-orc-dev:4",
                        "role": "developer",
                        "session": "tmux-orc-dev",
                        "window": "4",
                    },
                    {
                        "target": "tmux-orc-dev:5",
                        "role": "pm",
                        "session": "tmux-orc-dev",
                        "window": "5",
                    },
                ]
                agents.extend(dev_agents)

            # Check other project sessions
            sessions = self.tmux.list_sessions()
            for session in sessions:
                session_name = session.get("name", "")

                # Skip already processed sessions
                if session_name in ["tmux-orc-dev"]:
                    continue

                # Check for Claude agent windows
                try:
                    windows = self.tmux.list_windows(session_name)
                    for window in windows:
                        window_name = window.get("name", "")
                        window_id = window.get("index", "")

                        if "claude" in window_name.lower() or "agent" in window_name.lower():
                            role = self._determine_agent_role(session_name, window_name)
                            agents.append(
                                {
                                    "target": f"{session_name}:{window_id}",
                                    "role": role,
                                    "session": session_name,
                                    "window": window_id,
                                }
                            )
                except Exception as e:
                    self.logger.debug(f"Error checking session {session_name}: {str(e)}")

        except Exception as e:
            self.logger.error(f"Agent discovery error: {str(e)}")

        return agents

    def _determine_agent_role(self, session_name: str, window_name: str) -> str:
        """Determine agent role from session and window names."""
        session_lower = session_name.lower()
        window_lower = window_name.lower()

        # Role mapping
        if "pm" in session_lower or "pm" in window_lower or "manager" in window_lower:
            return "pm"
        elif "frontend" in session_lower or "frontend" in window_lower:
            return "developer"
        elif "backend" in session_lower or "backend" in window_lower:
            return "developer"
        elif "qa" in session_lower or "qa" in window_lower or "test" in window_lower:
            return "qa"
        elif "devops" in session_lower or "infra" in window_lower:
            return "devops"
        elif "orchestrator" in session_lower:
            return "orchestrator"
        else:
            return "developer"  # Default role

    async def _check_all_agents_health(self, agents: list[dict[str, str]]) -> list[dict[str, Any]]:
        """Check health status of all agents."""
        health_results: list[dict[str, Any]] = []

        for agent in agents:
            target = agent["target"]
            role = agent["role"]

            try:
                # Get agent's previous state
                previous_state = self.agent_states.get(target, {})
                consecutive_failures = previous_state.get("consecutive_failures", 0)
                last_response = previous_state.get("last_response", datetime.now())

                # Perform health check using existing detection logic
                is_failed, failure_reason, status_details = detect_failure(
                    tmux=self.tmux,
                    target=target,
                    last_response=last_response,
                    consecutive_failures=consecutive_failures,
                    max_failures=self.failure_threshold,
                    response_timeout=60,
                )

                # Build health result
                health_result = {
                    "target": target,
                    "role": role,
                    "session": agent["session"],
                    "window": agent["window"],
                    "is_failed": is_failed,
                    "failure_reason": failure_reason,
                    "status_details": status_details,
                    "check_time": datetime.now(),
                    "consecutive_failures": consecutive_failures + (1 if is_failed else 0),
                }

                health_results.append(health_result)

                # Log significant health changes
                if is_failed and not previous_state.get("is_failed", False):
                    self.logger.warning(f"Agent {target} ({role}) failure detected: {failure_reason}")
                elif not is_failed and previous_state.get("is_failed", False):
                    self.logger.info(f"Agent {target} ({role}) recovered")

            except Exception as e:
                self.logger.error(f"Health check failed for {target}: {str(e)}")

                # Create error result
                health_result = {
                    "target": target,
                    "role": role,
                    "session": agent["session"],
                    "window": agent["window"],
                    "is_failed": True,
                    "failure_reason": f"health_check_error: {str(e)}",
                    "status_details": {"health_check_failed": True},
                    "check_time": datetime.now(),
                    "consecutive_failures": previous_state.get("consecutive_failures", 0) + 1,
                }
                health_results.append(health_result)

        return health_results

    def _identify_recovery_candidates(self, health_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Identify agents that need recovery."""
        candidates: list[dict[str, Any]] = []

        for result in health_results:
            target = result["target"]

            # Check if recovery is needed
            if not result["is_failed"]:
                continue

            # Check if already in recovery
            if target in self.active_recoveries:
                self.logger.debug(f"Skipping {target} - already in recovery")
                continue

            # Check failure threshold
            if result["consecutive_failures"] < self.failure_threshold:
                self.logger.debug(
                    f"Skipping {target} - insufficient failures ({result['consecutive_failures']}/{self.failure_threshold})"
                )
                continue

            # Check recovery cooldown
            last_attempt = self.last_recovery_attempts.get(target)
            if last_attempt:
                time_since_last = datetime.now() - last_attempt
                if time_since_last.total_seconds() < self.recovery_cooldown:
                    remaining = self.recovery_cooldown - time_since_last.total_seconds()
                    self.logger.debug(f"Skipping {target} - cooldown active ({remaining:.0f}s remaining)")
                    continue

            # Add to recovery candidates
            candidates.append(result)
            self.logger.info(f"Recovery candidate identified: {target} ({result['role']}) - {result['failure_reason']}")

        return candidates

    async def _execute_recoveries(self, candidates: list[dict[str, Any]]) -> None:
        """Execute recovery for candidate agents."""
        # Limit concurrent recoveries
        available_slots = self.max_concurrent_recoveries - len(self.active_recoveries)
        if available_slots <= 0:
            self.logger.debug("No recovery slots available")
            return

        # Select candidates to recover (prioritize by failure count)
        candidates_to_recover = sorted(candidates, key=lambda x: x["consecutive_failures"], reverse=True)[
            :available_slots
        ]

        # Start recovery tasks
        recovery_tasks = []
        for candidate in candidates_to_recover:
            target = candidate["target"]

            # Mark as in recovery
            self.active_recoveries.add(target)
            self.last_recovery_attempts[target] = datetime.now()

            # Start recovery task
            task = asyncio.create_task(self._recover_agent(candidate))
            recovery_tasks.append(task)

        # Wait for all recoveries to complete
        if recovery_tasks:
            self.logger.info(f"Starting {len(recovery_tasks)} concurrent recoveries")
            await asyncio.gather(*recovery_tasks, return_exceptions=True)

    async def _recover_agent(self, agent_info: dict[str, Any]) -> None:
        """Recover a single agent."""
        target = agent_info["target"]
        role = agent_info["role"]

        try:
            self.logger.info(f"Starting recovery for {target} ({role})")
            self.total_recoveries_attempted += 1

            # Execute recovery using the recovery coordinator
            success, message, recovery_data = coordinate_agent_recovery(
                tmux=self.tmux,
                target=target,
                logger=self.logger,
                max_failures=self.failure_threshold,
                recovery_timeout=60,
                enable_auto_restart=True,
                use_structured_logging=True,
            )

            if success:
                self.total_recoveries_successful += 1
                self.logger.info(f"Recovery successful for {target}: {message}")
            else:
                self.logger.error(f"Recovery failed for {target}: {message}")

        except Exception as e:
            self.logger.error(f"Recovery error for {target}: {str(e)}")

        finally:
            # Remove from active recoveries
            self.active_recoveries.discard(target)

    def _update_agent_states(self, health_results: list[dict[str, Any]]) -> None:
        """Update internal agent state tracking."""
        for result in health_results:
            target = result["target"]

            # Update state
            self.agent_states[target] = {
                "target": target,
                "role": result["role"],
                "is_failed": result["is_failed"],
                "failure_reason": result["failure_reason"],
                "consecutive_failures": result["consecutive_failures"],
                "last_check": result["check_time"],
                "last_response": (
                    result["check_time"]
                    if not result["is_failed"]
                    else self.agent_states.get(target, {}).get("last_response", result["check_time"])
                ),
            }

    def _log_daemon_stats(self, last_cycle_duration: float) -> None:
        """Log daemon performance statistics."""
        stats = {
            "cycles_completed": self.cycle_count,
            "agents_monitored": len(self.agent_states),
            "active_recoveries": len(self.active_recoveries),
            "total_recoveries_attempted": self.total_recoveries_attempted,
            "total_recoveries_successful": self.total_recoveries_successful,
            "success_rate": ((self.total_recoveries_successful / max(self.total_recoveries_attempted, 1)) * 100),
            "last_cycle_duration": last_cycle_duration,
        }

        self.logger.info(
            f"Daemon stats: {stats['cycles_completed']} cycles, "
            f"{stats['agents_monitored']} agents, "
            f"{stats['active_recoveries']} active recoveries, "
            f"{stats['total_recoveries_attempted']} total attempts, "
            f"{stats['success_rate']:.1f}% success rate"
        )

    def _signal_handler(self, signum: int, frame: Any) -> None:
        """Handle shutdown signals."""
        signal_name = signal.Signals(signum).name
        self.logger.info(f"Received {signal_name} signal, initiating graceful shutdown...")
        self.shutdown_requested = True

    async def _shutdown(self) -> None:
        """Graceful shutdown of the daemon."""
        self.logger.info("Shutting down recovery daemon...")

        # Wait for active recoveries to complete (with timeout)
        if self.active_recoveries:
            self.logger.info(f"Waiting for {len(self.active_recoveries)} active recoveries to complete...")

            # Wait up to 2 minutes for recoveries to complete
            timeout = 120
            start_time = datetime.now()

            while self.active_recoveries and (datetime.now() - start_time).total_seconds() < timeout:
                await asyncio.sleep(1)

            if self.active_recoveries:
                self.logger.warning(f"Shutdown timeout - {len(self.active_recoveries)} recoveries still active")

        # Log final statistics
        self._log_daemon_stats(0)
        self.logger.info("Recovery daemon shutdown complete")


async def run_recovery_daemon(
    monitor_interval: int = 30,
    recovery_enabled: bool = True,
    max_concurrent_recoveries: int = 3,
    failure_threshold: int = 3,
    recovery_cooldown: int = 300,
    log_level: int = logging.INFO,
) -> None:
    """
    Run the recovery daemon with specified configuration.

    Args:
        monitor_interval: Seconds between monitoring cycles (default: 30)
        recovery_enabled: Whether to automatically trigger recovery (default: True)
        max_concurrent_recoveries: Max simultaneous recoveries (default: 3)
        failure_threshold: Failures before triggering recovery (default: 3)
        recovery_cooldown: Seconds between recovery attempts per agent (default: 300)
        log_level: Logging level (default: INFO)
    """
    daemon = RecoveryDaemon(
        monitor_interval=monitor_interval,
        recovery_enabled=recovery_enabled,
        max_concurrent_recoveries=max_concurrent_recoveries,
        failure_threshold=failure_threshold,
        recovery_cooldown=recovery_cooldown,
        log_level=log_level,
    )

    await daemon.start()


if __name__ == "__main__":
    asyncio.run(run_recovery_daemon())

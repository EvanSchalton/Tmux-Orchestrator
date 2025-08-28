"""Recovery coordination testing functionality."""

import asyncio
import logging
import time
from typing import Any

from tmux_orchestrator.core.recovery.recovery_coordinator import coordinate_agent_recovery
from tmux_orchestrator.utils.tmux import TMUXManager


class RecoveryCoordinationTest:
    """Tests for recovery coordination functionality."""

    def __init__(self, tmux_manager: TMUXManager, logger: logging.Logger):
        """Initialize recovery coordination test."""
        self.tmux = tmux_manager
        self.logger = logger

    async def test_recovery_coordination(self, target_agents: list[str]) -> dict[str, Any]:
        """Test recovery coordination without actually restarting agents."""
        coordination_results: dict[str, Any] = {
            "agents_tested": len(target_agents),
            "coordination_successful": 0,
            "coordination_failed": 0,
            "agent_results": [],
        }

        for target in target_agents:
            try:
                self.logger.info(f"Testing recovery coordination for {target}")

                # Test coordination with auto-restart disabled (dry run)
                success, message, recovery_data = coordinate_agent_recovery(
                    tmux=self.tmux,
                    target=target,
                    logger=self.logger,
                    max_failures=1,  # Lower threshold for testing
                    recovery_timeout=30,  # Shorter timeout for testing
                    enable_auto_restart=False,  # Don't actually restart
                    use_structured_logging=True,
                )

                agent_result = {
                    "target": target,
                    "coordination_success": success,
                    "message": message,
                    "recovery_data": recovery_data,
                    "health_checks_performed": len(recovery_data.get("health_checks", [])),
                    "notifications_sent": bool(recovery_data.get("recovery_start_notification", {}).get("sent", False)),
                }

                coordination_results["agent_results"].append(agent_result)

                if success or "healthy" in message.lower():
                    coordination_results["coordination_successful"] += 1
                    self.logger.info(f"Coordination test {target}: ✓ {message}")
                else:
                    coordination_results["coordination_failed"] += 1
                    self.logger.warning(f"Coordination test {target}: ✗ {message}")

            except Exception as e:
                self.logger.error(f"Coordination test failed for {target}: {str(e)}")
                coordination_results["agent_results"].append(
                    {"target": target, "coordination_success": False, "error": str(e)}
                )
                coordination_results["coordination_failed"] += 1

        return coordination_results

    async def test_concurrent_recoveries(self, target_agents: list[str]) -> dict[str, Any]:
        """Test concurrent recovery coordination.

        Args:
            target_agents: List of agents to test concurrent recovery

        Returns:
            Dictionary with concurrent recovery test results
        """
        concurrent_results: dict[str, Any] = {
            "agents_tested": len(target_agents),
            "concurrent_successful": 0,
            "concurrent_failed": 0,
            "agent_results": [],
            "total_duration": 0.0,
        }

        if not target_agents:
            return concurrent_results

        start_time = time.time()

        # Create tasks for concurrent recovery testing
        tasks = []
        for target in target_agents:
            task = self._single_recovery_test(target)
            tasks.append(task)

        # Execute all recovery tests concurrently
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for i, result in enumerate(results):
                target = target_agents[i]
                if isinstance(result, Exception):
                    self.logger.error(f"Concurrent recovery test failed for {target}: {result}")
                    concurrent_results["agent_results"].append(
                        {"target": target, "recovery_success": False, "error": str(result)}
                    )
                    concurrent_results["concurrent_failed"] += 1
                else:
                    concurrent_results["agent_results"].append(result)
                    if isinstance(result, dict) and result.get("recovery_success", False):
                        concurrent_results["concurrent_successful"] += 1
                    else:
                        concurrent_results["concurrent_failed"] += 1

        except Exception as e:
            self.logger.error(f"Concurrent recovery test failed: {e}")

        concurrent_results["total_duration"] = time.time() - start_time
        return concurrent_results

    async def _single_recovery_test(self, target: str) -> dict[str, Any]:
        """Perform a single recovery test for concurrent testing.

        Args:
            target: Agent target to test

        Returns:
            Dictionary with single recovery test results
        """
        try:
            success, message, recovery_data = coordinate_agent_recovery(
                tmux=self.tmux,
                target=target,
                logger=self.logger,
                max_failures=1,
                recovery_timeout=15,  # Shorter timeout for concurrent testing
                enable_auto_restart=False,
                use_structured_logging=True,
            )

            return {
                "target": target,
                "recovery_success": success,
                "message": message,
                "recovery_data": recovery_data,
                "duration": recovery_data.get("total_duration", 0.0),
            }

        except Exception as e:
            return {
                "target": target,
                "recovery_success": False,
                "error": str(e),
                "duration": 0.0,
            }

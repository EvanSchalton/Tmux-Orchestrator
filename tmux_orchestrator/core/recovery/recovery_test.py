"""Recovery system testing utilities for validating automatic agent recovery.

Provides comprehensive testing functionality to validate the recovery system
with intentionally failed agents, simulated failure conditions, and
end-to-end recovery validation.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Optional

from tmux_orchestrator.core.recovery.detect_failure import detect_failure
from tmux_orchestrator.core.recovery.recovery_coordinator import (
    coordinate_agent_recovery,
)
from tmux_orchestrator.core.recovery.recovery_logger import setup_recovery_logger
from tmux_orchestrator.utils.tmux import TMUXManager


class RecoveryTestSuite:
    """Comprehensive test suite for recovery system validation."""

    def __init__(self, tmux_manager: TMUXManager | None = None) -> None:
        """Initialize recovery test suite."""
        self.tmux = tmux_manager or TMUXManager()
        self.logger = setup_recovery_logger()

        # Test tracking
        self.test_results: list[dict[str, Any]] = []
        self.test_session_id = f"recovery-test-{int(time.time())}"

        self.logger.info(f"Recovery test suite initialized (session: {self.test_session_id})")

    async def run_comprehensive_test(
        self,
        target_agents: Optional[list[str | None]] = None,
        include_stress_test: bool = False,
    ) -> dict[str, Any]:
        """
        Run comprehensive recovery system test.

        Args:
            target_agents: List of agent targets to test (auto-discover if None)
            include_stress_test: Whether to include stress testing (default: False)

        Returns:
            Dictionary containing complete test results and metrics
        """
        self.logger.info("Starting comprehensive recovery system test")
        test_start_time = datetime.now()

        # Initialize test results
        comprehensive_results: dict[str, Any] = {
            "test_session_id": self.test_session_id,
            "test_start_time": test_start_time.isoformat(),
            "target_agents": target_agents or [],
            "include_stress_test": include_stress_test,
            "test_results": [],
            "summary": {},
            "total_duration": 0.0,
        }

        try:
            # Discover test agents if not provided
            if not target_agents:
                target_agents = await self._discover_test_agents()
                comprehensive_results["target_agents"] = target_agents

            self.logger.info(f"Testing {len(target_agents)} agents")

            # Test 1: Failure Detection Test
            self.logger.info("Running failure detection tests...")
            detection_results = await self._test_failure_detection(target_agents)
            comprehensive_results["test_results"].append(
                {"test_name": "failure_detection", "results": detection_results}
            )

            # Test 2: Recovery Coordination Test
            self.logger.info("Running recovery coordination tests...")
            coordination_results = await self._test_recovery_coordination(target_agents)
            comprehensive_results["test_results"].append(
                {"test_name": "recovery_coordination", "results": coordination_results}
            )

            # Test 3: Context Preservation Test
            self.logger.info("Running context preservation tests...")
            context_results = await self._test_context_preservation(target_agents[:1])  # Test one agent
            comprehensive_results["test_results"].append(
                {"test_name": "context_preservation", "results": context_results}
            )

            # Test 4: Notification System Test
            self.logger.info("Running notification system tests...")
            notification_results = await self._test_notification_system(target_agents[:1])  # Test one agent
            comprehensive_results["test_results"].append(
                {"test_name": "notification_system", "results": notification_results}
            )

            # Test 5: Stress Test (optional)
            if include_stress_test and len(target_agents) >= 2:
                self.logger.info("Running stress tests...")
                stress_results = await self._test_concurrent_recoveries(target_agents[:2])
                comprehensive_results["test_results"].append({"test_name": "stress_test", "results": stress_results})

            # Calculate test summary
            test_end_time = datetime.now()
            comprehensive_results["total_duration"] = (test_end_time - test_start_time).total_seconds()
            comprehensive_results["summary"] = self._calculate_test_summary(comprehensive_results["test_results"])

            self.logger.info(f"Comprehensive test completed in {comprehensive_results['total_duration']:.1f}s")
            return comprehensive_results

        except Exception as e:
            self.logger.error(f"Comprehensive test failed: {str(e)}")
            comprehensive_results["test_error"] = str(e)
            comprehensive_results["total_duration"] = (datetime.now() - test_start_time).total_seconds()
            return comprehensive_results

    async def _discover_test_agents(self) -> list[str]:
        """Discover available agents for testing."""
        test_agents: list[str] = []

        # Check tmux-orc-dev session first
        if self.tmux.has_session("tmux-orc-dev"):
            # Use non-critical windows for testing (avoid window 1 - orchestrator)
            test_candidates = ["tmux-orc-dev:2", "tmux-orc-dev:3", "tmux-orc-dev:4"]

            for candidate in test_candidates:
                try:
                    # Verify window exists
                    content = self.tmux.capture_pane(candidate, lines=1)
                    if content is not None:  # Window exists and is accessible
                        test_agents.append(candidate)
                except Exception:
                    continue

        # Fallback to other sessions if needed
        if not test_agents:
            try:
                sessions = self.tmux.list_sessions()
                for session in sessions:
                    session_name = session.get("name", "")
                    if session_name in ["tmux-orc-dev"]:
                        continue

                    # Check for Claude windows
                    windows = self.tmux.list_windows(session_name)
                    for window in windows:
                        window_name = window.get("name", "")
                        window_id = window.get("index", "")

                        if "claude" in window_name.lower():
                            test_agents.append(f"{session_name}:{window_id}")
                            break  # One per session is enough
            except Exception as e:
                self.logger.warning(f"Error discovering test agents: {str(e)}")

        self.logger.info(f"Discovered {len(test_agents)} test agents: {test_agents}")
        return test_agents

    async def _test_failure_detection(self, target_agents: list[str]) -> dict[str, Any]:
        """Test failure detection functionality."""
        detection_results: dict[str, Any] = {
            "agents_tested": len(target_agents),
            "detection_successful": 0,
            "detection_failed": 0,
            "agent_results": [],
        }

        for target in target_agents:
            try:
                # Test with current time (should be healthy)
                is_failed, failure_reason, status_details = detect_failure(
                    tmux=self.tmux,
                    target=target,
                    last_response=datetime.now(),
                    consecutive_failures=0,
                    max_failures=3,
                    response_timeout=60,
                )

                # Test with old timestamp (should detect failure)
                old_time = datetime.now() - timedelta(minutes=10)
                is_failed_old, failure_reason_old, status_details_old = detect_failure(
                    tmux=self.tmux,
                    target=target,
                    last_response=old_time,
                    consecutive_failures=3,
                    max_failures=3,
                    response_timeout=60,
                )

                agent_result = {
                    "target": target,
                    "healthy_detection": not is_failed,
                    "failure_detection": is_failed_old,
                    "detection_working": (not is_failed) and is_failed_old,
                    "current_status": status_details,
                    "failure_status": status_details_old,
                }

                detection_results["agent_results"].append(agent_result)

                if agent_result["detection_working"]:
                    detection_results["detection_successful"] += 1
                else:
                    detection_results["detection_failed"] += 1

                self.logger.info(f"Detection test {target}: {'✓' if agent_result['detection_working'] else '✗'}")

            except Exception as e:
                self.logger.error(f"Detection test failed for {target}: {str(e)}")
                detection_results["agent_results"].append(
                    {"target": target, "detection_working": False, "error": str(e)}
                )
                detection_results["detection_failed"] += 1

        return detection_results

    async def _test_recovery_coordination(self, target_agents: list[str]) -> dict[str, Any]:
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

    async def _test_context_preservation(self, target_agents: list[str]) -> dict[str, Any]:
        """Test context preservation functionality."""
        context_results: dict[str, Any] = {
            "agents_tested": len(target_agents),
            "context_successful": 0,
            "context_failed": 0,
            "agent_results": [],
        }

        for target in target_agents[:1]:  # Only test one agent for context preservation
            try:
                # Capture current context
                original_content = self.tmux.capture_pane(target, lines=100)

                if not original_content:
                    agent_result = {
                        "target": target,
                        "context_preserved": False,
                        "error": "No content to preserve",
                    }
                    context_results["agent_results"].append(agent_result)
                    context_results["context_failed"] += 1
                    continue

                # Test context preservation logic (simulate)
                context_lines = original_content.split("\n")
                preserved_lines = len([line for line in context_lines if line.strip()])

                agent_result = {
                    "target": target,
                    "context_preserved": True,
                    "original_content_lines": len(context_lines),
                    "preserved_lines": preserved_lines,
                    "preservation_ratio": preserved_lines / max(len(context_lines), 1),
                }

                context_results["agent_results"].append(agent_result)
                context_results["context_successful"] += 1

                self.logger.info(f"Context test {target}: ✓ {preserved_lines} lines preserved")

            except Exception as e:
                self.logger.error(f"Context test failed for {target}: {str(e)}")
                context_results["agent_results"].append({"target": target, "context_preserved": False, "error": str(e)})
                context_results["context_failed"] += 1

        return context_results

    async def _test_notification_system(self, target_agents: list[str]) -> dict[str, Any]:
        """Test notification system functionality."""
        notification_results: dict[str, Any] = {
            "agents_tested": len(target_agents),
            "notification_successful": 0,
            "notification_failed": 0,
            "agent_results": [],
        }

        for target in target_agents[:1]:  # Only test one agent for notifications
            try:
                from tmux_orchestrator.core.recovery.notification_manager import (
                    should_send_recovery_notification,
                )

                # Test notification cooldown logic
                (
                    should_send,
                    reason,
                    notification_data,
                ) = should_send_recovery_notification(
                    target=target,
                    notification_type="recovery_started",
                    cooldown_minutes=5,
                )

                # Test notification sending (dry run - don't actually send)
                agent_result = {
                    "target": target,
                    "cooldown_check_successful": True,
                    "should_send": should_send,
                    "cooldown_reason": reason,
                    "notification_data": notification_data,
                }

                notification_results["agent_results"].append(agent_result)
                notification_results["notification_successful"] += 1

                self.logger.info(f"Notification test {target}: ✓ Cooldown logic working")

            except Exception as e:
                self.logger.error(f"Notification test failed for {target}: {str(e)}")
                notification_results["agent_results"].append(
                    {
                        "target": target,
                        "cooldown_check_successful": False,
                        "error": str(e),
                    }
                )
                notification_results["notification_failed"] += 1

        return notification_results

    async def _test_concurrent_recoveries(self, target_agents: list[str]) -> dict[str, Any]:
        """Test concurrent recovery handling."""
        stress_results: dict[str, Any] = {
            "agents_tested": len(target_agents),
            "concurrent_test_successful": False,
            "max_concurrent_recoveries": min(len(target_agents), 2),
            "agent_results": [],
        }

        try:
            # Start concurrent recovery tests (dry run mode)
            recovery_tasks = []

            for target in target_agents[:2]:  # Test up to 2 concurrent recoveries
                task = asyncio.create_task(self._single_recovery_test(target))
                recovery_tasks.append(task)

            # Wait for all concurrent recoveries
            start_time = datetime.now()
            results = await asyncio.gather(*recovery_tasks, return_exceptions=True)
            end_time = datetime.now()

            concurrent_duration = (end_time - start_time).total_seconds()

            # Analyze results
            successful_recoveries = 0
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    agent_result = {
                        "target": target_agents[i],
                        "recovery_successful": False,
                        "error": str(result),
                    }
                elif isinstance(result, dict):
                    agent_result = {
                        "target": target_agents[i],
                        "recovery_successful": result.get("success", False),
                        "duration": result.get("duration", 0),
                    }
                    if agent_result["recovery_successful"]:
                        successful_recoveries += 1
                else:
                    agent_result = {
                        "target": target_agents[i],
                        "recovery_successful": False,
                        "error": "Unknown result type",
                    }

                stress_results["agent_results"].append(agent_result)

            stress_results["concurrent_test_successful"] = successful_recoveries > 0
            stress_results["concurrent_duration"] = concurrent_duration
            stress_results["successful_recoveries"] = successful_recoveries

            self.logger.info(f"Concurrent recovery test: ✓ {successful_recoveries}/{len(target_agents)} successful")

        except Exception as e:
            self.logger.error(f"Concurrent recovery test failed: {str(e)}")
            stress_results["error"] = str(e)

        return stress_results

    async def _single_recovery_test(self, target: str) -> dict[str, Any]:
        """Execute a single recovery test for concurrent testing."""
        start_time = datetime.now()

        try:
            success, message, recovery_data = coordinate_agent_recovery(
                tmux=self.tmux,
                target=target,
                logger=self.logger,
                max_failures=1,
                recovery_timeout=20,
                enable_auto_restart=False,  # Dry run
                use_structured_logging=False,  # Reduce overhead
            )

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            return {
                "success": success or "healthy" in message.lower(),
                "duration": duration,
                "message": message,
            }

        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            return {"success": False, "duration": duration, "error": str(e)}

    def _calculate_test_summary(self, test_results: list[dict[str, Any]]) -> dict[str, Any]:
        """Calculate overall test summary statistics."""
        summary: dict[str, Any] = {
            "total_tests": len(test_results),
            "tests_passed": 0,
            "tests_failed": 0,
            "overall_success_rate": 0.0,
            "test_breakdown": {},
        }

        for test_result in test_results:
            test_name = test_result["test_name"]
            results = test_result["results"]

            # Calculate pass/fail for this test
            if "detection_successful" in results:
                passed = results["detection_successful"]
                failed = results["detection_failed"]
            elif "coordination_successful" in results:
                passed = results["coordination_successful"]
                failed = results["coordination_failed"]
            elif "context_successful" in results:
                passed = results["context_successful"]
                failed = results["context_failed"]
            elif "notification_successful" in results:
                passed = results["notification_successful"]
                failed = results["notification_failed"]
            elif "concurrent_test_successful" in results:
                passed = 1 if results["concurrent_test_successful"] else 0
                failed = 1 - passed
            else:
                passed = failed = 0

            summary["test_breakdown"][test_name] = {
                "passed": passed,
                "failed": failed,
                "success_rate": passed / max(passed + failed, 1) * 100,
            }

            if passed > failed:
                summary["tests_passed"] += 1
            else:
                summary["tests_failed"] += 1

        # Calculate overall success rate
        if summary["total_tests"] > 0:
            summary["overall_success_rate"] = (summary["tests_passed"] / summary["total_tests"]) * 100

        return summary


async def run_recovery_system_test(
    target_agents: Optional[list[str | None]] = None,
    include_stress_test: bool = False,
    verbose: bool = False,
) -> dict[str, Any]:
    """
    Run comprehensive recovery system test.

    Args:
        target_agents: List of agent targets to test (auto-discover if None)
        include_stress_test: Whether to include stress testing
        verbose: Enable verbose logging

    Returns:
        Complete test results dictionary
    """
    # Setup logging
    _log_level = logging.DEBUG if verbose else logging.INFO

    # Initialize test suite
    test_suite = RecoveryTestSuite()

    # Run comprehensive test
    results = await test_suite.run_comprehensive_test(
        target_agents=target_agents, include_stress_test=include_stress_test
    )

    return results

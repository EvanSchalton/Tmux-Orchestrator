"""Recovery system testing utilities for validating automatic agent recovery.

This module has been refactored into focused test components following SRP:
- AgentDiscoveryTest: Agent discovery functionality
- FailureDetectionTest: Failure detection testing
- RecoveryCoordinationTest: Recovery coordination testing
- ContextPreservationTest: Context preservation testing
- NotificationSystemTest: Notification system testing
- TestSummaryCalculator: Test summary calculation utilities

The RecoveryTestSuite class provides the same interface for backwards compatibility.
"""

import time
from datetime import datetime
from typing import Any, Optional

from tmux_orchestrator.core.recovery.recovery_logger import setup_recovery_logger
from tmux_orchestrator.utils.tmux import TMUXManager

from .agent_discovery import AgentDiscoveryTest
from .context_preservation_tests import ContextPreservationTest
from .failure_detection_tests import FailureDetectionTest
from .notification_tests import NotificationSystemTest
from .recovery_coordination_tests import RecoveryCoordinationTest
from .test_summary import TestSummaryCalculator


class RecoveryTestSuite:
    """Comprehensive test suite for recovery system validation.

    This class now delegates to specialized test components following SRP.
    """

    def __init__(self, tmux_manager: TMUXManager | None = None) -> None:
        """Initialize recovery test suite."""
        self.tmux = tmux_manager or TMUXManager()
        self.logger = setup_recovery_logger()

        # Test tracking
        self.test_results: list[dict[str, Any]] = []
        self.test_session_id = f"recovery-test-{int(time.time())}"

        # Initialize test components
        self.agent_discovery = AgentDiscoveryTest(self.tmux, self.logger)
        self.failure_detection = FailureDetectionTest(self.tmux, self.logger)
        self.recovery_coordination = RecoveryCoordinationTest(self.tmux, self.logger)
        self.context_preservation = ContextPreservationTest(self.tmux, self.logger)
        self.notification_system = NotificationSystemTest(self.tmux, self.logger)
        self.summary_calculator = TestSummaryCalculator()

        self.logger.info(f"Recovery test suite initialized (session: {self.test_session_id})")

    async def run_comprehensive_test(
        self,
        target_agents: Optional[list[str]] = None,
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
                discovered_agents = await self.agent_discovery.discover_test_agents()
                target_agents = [agent for agent in (discovered_agents or []) if agent is not None]
                comprehensive_results["target_agents"] = target_agents

            self.logger.info(f"Testing {len(target_agents)} agents")

            # Test 1: Failure Detection Test
            self.logger.info("Running failure detection tests...")
            detection_results = await self.failure_detection.test_failure_detection(target_agents)
            comprehensive_results["test_results"].append(
                {"test_name": "failure_detection", "results": detection_results}
            )

            # Test 2: Recovery Coordination Test
            self.logger.info("Running recovery coordination tests...")
            coordination_results = await self.recovery_coordination.test_recovery_coordination(target_agents)
            comprehensive_results["test_results"].append(
                {"test_name": "recovery_coordination", "results": coordination_results}
            )

            # Test 3: Context Preservation Test
            self.logger.info("Running context preservation tests...")
            context_results = await self.context_preservation.test_context_preservation(target_agents[:1])
            comprehensive_results["test_results"].append(
                {"test_name": "context_preservation", "results": context_results}
            )

            # Test 4: Notification System Test
            self.logger.info("Running notification system tests...")
            notification_results = await self.notification_system.test_notification_system(target_agents)
            comprehensive_results["test_results"].append(
                {"test_name": "notification_system", "results": notification_results}
            )

            # Test 5: Concurrent Recovery Test (if stress testing enabled)
            if include_stress_test and len(target_agents) > 1:
                self.logger.info("Running concurrent recovery tests...")
                concurrent_results = await self.recovery_coordination.test_concurrent_recoveries(target_agents[:2])
                comprehensive_results["test_results"].append(
                    {"test_name": "concurrent_recovery", "results": concurrent_results}
                )

            # Calculate summary
            comprehensive_results["summary"] = self.summary_calculator.calculate_test_summary(
                comprehensive_results["test_results"]
            )

            # Calculate total duration
            test_end_time = datetime.now()
            comprehensive_results["total_duration"] = (test_end_time - test_start_time).total_seconds()
            comprehensive_results["test_end_time"] = test_end_time.isoformat()

            self.logger.info(f"Comprehensive test completed in {comprehensive_results['total_duration']:.2f}s")

        except Exception as e:
            self.logger.error(f"Comprehensive test failed: {str(e)}")
            comprehensive_results["error"] = str(e)
            comprehensive_results["total_duration"] = (datetime.now() - test_start_time).total_seconds()

        return comprehensive_results

    # Backward compatibility methods that delegate to components
    async def _discover_test_agents(self) -> list[str]:
        """Discover available agents for testing."""
        return await self.agent_discovery.discover_test_agents()

    async def _test_failure_detection(self, target_agents: list[str]) -> dict[str, Any]:
        """Test failure detection functionality."""
        return await self.failure_detection.test_failure_detection(target_agents)

    async def _test_recovery_coordination(self, target_agents: list[str]) -> dict[str, Any]:
        """Test recovery coordination without actually restarting agents."""
        return await self.recovery_coordination.test_recovery_coordination(target_agents)

    async def _test_context_preservation(self, target_agents: list[str]) -> dict[str, Any]:
        """Test context preservation functionality."""
        return await self.context_preservation.test_context_preservation(target_agents)

    async def _test_notification_system(self, target_agents: list[str]) -> dict[str, Any]:
        """Test notification system functionality."""
        return await self.notification_system.test_notification_system(target_agents)

    async def _test_concurrent_recoveries(self, target_agents: list[str]) -> dict[str, Any]:
        """Test concurrent recovery coordination."""
        return await self.recovery_coordination.test_concurrent_recoveries(target_agents)

    async def _single_recovery_test(self, target: str) -> dict[str, Any]:
        """Perform a single recovery test for concurrent testing."""
        return await self.recovery_coordination._single_recovery_test(target)

    def _calculate_test_summary(self, test_results: list[dict[str, Any]]) -> dict[str, Any]:
        """Calculate overall test summary statistics."""
        return self.summary_calculator.calculate_test_summary(test_results)


# Export main class for backwards compatibility
async def run_recovery_system_test(
    target_agents: Optional[list[str]] = None,
    include_stress_test: bool = False,
    tmux_manager: Optional[TMUXManager] = None,
) -> dict[str, Any]:
    """Run a complete recovery system test suite.

    Args:
        target_agents: List of agent targets to test
        include_stress_test: Whether to include stress testing
        tmux_manager: Optional TMUX manager instance

    Returns:
        Dictionary with comprehensive test results
    """
    test_suite = RecoveryTestSuite(tmux_manager)
    return await test_suite.run_comprehensive_test(target_agents, include_stress_test)


# Export all public classes for convenience
__all__ = [
    "RecoveryTestSuite",
    "AgentDiscoveryTest",
    "FailureDetectionTest",
    "RecoveryCoordinationTest",
    "ContextPreservationTest",
    "NotificationSystemTest",
    "TestSummaryCalculator",
    "run_recovery_system_test",
]

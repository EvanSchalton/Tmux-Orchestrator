"""Failure detection testing functionality."""

import logging
from datetime import datetime, timedelta
from typing import Any

from tmux_orchestrator.core.recovery.detect_failure import detect_failure
from tmux_orchestrator.utils.tmux import TMUXManager


class FailureDetectionTest:
    """Tests for failure detection functionality."""

    def __init__(self, tmux_manager: TMUXManager, logger: logging.Logger):
        """Initialize failure detection test."""
        self.tmux = tmux_manager
        self.logger = logger

    async def test_failure_detection(self, target_agents: list[str]) -> dict[str, Any]:
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

    def test_detection_accuracy(self, target: str) -> dict[str, Any]:
        """Test detection accuracy for a single agent.

        Args:
            target: Agent target to test

        Returns:
            Dictionary with accuracy test results
        """
        results: dict[str, Any] = {
            "target": target,
            "healthy_tests": 0,
            "failure_tests": 0,
            "accurate_detections": 0,
            "false_positives": 0,
            "false_negatives": 0,
        }

        # Test healthy state detection (recent timestamp)
        try:
            is_failed, _, _ = detect_failure(
                tmux=self.tmux,
                target=target,
                last_response=datetime.now(),
                consecutive_failures=0,
                max_failures=3,
                response_timeout=60,
            )
            results["healthy_tests"] = 1
            if not is_failed:
                results["accurate_detections"] += 1
            else:
                results["false_positives"] += 1
        except Exception as e:
            self.logger.error(f"Healthy detection test failed for {target}: {e}")

        # Test failure state detection (old timestamp)
        try:
            old_time = datetime.now() - timedelta(minutes=15)
            is_failed, _, _ = detect_failure(
                tmux=self.tmux,
                target=target,
                last_response=old_time,
                consecutive_failures=5,
                max_failures=3,
                response_timeout=60,
            )
            results["failure_tests"] = 1
            if is_failed:
                results["accurate_detections"] += 1
            else:
                results["false_negatives"] += 1
        except Exception as e:
            self.logger.error(f"Failure detection test failed for {target}: {e}")

        return results

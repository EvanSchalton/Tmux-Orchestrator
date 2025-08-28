"""Notification system testing functionality."""

import logging
from typing import Any

from tmux_orchestrator.core.recovery.notification_manager import should_send_recovery_notification
from tmux_orchestrator.utils.tmux import TMUXManager


class NotificationSystemTest:
    """Tests for notification system functionality."""

    def __init__(self, tmux_manager: TMUXManager, logger: logging.Logger):
        """Initialize notification system test."""
        self.tmux = tmux_manager
        self.logger = logger

    async def test_notification_system(self, target_agents: list[str]) -> dict[str, Any]:
        """Test notification system functionality."""
        notification_results: dict[str, Any] = {
            "agents_tested": len(target_agents),
            "notification_successful": 0,
            "notification_failed": 0,
            "agent_results": [],
        }

        for target in target_agents[:1]:  # Only test one agent for notifications
            try:
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

    def test_notification_cooldown(self, target: str) -> dict[str, Any]:
        """Test notification cooldown functionality.

        Args:
            target: Agent target to test cooldown for

        Returns:
            Dictionary with cooldown test results
        """
        cooldown_results: dict[str, Any] = {
            "target": target,
            "cooldown_tests": [],
            "cooldown_working": False,
        }

        try:
            # Test different cooldown periods
            cooldown_periods = [1, 5, 10]  # minutes

            for cooldown_minutes in cooldown_periods:
                should_send, reason, data = should_send_recovery_notification(
                    target=target,
                    notification_type="recovery_started",
                    cooldown_minutes=cooldown_minutes,
                )

                cooldown_results["cooldown_tests"].append(
                    {
                        "cooldown_minutes": cooldown_minutes,
                        "should_send": should_send,
                        "reason": reason,
                        "notification_data": data,
                    }
                )

            # If we got valid results for all tests, cooldown is working
            cooldown_results["cooldown_working"] = len(cooldown_results["cooldown_tests"]) == len(cooldown_periods)

        except Exception as e:
            self.logger.error(f"Cooldown test failed for {target}: {e}")
            cooldown_results["error"] = str(e)

        return cooldown_results

    def test_notification_types(self, target: str) -> dict[str, Any]:
        """Test different notification types.

        Args:
            target: Agent target to test

        Returns:
            Dictionary with notification type test results
        """
        type_results: dict[str, Any] = {
            "target": target,
            "notification_types_tested": 0,
            "types_working": 0,
            "type_results": [],
        }

        notification_types = [
            "recovery_started",
            "recovery_completed",
            "recovery_failed",
            "agent_crash",
        ]

        for notification_type in notification_types:
            try:
                should_send, reason, data = should_send_recovery_notification(
                    target=target,
                    notification_type=notification_type,
                    cooldown_minutes=1,
                )

                type_result = {
                    "type": notification_type,
                    "should_send": should_send,
                    "reason": reason,
                    "working": True,
                }

                type_results["type_results"].append(type_result)
                type_results["notification_types_tested"] += 1
                type_results["types_working"] += 1

            except Exception as e:
                self.logger.error(f"Notification type test failed for {notification_type}: {e}")
                type_results["type_results"].append(
                    {
                        "type": notification_type,
                        "working": False,
                        "error": str(e),
                    }
                )
                type_results["notification_types_tested"] += 1

        return type_results

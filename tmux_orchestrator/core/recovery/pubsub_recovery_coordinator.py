"""
Pubsub-enhanced recovery coordination system.

This module provides high-performance recovery coordination using the messaging daemon
for sub-100ms notification delivery during critical recovery operations.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Set

from tmux_orchestrator.core.config import Config
from tmux_orchestrator.core.messaging_daemon import DaemonClient
from tmux_orchestrator.core.monitoring.pubsub_integration import MonitorPubsubClient, PriorityMessageRouter
from tmux_orchestrator.utils.tmux import TMUXManager


class PubsubRecoveryCoordinator:
    """High-performance recovery coordinator using pubsub messaging."""

    def __init__(self, tmux: TMUXManager, config: Config, logger: logging.Logger):
        """Initialize the pubsub-enhanced recovery coordinator."""
        self.tmux = tmux
        self.config = config
        self.logger = logger
        
        # Initialize pubsub components
        self.pubsub_client = MonitorPubsubClient(logger)
        self.priority_router = PriorityMessageRouter(self.pubsub_client)
        
        # Recovery state tracking
        self._active_recoveries: Set[str] = set()
        self._recovery_history: Dict[str, List[Dict]] = {}
        self._pm_recovery_grace_period = 180  # 3 minutes grace after PM recovery
        
    async def notify_recovery_needed(
        self,
        target: str,
        issue: str,
        session: str,
        recovery_type: str = "agent",
        metadata: Optional[Dict] = None,
    ) -> bool:
        """
        Send high-priority recovery notification via pubsub.
        
        Args:
            target: Target agent/PM identifier
            issue: Description of the issue
            session: Session name
            recovery_type: Type of recovery (agent, pm, team)
            metadata: Additional recovery metadata
            
        Returns:
            Success status
        """
        if metadata is None:
            metadata = {}

        # Check if recovery is already active
        recovery_key = f"{session}:{target}"
        if recovery_key in self._active_recoveries:
            self.logger.debug(f"Recovery already active for {recovery_key}")
            return True

        # Mark recovery as active
        self._active_recoveries.add(recovery_key)

        # Build recovery message
        timestamp = datetime.now().strftime("%H:%M:%S")
        recovery_msg = self._build_recovery_message(target, issue, recovery_type, timestamp)

        # Determine priority based on recovery type
        priority = self._get_recovery_priority(recovery_type, issue)

        # Find PM to notify
        pm_target = self._find_pm_for_recovery(session)
        if not pm_target:
            self.logger.error(f"No PM found for recovery in session {session}")
            self._active_recoveries.remove(recovery_key)
            return False

        # Send via priority router for optimal delivery
        tags = ["recovery", recovery_type, "monitoring"]
        success = await self.priority_router.route_message(
            pm_target,
            recovery_msg,
            priority,
            tags,
        )

        # Track recovery in history
        self._track_recovery(recovery_key, {
            "timestamp": datetime.now(),
            "target": target,
            "issue": issue,
            "type": recovery_type,
            "priority": priority,
            "notified": success,
        })

        if success:
            self.logger.info(
                f"Recovery notification sent to PM {pm_target} for {target} "
                f"(priority: {priority}, issue: {issue})"
            )
        else:
            self.logger.error(f"Failed to send recovery notification for {target}")
            self._active_recoveries.remove(recovery_key)

        return success

    async def notify_recovery_complete(
        self,
        target: str,
        session: str,
        recovery_type: str = "agent",
        success: bool = True,
    ) -> bool:
        """Notify PM that recovery is complete."""
        recovery_key = f"{session}:{target}"
        
        # Remove from active recoveries
        self._active_recoveries.discard(recovery_key)

        # Build completion message
        status = "successful" if success else "failed"
        message = f"✅ RECOVERY COMPLETE: {target} - Recovery {status}"
        if not success:
            message = f"❌ RECOVERY FAILED: {target} - Manual intervention required"

        # Find PM
        pm_target = self._find_pm_for_recovery(session)
        if not pm_target:
            return False

        # Send completion notification (normal priority for success, high for failure)
        priority = "normal" if success else "high"
        return await self.priority_router.route_message(
            pm_target,
            message,
            priority,
            ["recovery", "complete", recovery_type],
        )

    async def notify_team_recovery(
        self,
        session: str,
        affected_agents: List[str],
        recovery_plan: str,
    ) -> bool:
        """Send team-wide recovery notification."""
        if not affected_agents:
            return True

        # Build team recovery message
        timestamp = datetime.now().strftime("%H:%M:%S")
        message = (
            f"🚨 TEAM RECOVERY INITIATED - {timestamp}\\n"
            f"Session: {session}\\n"
            f"Affected Agents: {', '.join(affected_agents)}\\n"
            f"Recovery Plan: {recovery_plan}"
        )

        # Notify all agents in parallel for speed
        tasks = []
        for agent in affected_agents:
            task = self.priority_router.route_message(
                agent,
                message,
                "high",
                ["recovery", "team", "broadcast"],
            )
            tasks.append(task)

        # Execute notifications concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for r in results if r is True)
        self.logger.info(
            f"Team recovery notification sent to {success_count}/{len(affected_agents)} agents"
        )

        return success_count > 0

    async def check_pm_recovery_grace(self, pm_target: str) -> bool:
        """Check if PM is in recovery grace period."""
        # Check recovery history for recent PM recovery
        pm_key = pm_target.replace(":", "_")
        pm_history = self._recovery_history.get(pm_key, [])
        
        if pm_history:
            latest_recovery = pm_history[-1]
            recovery_time = latest_recovery.get("timestamp")
            if recovery_time:
                elapsed = (datetime.now() - recovery_time).total_seconds()
                if elapsed < self._pm_recovery_grace_period:
                    self.logger.debug(
                        f"PM {pm_target} in grace period "
                        f"({elapsed:.0f}s < {self._pm_recovery_grace_period}s)"
                    )
                    return True
                    
        return False

    async def batch_recovery_status(self) -> Dict[str, any]:
        """Get comprehensive recovery status with performance metrics."""
        # Get pubsub performance stats
        perf_stats = self.pubsub_client.get_performance_stats()
        
        status = {
            "active_recoveries": list(self._active_recoveries),
            "recovery_count": len(self._active_recoveries),
            "history_entries": sum(len(h) for h in self._recovery_history.values()),
            "pubsub_performance": perf_stats,
            "meeting_performance_target": perf_stats.get("meeting_target", False),
        }

        # Check if we need to flush low-priority messages
        if hasattr(self.priority_router, "_batch_queue"):
            pending_low = len(self.priority_router._batch_queue.get("low", []))
            if pending_low > 0:
                flushed = await self.priority_router.flush_batch_queue()
                status["batch_flushed"] = flushed

        return status

    def _build_recovery_message(
        self,
        target: str,
        issue: str,
        recovery_type: str,
        timestamp: str,
    ) -> str:
        """Build formatted recovery message."""
        emoji_map = {
            "agent": "🔧",
            "pm": "🚨",
            "team": "⚡",
        }
        
        emoji = emoji_map.get(recovery_type, "🔧")
        type_label = recovery_type.upper()
        
        return (
            f"{emoji} {type_label} RECOVERY NEEDED - {timestamp}\\n"
            f"Target: {target}\\n"
            f"Issue: {issue}\\n"
            f"Action Required: Please investigate and recover {target}"
        )

    def _get_recovery_priority(self, recovery_type: str, issue: str) -> str:
        """Determine message priority based on recovery type and issue."""
        # Critical priorities
        if recovery_type == "pm":
            return "critical"
        if "crash" in issue.lower() or "failure" in issue.lower():
            return "critical"
            
        # High priorities
        if recovery_type == "team":
            return "high"
        if "not responding" in issue.lower():
            return "high"
            
        # Normal priority for standard agent issues
        return "normal"

    def _find_pm_for_recovery(self, session: str) -> Optional[str]:
        """Find PM in session for recovery notification."""
        try:
            windows = self.tmux.list_windows(session)
            for window in windows:
                window_name = window.get("name", "").lower()
                if "pm" in window_name or "project-manager" in window_name:
                    window_idx = window.get("index", "0")
                    return f"{session}:{window_idx}"
            return None
        except Exception as e:
            self.logger.error(f"Error finding PM in session {session}: {e}")
            return None

    def _track_recovery(self, recovery_key: str, recovery_data: Dict) -> None:
        """Track recovery in history."""
        history_key = recovery_key.replace(":", "_")
        if history_key not in self._recovery_history:
            self._recovery_history[history_key] = []
        
        self._recovery_history[history_key].append(recovery_data)
        
        # Limit history size
        if len(self._recovery_history[history_key]) > 100:
            self._recovery_history[history_key] = self._recovery_history[history_key][-50:]
"""Monitor module - refactored into focused components while maintaining backwards compatibility.

This module maintains the original IdleMonitor interface while internally using the new
modular architecture following SOLID principles and one-function-per-file patterns.
"""

# Import all components for internal use
# Module-level config for testing (backwards compatibility)
from typing import Any

from .agent_discovery import AgentDiscovery
from .daemon import DaemonAlreadyRunningError, DaemonManager
from .health_checker import HealthChecker
from .health_status import AgentHealthStatus
from .idle_detector import IdleDetector

# Import the refactored IdleMonitor that uses these components
from .idle_monitor import IdleMonitor
from .notifier import MonitorNotifier
from .recovery_manager import RecoveryManager
from .supervisor import SupervisorManager
from .terminal_cache import TerminalCache

config: dict[str, Any] = {}

# Export the original interface for backwards compatibility
__all__ = [
    "IdleMonitor",
    "DaemonAlreadyRunningError",
    "AgentHealthStatus",
    "TerminalCache",
    "config",
    # New components (available but not part of original interface)
    "DaemonManager",
    "HealthChecker",
    "IdleDetector",
    "MonitorNotifier",
    "RecoveryManager",
    "SupervisorManager",
    "AgentDiscovery",
]

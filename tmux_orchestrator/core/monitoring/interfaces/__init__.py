"""
Service contracts and interfaces for monitoring components.

This module defines the abstract interfaces following Interface Segregation Principle
to ensure proper dependency inversion throughout the monitoring system.

The interfaces have been decomposed into focused modules following SRP:
- CrashDetectorInterface: Crash detection services
- PMRecoveryManagerInterface: PM recovery management
- DaemonManagerInterface: Daemon lifecycle management
- HealthCheckerInterface: Agent health checking
- MonitorServiceInterface: Main monitoring service orchestrator
- ServiceContainerInterface: Dependency injection container
- MonitoringStrategyInterface, MonitorComponent: Pluggable monitoring strategies
- AgentMonitorInterface: Agent monitoring operations
- NotificationManagerInterface: Notification management
- StateTrackerInterface: State tracking operations
"""

# Re-export all interfaces for backwards compatibility
from .agent_monitor import AgentMonitorInterface
from .crash_detector import CrashDetectorInterface
from .daemon_manager import DaemonManagerInterface
from .health_checker import HealthCheckerInterface
from .monitor_service import MonitorServiceInterface
from .monitoring_strategy import MonitorComponent, MonitoringStrategyInterface
from .notification_manager import NotificationManagerInterface
from .pm_recovery import PMRecoveryManagerInterface
from .service_container import ServiceContainerInterface
from .state_tracker import StateTrackerInterface

# Export all classes for convenience
__all__ = [
    "CrashDetectorInterface",
    "PMRecoveryManagerInterface",
    "DaemonManagerInterface",
    "HealthCheckerInterface",
    "MonitorServiceInterface",
    "ServiceContainerInterface",
    "MonitoringStrategyInterface",
    "MonitorComponent",
    "AgentMonitorInterface",
    "NotificationManagerInterface",
    "StateTrackerInterface",
]

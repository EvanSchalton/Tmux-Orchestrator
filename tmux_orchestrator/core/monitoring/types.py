"""Data types and interfaces for the monitoring system."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Union

from tmux_orchestrator.core.config import Config
from tmux_orchestrator.utils.tmux import TMUXManager


class IdleType(Enum):
    """Types of idle states for agents."""

    UNKNOWN = "unknown"
    NEWLY_IDLE = "newly_idle"
    CONTINUOUSLY_IDLE = "continuously_idle"
    FRESH_AGENT = "fresh_agent"
    COMPACTION_STATE = "compaction_state"
    ERROR_STATE = "error_state"


class NotificationType(Enum):
    """Types of notifications."""

    AGENT_CRASH = "agent_crash"
    AGENT_IDLE = "agent_idle"
    AGENT_FRESH = "agent_fresh"
    TEAM_IDLE = "team_idle"
    RECOVERY_NEEDED = "recovery_needed"
    PM_ESCALATION = "pm_escalation"


class PluginStatus(Enum):
    """Status of a plugin."""

    DISCOVERED = "discovered"
    LOADED = "loaded"
    FAILED = "failed"
    DISABLED = "disabled"


@dataclass
class AgentInfo:
    """Structured agent information."""

    target: str
    session: str
    window: str
    name: str
    type: str
    status: str
    last_seen: Union[datetime, None] = None

    @property
    def display_name(self) -> str:
        """Get display name for the agent."""
        return f"{self.name} ({self.type})"


@dataclass
class IdleAnalysis:
    """Result of idle state analysis."""

    target: str
    is_idle: bool
    idle_type: IdleType
    confidence: float
    last_activity: datetime | None
    content_hash: str | None = None
    error_detected: bool = False
    error_type: str | None = None


@dataclass
class NotificationEvent:
    """A notification event to be sent."""

    type: NotificationType
    target: str
    message: str
    timestamp: datetime
    session: str
    metadata: dict[str, Any]

    @property
    def formatted_message(self) -> str:
        """Get formatted notification message."""
        return f"[{self.session}:{self.target}] {self.message}"


@dataclass
class MonitorStatus:
    """Overall monitor system status."""

    is_running: bool
    active_agents: int
    idle_agents: int
    last_cycle_time: float
    uptime: timedelta
    cycle_count: int
    errors_detected: int
    start_time: datetime | None = None
    end_time: datetime | None = None


@dataclass
class AgentState:
    """Current state tracking for an agent."""

    target: str
    session: str
    window: str
    last_content: str | None = None
    last_content_hash: str | None = None
    last_activity: datetime | None = None
    consecutive_idle_count: int = 0
    submission_attempts: int = 0
    last_submission_time: datetime | None = None
    is_fresh: bool = True
    error_count: int = 0
    last_error_time: datetime | None = None


@dataclass
class PluginInfo:
    """Information about a discovered plugin."""

    name: str
    file_path: Path
    module_name: str
    class_name: str
    status: PluginStatus
    description: str | None = None
    version: str | None = None
    author: str | None = None
    instance: Any | None = None
    error: str | None = None
    dependencies: list[str] | None = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class MonitorComponent(ABC):
    """Base interface for all monitor components."""

    def __init__(self, tmux: TMUXManager, config: Config, logger: logging.Logger):
        self.tmux = tmux
        self.config = config
        self.logger = logger

    @abstractmethod
    def initialize(self) -> bool:
        """Initialize component."""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up component resources."""
        pass


class AgentMonitorInterface(MonitorComponent):
    """Interface for agent monitoring and discovery."""

    @abstractmethod
    def discover_agents(self) -> list[AgentInfo]:
        """Discover all active agents."""
        pass

    @abstractmethod
    def is_agent_window(self, target: str) -> bool:
        """Check if window is an agent window."""
        pass

    @abstractmethod
    def get_agent_display_name(self, target: str) -> str:
        """Get display name for agent."""
        pass

    @abstractmethod
    def analyze_agent_content(self, target: str) -> IdleAnalysis:
        """Analyze agent content for idle state."""
        pass


class NotificationManagerInterface(MonitorComponent):
    """Interface for notification management."""

    @abstractmethod
    def queue_notification(self, event: NotificationEvent) -> None:
        """Queue a notification for sending."""
        pass

    @abstractmethod
    def send_queued_notifications(self) -> int:
        """Send all queued notifications."""
        pass

    @abstractmethod
    def notify_agent_crash(self, target: str, error_type: str, session: str) -> None:
        """Send agent crash notification."""
        pass

    @abstractmethod
    def notify_agent_idle(self, target: str, idle_type: IdleType, session: str) -> None:
        """Send agent idle notification."""
        pass


class StateTrackerInterface(MonitorComponent):
    """Interface for agent state tracking."""

    @abstractmethod
    def update_agent_state(self, target: str, content: str) -> AgentState:
        """Update agent state with new content."""
        pass

    @abstractmethod
    def get_agent_state(self, target: str) -> AgentState | None:
        """Get current agent state."""
        pass

    @abstractmethod
    def reset_agent_state(self, target: str) -> None:
        """Reset agent tracking state."""
        pass

    @abstractmethod
    def get_session_agents(self, session: str) -> list[AgentState]:
        """Get all agents in a session."""
        pass

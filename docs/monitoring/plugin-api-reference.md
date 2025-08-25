# Plugin API Reference

Complete API documentation for the Tmux Orchestrator monitoring plugin system.

## Core Interfaces

### MonitoringStrategyInterface

The base interface that all monitoring strategy plugins must implement.

```python
class MonitoringStrategyInterface(ABC):
    """Base interface for monitoring strategy plugins."""

    @abstractmethod
    def get_name(self) -> str:
        """Get the unique name for this strategy.

        Returns:
            str: Strategy name (e.g., "polling", "priority_based")

        Note:
            - Must be unique across all loaded plugins
            - Should be lowercase with underscores
            - Used for strategy selection via CLI/config
        """
        pass

    @abstractmethod
    def get_description(self) -> str:
        """Get human-readable description of the strategy.

        Returns:
            str: Description of what this strategy does

        Note:
            - Shown in help text and logs
            - Should be concise but informative
        """
        pass

    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> MonitorStatus:
        """Execute the monitoring strategy.

        Args:
            context: Execution context containing:
                - Component interfaces (see Component Access)
                - Runtime configuration
                - Logger instance
                - Metrics collector (optional)
                - Other runtime data

        Returns:
            MonitorStatus: Results of the monitoring cycle

        Raises:
            Exception: Any exception will be caught and logged

        Note:
            - This is the main entry point for your strategy
            - Should handle all exceptions gracefully
            - Must return a valid MonitorStatus even on error
        """
        pass

    @abstractmethod
    def get_required_components(self) -> List[type]:
        """Declare required component interfaces.

        Returns:
            List[type]: List of interface types this strategy needs

        Example:
            return [
                AgentMonitorInterface,
                StateTrackerInterface,
                NotificationManagerInterface,
            ]

        Note:
            - Plugin will not load if components are missing
            - Used for dependency validation
        """
        pass
```

## Component Interfaces

### AgentMonitorInterface

Provides agent discovery and content analysis.

```python
class AgentMonitorInterface(MonitorComponent):
    """Interface for agent monitoring and discovery."""

    def discover_agents(self) -> List[AgentInfo]:
        """Discover all active agents across all sessions.

        Returns:
            List[AgentInfo]: List of discovered agents

        Note:
            - Filters out non-agent windows (like vim, system windows)
            - Returns empty list if no agents found
        """

    def is_agent_window(self, target: str) -> bool:
        """Check if a window contains an agent.

        Args:
            target: Target in format "session:window"

        Returns:
            bool: True if window contains an agent
        """

    def get_agent_display_name(self, target: str) -> str:
        """Get display name for an agent.

        Args:
            target: Target in format "session:window"

        Returns:
            str: Human-friendly display name
        """

    def analyze_agent_content(self, target: str) -> IdleAnalysis:
        """Analyze agent window content for idle state.

        Args:
            target: Target in format "session:window"

        Returns:
            IdleAnalysis: Analysis results including:
                - is_idle: Whether agent is idle
                - idle_type: Type of idle state
                - content: Raw window content
                - confidence: Confidence level (0-1)
                - idle_duration: How long idle (if tracked)
        """
```

### StateTrackerInterface

Manages agent state and session tracking.

```python
class StateTrackerInterface(MonitorComponent):
    """Interface for agent state tracking."""

    def update_agent_state(self, target: str, content: str) -> AgentState:
        """Update agent state with new content.

        Args:
            target: Agent target identifier
            content: Current agent content

        Returns:
            AgentState: Updated state object with:
                - target: Agent identifier
                - last_activity: Last activity timestamp
                - consecutive_idle_count: Idle cycles
                - is_fresh: Whether agent is fresh
                - submission_attempts: Auto-submission count

        Note:
            - Automatically detects content changes
            - Updates idle tracking
        """

    def get_agent_state(self, target: str) -> Optional[AgentState]:
        """Get current agent state.

        Args:
            target: Agent target identifier

        Returns:
            Optional[AgentState]: State or None if not tracked
        """

    def reset_agent_state(self, target: str) -> None:
        """Reset all tracking for an agent.

        Args:
            target: Agent target identifier

        Note:
            - Clears all state including submission attempts
            - Use when agent is restarted/recovered
        """

    def get_session_agents(self, session: str) -> List[AgentState]:
        """Get all agents in a session.

        Args:
            session: Session name

        Returns:
            List[AgentState]: All tracked agents in session
        """

    def is_agent_idle(self, target: str) -> bool:
        """Check if agent is currently idle.

        Args:
            target: Agent target identifier

        Returns:
            bool: True if agent is idle
        """

    def get_idle_duration(self, target: str) -> Optional[float]:
        """Get how long agent has been idle.

        Args:
            target: Agent target identifier

        Returns:
            Optional[float]: Seconds idle, or None
        """

    def get_all_sessions(self) -> Set[str]:
        """Get all sessions with tracked agents.

        Returns:
            Set[str]: Unique session names
        """
```

### NotificationManagerInterface

Handles notification queuing and delivery.

```python
class NotificationManagerInterface(MonitorComponent):
    """Interface for notification management."""

    def queue_notification(self, event: NotificationEvent) -> None:
        """Queue a notification for sending.

        Args:
            event: NotificationEvent to queue

        Note:
            - Notifications are batched and throttled
            - Duplicate notifications are suppressed
        """

    def send_queued_notifications(self) -> int:
        """Send all queued notifications to PMs.

        Returns:
            int: Number of notification batches sent

        Note:
            - Groups by PM/session for efficiency
            - Clears queue after sending
        """

    def notify_agent_crash(
        self,
        target: str,
        error_type: str,
        session: str,
        metadata: Optional[Dict] = None
    ) -> None:
        """Send agent crash notification.

        Args:
            target: Agent that crashed
            error_type: Type of error detected
            session: Session containing agent
            metadata: Additional notification data
        """

    def notify_agent_idle(
        self,
        target: str,
        idle_type: IdleType,
        session: str,
        metadata: Optional[Dict] = None
    ) -> None:
        """Send agent idle notification.

        Args:
            target: Idle agent
            idle_type: Type of idle state
            session: Session containing agent
            metadata: Additional notification data
        """

    def notify_fresh_agent(
        self,
        target: str,
        session: str,
        metadata: Optional[Dict] = None
    ) -> None:
        """Notify about fresh agent needing briefing.

        Args:
            target: Fresh agent
            session: Session containing agent
            metadata: Additional notification data
        """
```

### CrashDetectorInterface

Detects agent and PM crashes.

```python
class CrashDetectorInterface(ABC):
    """Interface for crash detection services."""

    def detect_crash(
        self,
        agent_info: AgentInfo,
        window_content: List[str],
        idle_duration: Optional[float] = None
    ) -> Tuple[bool, Optional[str]]:
        """Detect if an agent has crashed.

        Args:
            agent_info: Agent information
            window_content: Recent lines from window
            idle_duration: How long agent has been idle

        Returns:
            Tuple[bool, Optional[str]]: (is_crashed, crash_reason)

        Note:
            - Uses pattern matching and heuristics
            - Considers idle duration for timeout detection
        """

    def detect_pm_crash(
        self,
        session_name: str
    ) -> Tuple[bool, Optional[str]]:
        """Detect if a PM has crashed in a session.

        Args:
            session_name: Session to check

        Returns:
            Tuple[bool, Optional[str]]: (is_crashed, pm_target)
        """
```

### PMRecoveryManagerInterface

Manages PM health checks and recovery.

```python
class PMRecoveryManagerInterface(ABC):
    """Interface for PM recovery management."""

    def check_pm_health(
        self,
        session_name: str
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Check PM health in a session.

        Args:
            session_name: Session to check

        Returns:
            Tuple containing:
                - is_healthy: Whether PM is healthy
                - pm_target: PM window target if found
                - issue_description: Description of any issues
        """

    def should_attempt_recovery(self, session_name: str) -> bool:
        """Determine if recovery should be attempted.

        Args:
            session_name: Session to check

        Returns:
            bool: True if recovery should be attempted

        Note:
            - Considers recovery history
            - Implements backoff for repeated failures
        """

    def recover_pm(
        self,
        session_name: str,
        crashed_target: Optional[str] = None
    ) -> bool:
        """Recover a crashed or missing PM.

        Args:
            session_name: Session needing recovery
            crashed_target: Target of crashed PM

        Returns:
            bool: True if recovery successful

        Note:
            - Spawns new PM if missing
            - Restores PM state if possible
        """
```

## Data Types

### AgentInfo

```python
@dataclass
class AgentInfo:
    """Agent identification and metadata."""

    target: str          # Format: "session:window"
    session: str         # Session name
    window: str          # Window index
    name: str           # Window name
    type: str           # Agent type (e.g., "agent", "pm")
    status: str         # Current status
    last_seen: Optional[datetime] = None
```

### AgentState

```python
@dataclass
class AgentState:
    """Runtime state for an agent."""

    target: str
    session: str
    window: str
    last_content: Optional[str] = None
    last_content_hash: Optional[str] = None
    last_activity: Optional[datetime] = None
    consecutive_idle_count: int = 0
    submission_attempts: int = 0
    last_submission_time: Optional[datetime] = None
    is_fresh: bool = True
    error_count: int = 0
    last_error_time: Optional[datetime] = None
```

### MonitorStatus

```python
@dataclass
class MonitorStatus:
    """Results from a monitoring cycle."""

    start_time: datetime
    agents_monitored: int
    agents_healthy: int
    agents_idle: int
    agents_crashed: int
    cycle_count: int
    errors_detected: int
    end_time: Optional[datetime] = None
```

### IdleAnalysis

```python
@dataclass
class IdleAnalysis:
    """Results from agent content analysis."""

    is_idle: bool
    idle_type: IdleType
    content: str
    confidence: float = 1.0
    idle_duration: Optional[float] = None
    last_activity_marker: Optional[str] = None
```

### NotificationEvent

```python
@dataclass
class NotificationEvent:
    """A notification to be sent."""

    type: NotificationType
    target: str
    message: str
    timestamp: datetime
    session: str
    metadata: Dict[str, Any] = field(default_factory=dict)
```

## Context Parameters

The `context` dictionary passed to `execute()` contains:

### Required Components

Components are passed by their interface type name:

```python
context = {
    'agent_monitor': AgentMonitorInterface,      # Required if declared
    'state_tracker': StateTrackerInterface,      # Required if declared
    'notification_manager': NotificationManagerInterface,
    'crash_detector': CrashDetectorInterface,
    'pm_recovery_manager': PMRecoveryManagerInterface,
}
```

### Optional Components

```python
context = {
    'logger': logging.Logger,           # Logger instance
    'config': Config,                   # Configuration object
    'metrics': MetricsCollector,        # Metrics collector
    'tmux_pool': TMuxConnectionPool,    # Connection pool
    'agent_cache': AgentContentCache,   # Content cache
    'command_cache': TMuxCommandCache,  # Command cache
}
```

### Runtime Data

```python
context = {
    'cycle_count': int,                 # Current cycle number
    'start_time': datetime,             # Cycle start time
    'last_cycle_status': MonitorStatus, # Previous cycle results
}
```

## Plugin Loading

### Discovery

Plugins are discovered from:
1. `tmux_orchestrator/core/monitoring/strategies/` (built-in)
2. `~/.tmux_orchestrator/plugins/` (user plugins)

### Validation

Plugins are validated for:
1. Correct interface implementation
2. Required method signatures
3. Component availability
4. No naming conflicts

### Lifecycle Events

1. **Discovery**: Plugin file found and inspected
2. **Loading**: Plugin class instantiated
3. **Validation**: Interface compliance checked
4. **Execution**: `execute()` called per monitoring cycle
5. **Unloading**: Plugin removed from active strategies

## Best Practices

### Error Handling

```python
async def execute(self, context: Dict[str, Any]) -> MonitorStatus:
    status = MonitorStatus(...)

    try:
        # Your monitoring logic
        pass
    except Exception as e:
        # Log but don't crash
        logger.error(f"Error in plugin: {e}")
        status.errors_detected += 1

    # Always return valid status
    return status
```

### Performance

```python
# Use async for I/O operations
async with tmux_pool.acquire() as tmux:
    content = await asyncio.to_thread(tmux.capture_pane, target)

# Leverage caching
content, cache_status = await cache.get_agent_content(session, window)
if cache_status != CacheEntryStatus.FRESH:
    content = await fetch_content()
    await cache.set_agent_content(session, window, content)

# Track performance
metrics.start_timer("my_operation")
result = await do_operation()
metrics.stop_timer("my_operation")
```

### Configuration

```python
class MyStrategy(MonitoringStrategyInterface):
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

        # Use defaults
        self.timeout = self.config.get('timeout', 30.0)
        self.max_retries = self.config.get('max_retries', 3)
```

## Examples

See the following example implementations:
- `polling_strategy.py`: Basic sequential monitoring
- `concurrent_strategy.py`: Parallel monitoring with semaphores
- `async_polling_strategy.py`: Async with caching and pooling
- `priority_based_strategy.py`: Advanced prioritization example

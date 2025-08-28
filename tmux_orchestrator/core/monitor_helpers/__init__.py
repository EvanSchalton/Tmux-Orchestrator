"""Monitor helper functions - decomposed module with backwards compatibility.

This module has been refactored following development-patterns.md:
- Each function category in its own file following SRP
- Constants and enums in state_types.py
- Full backwards compatibility via re-exports
"""

# Re-export all constants and enums
# Re-export agent state functions
from .agent_state import (
    detect_agent_state,
    has_unsubmitted_message,
    is_terminal_idle,
    needs_recovery,
    should_notify_continuously_idle,
    should_notify_pm,
)

# Re-export Claude detection functions
from .claude_detection import (
    detect_claude_state,
    has_crash_indicators,
    has_error_indicators,
    is_claude_interface_present,
)

# Re-export PM detection functions
from .pm_detection import calculate_change_distance, is_pm_busy

# Re-export rate limit functions
from .rate_limit import calculate_sleep_duration, extract_rate_limit_reset_time
from .state_types import (
    DAEMON_CONTROL_LOOP_COOLDOWN_SECONDS,
    DAEMON_CONTROL_LOOP_SECONDS,
    ENABLE_PM_BUSY_STATE_DETECTION,
    MAX_RATE_LIMIT_SECONDS,
    MISSING_AGENT_GRACE_MINUTES,
    MISSING_AGENT_NOTIFICATION_COOLDOWN_MINUTES,
    PM_ESCALATION_CONFIG,
    PM_MESSAGE_QUEUE_MAX_SIZE,
    PM_MESSAGE_QUEUE_RETRY_INTERVAL_SECONDS,
    RATE_LIMIT_BUFFER_SECONDS,
    AgentState,
    DaemonAction,
)

# Maintain backwards compatibility aliases
_calculate_change_distance = calculate_change_distance  # Private version
_has_crash_indicators = has_crash_indicators  # Private version
_has_error_indicators = has_error_indicators  # Private version

__all__ = [
    # Constants
    "MAX_RATE_LIMIT_SECONDS",
    "RATE_LIMIT_BUFFER_SECONDS",
    "MISSING_AGENT_GRACE_MINUTES",
    "MISSING_AGENT_NOTIFICATION_COOLDOWN_MINUTES",
    "DAEMON_CONTROL_LOOP_SECONDS",
    "DAEMON_CONTROL_LOOP_COOLDOWN_SECONDS",
    "ENABLE_PM_BUSY_STATE_DETECTION",
    "PM_MESSAGE_QUEUE_MAX_SIZE",
    "PM_MESSAGE_QUEUE_RETRY_INTERVAL_SECONDS",
    "PM_ESCALATION_CONFIG",
    # Enums
    "AgentState",
    "DaemonAction",
    # Functions
    "is_claude_interface_present",
    "detect_agent_state",
    "detect_claude_state",
    "is_pm_busy",
    "has_unsubmitted_message",
    "is_terminal_idle",
    "needs_recovery",
    "should_notify_pm",
    "should_notify_continuously_idle",
    "extract_rate_limit_reset_time",
    "calculate_sleep_duration",
    # Private functions (backwards compatibility)
    "_calculate_change_distance",
    "_has_crash_indicators",
    "_has_error_indicators",
]

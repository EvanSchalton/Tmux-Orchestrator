"""Agent state types and enums for monitoring."""

from enum import Enum

# Rate limit constants
MAX_RATE_LIMIT_SECONDS = 14400  # 4 hours in seconds
RATE_LIMIT_BUFFER_SECONDS = 120  # 2 minute buffer after rate limit reset

# Recovery constants
MISSING_AGENT_GRACE_MINUTES = 2  # Grace period before notifying about missing agents
MISSING_AGENT_NOTIFICATION_COOLDOWN_MINUTES = 30  # Cooldown between repeated missing agent notifications

# Daemon timing constants
DAEMON_CONTROL_LOOP_SECONDS = 10  # How often the daemon checks agent status
DAEMON_CONTROL_LOOP_COOLDOWN_SECONDS = 60  # Cooldown after notifying any PM

# PM messaging constants
ENABLE_PM_BUSY_STATE_DETECTION = True  # Enable/disable busy-state detection for PM messaging
PM_MESSAGE_QUEUE_MAX_SIZE = 50  # Maximum queued messages per PM
PM_MESSAGE_QUEUE_RETRY_INTERVAL_SECONDS = 30  # Retry queued messages every 30s


class AgentState(Enum):
    """Enumeration of possible agent states."""

    ACTIVE = "active"  # Working normally (was healthy/active/starting)
    CRASHED = "crashed"  # Claude not running
    ERROR = "error"  # Has error indicators
    FRESH = "fresh"  # Fresh Claude instance (needs context/direction)
    IDLE = "idle"  # Claude running but not doing anything
    MESSAGE_QUEUED = "message_queued"  # Has unsubmitted message
    RATE_LIMITED = "rate_limited"  # Claude API rate limit reached


class DaemonAction(Enum):
    """Enumeration of daemon actions for PM escalation."""

    MESSAGE = "message"
    KILL = "kill"


# PM escalation configuration for team-wide idleness
PM_ESCALATION_CONFIG = {
    "team_idle_threshold_agents": 3,  # Number of idle agents before escalation
    "team_idle_threshold_percentage": 0.5,  # Percentage of team idle before escalation
    "escalation_cooldown_minutes": 15,  # Cooldown between escalations
    "escalation_message_template": "🚨 TEAM IDLE ALERT: {idle_count}/{total_count} agents are idle ({percentage:.0%}). Immediate intervention required.",
}

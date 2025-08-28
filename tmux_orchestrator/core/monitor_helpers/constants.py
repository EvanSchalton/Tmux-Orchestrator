"""Constants and enums for monitoring system."""

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
NONRESPONSIVE_PM_ESCALATIONS_MINUTES: dict[int, tuple[DaemonAction, str | None]] = {
    3: (
        DaemonAction.MESSAGE,
        "⚠️ IDLE TEAM ALERT (3 min)\n"
        "Your entire team is idle and waiting for task assignments.\n"
        "As PM, you should: Check your team plan → Assign tasks → Monitor progress\n"
        "Reference your team-plan.md in .tmux_orchestrator/planning/ for agent roles and responsibilities.\n"
        "For more information about your role run: 'tmux-orc context show pm'",
    ),
    5: (
        DaemonAction.MESSAGE,
        "🚨 CRITICAL: TEAM IDLE (5 min)\n\n"
        "First, rehydrate your context by running: tmux-orc context show pm\n\n"
        "Your entire team is idle and waiting for task assignments. As the Project Manager, "
        "you need to immediately assign work to your idle agents based on your team plan.",
    ),
    8: (DaemonAction.KILL, None),  # Kill PM - daemon will auto-spawn replacement
}

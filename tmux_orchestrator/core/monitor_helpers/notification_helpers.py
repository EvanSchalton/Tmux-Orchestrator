"""Notification decision logic for the monitoring system."""

from datetime import datetime, timedelta

from .constants import AgentState


def needs_recovery(state: AgentState) -> bool:
    """Determine if agent needs recovery based on state.

    Args:
        state: Current agent state

    Returns:
        True if recovery is needed, False otherwise
    """
    return state in [AgentState.CRASHED, AgentState.ERROR, AgentState.RATE_LIMITED]


def should_notify_pm(state: AgentState, target: str, notification_history: dict[str, datetime]) -> bool:
    """Determine if PM should be notified about agent state.

    Args:
        state: Current agent state
        target: Agent target identifier
        notification_history: History of notifications sent

    Returns:
        True if PM should be notified, False otherwise
    """
    # Rate limits need immediate notification - no cooldown
    if state == AgentState.RATE_LIMITED:
        return True

    # Crashes and errors have cooldown to prevent spam
    if state in [AgentState.CRASHED, AgentState.ERROR]:
        # 5 minute cooldown for crash/error notifications
        last_notified = notification_history.get(f"crash_{target}")
        if last_notified:
            time_since = datetime.now() - last_notified
            if time_since < timedelta(minutes=5):
                return False
        return True

    # Notify for fresh agents that need context/briefing
    if state == AgentState.FRESH:
        # 10 minute cooldown for fresh agent notifications
        last_notified = notification_history.get(f"fresh_{target}")
        if last_notified:
            time_since = datetime.now() - last_notified
            if time_since < timedelta(minutes=10):
                return False
        return True

    # Notify for idle agents (immediate for newly idle, cooldown for continuously idle)
    if state == AgentState.IDLE:
        # This will be handled by the caller - newly idle always notifies, continuously idle uses cooldown
        return True

    # Don't notify for healthy/active agents or messages queued
    return False


def should_notify_continuously_idle(target: str, notification_history: dict[str, datetime]) -> bool:
    """Check if continuously idle agent should trigger notification (with cooldown).

    Args:
        target: Agent target identifier
        notification_history: History of notifications sent

    Returns:
        True if notification should be sent, False if in cooldown
    """
    # 5 minute cooldown for continuously idle agents to prevent spam
    last_notified = notification_history.get(target)
    if last_notified:
        time_since = datetime.now() - last_notified
        if time_since < timedelta(minutes=5):
            return False
    return True

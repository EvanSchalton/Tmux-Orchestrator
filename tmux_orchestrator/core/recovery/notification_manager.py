"""Recovery notification manager with cooldown and throttling.

Manages recovery notifications to prevent spam and implement intelligent
throttling based on agent status, notification history, and cooldown periods.
Follows one-function-per-file pattern with comprehensive type annotations.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from tmux_orchestrator.utils.tmux import TMUXManager


def should_send_recovery_notification(
    target: str,
    notification_type: str,
    cooldown_minutes: int = 5,
    state_file: Optional[Path] = None,
    logger: Optional[logging.Logger] = None,
) -> tuple[bool, str, dict[str, Any]]:
    """
    Determine if recovery notification should be sent based on cooldown policy.

    Implements intelligent notification throttling to prevent spam while ensuring
    critical recovery events are communicated. Maintains persistent state across
    restarts for consistent cooldown enforcement.

    Args:
        target: Target agent in format 'session:window'
        notification_type: Type of notification ('recovery_started', 'recovery_failed', 'recovery_success')
        cooldown_minutes: Cooldown period in minutes between notifications (default: 5)
        state_file: Optional path to notification state file (defaults to project registry)
        logger: Optional logger instance for notification events

    Returns:
        Tuple of (should_send, reason, notification_data) where:
        - should_send: Boolean indicating if notification should be sent
        - reason: Human-readable reason for the decision
        - notification_data: Dictionary containing notification state information

    Raises:
        ValueError: If target format is invalid or notification_type is unrecognized
        IOError: If state file operations fail critically
    """
    # Initialize logger if not provided
    if logger is None:
        logger = logging.getLogger(__name__)

    # Validate inputs
    if ":" not in target:
        raise ValueError(f"Invalid target format: {target}. Expected 'session:window'")

    valid_types: list[str] = [
        "recovery_started",
        "recovery_failed",
        "recovery_success",
        "agent_healthy",
    ]
    if notification_type not in valid_types:
        raise ValueError(f"Invalid notification type: {notification_type}. Valid types: {valid_types}")

    # Initialize state file path
    if state_file is None:
        state_file = _get_default_state_file()

    current_time: datetime = datetime.now()

    logger.debug(f"Checking notification cooldown for {target} (type: {notification_type})")

    # Initialize notification data
    notification_data: dict[str, Any] = {
        "target": target,
        "notification_type": notification_type,
        "check_time": current_time.isoformat(),
        "cooldown_minutes": cooldown_minutes,
        "state_file": str(state_file),
    }

    try:
        # Load notification state
        notification_state: dict[str, Any] = _load_notification_state(state_file, logger)
        notification_data["state_loaded"] = True

        # Check cooldown for this target
        target_key: str = f"{target}:{notification_type}"
        last_notification: Optional[dict[str, Any]] = notification_state.get(target_key)

        if last_notification is None:
            # No previous notification of this type for this target
            reason: str = f"No previous {notification_type} notification for {target}"
            logger.info(reason)

            # Update state with current notification
            _update_notification_state(
                state_file=state_file,
                target_key=target_key,
                notification_data={
                    "target": target,
                    "type": notification_type,
                    "timestamp": current_time.isoformat(),
                    "cooldown_minutes": cooldown_minutes,
                },
                logger=logger,
            )

            notification_data["last_notification"] = None
            notification_data["cooldown_remaining"] = 0

            return True, reason, notification_data

        # Check if cooldown period has passed
        last_time_str: str = last_notification.get("timestamp", "")
        try:
            last_time: datetime = datetime.fromisoformat(last_time_str)
        except ValueError:
            logger.warning(f"Invalid timestamp format in state: {last_time_str}")
            # Treat as no previous notification
            reason = f"Invalid timestamp in state for {target}, treating as new notification"
            return True, reason, notification_data

        # Calculate time since last notification
        time_since_last: timedelta = current_time - last_time
        cooldown_period: timedelta = timedelta(minutes=cooldown_minutes)

        notification_data["last_notification"] = last_notification
        notification_data["time_since_last_minutes"] = time_since_last.total_seconds() / 60
        notification_data["cooldown_remaining"] = max(0, (cooldown_period - time_since_last).total_seconds() / 60)

        if time_since_last >= cooldown_period:
            # Cooldown period has passed, allow notification
            reason = f"Cooldown period passed for {target} ({time_since_last.total_seconds() / 60:.1f}min >= {cooldown_minutes}min)"
            logger.info(reason)

            # Update state with current notification
            _update_notification_state(
                state_file=state_file,
                target_key=target_key,
                notification_data={
                    "target": target,
                    "type": notification_type,
                    "timestamp": current_time.isoformat(),
                    "cooldown_minutes": cooldown_minutes,
                },
                logger=logger,
            )

            return True, reason, notification_data
        else:
            # Still in cooldown period
            remaining_minutes: float = (cooldown_period - time_since_last).total_seconds() / 60
            reason = f"Cooldown active for {target} ({remaining_minutes:.1f}min remaining)"
            logger.debug(reason)

            return False, reason, notification_data

    except Exception as e:
        # Handle state file errors gracefully
        error_msg: str = f"Notification state error for {target}: {str(e)}"
        logger.error(error_msg)

        # In case of error, allow notification (fail-safe approach)
        notification_data["state_error"] = str(e)
        notification_data["fail_safe_allowed"] = True

        return (
            True,
            f"State error, allowing notification: {error_msg}",
            notification_data,
        )


def _get_default_state_file() -> Path:
    """Get default path for notification state file."""
    state_dir: Path = Path.cwd() / "registry" / "recovery"
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir / "notification_state.json"


def _load_notification_state(state_file: Path, logger: logging.Logger) -> dict[str, Any]:
    """Load notification state from file."""
    try:
        if state_file.exists():
            with open(state_file, encoding="utf-8") as f:
                state_data: dict[str, Any] = json.load(f)
                logger.debug(f"Loaded notification state from {state_file}")
                return state_data
        else:
            logger.debug(f"No existing notification state file at {state_file}")
            return {}

    except json.JSONDecodeError as e:
        logger.warning(f"Invalid JSON in notification state file: {str(e)}")
        # Backup corrupted file and start fresh
        backup_file: Path = state_file.with_suffix(".json.backup")
        if state_file.exists():
            state_file.rename(backup_file)
        return {}

    except Exception as e:
        logger.error(f"Failed to load notification state: {str(e)}")
        return {}


def _update_notification_state(
    state_file: Path,
    target_key: str,
    notification_data: dict[str, Any],
    logger: logging.Logger,
) -> None:
    """Update notification state file with new notification."""
    try:
        # Load current state
        current_state: dict[str, Any] = _load_notification_state(state_file, logger)

        # Update with new notification
        current_state[target_key] = notification_data

        # Clean up old entries (keep last 100 entries)
        if len(current_state) > 100:
            # Sort by timestamp and keep the 100 most recent
            sorted_items = sorted(
                current_state.items(),
                key=lambda item: item[1].get("timestamp", ""),
                reverse=True,
            )[:100]
            current_state = dict(sorted_items)

        # Write updated state
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(current_state, f, indent=2, ensure_ascii=False)

        logger.debug(f"Updated notification state for {target_key}")

    except Exception as e:
        logger.error(f"Failed to update notification state: {str(e)}")
        # Don't raise exception - notification throttling is non-critical


def send_recovery_notification(
    tmux: TMUXManager,
    target: str,
    notification_type: str,
    message: str,
    pm_target: Optional[str] = None,
    force_send: bool = False,
    cooldown_minutes: int = 5,
    logger: Optional[logging.Logger] = None,
) -> tuple[bool, str, dict[str, Any]]:
    """
    Send recovery notification with cooldown management.

    Comprehensive notification sending with intelligent throttling,
    PM auto-discovery, and detailed result tracking.

    Args:
        tmux: TMUX manager instance for session operations
        target: Target agent in format 'session:window'
        notification_type: Type of notification ('recovery_started', 'recovery_failed', 'recovery_success')
        message: Notification message content
        pm_target: Optional PM target (auto-discovered if not provided)
        force_send: Whether to bypass cooldown checks (default: False)
        cooldown_minutes: Cooldown period in minutes (default: 5)
        logger: Optional logger instance for notification events

    Returns:
        Tuple of (sent, result_message, notification_data)

    Raises:
        ValueError: If target format is invalid
        RuntimeError: If PM discovery or message sending fails critically
    """
    # Initialize logger if not provided
    if logger is None:
        logger = logging.getLogger(__name__)

    logger.info(f"Attempting to send {notification_type} notification for {target}")

    # Initialize result data
    result_data: dict[str, Any] = {
        "target": target,
        "notification_type": notification_type,
        "message_length": len(message),
        "force_send": force_send,
        "pm_auto_discovered": False,
        "cooldown_checked": False,
        "notification_sent": False,
    }

    try:
        # Step 1: Check cooldown unless forced
        if not force_send:
            should_send: bool
            cooldown_reason: str
            cooldown_data: dict[str, Any]

            (
                should_send,
                cooldown_reason,
                cooldown_data,
            ) = should_send_recovery_notification(
                target=target,
                notification_type=notification_type,
                cooldown_minutes=cooldown_minutes,
                logger=logger,
            )

            result_data["cooldown_checked"] = True
            result_data["cooldown_data"] = cooldown_data
            result_data["should_send"] = should_send
            result_data["cooldown_reason"] = cooldown_reason

            if not should_send:
                logger.info(f"Notification blocked by cooldown: {cooldown_reason}")
                return False, f"Notification blocked: {cooldown_reason}", result_data
        else:
            result_data["cooldown_bypassed"] = True
            logger.info(f"Cooldown bypassed for {target} (force_send=True)")

        # Step 2: Discover PM target if not provided
        if pm_target is None:
            pm_target = _discover_pm_target(tmux, logger)
            result_data["pm_auto_discovered"] = True
            result_data["discovered_pm_target"] = pm_target
        else:
            result_data["pm_target_provided"] = pm_target

        if pm_target is None:
            error_msg: str = "No PM target available for notification"
            logger.error(error_msg)
            result_data["pm_discovery_failed"] = True
            return False, error_msg, result_data

        # Step 3: Send notification
        logger.info(f"Sending notification to PM at {pm_target}")

        # Format message with metadata
        formatted_message: str = _format_recovery_message(
            target=target,
            notification_type=notification_type,
            message=message,
            timestamp=datetime.now(),
        )

        result_data["formatted_message_length"] = len(formatted_message)

        # Send using the CLI command
        import subprocess

        result = subprocess.run(
            ["tmux-orc", "agent", "send", pm_target, formatted_message],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            success_msg: str = f"Recovery notification sent successfully to {pm_target}"
            logger.info(success_msg)

            result_data["notification_sent"] = True
            result_data["send_success"] = True

            return True, success_msg, result_data
        else:
            error_msg = f"Failed to send notification: {result.stderr}"
            logger.error(error_msg)

            result_data["notification_sent"] = False
            result_data["send_error"] = result.stderr

            return False, error_msg, result_data

    except Exception as e:
        error_msg = f"Recovery notification failed for {target}: {str(e)}"
        logger.error(error_msg)

        result_data["notification_exception"] = str(e)
        result_data["notification_sent"] = False

        return False, error_msg, result_data


def _discover_pm_target(tmux: TMUXManager, logger: logging.Logger) -> Optional[str]:
    """Discover PM target automatically."""
    logger.debug("Auto-discovering PM target")

    # Check tmux-orc-dev session first (most likely)
    try:
        if tmux.has_session("tmux-orc-dev"):
            windows = tmux.list_windows("tmux-orc-dev")
            for window in windows:
                if window.get("index") == "5":  # PM window is typically window 5
                    pm_target = "tmux-orc-dev:5"
                    logger.info(f"Found PM at {pm_target}")
                    return pm_target
    except Exception as e:
        logger.debug(f"Failed to check tmux-orc-dev for PM: {str(e)}")

    # Search other sessions for PM windows
    try:
        sessions = tmux.list_sessions()
        for session in sessions:
            session_name = session.get("name", "")
            if "pm" in session_name.lower() or "project-manager" in session_name.lower():
                # Found PM session, use window 0
                pm_target = f"{session_name}:0"
                logger.info(f"Found PM session at {pm_target}")
                return pm_target
    except Exception as e:
        logger.debug(f"Failed to search sessions for PM: {str(e)}")

    logger.warning("No PM target could be discovered")
    return None


def _format_recovery_message(target: str, notification_type: str, message: str, timestamp: datetime) -> str:
    """Format recovery notification message with metadata."""
    emoji_map = {
        "recovery_started": "🔄",
        "recovery_failed": "❌",
        "recovery_success": "✅",
        "agent_healthy": "🟢",
    }

    emoji = emoji_map.get(notification_type, "🔔")
    type_title = notification_type.replace("_", " ").title()

    formatted_parts = [
        f"{emoji} **RECOVERY NOTIFICATION**: {type_title}",
        "",
        f"**Agent**: {target}",
        f"**Time**: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Type**: {notification_type}",
        "",
        "**Details**:",
        message,
        "",
        "This is an automated recovery system notification.",
    ]

    return "\n".join(formatted_parts)

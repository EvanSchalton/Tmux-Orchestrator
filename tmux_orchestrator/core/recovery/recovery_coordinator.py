"""Recovery coordinator for automatic agent recovery system.

Coordinates the complete recovery workflow: health monitoring, failure detection,
auto-restart with context preservation, and briefing restoration. Implements
the 60-second recovery requirement with comprehensive error handling.
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any

from tmux_orchestrator.core.recovery.auto_restart import auto_restart_agent
from tmux_orchestrator.core.recovery.check_agent_health import (
    AgentHealthStatus,
    check_agent_health,
)
from tmux_orchestrator.core.recovery.notification_manager import (
    send_recovery_notification,
)
from tmux_orchestrator.core.recovery.recovery_logger import (
    create_recovery_audit_log,
    log_recovery_event,
    setup_recovery_logger,
)
from tmux_orchestrator.utils.tmux import TMUXManager


def coordinate_agent_recovery(
    tmux: TMUXManager,
    target: str,
    logger: logging.Logger | None = None,
    max_failures: int = 3,
    recovery_timeout: int = 60,
    enable_auto_restart: bool = True,
    briefing_text: str | None = None,
    use_structured_logging: bool = True,
) -> tuple[bool, str, dict[str, Any]]:
    """
    Coordinate complete agent recovery workflow.

    Performs health check, determines recovery action, executes auto-restart
    if needed, and tracks recovery metrics. Meets 60-second recovery requirement
    with comprehensive error handling and logging.

    Args:
        tmux: TMUX manager instance for session operations
        target: Target agent in format 'session:window'
        logger: Logger instance for recovery event tracking
        max_failures: Maximum failures before triggering recovery (default: 3)
        recovery_timeout: Maximum time allowed for recovery in seconds (default: 60)
        enable_auto_restart: Whether to automatically restart failed agents (default: True)
        briefing_text: Custom briefing text to restore after restart

    Returns:
        Tuple of (recovery_success, status_message, recovery_data) where:
        - recovery_success: Boolean indicating if recovery was successful
        - status_message: Human-readable recovery result message
        - recovery_data: Dictionary containing detailed recovery metrics

    Raises:
        ValueError: If target format is invalid
        RuntimeError: If critical recovery operations fail
    """
    recovery_start_time: datetime = datetime.now()
    recovery_session_id: str = str(uuid.uuid4())[:8]  # Short unique ID

    # Setup structured logging if requested
    recovery_logger: logging.Logger
    if use_structured_logging:
        recovery_logger = setup_recovery_logger()
    else:
        recovery_logger = logger or logging.getLogger(__name__)

    recovery_logger.info(f"Starting recovery coordination for agent: {target} (session: {recovery_session_id})")

    # Initialize recovery data tracking
    recovery_data: dict[str, Any] = {
        "target": target,
        "recovery_session_id": recovery_session_id,
        "recovery_start": recovery_start_time.isoformat(),
        "recovery_timeout": recovery_timeout,
        "max_failures": max_failures,
        "health_checks": [],
        "recovery_attempted": False,
        "recovery_successful": False,
        "total_duration": 0,
        "auto_restart_enabled": enable_auto_restart,
        "logged_events": [],
    }

    try:
        # Step 1: Perform initial health check
        recovery_logger.info(f"Performing health check for {target}")

        # Estimate last response time (use current time minus timeout as baseline)
        estimated_last_response: datetime = recovery_start_time - timedelta(seconds=recovery_timeout)

        health_status: AgentHealthStatus = check_agent_health(
            tmux=tmux,
            target=target,
            last_response=estimated_last_response,
            consecutive_failures=0,  # Start fresh for recovery assessment
            max_failures=max_failures,
            response_timeout=recovery_timeout,
        )

        # Record health check results
        health_data: dict[str, Any] = {
            "check_time": health_status.last_check.isoformat(),
            "is_healthy": health_status.is_healthy,
            "is_idle": health_status.is_idle,
            "failure_reason": health_status.failure_reason,
            "consecutive_failures": health_status.consecutive_failures,
        }
        recovery_data["health_checks"].append(health_data)

        # Log structured health check event
        if use_structured_logging:
            health_event = log_recovery_event(recovery_logger, "health_check", target, health_data)
            recovery_data["logged_events"].append(health_event)

        recovery_logger.info(
            f"Health check result for {target}: healthy={health_status.is_healthy}, idle={health_status.is_idle}"
        )

        # Step 2: Determine recovery action needed
        needs_recovery: bool = not health_status.is_healthy

        # Log failure detection if needed
        if needs_recovery and use_structured_logging:
            failure_event = log_recovery_event(
                recovery_logger,
                "failure_detected",
                target,
                {
                    "failure_reason": health_status.failure_reason,
                    "is_idle": health_status.is_idle,
                    "consecutive_failures": health_status.consecutive_failures,
                },
            )
            recovery_data["logged_events"].append(failure_event)

        if not needs_recovery:
            # Agent is healthy, no recovery needed
            success_message: str = f"Agent {target} is healthy, no recovery needed"
            recovery_logger.info(success_message)

            recovery_data["recovery_successful"] = True
            recovery_data["total_duration"] = (datetime.now() - recovery_start_time).total_seconds()

            # Log healthy agent event
            if use_structured_logging:
                healthy_event = log_recovery_event(
                    recovery_logger,
                    "agent_verified",
                    target,
                    {"verification_result": "healthy", "recovery_needed": False},
                )
                recovery_data["logged_events"].append(healthy_event)

                # Create audit log for session
                create_recovery_audit_log(
                    recovery_logger,
                    recovery_session_id,
                    recovery_data["logged_events"],
                    "success",
                    recovery_data["total_duration"],
                )

            return True, success_message, recovery_data

        # Step 3: Agent needs recovery - check timeout before proceeding
        elapsed_time: float = (datetime.now() - recovery_start_time).total_seconds()
        if elapsed_time >= recovery_timeout:
            timeout_message: str = f"Recovery timeout reached for {target} ({elapsed_time:.1f}s >= {recovery_timeout}s)"
            recovery_logger.error(timeout_message)

            recovery_data["recovery_successful"] = False
            recovery_data["timeout_reached"] = True
            recovery_data["total_duration"] = elapsed_time

            return False, timeout_message, recovery_data

        # Step 4: Send recovery started notification
        try:
            (
                notification_sent,
                notification_msg,
                notification_data,
            ) = send_recovery_notification(
                tmux=tmux,
                target=target,
                notification_type="recovery_started",
                message=f"Automatic recovery initiated for {target}. Reason: {health_status.failure_reason}",
                cooldown_minutes=5,
                logger=recovery_logger,
            )

            recovery_data["recovery_start_notification"] = {
                "sent": notification_sent,
                "message": notification_msg,
                "data": notification_data,
            }

        except Exception as e:
            recovery_logger.warning(f"Failed to send recovery start notification: {str(e)}")

        # Step 5: Execute auto-restart if enabled
        if not enable_auto_restart:
            no_restart_message: str = (
                f"Agent {target} needs recovery but auto-restart is disabled. Reason: {health_status.failure_reason}"
            )
            recovery_logger.warning(no_restart_message)

            recovery_data["recovery_successful"] = False
            recovery_data["auto_restart_disabled"] = True
            recovery_data["total_duration"] = (datetime.now() - recovery_start_time).total_seconds()

            # Send failure notification
            try:
                send_recovery_notification(
                    tmux=tmux,
                    target=target,
                    notification_type="recovery_failed",
                    message=f"Recovery disabled for {target}. Auto-restart is not enabled.",
                    cooldown_minutes=5,
                    logger=recovery_logger,
                )
            except Exception as e:
                recovery_logger.warning(f"Failed to send recovery failure notification: {str(e)}")

            return False, no_restart_message, recovery_data

        recovery_logger.info(f"Initiating auto-restart for failed agent: {target}")
        recovery_data["recovery_attempted"] = True

        # Calculate remaining time for restart
        remaining_timeout: int = int(recovery_timeout - elapsed_time)
        max_retries: int = min(3, remaining_timeout // 15)  # 15s per retry minimum

        restart_success: bool
        restart_message: str
        restart_context: dict[str, Any]

        restart_success, restart_message, restart_context = auto_restart_agent(
            tmux=tmux,
            target=target,
            logger=recovery_logger,
            max_retries=max_retries,
            preserve_context=True,
            briefing_text=briefing_text,
        )

        # Record restart results
        recovery_data["restart_results"] = restart_context
        recovery_data["recovery_successful"] = restart_success

        # Step 5: Verify recovery success with final health check
        if restart_success:
            recovery_logger.info(f"Verifying recovery for {target} with final health check")

            # Wait briefly for agent to stabilize

            # Final health verification
            final_health: AgentHealthStatus = check_agent_health(
                tmux=tmux,
                target=target,
                last_response=datetime.now(),
                consecutive_failures=0,
                max_failures=max_failures,
                response_timeout=30,  # Shorter timeout for verification
            )

            final_health_data: dict[str, Any] = {
                "check_time": final_health.last_check.isoformat(),
                "is_healthy": final_health.is_healthy,
                "is_idle": final_health.is_idle,
                "failure_reason": final_health.failure_reason,
                "verification_check": True,
            }
            recovery_data["health_checks"].append(final_health_data)

            if final_health.is_healthy:
                recovery_data["recovery_verified"] = True
                recovery_logger.info(f"Recovery verified: {target} is now healthy")
            else:
                recovery_data["recovery_verified"] = False
                recovery_logger.warning(
                    f"Recovery incomplete: {target} still shows issues: {final_health.failure_reason}"
                )

        # Calculate final metrics
        total_duration: float = (datetime.now() - recovery_start_time).total_seconds()
        recovery_data["total_duration"] = total_duration

        # Generate final status message and send final notification
        if restart_success and recovery_data.get("recovery_verified", True):
            final_message: str = f"Recovery successful for {target} in {total_duration:.1f}s: {restart_message}"
            recovery_logger.info(final_message)

            # Send success notification
            try:
                send_recovery_notification(
                    tmux=tmux,
                    target=target,
                    notification_type="recovery_success",
                    message=f"Agent {target} successfully recovered in {total_duration:.1f}s. Agent is now healthy and operational.",
                    cooldown_minutes=5,
                    logger=recovery_logger,
                )
            except Exception as e:
                recovery_logger.warning(f"Failed to send recovery success notification: {str(e)}")

            # Create final audit log
            if use_structured_logging:
                create_recovery_audit_log(
                    recovery_logger,
                    recovery_session_id,
                    recovery_data["logged_events"],
                    "success",
                    total_duration,
                )

            return True, final_message, recovery_data
        else:
            final_error: str = f"Recovery failed for {target} after {total_duration:.1f}s: {restart_message}"
            recovery_logger.error(final_error)

            # Send failure notification
            try:
                send_recovery_notification(
                    tmux=tmux,
                    target=target,
                    notification_type="recovery_failed",
                    message=f"Recovery failed for {target} after {total_duration:.1f}s. Manual intervention may be required. Error: {restart_message}",
                    cooldown_minutes=5,
                    logger=recovery_logger,
                )
            except Exception as e:
                recovery_logger.warning(f"Failed to send recovery failure notification: {str(e)}")

            # Create final audit log
            if use_structured_logging:
                create_recovery_audit_log(
                    recovery_logger,
                    recovery_session_id,
                    recovery_data["logged_events"],
                    "failed",
                    total_duration,
                )

            return False, final_error, recovery_data

    except Exception as e:
        # Handle unexpected errors during recovery
        error_duration: float = (datetime.now() - recovery_start_time).total_seconds()
        recovery_data["total_duration"] = error_duration
        recovery_data["recovery_successful"] = False
        recovery_data["recovery_error"] = str(e)

        exception_message: str = f"Recovery coordination failed for {target} after {error_duration:.1f}s: {str(e)}"
        recovery_logger.error(exception_message)

        return False, exception_message, recovery_data


def batch_recovery_coordination(
    tmux: TMUXManager,
    targets: list[str],
    logger: logging.Logger,
    parallel_limit: int = 3,
    **recovery_kwargs: Any,
) -> dict[str, tuple[bool, str, dict[str, Any]]]:
    """
    Coordinate recovery for multiple agents with parallel processing.

    Manages recovery of multiple agents simultaneously while respecting
    resource limits and providing comprehensive result tracking.

    Args:
        tmux: TMUX manager instance for session operations
        targets: List of agent targets in format 'session:window'
        logger: Logger instance for recovery event tracking
        parallel_limit: Maximum number of simultaneous recoveries (default: 3)
        **recovery_kwargs: Additional arguments passed to coordinate_agent_recovery

    Returns:
        Dictionary mapping target -> (success, message, recovery_data)

    Raises:
        ValueError: If targets list is empty or contains invalid formats
    """
    if not targets:
        raise ValueError("No targets provided for batch recovery")

    logger.info(f"Starting batch recovery coordination for {len(targets)} agents")

    results: dict[str, tuple[bool, str, dict[str, Any]]] = {}

    # For now, implement sequential processing
    # Future enhancement: implement parallel processing with threading
    for target in targets:
        try:
            logger.info(f"Processing recovery for {target}")

            success, message, data = coordinate_agent_recovery(
                tmux=tmux, target=target, logger=logger, **recovery_kwargs
            )

            results[target] = (success, message, data)

            logger.info(f"Recovery result for {target}: {'SUCCESS' if success else 'FAILED'}")

        except Exception as e:
            error_message: str = f"Batch recovery error for {target}: {str(e)}"
            logger.error(error_message)

            error_data: dict[str, Any] = {
                "target": target,
                "batch_error": str(e),
                "recovery_successful": False,
            }

            results[target] = (False, error_message, error_data)

    successful_count: int = sum(1 for success, _, _ in results.values() if success)
    logger.info(f"Batch recovery completed: {successful_count}/{len(targets)} successful")

    return results

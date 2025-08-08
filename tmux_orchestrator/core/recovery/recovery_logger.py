"""Comprehensive recovery event logging system.

Provides structured logging for all recovery events with proper formatting,
metrics tracking, audit trails, and integration with monitoring systems.
Follows one-function-per-file pattern with comprehensive type annotations.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

from logging.handlers import RotatingFileHandler


def setup_recovery_logger(
    log_dir: Optional[Path] = None,
    log_level: int = logging.INFO,
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    enable_console: bool = True
) -> logging.Logger:
    """
    Set up comprehensive recovery event logger with rotation and formatting.
    
    Creates a dedicated logger for recovery events with structured formatting,
    file rotation, and optional console output. Ensures all recovery events
    are properly tracked and auditable.
    
    Args:
        log_dir: Directory for log files (defaults to registry/logs/recovery)
        log_level: Logging level (default: INFO)
        max_file_size: Maximum log file size in bytes before rotation (default: 10MB)
        backup_count: Number of backup files to keep (default: 5)
        enable_console: Whether to enable console logging (default: True)
        
    Returns:
        Configured logger instance for recovery events
        
    Raises:
        OSError: If log directory cannot be created
        PermissionError: If log files cannot be written
    """
    # Initialize log directory
    if log_dir is None:
        log_dir = Path.cwd() / "registry" / "logs" / "recovery"
    
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Create recovery logger
    logger: logging.Logger = logging.getLogger('recovery_system')
    logger.setLevel(log_level)
    
    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Create formatter for structured logging
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler with rotation
    log_file: Path = log_dir / "recovery_events.log"
    file_handler = RotatingFileHandler(
        filename=str(log_file),
        maxBytes=max_file_size,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Console handler (optional)
    if enable_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    logger.info(f"Recovery logger initialized - Log file: {log_file}")
    return logger


def log_recovery_event(
    logger: logging.Logger,
    event_type: str,
    target: str,
    event_data: Dict[str, Any],
    level: int = logging.INFO,
    include_metrics: bool = True
) -> Dict[str, Any]:
    """
    Log a structured recovery event with comprehensive metadata.
    
    Creates detailed, structured log entries for recovery events with
    standardized formatting, metrics, and searchable metadata.
    
    Args:
        logger: Logger instance for recovery events
        event_type: Type of recovery event ('failure_detected', 'recovery_started', etc.)
        target: Target agent in format 'session:window'
        event_data: Event-specific data dictionary
        level: Logging level for this event (default: INFO)
        include_metrics: Whether to include performance metrics (default: True)
        
    Returns:
        Dictionary containing the complete logged event data
        
    Raises:
        ValueError: If event_type or target format is invalid
    """
    # Validate inputs
    valid_event_types: List[str] = [
        'failure_detected', 'recovery_started', 'recovery_success', 'recovery_failed',
        'health_check', 'auto_restart', 'briefing_restored', 'notification_sent',
        'context_preserved', 'agent_verified'
    ]
    
    if event_type not in valid_event_types:
        raise ValueError(f"Invalid event_type: {event_type}. Valid types: {valid_event_types}")
    
    if ':' not in target:
        raise ValueError(f"Invalid target format: {target}. Expected 'session:window'")
    
    # Build comprehensive event record
    event_record: Dict[str, Any] = {
        'timestamp': datetime.now().isoformat(),
        'event_type': event_type,
        'target': target,
        'session': target.split(':')[0],
        'window': target.split(':')[1].split('.')[0],  # Remove pane if present
        'event_data': event_data.copy(),
        'log_level': logging.getLevelName(level)
    }
    
    # Add performance metrics if requested
    if include_metrics:
        metrics: Dict[str, Any] = _extract_performance_metrics(event_data)
        if metrics:
            event_record['metrics'] = metrics
    
    # Add event-specific metadata
    event_record['metadata'] = _build_event_metadata(event_type, event_data)
    
    # Generate human-readable summary
    summary: str = _generate_event_summary(event_type, target, event_data)
    event_record['summary'] = summary
    
    # Create structured log message
    log_message: str = f"RECOVERY_EVENT | {event_type.upper()} | {target} | {summary}"
    
    # Add JSON data for structured parsing
    json_data: str = json.dumps(event_record, separators=(',', ':'))
    full_log_message: str = f"{log_message} | DATA: {json_data}"
    
    # Log the event
    logger.log(level, full_log_message)
    
    return event_record


def _extract_performance_metrics(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract performance metrics from event data."""
    metrics: Dict[str, Any] = {}
    
    # Duration metrics
    if 'total_duration' in event_data:
        metrics['duration_seconds'] = event_data['total_duration']
        
    if 'retry_attempts' in event_data:
        metrics['retry_count'] = event_data['retry_attempts']
    
    # Success metrics
    if 'recovery_successful' in event_data:
        metrics['success'] = event_data['recovery_successful']
    
    if 'delivery_successful' in event_data:
        metrics['delivery_success'] = event_data['delivery_successful']
    
    # Size metrics
    if 'briefing_length' in event_data:
        metrics['briefing_chars'] = event_data['briefing_length']
    
    if 'conversation_history' in event_data:
        history = event_data['conversation_history']
        if isinstance(history, list):
            metrics['context_lines'] = len(history)
    
    return metrics


def _build_event_metadata(event_type: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Build event-specific metadata."""
    metadata: Dict[str, Any] = {
        'event_category': _get_event_category(event_type)
    }
    
    # Add role information if available
    if 'agent_role' in event_data:
        metadata['agent_role'] = event_data['agent_role']
    
    # Add failure reason for failure events
    if event_type in ['failure_detected', 'recovery_failed'] and 'failure_reason' in event_data:
        metadata['failure_reason'] = event_data['failure_reason']
    
    # Add notification information
    if event_type == 'notification_sent':
        if 'notification_type' in event_data:
            metadata['notification_type'] = event_data['notification_type']
        if 'cooldown_minutes' in event_data:
            metadata['cooldown_minutes'] = event_data['cooldown_minutes']
    
    # Add health status
    if 'is_healthy' in event_data:
        metadata['agent_healthy'] = event_data['is_healthy']
    if 'is_idle' in event_data:
        metadata['agent_idle'] = event_data['is_idle']
    
    return metadata


def _get_event_category(event_type: str) -> str:
    """Get category for event type."""
    category_map: Dict[str, str] = {
        'failure_detected': 'detection',
        'health_check': 'monitoring',
        'recovery_started': 'recovery',
        'recovery_success': 'recovery', 
        'recovery_failed': 'recovery',
        'auto_restart': 'restart',
        'briefing_restored': 'briefing',
        'notification_sent': 'notification',
        'context_preserved': 'context',
        'agent_verified': 'verification'
    }
    return category_map.get(event_type, 'unknown')


def _generate_event_summary(event_type: str, target: str, event_data: Dict[str, Any]) -> str:
    """Generate human-readable event summary."""
    session: str = target.split(':')[0]
    
    if event_type == 'failure_detected':
        reason: str = event_data.get('failure_reason', 'unknown')
        return f"Failure detected in {session}: {reason}"
    
    elif event_type == 'recovery_started':
        return f"Recovery initiated for {session}"
    
    elif event_type == 'recovery_success':
        duration: float = event_data.get('total_duration', 0)
        return f"Recovery completed for {session} in {duration:.1f}s"
    
    elif event_type == 'recovery_failed':
        reason: str = event_data.get('failure_reason', 'unknown error')
        return f"Recovery failed for {session}: {reason}"
    
    elif event_type == 'auto_restart':
        attempts: int = event_data.get('retry_attempts', 1)
        success: bool = event_data.get('restart_successful', False)
        status: str = "succeeded" if success else "failed"
        return f"Auto-restart {status} for {session} (attempt {attempts})"
    
    elif event_type == 'briefing_restored':
        role: str = event_data.get('agent_role', 'unknown')
        success: bool = event_data.get('briefing_restored', False)
        status: str = "succeeded" if success else "failed"
        return f"Briefing restoration {status} for {role} in {session}"
    
    elif event_type == 'notification_sent':
        notification_type: str = event_data.get('notification_type', 'unknown')
        return f"Sent {notification_type} notification for {session}"
    
    elif event_type == 'health_check':
        healthy: bool = event_data.get('is_healthy', False)
        status: str = "healthy" if healthy else "unhealthy"
        return f"Health check: {session} is {status}"
    
    elif event_type == 'context_preserved':
        lines: int = len(event_data.get('conversation_history', []))
        return f"Context preserved for {session} ({lines} lines)"
    
    elif event_type == 'agent_verified':
        verified: bool = event_data.get('recovery_verified', False)
        status: str = "verified" if verified else "failed verification"
        return f"Agent verification: {session} {status}"
    
    else:
        return f"Event {event_type} for {session}"


def create_recovery_audit_log(
    logger: logging.Logger,
    recovery_session_id: str,
    events: List[Dict[str, Any]],
    final_status: str,
    total_duration: float
) -> Dict[str, Any]:
    """
    Create comprehensive audit log for complete recovery session.
    
    Generates a complete audit trail for an entire recovery session,
    including all events, timelines, metrics, and final outcomes.
    
    Args:
        logger: Logger instance for recovery events
        recovery_session_id: Unique identifier for this recovery session
        events: List of all events that occurred during recovery
        final_status: Final recovery status ('success', 'failed', 'timeout')
        total_duration: Total time taken for recovery in seconds
        
    Returns:
        Dictionary containing complete audit log data
        
    Raises:
        ValueError: If recovery session data is invalid
    """
    if not recovery_session_id:
        raise ValueError("Recovery session ID cannot be empty")
    
    if not events:
        raise ValueError("No events provided for audit log")
    
    audit_timestamp: datetime = datetime.now()
    
    # Build comprehensive audit record
    audit_log: Dict[str, Any] = {
        'audit_timestamp': audit_timestamp.isoformat(),
        'recovery_session_id': recovery_session_id,
        'final_status': final_status,
        'total_duration': total_duration,
        'event_count': len(events),
        'events': events.copy()
    }
    
    # Extract targets involved
    targets: List[str] = list(set(event.get('target', '') for event in events if event.get('target')))
    audit_log['targets_involved'] = targets
    
    # Calculate session metrics
    session_metrics: Dict[str, Any] = _calculate_session_metrics(events, total_duration)
    audit_log['session_metrics'] = session_metrics
    
    # Generate timeline
    timeline: List[Dict[str, Any]] = _generate_recovery_timeline(events)
    audit_log['timeline'] = timeline
    
    # Create summary
    summary: str = _generate_session_summary(
        recovery_session_id, final_status, len(targets), total_duration, session_metrics
    )
    audit_log['summary'] = summary
    
    # Log the audit record
    audit_message: str = f"RECOVERY_AUDIT | {recovery_session_id} | {final_status.upper()} | {summary}"
    audit_json: str = json.dumps(audit_log, separators=(',', ':'))
    full_audit_message: str = f"{audit_message} | AUDIT: {audit_json}"
    
    logger.info(full_audit_message)
    
    return audit_log


def _calculate_session_metrics(events: List[Dict[str, Any]], total_duration: float) -> Dict[str, Any]:
    """Calculate metrics for recovery session."""
    metrics: Dict[str, Any] = {
        'total_duration': total_duration,
        'event_count': len(events),
        'success_rate': 0.0,
        'avg_event_duration': 0.0,
        'restart_attempts': 0,
        'notification_count': 0,
        'failure_count': 0
    }
    
    success_events: int = 0
    total_event_duration: float = 0.0
    duration_count: int = 0
    
    for event in events:
        event_data = event.get('event_data', {})
        event_type = event.get('event_type', '')
        
        # Count successes
        if event_type in ['recovery_success', 'briefing_restored'] and event_data.get('success', False):
            success_events += 1
        
        # Count failures
        if event_type in ['failure_detected', 'recovery_failed']:
            metrics['failure_count'] += 1
        
        # Count restarts
        if event_type == 'auto_restart':
            metrics['restart_attempts'] += event_data.get('retry_attempts', 1)
        
        # Count notifications
        if event_type == 'notification_sent':
            metrics['notification_count'] += 1
        
        # Calculate durations
        if 'total_duration' in event_data:
            total_event_duration += event_data['total_duration']
            duration_count += 1
    
    # Calculate rates
    if len(events) > 0:
        metrics['success_rate'] = success_events / len(events)
    
    if duration_count > 0:
        metrics['avg_event_duration'] = total_event_duration / duration_count
    
    return metrics


def _generate_recovery_timeline(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate chronological timeline of recovery events."""
    timeline: List[Dict[str, Any]] = []
    
    for event in sorted(events, key=lambda x: x.get('timestamp', '')):
        timeline_entry: Dict[str, Any] = {
            'timestamp': event.get('timestamp'),
            'event_type': event.get('event_type'),
            'target': event.get('target'),
            'summary': event.get('summary')
        }
        
        # Add key metrics for this event
        if 'metrics' in event:
            timeline_entry['metrics'] = event['metrics']
        
        timeline.append(timeline_entry)
    
    return timeline


def _generate_session_summary(
    session_id: str,
    final_status: str,
    target_count: int,
    total_duration: float,
    metrics: Dict[str, Any]
) -> str:
    """Generate human-readable session summary."""
    status_emoji: str = "✅" if final_status == "success" else "❌" if final_status == "failed" else "⏱️"
    
    summary_parts: List[str] = [
        f"Session {session_id} {status_emoji} {final_status}",
        f"{target_count} agent(s)",
        f"{total_duration:.1f}s duration",
        f"{metrics.get('event_count', 0)} events"
    ]
    
    if metrics.get('restart_attempts', 0) > 0:
        summary_parts.append(f"{metrics['restart_attempts']} restart(s)")
    
    if metrics.get('success_rate', 0) > 0:
        success_pct: float = metrics['success_rate'] * 100
        summary_parts.append(f"{success_pct:.0f}% success")
    
    return " | ".join(summary_parts)
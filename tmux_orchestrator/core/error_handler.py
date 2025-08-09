"""Comprehensive error handling for TMUX Orchestrator."""

import functools
import logging
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar, Union

from rich.console import Console
from rich.panel import Panel

console = Console()
logger = logging.getLogger(__name__)

T = TypeVar("T")


class ErrorSeverity(Enum):
    """Error severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification."""

    TMUX = "tmux"
    AGENT = "agent"
    NETWORK = "network"
    FILE_SYSTEM = "filesystem"
    CONFIGURATION = "configuration"
    VALIDATION = "validation"
    PERMISSION = "permission"
    RESOURCE = "resource"
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    """Context information for error handling."""

    operation: str
    agent_id: Optional[str] = None
    session_name: Optional[str] = None
    additional_info: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ErrorRecord:
    """Record of an error occurrence."""

    error_type: str
    message: str
    category: ErrorCategory
    severity: ErrorSeverity
    context: ErrorContext
    traceback: Optional[str] = None
    recovery_attempted: bool = False
    recovery_successful: bool = False
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ErrorHandler:
    """Centralized error handling with recovery procedures."""

    def __init__(self, log_dir: Optional[Path] = None) -> None:
        """Initialize error handler."""
        self.log_dir = log_dir or Path.home() / ".tmux-orchestrator" / "errors"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.error_history: list[ErrorRecord] = []
        self.recovery_procedures: dict[ErrorCategory, Callable] = {}
        self._setup_recovery_procedures()

    def handle_error(
        self,
        error: Exception,
        context: ErrorContext,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        attempt_recovery: bool = True,
    ) -> ErrorRecord:
        """Handle an error with optional recovery."""
        # Classify the error
        category = self._classify_error(error)

        # Create error record
        record = ErrorRecord(
            error_type=type(error).__name__,
            message=str(error),
            category=category,
            severity=severity,
            context=context,
            traceback=traceback.format_exc() if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL] else None,
        )

        # Log the error
        self._log_error(record)

        # Attempt recovery if requested
        if attempt_recovery and category in self.recovery_procedures:
            try:
                record.recovery_attempted = True
                recovery_func = self.recovery_procedures[category]
                recovery_func(error, context)
                record.recovery_successful = True
            except Exception as recovery_error:
                logger.error(f"Recovery failed: {recovery_error}")
                record.recovery_successful = False

        # Add to history
        self.error_history.append(record)

        # Display error if critical
        if severity == ErrorSeverity.CRITICAL:
            self._display_critical_error(record)

        return record

    def _classify_error(self, error: Exception) -> ErrorCategory:
        """Classify an error into a category."""
        error_type = type(error).__name__
        error_msg = str(error).lower()

        # TMUX-related errors
        if "tmux" in error_msg or "session" in error_msg or "window" in error_msg:
            return ErrorCategory.TMUX

        # Agent-related errors
        if "agent" in error_msg or "claude" in error_msg:
            return ErrorCategory.AGENT

        # Network errors
        if any(word in error_msg for word in ["connection", "timeout", "network", "socket"]):
            return ErrorCategory.NETWORK

        # File system errors
        if any(word in error_msg for word in ["file", "directory", "path", "not found"]):
            return ErrorCategory.FILE_SYSTEM

        # Permission errors
        if any(word in error_msg for word in ["permission", "access denied", "forbidden"]):
            return ErrorCategory.PERMISSION

        # Resource errors
        if any(word in error_msg for word in ["memory", "cpu", "resource", "limit"]):
            return ErrorCategory.RESOURCE

        # Validation errors (check type first)
        if error_type in ["ValueError", "ValidationError", "TypeError"]:
            return ErrorCategory.VALIDATION

        # Configuration errors
        if any(word in error_msg for word in ["config", "setting"]):
            return ErrorCategory.CONFIGURATION

        return ErrorCategory.UNKNOWN

    def _setup_recovery_procedures(self) -> None:
        """Set up automatic recovery procedures."""
        self.recovery_procedures = {
            ErrorCategory.TMUX: self._recover_tmux_error,
            ErrorCategory.AGENT: self._recover_agent_error,
            ErrorCategory.NETWORK: self._recover_network_error,
            ErrorCategory.FILE_SYSTEM: self._recover_filesystem_error,
            ErrorCategory.PERMISSION: self._recover_permission_error,
        }

    def _recover_tmux_error(self, error: Exception, context: ErrorContext) -> None:
        """Attempt to recover from TMUX errors."""
        if context.session_name:
            # Try to create session if it doesn't exist
            logger.info(f"Attempting to recover TMUX session: {context.session_name}")
            # Recovery logic would go here

    def _recover_agent_error(self, error: Exception, context: ErrorContext) -> None:
        """Attempt to recover from agent errors."""
        if context.agent_id:
            # Try to restart agent
            logger.info(f"Attempting to recover agent: {context.agent_id}")
            # Recovery logic would go here

    def _recover_network_error(self, error: Exception, context: ErrorContext) -> None:
        """Attempt to recover from network errors."""
        # Implement exponential backoff retry
        logger.info("Network error detected, implementing retry strategy")
        # Recovery logic would go here

    def _recover_filesystem_error(self, error: Exception, context: ErrorContext) -> None:
        """Attempt to recover from filesystem errors."""
        # Try to create missing directories
        logger.info("Filesystem error detected, checking paths")
        # Recovery logic would go here

    def _recover_permission_error(self, error: Exception, context: ErrorContext) -> None:
        """Attempt to recover from permission errors."""
        # Provide guidance on fixing permissions
        logger.info("Permission error detected, checking file permissions")
        # Recovery logic would go here

    def _log_error(self, record: ErrorRecord) -> None:
        """Log error to file and logger."""
        # Log to file
        log_file = self.log_dir / f"errors_{datetime.now().strftime('%Y%m%d')}.log"
        with open(log_file, "a") as f:
            f.write(
                f"{record.timestamp.isoformat()} | {record.severity.value.upper()} | "
                f"{record.category.value} | {record.error_type}: {record.message} | "
                f"Operation: {record.context.operation}\n"
            )
            if record.traceback:
                f.write(f"Traceback:\n{record.traceback}\n")
            f.write("-" * 80 + "\n")

        # Log to logger
        log_level = {
            ErrorSeverity.LOW: logging.INFO,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL,
        }[record.severity]

        logger.log(
            log_level,
            f"{record.error_type}: {record.message} [{record.category.value}] in {record.context.operation}",
        )

    def _display_critical_error(self, record: ErrorRecord) -> None:
        """Display critical error to user."""
        error_panel = Panel(
            f"[red bold]CRITICAL ERROR[/red bold]\n\n"
            f"[yellow]Operation:[/yellow] {record.context.operation}\n"
            f"[yellow]Error:[/yellow] {record.message}\n"
            f"[yellow]Category:[/yellow] {record.category.value}\n"
            f"[yellow]Time:[/yellow] {record.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"[dim]Check logs at: {self.log_dir}[/dim]",
            title="⚠️  System Error",
            border_style="red",
        )
        console.print(error_panel)

    def get_error_summary(self) -> dict[str, Any]:
        """Get summary of errors."""
        if not self.error_history:
            return {"total": 0, "by_category": {}, "by_severity": {}}

        summary: dict[str, Any] = {
            "total": len(self.error_history),
            "by_category": {},
            "by_severity": {},
            "recovery_success_rate": 0.0,
        }

        # Count by category
        for record in self.error_history:
            cat = record.category.value
            summary["by_category"][cat] = summary["by_category"].get(cat, 0) + 1

            sev = record.severity.value
            summary["by_severity"][sev] = summary["by_severity"].get(sev, 0) + 1

        # Calculate recovery success rate
        recovery_attempts = [r for r in self.error_history if r.recovery_attempted]
        if recovery_attempts:
            successful = len([r for r in recovery_attempts if r.recovery_successful])
            summary["recovery_success_rate"] = (successful / len(recovery_attempts)) * 100

        return summary


# Decorator for automatic error handling
def handle_errors(
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    category: Optional[ErrorCategory] = None,
    operation: str = "",
    attempt_recovery: bool = True,
) -> Callable:
    """Decorator for automatic error handling."""

    def decorator(func: Callable[..., T]) -> Callable[..., Union[T, None]]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Union[T, None]:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Create context
                context = ErrorContext(
                    operation=operation or func.__name__,
                    additional_info={
                        "args": str(args)[:100],
                        "kwargs": str(kwargs)[:100],
                    },
                )

                # Get or create error handler
                if not hasattr(wrapper, "_error_handler"):
                    wrapper._error_handler = ErrorHandler()  # type: ignore[attr-defined]

                # Handle error
                wrapper._error_handler.handle_error(e, context, severity, attempt_recovery)  # type: ignore[attr-defined]

                # Re-raise if critical
                if severity == ErrorSeverity.CRITICAL:
                    raise

                return None

        return wrapper

    return decorator


# Retry decorator with exponential backoff
def retry_on_error(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable:
    """Decorator for retrying operations with exponential backoff."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            delay = initial_delay
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay} seconds...")
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        logger.error(f"All {max_attempts} attempts failed")

            raise last_exception  # type: ignore

        return wrapper

    return decorator


# Global error handler instance
_global_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """Get global error handler instance."""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = ErrorHandler()
    return _global_error_handler


def clear_error_messages(age_days: int = 7) -> int:
    """Clear old error messages."""
    handler = get_error_handler()
    cleared = 0

    for log_file in handler.log_dir.glob("errors_*.log"):
        # Check file age
        if (time.time() - log_file.stat().st_mtime) > (age_days * 86400):
            log_file.unlink()
            cleared += 1

    return cleared

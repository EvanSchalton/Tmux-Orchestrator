"""Tests for error handler."""

import os
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from tmux_orchestrator.core.error_handler import (
    ErrorCategory,
    ErrorContext,
    ErrorHandler,
    ErrorSeverity,
    clear_error_messages,
    get_error_handler,
    handle_errors,
    retry_on_error,
)


@pytest.fixture
def temp_log_dir(tmp_path: Path) -> Path:
    """Create temporary log directory."""
    return tmp_path / "error_logs"


@pytest.fixture
def error_handler(temp_log_dir: Path) -> ErrorHandler:
    """Create error handler with temp directory."""
    return ErrorHandler(log_dir=temp_log_dir)


def test_error_classification(error_handler: ErrorHandler) -> None:
    """Test error classification."""
    # TMUX errors
    tmux_error = Exception("Failed to create tmux session")
    assert error_handler._classify_error(tmux_error) == ErrorCategory.TMUX

    # Agent errors
    agent_error = Exception("Agent claude-1 not responding")
    assert error_handler._classify_error(agent_error) == ErrorCategory.AGENT

    # Network errors
    network_error = Exception("Connection timeout")
    assert error_handler._classify_error(network_error) == ErrorCategory.NETWORK

    # File system errors
    fs_error = Exception("File not found: config.yaml")
    assert error_handler._classify_error(fs_error) == ErrorCategory.FILE_SYSTEM

    # Permission errors
    perm_error = Exception("Permission denied")
    assert error_handler._classify_error(perm_error) == ErrorCategory.PERMISSION

    # Validation errors
    val_error = ValueError("Invalid value")
    assert error_handler._classify_error(val_error) == ErrorCategory.VALIDATION

    # Unknown errors
    unknown_error = Exception("Something went wrong")
    assert error_handler._classify_error(unknown_error) == ErrorCategory.UNKNOWN


def test_handle_error_basic(error_handler: ErrorHandler) -> None:
    """Test basic error handling."""
    error = Exception("Test error")
    context = ErrorContext(operation="test_operation")

    record = error_handler.handle_error(error, context, severity=ErrorSeverity.LOW)

    assert record.error_type == "Exception"
    assert record.message == "Test error"
    assert record.severity == ErrorSeverity.LOW
    assert record.context.operation == "test_operation"
    assert len(error_handler.error_history) == 1


def test_handle_error_with_recovery(error_handler: ErrorHandler) -> None:
    """Test error handling with recovery attempt."""
    # Mock recovery procedure
    mock_recovery = Mock()
    error_handler.recovery_procedures[ErrorCategory.TMUX] = mock_recovery

    error = Exception("tmux session error")
    context = ErrorContext(operation="session_create", session_name="test-session")

    record = error_handler.handle_error(error, context, attempt_recovery=True)

    assert record.recovery_attempted
    mock_recovery.assert_called_once_with(error, context)


def test_handle_critical_error(error_handler: ErrorHandler) -> None:
    """Test critical error handling."""
    error = Exception("Critical failure")
    context = ErrorContext(operation="critical_op")

    with patch("tmux_orchestrator.core.error_handler.console.print") as mock_print:
        record = error_handler.handle_error(error, context, severity=ErrorSeverity.CRITICAL)

        assert record.severity == ErrorSeverity.CRITICAL
        assert record.traceback is not None
        mock_print.assert_called_once()  # Critical error displayed


def test_error_logging(error_handler: ErrorHandler, temp_log_dir: Path) -> None:
    """Test error logging to file."""
    error = Exception("Log test error")
    context = ErrorContext(operation="log_test")

    error_handler.handle_error(error, context)

    # Check log file exists
    log_files = list(temp_log_dir.glob("errors_*.log"))
    assert len(log_files) == 1

    # Check log content
    with open(log_files[0]) as f:
        content = f.read()
        assert "Log test error" in content
        assert "log_test" in content


def test_get_error_summary(error_handler: ErrorHandler) -> None:
    """Test error summary generation."""
    # Add various errors
    errors = [
        (Exception("tmux error 1"), ErrorCategory.TMUX, ErrorSeverity.LOW),
        (Exception("tmux error 2"), ErrorCategory.TMUX, ErrorSeverity.MEDIUM),
        (Exception("agent error"), ErrorCategory.AGENT, ErrorSeverity.HIGH),
        (Exception("network error"), ErrorCategory.NETWORK, ErrorSeverity.CRITICAL),
    ]

    for error, _, severity in errors:
        context = ErrorContext(operation="test")
        error_handler.handle_error(error, context, severity=severity)

    summary = error_handler.get_error_summary()

    assert summary["total"] == 4
    assert summary["by_category"]["tmux"] == 2
    assert summary["by_category"]["agent"] == 1
    assert summary["by_category"]["network"] == 1
    assert summary["by_severity"]["low"] == 1
    assert summary["by_severity"]["medium"] == 1
    assert summary["by_severity"]["high"] == 1
    assert summary["by_severity"]["critical"] == 1


def test_handle_errors_decorator() -> None:
    """Test handle_errors decorator."""

    @handle_errors(severity=ErrorSeverity.MEDIUM, operation="decorated_func")
    def failing_function() -> str:
        raise ValueError("Decorated error")

    # Function should not raise but return None
    result = failing_function()
    assert result is None


def test_handle_errors_decorator_critical() -> None:
    """Test handle_errors decorator with critical error."""

    @handle_errors(severity=ErrorSeverity.CRITICAL, operation="critical_func")
    def critical_function() -> str:
        raise Exception("Critical error")

    # Critical errors should still raise
    with pytest.raises(Exception, match="Critical error"):
        critical_function()


def test_retry_on_error_decorator() -> None:
    """Test retry_on_error decorator."""
    attempt_count = 0

    @retry_on_error(max_attempts=3, initial_delay=0.1)
    def flaky_function() -> str:
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 3:
            raise ConnectionError("Network error")
        return "Success"

    result = flaky_function()
    assert result == "Success"
    assert attempt_count == 3


def test_retry_on_error_all_fail() -> None:
    """Test retry decorator when all attempts fail."""

    @retry_on_error(max_attempts=3, initial_delay=0.1)
    def always_fails() -> str:
        raise ConnectionError("Always fails")

    with pytest.raises(ConnectionError, match="Always fails"):
        always_fails()


def test_retry_specific_exceptions() -> None:
    """Test retry decorator with specific exceptions."""

    @retry_on_error(max_attempts=3, initial_delay=0.1, exceptions=(ConnectionError, TimeoutError))
    def specific_error() -> str:
        raise ValueError("Not retryable")

    # ValueError not in exceptions tuple, should fail immediately
    with pytest.raises(ValueError, match="Not retryable"):
        specific_error()


def test_get_error_handler_singleton() -> None:
    """Test global error handler singleton."""
    handler1 = get_error_handler()
    handler2 = get_error_handler()
    assert handler1 is handler2


def test_clear_error_messages(temp_log_dir: Path) -> None:
    """Test clearing old error messages."""
    # Create old log files
    old_file = temp_log_dir / "errors_20230101.log"
    old_file.parent.mkdir(parents=True, exist_ok=True)
    old_file.touch()

    # Make file appear old
    old_time = time.time() - (8 * 86400)  # 8 days old
    os.utime(old_file, (old_time, old_time))

    # Create recent file
    recent_file = temp_log_dir / "errors_20231201.log"
    recent_file.touch()

    # Clear old files
    with patch("tmux_orchestrator.core.error_handler.get_error_handler") as mock_get:
        mock_handler = Mock()
        mock_handler.log_dir = temp_log_dir
        mock_get.return_value = mock_handler

        cleared = clear_error_messages(age_days=7)

    assert cleared == 1
    assert not old_file.exists()
    assert recent_file.exists()


def test_error_context_additional_info(error_handler: ErrorHandler) -> None:
    """Test error context with additional information."""
    error = Exception("Context test")
    context = ErrorContext(
        operation="complex_operation",
        agent_id="agent-1",
        session_name="test-session",
        additional_info={
            "retry_count": 3,
            "last_success": "2023-12-01",
        },
    )

    record = error_handler.handle_error(error, context)

    assert record.context.agent_id == "agent-1"
    assert record.context.session_name == "test-session"
    assert record.context.additional_info["retry_count"] == 3
    assert record.context.additional_info["last_success"] == "2023-12-01"


def test_recovery_procedures_setup(error_handler: ErrorHandler) -> None:
    """Test recovery procedures are set up."""
    assert ErrorCategory.TMUX in error_handler.recovery_procedures
    assert ErrorCategory.AGENT in error_handler.recovery_procedures
    assert ErrorCategory.NETWORK in error_handler.recovery_procedures
    assert ErrorCategory.FILE_SYSTEM in error_handler.recovery_procedures
    assert ErrorCategory.PERMISSION in error_handler.recovery_procedures

    # Unknown category should not have recovery
    assert ErrorCategory.UNKNOWN not in error_handler.recovery_procedures


def test_exponential_backoff() -> None:
    """Test exponential backoff in retry decorator."""
    delays: list[float] = []

    @retry_on_error(max_attempts=4, initial_delay=0.1, backoff_factor=2.0)
    def track_delays() -> str:
        if len(delays) < 3:
            delays.append(time.time())
            raise ConnectionError("Retry me")
        return "Success"

    result = track_delays()

    assert result == "Success"
    assert len(delays) == 3

    # Check delays are approximately correct (with some tolerance)
    # Expected delays: 0.1, 0.2, 0.4
    if len(delays) >= 2:
        first_delay = delays[1] - delays[0]
        assert 0.05 < first_delay < 0.15  # ~0.1s

        second_delay = delays[2] - delays[1]
        assert 0.15 < second_delay < 0.25  # ~0.2s

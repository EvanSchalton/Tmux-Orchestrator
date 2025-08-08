"""Tests for detect_failure module."""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime, timedelta

from tmux_orchestrator.core.recovery.detect_failure import (
    detect_failure,
    _check_idle_status,
    _has_critical_errors,
    _has_normal_claude_interface
)


class TestDetectFailure:
    """Test suite for detect_failure function."""
    
    def test_detect_failure_with_critical_error(self) -> None:
        """Test failure detection when critical errors are present."""
        # Arrange
        tmux_mock: Mock = Mock()
        tmux_mock.capture_pane.return_value = "connection lost - cannot proceed"
        target: str = "test-session:0"
        last_response: datetime = datetime.now() - timedelta(minutes=1)
        
        # Act
        is_failed, failure_reason, is_idle = detect_failure(
            tmux_mock, target, last_response, 0
        )
        
        # Assert
        assert is_failed is True
        assert failure_reason == "critical_error_detected"
        assert isinstance(is_idle, bool)
    
    def test_detect_failure_with_max_failures(self) -> None:
        """Test failure detection when max consecutive failures reached."""
        # Arrange
        tmux_mock: Mock = Mock()
        tmux_mock.capture_pane.return_value = "│ > waiting for input"
        target: str = "test-session:0"
        last_response: datetime = datetime.now() - timedelta(minutes=1)
        consecutive_failures: int = 3
        max_failures: int = 3
        
        # Act
        is_failed, failure_reason, is_idle = detect_failure(
            tmux_mock, target, last_response, consecutive_failures, max_failures
        )
        
        # Assert
        assert is_failed is True
        assert failure_reason == "max_consecutive_failures_reached"
    
    def test_detect_failure_with_extended_unresponsiveness(self) -> None:
        """Test failure detection with extended unresponsiveness."""
        # Arrange
        tmux_mock: Mock = Mock()
        tmux_mock.capture_pane.return_value = "│ > normal interface"
        target: str = "test-session:0"
        last_response: datetime = datetime.now() - timedelta(minutes=10)
        response_timeout: int = 60  # 1 minute
        
        # Act
        is_failed, failure_reason, is_idle = detect_failure(
            tmux_mock, target, last_response, 0, 3, response_timeout
        )
        
        # Assert
        assert is_failed is True
        assert failure_reason == "extended_unresponsiveness"
    
    def test_detect_failure_healthy_agent(self) -> None:
        """Test failure detection with healthy agent."""
        # Arrange
        tmux_mock: Mock = Mock()
        tmux_mock.capture_pane.return_value = "│ > I'll help you with that task"
        target: str = "test-session:0"
        last_response: datetime = datetime.now() - timedelta(seconds=30)
        
        # Act
        is_failed, failure_reason, is_idle = detect_failure(
            tmux_mock, target, last_response, 0
        )
        
        # Assert
        assert is_failed is False
        assert failure_reason == "healthy"
    
    def test_detect_failure_invalid_target_format(self) -> None:
        """Test failure detection with invalid target format."""
        # Arrange
        tmux_mock: Mock = Mock()
        target: str = "invalid-target-format"
        last_response: datetime = datetime.now()
        
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid target format"):
            detect_failure(tmux_mock, target, last_response, 0)


class TestCheckIdleStatus:
    """Test suite for _check_idle_status function."""
    
    def test_check_idle_status_agent_is_idle(self) -> None:
        """Test idle detection when agent is idle."""
        # Arrange
        tmux_mock: Mock = Mock()
        tmux_mock.capture_pane.return_value = "│ > same output line"
        target: str = "test-session:0"
        
        # Act
        is_idle: bool = _check_idle_status(tmux_mock, target)
        
        # Assert
        assert is_idle is True
        assert tmux_mock.capture_pane.call_count == 4
    
    def test_check_idle_status_agent_is_active(self) -> None:
        """Test idle detection when agent is active."""
        # Arrange
        tmux_mock: Mock = Mock()
        # Simulate changing output
        tmux_mock.capture_pane.side_effect = [
            "line 1", "line 2", "line 3", "line 4"
        ]
        target: str = "test-session:0"
        
        # Act
        is_idle: bool = _check_idle_status(tmux_mock, target)
        
        # Assert
        assert is_idle is False
        assert tmux_mock.capture_pane.call_count == 4


class TestHasCriticalErrors:
    """Test suite for _has_critical_errors function."""
    
    def test_has_critical_errors_with_error(self) -> None:
        """Test critical error detection with error present."""
        # Arrange
        content: str = "Connection lost - unable to proceed"
        
        # Act
        has_errors: bool = _has_critical_errors(content)
        
        # Assert
        assert has_errors is True
    
    def test_has_critical_errors_without_error(self) -> None:
        """Test critical error detection with normal content."""
        # Arrange
        content: str = "│ > I'm ready to help with your task"
        
        # Act
        has_errors: bool = _has_critical_errors(content)
        
        # Assert
        assert has_errors is False
    
    def test_has_critical_errors_case_insensitive(self) -> None:
        """Test critical error detection is case insensitive."""
        # Arrange
        content: str = "NETWORK ERROR occurred during processing"
        
        # Act
        has_errors: bool = _has_critical_errors(content)
        
        # Assert
        assert has_errors is True


class TestHasNormalClaudeInterface:
    """Test suite for _has_normal_claude_interface function."""
    
    def test_has_normal_claude_interface_with_prompt(self) -> None:
        """Test Claude interface detection with prompt box."""
        # Arrange
        content: str = "│ > waiting for your input"
        
        # Act
        has_interface: bool = _has_normal_claude_interface(content)
        
        # Assert
        assert has_interface is True
    
    def test_has_normal_claude_interface_with_assistant_marker(self) -> None:
        """Test Claude interface detection with assistant marker."""
        # Arrange
        content: str = "assistant: I'll help you with that"
        
        # Act
        has_interface: bool = _has_normal_claude_interface(content)
        
        # Assert
        assert has_interface is True
    
    def test_has_normal_claude_interface_without_markers(self) -> None:
        """Test Claude interface detection without interface markers."""
        # Arrange
        content: str = "some random terminal output"
        
        # Act
        has_interface: bool = _has_normal_claude_interface(content)
        
        # Assert
        assert has_interface is False
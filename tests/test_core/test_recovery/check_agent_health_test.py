"""Tests for check_agent_health module."""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from tmux_orchestrator.core.recovery.check_agent_health import (
    AgentHealthStatus,
    check_agent_health,
)


class TestCheckAgentHealth:
    """Test suite for check_agent_health function."""

    def test_check_agent_health_healthy_agent(self) -> None:
        """Test health check for healthy agent."""
        # Arrange
        tmux_mock: Mock = Mock()
        target: str = "test-session:0"
        last_response: datetime = datetime.now() - timedelta(seconds=30)

        with patch("tmux_orchestrator.core.recovery.check_agent_health.detect_failure") as detect_mock:
            detect_mock.return_value = (False, "healthy", {"is_idle": False})

            # Act
            health_status: AgentHealthStatus = check_agent_health(tmux_mock, target, last_response)

            # Assert
            assert health_status.target == target
            assert health_status.is_healthy is True
            assert health_status.failure_reason == "healthy"
            assert health_status.consecutive_failures == 0
            assert health_status.is_idle is False

    def test_check_agent_health_unhealthy_agent(self) -> None:
        """Test health check for unhealthy agent."""
        # Arrange
        tmux_mock: Mock = Mock()
        target: str = "test-session:0"
        last_response: datetime = datetime.now() - timedelta(minutes=5)
        consecutive_failures: int = 2

        with patch("tmux_orchestrator.core.recovery.check_agent_health.detect_failure") as detect_mock:
            detect_mock.return_value = (True, "critical_error_detected", {"is_idle": True})

            # Act
            health_status: AgentHealthStatus = check_agent_health(
                tmux_mock, target, last_response, consecutive_failures
            )

            # Assert
            assert health_status.target == target
            assert health_status.is_healthy is False
            assert health_status.failure_reason == "critical_error_detected"
            assert health_status.consecutive_failures == 3

    def test_check_agent_health_invalid_target_format(self) -> None:
        """Test health check with invalid target format."""
        # Arrange
        tmux_mock: Mock = Mock()
        target: str = "invalid-format"
        last_response: datetime = datetime.now()

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid target format"):
            check_agent_health(tmux_mock, target, last_response)

    def test_check_agent_health_failure_count_reset(self) -> None:
        """Test that failure count resets when agent becomes healthy."""
        # Arrange
        tmux_mock: Mock = Mock()
        target: str = "test-session:0"
        last_response: datetime = datetime.now() - timedelta(seconds=30)
        consecutive_failures: int = 2

        with patch("tmux_orchestrator.core.recovery.check_agent_health.detect_failure") as detect_mock:
            detect_mock.return_value = (False, "healthy", {"is_idle": False})

            # Act
            health_status: AgentHealthStatus = check_agent_health(
                tmux_mock, target, last_response, consecutive_failures
            )

            # Assert
            assert health_status.consecutive_failures == 0

    def test_check_agent_health_exception_handling(self) -> None:
        """Test health check exception handling."""
        # Arrange
        tmux_mock: Mock = Mock()
        target: str = "test-session:0"
        last_response: datetime = datetime.now()

        with patch("tmux_orchestrator.core.recovery.check_agent_health.detect_failure") as detect_mock:
            detect_mock.side_effect = RuntimeError("Connection failed")

            # Act
            health_status: AgentHealthStatus = check_agent_health(tmux_mock, target, last_response)

            # Assert
            assert health_status.is_healthy is False
            assert "health_check_failed" in health_status.failure_reason
            assert health_status.consecutive_failures == 1

    def test_agent_health_status_namedtuple_structure(self) -> None:
        """Test AgentHealthStatus structure."""
        # Arrange
        status: AgentHealthStatus = AgentHealthStatus(
            target="test:0",
            is_healthy=True,
            is_idle=False,
            failure_reason="healthy",
            last_check=datetime.now(),
            consecutive_failures=0,
        )

        # Assert
        assert status.target == "test:0"
        assert status.is_healthy is True
        assert status.is_idle is False
        assert status.failure_reason == "healthy"
        assert isinstance(status.last_check, datetime)
        assert status.consecutive_failures == 0

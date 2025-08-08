"""Tests for restart_agent module."""

import pytest
import subprocess
from unittest.mock import Mock, patch

from tmux_orchestrator.core.recovery.restart_agent import restart_agent


class TestRestartAgent:
    """Test suite for restart_agent function."""
    
    def test_restart_agent_success(self) -> None:
        """Test successful agent restart."""
        # Arrange
        target: str = "test-session:0"
        logger_mock: Mock = Mock()
        
        with patch('subprocess.run') as subprocess_mock:
            subprocess_mock.return_value = Mock(
                returncode=0,
                stdout="Agent restarted successfully",
                stderr=""
            )
            
            # Act
            success, message = restart_agent(target, logger_mock)
            
            # Assert
            assert success is True
            assert "Successfully restarted agent test-session:0" in message
            logger_mock.warning.assert_called_once()
            logger_mock.info.assert_called_once()
    
    def test_restart_agent_cli_failure(self) -> None:
        """Test agent restart when CLI command fails."""
        # Arrange
        target: str = "test-session:0"
        logger_mock: Mock = Mock()
        
        with patch('subprocess.run') as subprocess_mock:
            subprocess_mock.side_effect = subprocess.CalledProcessError(
                returncode=1,
                cmd=['tmux-orchestrator', 'agent', 'restart', target],
                stderr="Session not found"
            )
            
            # Act
            success, message = restart_agent(target, logger_mock)
            
            # Assert
            assert success is False
            assert "CLI restart failed" in message
            assert "Session not found" in message
            logger_mock.error.assert_called_once()
    
    def test_restart_agent_cli_not_found(self) -> None:
        """Test agent restart when CLI is not found."""
        # Arrange
        target: str = "test-session:0"
        logger_mock: Mock = Mock()
        
        with patch('subprocess.run') as subprocess_mock:
            subprocess_mock.side_effect = FileNotFoundError("command not found")
            
            # Act & Assert
            with pytest.raises(RuntimeError, match="tmux-orchestrator CLI not found"):
                restart_agent(target, logger_mock)
    
    def test_restart_agent_invalid_target_format(self) -> None:
        """Test agent restart with invalid target format."""
        # Arrange
        target: str = "invalid-format"
        logger_mock: Mock = Mock()
        
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid target format"):
            restart_agent(target, logger_mock)
    
    def test_restart_agent_unexpected_error(self) -> None:
        """Test agent restart with unexpected error."""
        # Arrange
        target: str = "test-session:0"
        logger_mock: Mock = Mock()
        
        with patch('subprocess.run') as subprocess_mock:
            subprocess_mock.side_effect = RuntimeError("Unexpected error")
            
            # Act & Assert
            with pytest.raises(RuntimeError, match="Unexpected error restarting"):
                restart_agent(target, logger_mock)
    
    def test_restart_agent_calls_correct_command(self) -> None:
        """Test that restart_agent calls the correct CLI command."""
        # Arrange
        target: str = "test-session:0"
        logger_mock: Mock = Mock()
        
        with patch('subprocess.run') as subprocess_mock:
            subprocess_mock.return_value = Mock(
                returncode=0,
                stdout="Success",
                stderr=""
            )
            
            # Act
            restart_agent(target, logger_mock)
            
            # Assert
            subprocess_mock.assert_called_once_with([
                'tmux-orchestrator', 'agent', 'restart', target
            ], capture_output=True, text=True, check=True)
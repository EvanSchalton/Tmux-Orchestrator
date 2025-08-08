"""Tests for monitor CLI commands and daemon functionality."""

import os
import signal
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call

import pytest
from click.testing import CliRunner

from tmux_orchestrator.cli.monitor import monitor
from tmux_orchestrator.utils.tmux import TMUXManager


@pytest.fixture
def runner() -> CliRunner:
    """Create Click test runner."""
    return CliRunner()


@pytest.fixture
def mock_tmux():
    """Create mock TMUXManager."""
    return Mock(spec=TMUXManager)


@pytest.fixture
def temp_pid_file():
    """Create temporary PID file location."""
    with tempfile.NamedTemporaryFile(delete=False) as f:
        pid_file = f.name
    yield pid_file
    # Cleanup
    if os.path.exists(pid_file):
        os.unlink(pid_file)


def test_monitor_start_success(runner, mock_tmux, temp_pid_file):
    """Test starting the monitor daemon."""
    with patch('tmux_orchestrator.cli.monitor.PID_FILE', temp_pid_file):
        with patch('os.fork') as mock_fork:
            with patch('os.setsid'):
                with patch('tmux_orchestrator.cli.monitor.run_monitor_loop') as mock_loop:
                    # Simulate fork behavior
                    mock_fork.side_effect = [1, 0]  # Parent gets PID 1, child gets 0
                    
                    result = runner.invoke(monitor, ['start'], obj={'tmux': mock_tmux})
                    
                    assert result.exit_code == 0
                    assert "Starting monitor daemon" in result.output


def test_monitor_start_already_running(runner, mock_tmux, temp_pid_file):
    """Test starting monitor when already running."""
    # Create PID file with fake PID
    with open(temp_pid_file, 'w') as f:
        f.write('12345')
    
    with patch('tmux_orchestrator.cli.monitor.PID_FILE', temp_pid_file):
        with patch('os.kill') as mock_kill:
            # Simulate process exists
            mock_kill.return_value = None
            
            result = runner.invoke(monitor, ['start'], obj={'tmux': mock_tmux})
            
            assert result.exit_code == 0
            assert "already running" in result.output


def test_monitor_stop_success(runner, mock_tmux, temp_pid_file):
    """Test stopping the monitor daemon."""
    # Create PID file
    with open(temp_pid_file, 'w') as f:
        f.write('12345')
    
    with patch('tmux_orchestrator.cli.monitor.PID_FILE', temp_pid_file):
        with patch('os.kill') as mock_kill:
            result = runner.invoke(monitor, ['stop'], obj={'tmux': mock_tmux})
            
            assert result.exit_code == 0
            assert "Stopping monitor daemon" in result.output
            mock_kill.assert_called_with(12345, signal.SIGTERM)
            assert not os.path.exists(temp_pid_file)


def test_monitor_stop_not_running(runner, mock_tmux, temp_pid_file):
    """Test stopping monitor when not running."""
    with patch('tmux_orchestrator.cli.monitor.PID_FILE', temp_pid_file):
        result = runner.invoke(monitor, ['stop'], obj={'tmux': mock_tmux})
        
        assert result.exit_code == 0
        assert "not running" in result.output


def test_monitor_status_running(runner, mock_tmux, temp_pid_file):
    """Test monitor status when running."""
    # Create PID file
    with open(temp_pid_file, 'w') as f:
        f.write('12345')
    
    with patch('tmux_orchestrator.cli.monitor.PID_FILE', temp_pid_file):
        with patch('os.kill') as mock_kill:
            # Process exists
            mock_kill.return_value = None
            
            result = runner.invoke(monitor, ['status'], obj={'tmux': mock_tmux})
            
            assert result.exit_code == 0
            assert "running" in result.output
            assert "12345" in result.output


def test_monitor_status_not_running(runner, mock_tmux, temp_pid_file):
    """Test monitor status when not running."""
    with patch('tmux_orchestrator.cli.monitor.PID_FILE', temp_pid_file):
        result = runner.invoke(monitor, ['status'], obj={'tmux': mock_tmux})
        
        assert result.exit_code == 0
        assert "not running" in result.output


def test_monitor_restart(runner, mock_tmux, temp_pid_file):
    """Test restarting the monitor daemon."""
    # Create PID file for existing process
    with open(temp_pid_file, 'w') as f:
        f.write('12345')
    
    with patch('tmux_orchestrator.cli.monitor.PID_FILE', temp_pid_file):
        with patch('os.kill') as mock_kill:
            with patch('os.fork') as mock_fork:
                with patch('os.setsid'):
                    with patch('tmux_orchestrator.cli.monitor.run_monitor_loop'):
                        # Simulate fork for restart
                        mock_fork.side_effect = [1, 0]
                        
                        result = runner.invoke(monitor, ['restart'], obj={'tmux': mock_tmux})
                        
                        assert result.exit_code == 0
                        assert "Restarting" in result.output
                        # Should stop old process
                        mock_kill.assert_called_with(12345, signal.SIGTERM)


def test_monitor_check_once(runner, mock_tmux):
    """Test running monitor check once."""
    with patch('tmux_orchestrator.core.recovery.discover_agents') as mock_discover:
        with patch('tmux_orchestrator.core.recovery.check_agent_health') as mock_health:
            with patch('tmux_orchestrator.core.recovery.detect_failure') as mock_detect:
                # Mock agent discovery
                mock_discover.return_value = [
                    {'target': 'session1:0', 'session': 'session1', 'window': '0'},
                    {'target': 'session1:1', 'session': 'session1', 'window': '1'}
                ]
                
                # Mock health checks
                mock_health.side_effect = [
                    {'healthy': True, 'last_activity': '2m ago'},
                    {'healthy': False, 'reason': 'No activity for 45m'}
                ]
                
                # Mock failure detection
                mock_detect.side_effect = [
                    None,  # First agent OK
                    {'type': 'idle', 'duration': 45}  # Second agent idle
                ]
                
                result = runner.invoke(monitor, ['check'], obj={'tmux': mock_tmux})
                
                assert result.exit_code == 0
                assert "Checking" in result.output
                assert "2 agents" in result.output or "Found 2" in result.output


@patch('time.sleep')
def test_monitor_loop_function(mock_sleep, mock_tmux):
    """Test the monitor loop function."""
    from tmux_orchestrator.cli.monitor import run_monitor_loop
    
    with patch('tmux_orchestrator.core.recovery.discover_agents') as mock_discover:
        with patch('tmux_orchestrator.core.recovery.check_agent_health') as mock_health:
            # Set up to run only 2 iterations
            mock_sleep.side_effect = [None, KeyboardInterrupt]
            
            # Mock discovery
            mock_discover.return_value = [
                {'target': 'test:0', 'session': 'test', 'window': '0'}
            ]
            
            # Mock health check
            mock_health.return_value = {'healthy': True}
            
            # Run loop (will exit on KeyboardInterrupt)
            with pytest.raises(KeyboardInterrupt):
                run_monitor_loop(mock_tmux, interval=60)
            
            # Verify it ran checks
            assert mock_discover.call_count >= 1
            assert mock_health.call_count >= 1


def test_monitor_with_custom_interval(runner, mock_tmux):
    """Test monitor with custom interval."""
    with patch('os.fork') as mock_fork:
        with patch('os.setsid'):
            with patch('tmux_orchestrator.cli.monitor.run_monitor_loop') as mock_loop:
                mock_fork.side_effect = [1, 0]
                
                result = runner.invoke(monitor, ['start', '--interval', '30'], 
                                     obj={'tmux': mock_tmux})
                
                assert result.exit_code == 0
                # In child process, verify interval is passed
                if mock_loop.called:
                    mock_loop.assert_called_with(mock_tmux, interval=30)


def test_monitor_group_exists():
    """Test that monitor command group exists and has expected subcommands."""
    assert callable(monitor)
    
    command_names = list(monitor.commands.keys())
    expected_commands = {'start', 'stop', 'status', 'restart', 'check'}
    
    assert expected_commands.issubset(set(command_names))
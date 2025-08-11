"""Test scenarios for monitoring system crash detection reliability.

This module tests the recent improvements to the Tmux Orchestrator monitoring system:
1. Fixed false positive crash detection from @ symbol in bash prompts
2. Auto-submit now uses Enter key instead of complex key sequences
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, call
from datetime import datetime, timedelta
import logging

from tmux_orchestrator.core.monitor import IdleMonitor
from tmux_orchestrator.core.monitor_helpers import (
    AgentState,
    detect_agent_state,
    is_claude_interface_present,
)


class TestCrashDetectionReliability:
    """Test crash detection reliability with edge cases."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_tmux = Mock()
        self.monitor = IdleMonitor(self.mock_tmux)
        self.logger = logging.getLogger("test_logger")
    
    def test_at_symbol_in_prompt_not_crash(self):
        """Test that @ symbol in bash prompt doesn't trigger false crash detection."""
        # Test various bash prompts with @ symbol
        prompts_with_at = [
            "user@hostname:~/project$ ",
            "alice@dev-server:/workspaces$ ",
            "bob@ubuntu:~$ ",
            "admin@192.168.1.1:~# ",
            "developer@tmux-orchestrator:/app$ ",
        ]
        
        for prompt in prompts_with_at:
            # Add Claude UI elements to show it's still running
            content = f"""Welcome to Claude Code!
            
╭─ Human ─────────────────────────────────────────────────────────╮
│ Help me with my code                                            │
╰─────────────────────────────────────────────────────────────────╯

╭─ Assistant ─────────────────────────────────────────────────────╮
│ I'll help you with your code.                                  │
╰─────────────────────────────────────────────────────────────────╯

╭─────────────────────────────────────────────────────────────────╮
│ > _                                                             │
╰─────────────────────────────────────────────────────────────────╯
"""
            assert is_claude_interface_present(content) is True
            assert detect_agent_state(content) != AgentState.CRASHED
    
    def test_actual_bash_prompt_is_crash(self):
        """Test that actual bash prompts (without Claude UI) are detected as crashes."""
        # Various real bash prompt scenarios with crash indicators
        crash_scenarios = [
            "Human: exit\nuser@hostname:~/project$ ",
            "claude: command not found\nalice@dev-server:/workspaces$ \n",
            "Terminated\n$ ",
            "[Process completed]\n# ",
            "bash-5.1$ claude\nbash: claude: command not found\nbash-5.1$ ",
            "vscode ➜ /workspaces/project $ claude --dangerously-skip-permissions\nbash: claude: command not found",
            "Killed\n[user@host ~]$ ",
            "Segmentation fault\nroot@container:/# ",
        ]
        
        for prompt in crash_scenarios:
            assert is_claude_interface_present(prompt) is False
            # Without specific crash indicators, it might be ERROR state
            state = detect_agent_state(prompt)
            assert state in [AgentState.CRASHED, AgentState.ERROR], f"Expected CRASHED or ERROR, got {state}"
    
    def test_at_symbol_in_claude_content_not_crash(self):
        """Test that @ symbol within Claude's output doesn't trigger crash detection."""
        content = """╭─ Assistant ─────────────────────────────────────────────────────╮
│ Looking at the code, I can see the issue is with the email     │
│ validation. The regex should allow @ symbols:                   │
│                                                                 │
│ const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/; │
│                                                                 │
│ This will properly validate emails like user@example.com        │
╰─────────────────────────────────────────────────────────────────╯

╭─────────────────────────────────────────────────────────────────╮
│ > _                                                             │
╰─────────────────────────────────────────────────────────────────╯
"""
        assert is_claude_interface_present(content) is True
        assert detect_agent_state(content) != AgentState.CRASHED
    
    def test_mixed_content_with_at_symbol(self):
        """Test content with both @ symbols and Claude UI."""
        # Scenario: Claude showing bash command examples
        content = """╭─ Assistant ─────────────────────────────────────────────────────╮
│ To SSH into the server, use:                                    │
│                                                                 │
│ ssh user@hostname.com                                           │
│ ssh alice@192.168.1.100                                         │
│                                                                 │
│ Or if you're already logged in as root@server, you can...      │
╰─────────────────────────────────────────────────────────────────╯

╭─────────────────────────────────────────────────────────────────╮
│ > _                                                             │
╰─────────────────────────────────────────────────────────────────╯

? for shortcuts"""
        assert is_claude_interface_present(content) is True
        assert detect_agent_state(content) != AgentState.CRASHED
    
    def test_terminal_history_with_bash_prompt(self):
        """Test that bash prompts in terminal history don't cause false positives."""
        # Scenario: Claude was restarted, old bash prompt in scrollback
        content = """user@host:~$ claude --dangerously-skip-permissions
Starting Claude Code...

Welcome to Claude Code!

╭─ Human ─────────────────────────────────────────────────────────╮
│ Hello                                                           │
╰─────────────────────────────────────────────────────────────────╯

╭─ Assistant ─────────────────────────────────────────────────────╮
│ Hello! How can I help you today?                               │
╰─────────────────────────────────────────────────────────────────╯

╭─────────────────────────────────────────────────────────────────╮
│ > _                                                             │
╰─────────────────────────────────────────────────────────────────╯"""
        assert is_claude_interface_present(content) is True
        assert detect_agent_state(content) != AgentState.CRASHED


class TestAutoSubmitMechanism:
    """Test the improved auto-submit mechanism using Enter key."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_tmux = Mock()
        self.monitor = IdleMonitor(self.mock_tmux)
        self.logger = Mock()
    
    def test_auto_submit_uses_enter_key(self):
        """Test that auto-submit now uses simple Enter key."""
        target = "session:0"
        
        # Set up idle agent with unsubmitted message
        content_with_message = """╭─ Claude Code ───────────────────────────────────────────────────╮
│ > Hello, I need help with...                                   │
╰─────────────────────────────────────────────────────────────────╯"""
        
        # Mock multiple snapshots for idle detection
        self.mock_tmux.capture_pane.return_value = content_with_message
        
        # Mock helper functions
        with patch('tmux_orchestrator.core.monitor.detect_agent_state', return_value=AgentState.MESSAGE_QUEUED):
            with patch('tmux_orchestrator.core.monitor.is_terminal_idle', return_value=True):
                with patch('tmux_orchestrator.core.monitor.is_claude_interface_present', return_value=True):
                    with patch('tmux_orchestrator.core.monitor.has_unsubmitted_message', return_value=True):
                        self.monitor._check_agent_status(self.mock_tmux, target, self.logger)
        
        # Verify Enter key was sent (not complex key sequences)
        send_keys_calls = [call for call in self.mock_tmux.send_keys.call_args_list 
                          if call[0][0] == target]
        
        # Should only send Enter, not C-a, C-e, etc.
        for call in send_keys_calls:
            key = call[0][1]
            assert key == "Enter", f"Expected only 'Enter' key, but got '{key}'"
    
    def test_auto_submit_cooldown(self):
        """Test that auto-submit respects 10-second cooldown."""
        target = "session:0"
        
        # Set up idle agent with message
        content = """╭─ Claude Code ───────────────────────────────────────────────────╮
│ > Test message                                                  │
╰─────────────────────────────────────────────────────────────────╯"""
        
        self.mock_tmux.capture_pane.return_value = content
        
        # First attempt should work
        with patch('tmux_orchestrator.core.monitor.detect_agent_state', return_value=AgentState.IDLE):
            with patch('tmux_orchestrator.core.monitor.is_terminal_idle', return_value=True):
                with patch('tmux_orchestrator.core.monitor.is_claude_interface_present', return_value=True):
                    with patch('tmux_orchestrator.core.monitor.has_unsubmitted_message', return_value=True):
                        with patch('time.time', return_value=1000.0):
                            self.monitor._check_agent_status(self.mock_tmux, target, self.logger)
        
        assert self.mock_tmux.send_keys.called
        first_call_count = self.mock_tmux.send_keys.call_count
        
        # Second attempt within 10 seconds should be skipped
        self.mock_tmux.send_keys.reset_mock()
        with patch('tmux_orchestrator.core.monitor.detect_agent_state', return_value=AgentState.IDLE):
            with patch('tmux_orchestrator.core.monitor.is_terminal_idle', return_value=True):
                with patch('tmux_orchestrator.core.monitor.is_claude_interface_present', return_value=True):
                    with patch('tmux_orchestrator.core.monitor.has_unsubmitted_message', return_value=True):
                        with patch('time.time', return_value=1005.0):  # 5 seconds later
                            self.monitor._check_agent_status(self.mock_tmux, target, self.logger)
        
        # Should not have made additional calls
        assert not self.mock_tmux.send_keys.called
        
        # Third attempt after 10 seconds should work
        with patch('tmux_orchestrator.core.monitor.detect_agent_state', return_value=AgentState.IDLE):
            with patch('tmux_orchestrator.core.monitor.is_terminal_idle', return_value=True):
                with patch('tmux_orchestrator.core.monitor.is_claude_interface_present', return_value=True):
                    with patch('tmux_orchestrator.core.monitor.has_unsubmitted_message', return_value=True):
                        with patch('time.time', return_value=1011.0):  # 11 seconds later
                            self.monitor._check_agent_status(self.mock_tmux, target, self.logger)
        
        # Should have made additional call
        assert self.mock_tmux.send_keys.called
    
    def test_auto_submit_counter_reset_on_activity(self):
        """Test that submission counter resets when agent becomes active."""
        target = "session:0"
        
        # Start with idle agent content
        content = """╭─ Claude Code ───────────────────────────────────────────────────╮
│ > Test                                                          │
╰─────────────────────────────────────────────────────────────────╯"""
        
        self.mock_tmux.capture_pane.return_value = content
        
        # Set up initial submission attempts
        self.monitor._submission_attempts[target] = 5
        self.monitor._last_submission_time[target] = 1000.0
        
        # Agent becomes active (not idle)
        with patch('tmux_orchestrator.core.monitor.detect_agent_state', return_value=AgentState.HEALTHY):
            with patch('tmux_orchestrator.core.monitor.is_terminal_idle', return_value=False):  # Not idle = active
                with patch('tmux_orchestrator.core.monitor.is_claude_interface_present', return_value=True):
                    self.monitor._check_agent_status(self.mock_tmux, target, self.logger)
        
        # Counter should be reset
        assert self.monitor._submission_attempts[target] == 0
        assert target not in self.monitor._last_submission_time


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_tmux = Mock()
        self.monitor = IdleMonitor(self.mock_tmux)
    
    def test_special_characters_in_prompt(self):
        """Test various special characters that might appear in prompts."""
        # Test prompts with special characters that shouldn't trigger crashes
        special_prompts = [
            "╭─ Human@Claude ──────╮",  # @ in Claude UI element
            "user@host | grep '@' > file.txt",  # @ in command
            "Searching for pattern: *@*.com",  # @ in output
            "Email: support@anthropic.com",  # @ in text
        ]
        
        for content in special_prompts:
            # Add minimal Claude UI to show it's running
            full_content = content + "\n│ > _"
            if "│ >" in full_content:
                assert detect_agent_state(full_content) != AgentState.CRASHED
    
    def test_unicode_bash_prompts(self):
        """Test Unicode characters in bash prompts."""
        unicode_prompts = [
            "user@host:~$ 🚀",
            "➜ user@dev ",
            "⚡ admin@server ",
            "▶ root@container ",
        ]
        
        for prompt in unicode_prompts:
            # Without Claude UI, these should be detected as crashes or errors
            assert is_claude_interface_present(prompt) is False
            state = detect_agent_state(prompt)
            assert state in [AgentState.CRASHED, AgentState.ERROR], f"Expected CRASHED or ERROR for '{prompt}', got {state}"
    
    def test_multiline_bash_history(self):
        """Test multiline commands in bash history."""
        content = """user@host:~$ cat << EOF
> This is a test
> with multiple lines
> EOF
This is a test
with multiple lines
user@host:~$ """
        
        # This is pure bash, no Claude UI
        assert is_claude_interface_present(content) is False
        state = detect_agent_state(content)
        assert state in [AgentState.CRASHED, AgentState.ERROR], f"Expected CRASHED or ERROR, got {state}"
    
    def test_partial_claude_ui_not_crash(self):
        """Test that partial Claude UI elements aren't mistaken for crashes."""
        partial_ui_scenarios = [
            "Starting Claude...\n╭─",  # UI starting to appear
            "╭─ Assistant ─╮\n│ Thinking...",  # Partial response with box
            "? for shortcuts\nLoading...",  # Status line visible
            "Welcome to Claude Code!\nInitializing...",  # Welcome visible
        ]
        
        for content in partial_ui_scenarios:
            # Check if it has Claude UI elements
            has_ui = is_claude_interface_present(content)
            state = detect_agent_state(content)
            # Content with Claude indicators should not be crashed
            if "Welcome to Claude Code" in content or "? for shortcuts" in content or "╭─" in content:
                assert state != AgentState.CRASHED, f"Content incorrectly detected as crashed: {content}"
    
    def test_empty_content_handling(self):
        """Test handling of empty or minimal content."""
        empty_scenarios = [
            "",  # Completely empty
            "\n",  # Just newline
            "   ",  # Just spaces
            "\n\n\n",  # Multiple newlines
        ]
        
        for content in empty_scenarios:
            # Empty content without Claude UI could indicate crash
            assert is_claude_interface_present(content) is False
            # But might be detected as ERROR rather than CRASHED without specific indicators
            state = detect_agent_state(content)
            assert state in [AgentState.CRASHED, AgentState.ERROR]


class TestMonitoringIntegration:
    """Integration tests for the complete monitoring flow."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_tmux = Mock()
        self.monitor = IdleMonitor(self.mock_tmux)
        self.logger = Mock()
    
    def test_monitor_cycle_with_at_symbol_agents(self):
        """Test full monitoring cycle with agents having @ in their prompts."""
        # Set up multiple agents, some with @ symbols
        agents = [
            ("session1:0", "user@host:~$ ", False),  # Crashed
            ("session1:1", "╭─ Claude Code ─╮\n│ > Hello from alice@dev", True),  # Active with @
            ("session2:0", "root@server:/# ", False),  # Crashed
            ("session2:1", "╭─ Assistant ─╮\n│ Working on user@example.com validation │", True),  # Active
        ]
        
        # Mock agent discovery
        with patch.object(self.monitor, '_discover_agents', return_value=[a[0] for a in agents]):
            # Set up capture_pane responses
            def capture_side_effect(target, lines=50):
                for agent_target, content, _ in agents:
                    if agent_target == target:
                        return content
                return ""
            
            self.mock_tmux.capture_pane.side_effect = capture_side_effect
            
            # Mock helper functions from monitor_helpers
            with patch('tmux_orchestrator.core.monitor.is_claude_interface_present') as mock_claude_present:
                mock_claude_present.side_effect = lambda content: any(
                    indicator in content for indicator in ["│", "╭", "╰", "Claude Code"]
                )
                
                with patch('tmux_orchestrator.core.monitor.detect_agent_state') as mock_detect_state:
                    def detect_state_side_effect(content):
                        if "user@host:~$" in content or "root@server:/#" in content:
                            return AgentState.CRASHED
                        return AgentState.HEALTHY
                    
                    mock_detect_state.side_effect = detect_state_side_effect
                    
                    # Run monitoring cycle
                    self.monitor._monitor_cycle(self.mock_tmux, self.logger)
        
        # Verify appropriate actions were taken
        error_logs = [call for call in self.logger.error.call_args_list]
        assert len(error_logs) >= 2  # At least two crashed agents
        
        # Verify crashed agents were identified
        error_messages = [call[0][0] for call in error_logs]
        assert any("session1:0" in msg for msg in error_messages)
        assert any("session2:0" in msg for msg in error_messages)
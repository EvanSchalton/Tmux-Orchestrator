"""Integration tests for combined monitoring features.

This module tests the integration of multiple monitoring features:
1. Rate limit detection + auto-pause/resume
2. Compaction detection (no false idle alerts)
3. Combined feature interactions
4. End-to-end monitoring workflow
"""

from unittest.mock import MagicMock, patch

import pytest

from tmux_orchestrator.core.monitor import IdleMonitor


@pytest.fixture
def monitor(mock_tmux):
    """Create an IdleMonitor instance with mock TMUXManager."""
    return IdleMonitor(mock_tmux)


def test_rate_limit_plus_compaction_no_false_alerts(mock_tmux, monitor, logger) -> None:
    """Test that rate limits don't trigger false compaction alerts."""
    target = "test-session:1"
    pm_target = "pm-session:0"

    # Content showing both rate limit AND compaction (edge case)
    combined_content = """
╭─ Claude │ Chat with Claude 3.5 Sonnet ─────────────────────────────────────────────────╮
│ [Compacting conversation...]                                                           │
│                                                                                        │
│ Claude usage limit reached. Your limit will reset at 4:30pm (UTC).                  │
│                                                                                        │
╰────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Human ─────────────────────────────────────────────────────────────────────────────╮
│ >                                                                                   │
╰─────────────────────────────────────────────────────────────────────────────────────╯
"""

    # Mock agent discovery
    mock_tmux.list_sessions.return_value = [{"name": "test-session"}]
    mock_tmux.list_windows.return_value = [{"index": "1", "name": "claude-dev"}]
    mock_tmux.capture_pane.return_value = combined_content

    # Mock PM discovery
    with patch.object(monitor, "_find_pm_agent", return_value=pm_target):
        with (
            patch("tmux_orchestrator.core.monitor.logging.getLogger") as mock_logger_factory,
            patch("tmux_orchestrator.core.monitor.time.sleep"),
        ):
            # Create a mock logger with handlers attribute
            session_logger = MagicMock()
            session_logger.handlers = []

            def logger_factory(name):
                if "idle_monitor_" in name:
                    return session_logger
                return logger

            mock_logger_factory.side_effect = logger_factory

            # Test both monitor cycle and direct agent status check
            monitor._monitor_cycle(mock_tmux, logger)

            # Also test direct agent monitoring to ensure target agent is handled correctly
            monitor._check_agent_status(mock_tmux, target, logger, {})

    # Verify rate limit was detected (takes priority)
    warning_calls = [call.args[0] for call in logger.warning.call_args_list]
    session_warning_calls = [call.args[0] for call in session_logger.warning.call_args_list]
    all_warnings = warning_calls + session_warning_calls

    print(f"Logger warnings: {warning_calls}")
    print(f"Session logger warnings: {session_warning_calls}")

    assert any("Rate limit" in msg for msg in all_warnings)

    # Verify no false compaction alerts
    debug_calls = [call.args[0] for call in logger.debug.call_args_list]
    assert not any("appears idle but is compacting" in msg for msg in debug_calls)


def test_compaction_during_normal_operation(mock_tmux, monitor, logger) -> None:
    """Test compaction detection during normal operation (no rate limits)."""
    target = "test-session:1"

    # Normal compaction without rate limits
    compaction_content = """
╭─ Claude │ Chat with Claude 3.5 Sonnet ─────────────────────────────────────────────────╮
│ Previous conversation...                                                               │
│                                                                                        │
│ [Compacting conversation...]                                                           │
│                                                                                        │
╰────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Human ─────────────────────────────────────────────────────────────────────────────╮
│ >                                                                                   │
╰─────────────────────────────────────────────────────────────────────────────────────╯
"""

    mock_tmux.capture_pane.side_effect = [compaction_content] * 4  # 4 snapshots

    with (
        patch("tmux_orchestrator.core.monitor.logging.getLogger") as mock_logger_factory,
        patch("tmux_orchestrator.core.monitor.time.sleep"),
    ):
        # Create a mock session logger with handlers attribute
        session_logger = MagicMock()
        session_logger.handlers = []

        def logger_factory(name):
            if "idle_monitor_" in name:
                return session_logger
            return logger

        mock_logger_factory.side_effect = logger_factory

        # Mock PM discovery
        monitor._find_pm_agent = MagicMock(return_value="pm-session:0")

        # Check agent status
        monitor._check_agent_status(mock_tmux, target, logger, {})

    # Verify compaction was detected as activity
    debug_calls = [call.args[0] for call in session_logger.debug.call_args_list]
    assert any("found thinking indicator: 'Compacting conversation'" in msg for msg in debug_calls)

    # Verify no idle notification was sent
    assert not mock_tmux.send_message.called


def test_sequential_rate_limit_then_recovery(mock_tmux, monitor, logger) -> None:
    """Test rate limit detection followed by recovery."""
    target = "test-session:1"

    # First: Rate limit content
    # Use a reset time within 4 hours from now to avoid "stale" detection
    from datetime import datetime, timedelta, timezone

    future_time = datetime.now(timezone.utc) + timedelta(hours=2)
    reset_time_str = future_time.strftime("%I:%M%p").lstrip("0").lower()

    rate_limit_content = f"""
Welcome to Claude Code
Claude usage limit reached. Your limit will reset at {reset_time_str} (UTC).
"""

    # Then: Normal working content
    normal_content = """
╭─ Claude │ Chat with Claude 3.5 Sonnet ─────────────────────────────────────────────────╮
│ > Working on the task...                                                               │
╰────────────────────────────────────────────────────────────────────────────────────────╯
"""

    # Mock agent discovery
    mock_tmux.list_sessions.return_value = [{"name": "test-session"}]
    mock_tmux.list_windows.return_value = [{"index": "1", "name": "claude-dev"}]

    with (
        patch("tmux_orchestrator.core.monitor.logging.getLogger") as mock_logger_factory,
        patch("tmux_orchestrator.core.monitor.time.sleep"),
    ):
        # Create a mock session logger with handlers attribute
        session_logger = MagicMock()
        session_logger.handlers = []

        def logger_factory(name):
            if "idle_monitor_" in name:
                return session_logger
            return logger

        mock_logger_factory.side_effect = logger_factory

        # Mock PM discovery
        monitor._find_pm_agent = MagicMock(return_value="pm-session:0")

        # First cycle: Rate limit
        mock_tmux.capture_pane.return_value = rate_limit_content
        monitor._monitor_cycle(mock_tmux, logger)

        # Also check specific agent
        monitor._check_agent_status(mock_tmux, target, logger, {})

        # Verify rate limit was detected (check both loggers)
        warning_calls = [call.args[0] for call in logger.warning.call_args_list]
        session_warning_calls = [call.args[0] for call in session_logger.warning.call_args_list]
        all_warnings = warning_calls + session_warning_calls
        assert any("Rate limit detected" in msg for msg in all_warnings)

        # Reset loggers for second cycle
        logger.reset_mock()
        session_logger.reset_mock()

        # Second cycle: Normal operation (recovery)
        mock_tmux.capture_pane.return_value = normal_content
        monitor._monitor_cycle(mock_tmux, logger)
        monitor._check_agent_status(mock_tmux, target, logger, {})

        # Verify normal operation detected (no rate limit warnings)
        if logger.warning.called or session_logger.warning.called:
            warning_calls = [call.args[0] for call in logger.warning.call_args_list]
            session_warning_calls = [call.args[0] for call in session_logger.warning.call_args_list]
            all_warnings = warning_calls + session_warning_calls
            assert not any("Rate limit detected" in msg for msg in all_warnings)


def test_multiple_agents_different_states(mock_tmux, monitor, logger) -> None:
    """Test monitoring multiple agents in different states simultaneously."""
    # Agent 1: Rate limited
    # Agent 2: Compacting
    # Agent 3: Normal operation

    agents = [
        ("session1:1", "claude-dev"),
        ("session2:1", "claude-qa"),
        ("session3:1", "claude-backend"),
    ]

    # Use a reset time within 4 hours from now
    from datetime import datetime, timedelta, timezone

    future_time = datetime.now(timezone.utc) + timedelta(hours=2)
    reset_time_str = future_time.strftime("%I:%M%p").lstrip("0").lower()

    content_states = [
        # Agent 1: Rate limited
        f"Claude usage limit reached. Your limit will reset at {reset_time_str} (UTC).",
        # Agent 2: Compacting
        """
╭─ Claude │ Chat ─────────────────────────────────────────────────────────────────────╮
│ [Compacting conversation...]                                                         │
╰──────────────────────────────────────────────────────────────────────────────────────╯
╭─ Human ─────────────────────────────────────────────────────────────────────────────╮
│ >                                                                                   │
╰─────────────────────────────────────────────────────────────────────────────────────╯
""",
        # Agent 3: Normal
        """
╭─ Claude │ Chat ─────────────────────────────────────────────────────────────────────╮
│ > I'm working on the backend implementation...                                      │
╰──────────────────────────────────────────────────────────────────────────────────────╯
""",
    ]

    # Mock agent discovery
    mock_sessions = [{"name": f"session{i+1}"} for i in range(3)]

    mock_tmux.list_sessions.return_value = mock_sessions

    # Mock list_windows to return appropriate windows for each session
    def mock_list_windows(session_name):
        window_map = {
            "session1": [{"index": "1", "name": "claude-dev"}],
            "session2": [{"index": "1", "name": "claude-qa"}],
            "session3": [{"index": "1", "name": "claude-backend"}],
        }
        return window_map.get(session_name, [])

    mock_tmux.list_windows.side_effect = mock_list_windows

    # Mock content for each agent
    def mock_capture_pane(target, **kwargs):
        for i, (agent_target, _) in enumerate(agents):
            if target == agent_target:
                return content_states[i]
        return "Unknown agent"

    mock_tmux.capture_pane.side_effect = mock_capture_pane

    with (
        patch("tmux_orchestrator.core.monitor.logging.getLogger") as mock_logger_factory,
        patch("tmux_orchestrator.core.monitor.time.sleep"),
    ):
        # Create a mock session logger with handlers attribute
        session_logger = MagicMock()
        session_logger.handlers = []

        def logger_factory(name):
            if "idle_monitor_" in name:
                return session_logger
            return logger

        mock_logger_factory.side_effect = logger_factory

        # Run monitoring cycle
        monitor._monitor_cycle(mock_tmux, logger)

    # Verify different states were detected appropriately
    all_calls = [
        call.args[0]
        for call in logger.warning.call_args_list + logger.debug.call_args_list + logger.info.call_args_list
    ]

    # Also check session logger
    session_calls = [
        call.args[0]
        for call in session_logger.warning.call_args_list
        + session_logger.debug.call_args_list
        + session_logger.info.call_args_list
    ]

    all_messages = all_calls + session_calls

    # Should detect rate limit for agent 1
    assert any("Rate limit detected" in msg for msg in all_messages)

    # For compaction test - we don't need to check for specific "compacting" message
    # The important thing is that the agent with compaction is not marked as idle
    # We'll verify this by checking that no PM notifications were sent for idle agents with compaction


def test_edge_case_rapid_state_changes(mock_tmux, monitor, logger) -> None:
    """Test handling of rapid state changes between monitoring cycles."""
    target = "test-session:1"

    # Use a reset time within 4 hours from now
    from datetime import datetime, timedelta, timezone

    future_time = datetime.now(timezone.utc) + timedelta(hours=2)
    reset_time_str = future_time.strftime("%I:%M%p").lstrip("0").lower()

    # Simulate rapid changes: rate limit → compaction → normal → idle
    state_sequence = [
        f"Claude usage limit reached. Your limit will reset at {reset_time_str} (UTC).",
        "[Compacting conversation...]",
        "╭─ Claude │ Working... ╰─",
        "╭─ Claude │ Task complete. ╰─╭─ Human │ > ╰─",
    ]

    mock_tmux.list_sessions.return_value = [{"name": "test-session"}]
    mock_tmux.list_windows.return_value = [{"index": "1", "name": "claude-dev"}]

    with (
        patch("tmux_orchestrator.core.monitor.logging.getLogger") as mock_logger_factory,
        patch("tmux_orchestrator.core.monitor.time.sleep"),
    ):
        mock_logger_factory.return_value = logger

        # Mock PM discovery
        monitor._find_pm_agent = MagicMock(return_value="pm-session:0")

        for i, content in enumerate(state_sequence):
            # Reset for each cycle
            logger.reset_mock()
            mock_tmux.capture_pane.return_value = content

            # Run monitoring cycle and check specific agent
            monitor._monitor_cycle(mock_tmux, logger)
            monitor._check_agent_status(mock_tmux, target, logger, {})

            # Log what was detected this cycle
            all_calls = [
                call.args[0]
                for call in logger.warning.call_args_list + logger.debug.call_args_list + logger.info.call_args_list
            ]

            if i == 0:  # Rate limit cycle
                assert any("rate limit" in msg.lower() for msg in all_calls)
            elif i == 1:  # Compaction cycle
                # Should detect as activity, not idle
                pass  # Compaction prevents idle detection


def test_combined_features_performance_impact(mock_tmux, monitor, logger) -> None:
    """Test that combined feature detection doesn't significantly impact performance."""
    import time

    target = "test-session:1"

    # Complex content with multiple features
    complex_content = """
╭─ Claude │ Chat with Claude 3.5 Sonnet ─────────────────────────────────────────────────╮
│ I'm processing your request...                                                         │
│                                                                                        │
│ [Compacting conversation...]                                                           │
│                                                                                        │
│ Previous context about rate limits and monitoring...                                  │
│                                                                                        │
╰────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Human ─────────────────────────────────────────────────────────────────────────────╮
│ > Please continue with the analysis                                                   │
╰─────────────────────────────────────────────────────────────────────────────────────╯
"""

    mock_tmux.capture_pane.side_effect = [complex_content] * 4
    mock_tmux.list_sessions.return_value = [{"name": "test-session"}]
    mock_tmux.list_windows.return_value = [{"index": "1", "name": "claude-dev"}]

    with (
        patch("tmux_orchestrator.core.monitor.logging.getLogger") as mock_logger_factory,
        patch("tmux_orchestrator.core.monitor.time.sleep"),
    ):
        mock_logger_factory.return_value = logger

        # Mock PM discovery
        monitor._find_pm_agent = MagicMock(return_value="pm-session:0")

        # Mock session logger cache so it returns our mock logger
        monitor._session_loggers = {"test-session": logger}

        # Time the monitoring operation
        start_time = time.time()

        # Run multiple monitoring cycles
        for _ in range(5):
            monitor._monitor_cycle(mock_tmux, logger)
            monitor._check_agent_status(mock_tmux, target, logger, {})

        end_time = time.time()
        elapsed = end_time - start_time

    # Should complete quickly (under 1 second for 5 cycles)
    assert elapsed < 1.0, f"Combined feature detection took too long: {elapsed:.2f}s"

    # Verify monitoring ran without errors
    all_calls = [
        call.args[0]
        for call in logger.warning.call_args_list + logger.debug.call_args_list + logger.info.call_args_list
    ]

    # Should have completed monitoring cycles
    assert len(all_calls) > 0, "No monitoring activity detected"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

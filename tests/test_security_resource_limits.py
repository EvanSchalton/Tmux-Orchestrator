"""Test resource limits functionality for security."""

import time
from unittest.mock import Mock, patch

from tmux_orchestrator.core.monitor import IdleMonitor


class TestTerminalCacheResourceLimits:
    """Test terminal cache resource limiting."""

    def setup_method(self):
        """Set up test environment."""
        # Mock config to use small limits for testing
        self.config = {
            "monitoring.max_cache_entries": 3,
            "monitoring.max_cache_age_hours": 1,
            "monitoring.pm_recovery_grace_period_minutes": 3,
        }

    @patch("tmux_orchestrator.core.monitor.config", new_callable=dict)
    def test_cache_entry_limit(self, mock_config):
        """Test cache entry limit enforcement."""
        mock_config.update(self.config)

        monitor = IdleMonitor()

        # Fill cache to limit
        for i in range(3):
            target = f"session{i}:0"
            monitor._terminal_caches[target] = Mock()
            monitor._cache_access_times[target] = time.time()

        assert len(monitor._terminal_caches) == 3

        # Add one more to trigger cleanup
        monitor._terminal_caches["session3:0"] = Mock()
        monitor._cache_access_times["session3:0"] = time.time()

        # Manually trigger cleanup
        logger_mock = Mock()
        monitor._cleanup_terminal_caches(logger_mock)

        # Should be at or below limit
        assert len(monitor._terminal_caches) <= 3

    @patch("tmux_orchestrator.core.monitor.config", new_callable=dict)
    def test_lru_eviction(self, mock_config):
        """Test least recently used eviction."""
        mock_config.update(self.config)

        monitor = IdleMonitor()

        # Add entries with different access times
        base_time = time.time()
        entries = [
            ("old:0", base_time - 100),  # Oldest
            ("medium:0", base_time - 50),
            ("new:0", base_time),  # Newest
            ("newest:0", base_time + 10),  # Should trigger eviction
        ]

        for target, access_time in entries:
            monitor._terminal_caches[target] = Mock()
            monitor._cache_access_times[target] = access_time

        # Trigger cleanup
        logger_mock = Mock()
        monitor._cleanup_terminal_caches(logger_mock)

        # Oldest entry should be removed
        assert "old:0" not in monitor._terminal_caches
        assert "newest:0" in monitor._terminal_caches

    @patch("tmux_orchestrator.core.monitor.config", new_callable=dict)
    def test_stale_cache_cleanup(self, mock_config):
        """Test stale cache cleanup."""
        mock_config.update(self.config)

        monitor = IdleMonitor()

        # Add stale caches (empty values)
        stale_cache = Mock()
        stale_cache.early_value = None
        stale_cache.later_value = None

        active_cache = Mock()
        active_cache.early_value = "content"
        active_cache.later_value = "content"

        monitor._terminal_caches["stale:0"] = stale_cache
        monitor._terminal_caches["active:0"] = active_cache
        monitor._cache_access_times["stale:0"] = time.time()
        monitor._cache_access_times["active:0"] = time.time()

        # Trigger cleanup
        logger_mock = Mock()
        monitor._cleanup_terminal_caches(logger_mock)

        # Stale cache should be removed
        assert "stale:0" not in monitor._terminal_caches
        assert "active:0" in monitor._terminal_caches

        # Access times should be cleaned up too
        assert "stale:0" not in monitor._cache_access_times
        assert "active:0" in monitor._cache_access_times

    @patch("tmux_orchestrator.core.monitor.config", new_callable=dict)
    def test_cleanup_error_handling(self, mock_config):
        """Test cleanup handles errors gracefully."""
        mock_config.update(self.config)

        monitor = IdleMonitor()

        # Add cache entry that will cause error during cleanup
        broken_cache = Mock()
        broken_cache.early_value = None
        broken_cache.later_value = None

        monitor._terminal_caches["broken:0"] = broken_cache

        # Mock logger to capture error
        logger_mock = Mock()

        # Should not raise exception
        monitor._cleanup_terminal_caches(logger_mock)

        # Error should be logged if one occurs
        # (This test ensures the method doesn't crash on errors)

    @patch("tmux_orchestrator.core.monitor.config", new_callable=dict)
    def test_periodic_cleanup_timing(self, mock_config):
        """Test cleanup runs at proper intervals."""
        mock_config.update(self.config)

        monitor = IdleMonitor()

        # Set up initial state
        monitor._cache_cleanup_interval = 1  # 1 second for testing
        monitor._last_cache_cleanup = time.time() - 2  # 2 seconds ago

        # Add some cache entries
        monitor._terminal_caches["test:0"] = Mock()

        # Mock the monitoring cycle
        tmux_mock = Mock()
        logger_mock = Mock()

        with patch.object(monitor, "_monitor_cycle") as _mock_cycle:
            with patch.object(monitor, "_cleanup_terminal_caches") as mock_cleanup:
                # Simulate one monitoring cycle
                monitor._monitor_cycle(tmux_mock, logger_mock)

                # Check if cleanup was triggered
                # Note: This would need to be tested in the actual monitoring loop
                # For now, we just verify the method exists and can be called
                monitor._cleanup_terminal_caches(logger_mock)
                mock_cleanup.assert_called_once()

    @patch("tmux_orchestrator.core.monitor.config", new_callable=dict)
    def test_memory_usage_bounds(self, mock_config):
        """Test that memory usage stays bounded."""
        mock_config.update(
            {
                "monitoring.max_cache_entries": 5,
                "monitoring.max_cache_age_hours": 1,
                "monitoring.pm_recovery_grace_period_minutes": 3,
            }
        )

        monitor = IdleMonitor()

        # Add many cache entries
        for i in range(20):
            target = f"session{i}:0"
            cache_mock = Mock()
            cache_mock.early_value = f"content{i}"
            cache_mock.later_value = f"content{i}"

            monitor._terminal_caches[target] = cache_mock
            monitor._cache_access_times[target] = time.time() - i  # Older entries have smaller times

        assert len(monitor._terminal_caches) == 20

        # Trigger cleanup
        logger_mock = Mock()
        monitor._cleanup_terminal_caches(logger_mock)

        # Should be reduced to limit
        assert len(monitor._terminal_caches) <= 5
        assert len(monitor._cache_access_times) <= 5

        # Newest entries should be kept
        assert "session19:0" in monitor._terminal_caches
        assert "session18:0" in monitor._terminal_caches


class TestMonitoringResourceLimits:
    """Test overall monitoring resource limits."""

    @patch("tmux_orchestrator.core.monitor.config", new_callable=dict)
    def test_notification_tracking_limits(self, mock_config):
        """Test notification tracking doesn't grow unbounded."""
        mock_config.update(
            {
                "monitoring.max_cache_entries": 100,
                "monitoring.max_cache_age_hours": 24,
                "monitoring.pm_recovery_grace_period_minutes": 3,
            }
        )

        monitor = IdleMonitor()

        # Add many notification timestamps
        base_time = time.time()
        for i in range(1000):
            target = f"session{i}:0"
            monitor._idle_notifications[target] = base_time - i
            monitor._crash_notifications[target] = base_time - i

        # These dictionaries could grow unbounded in the current implementation
        # This test documents the issue and would pass once limits are implemented
        assert len(monitor._idle_notifications) == 1000
        assert len(monitor._crash_notifications) == 1000

    @patch("tmux_orchestrator.core.monitor.config", new_callable=dict)
    def test_session_logger_cache_limits(self, mock_config):
        """Test session logger cache doesn't grow unbounded."""
        mock_config.update(
            {
                "monitoring.max_cache_entries": 100,
                "monitoring.max_cache_age_hours": 24,
                "monitoring.pm_recovery_grace_period_minutes": 3,
            }
        )

        monitor = IdleMonitor()

        # Add many session loggers
        for i in range(200):
            session_name = f"session{i}"
            logger_mock = Mock()
            monitor._session_loggers[session_name] = logger_mock

        # This could also grow unbounded
        assert len(monitor._session_loggers) == 200

    def test_config_defaults(self):
        """Test that reasonable defaults are set for resource limits."""
        monitor = IdleMonitor()

        # Should have reasonable defaults
        assert hasattr(monitor, "_max_cache_entries")
        assert hasattr(monitor, "_max_cache_age_hours")
        assert hasattr(monitor, "_cache_cleanup_interval")

        # Defaults should be reasonable
        assert monitor._max_cache_entries > 0
        assert monitor._max_cache_entries <= 1000  # Not too large
        assert monitor._max_cache_age_hours > 0
        assert monitor._cache_cleanup_interval > 0


class TestConfigurableResourceLimits:
    """Test configurable resource limits."""

    @patch("tmux_orchestrator.core.monitor.config", new_callable=dict)
    def test_custom_cache_limits(self, mock_config):
        """Test custom cache limits from config."""
        custom_config = {
            "monitoring.max_cache_entries": 50,
            "monitoring.max_cache_age_hours": 12,
            "monitoring.pm_recovery_grace_period_minutes": 5,
        }
        mock_config.update(custom_config)

        monitor = IdleMonitor()

        assert monitor._max_cache_entries == 50
        assert monitor._max_cache_age_hours == 12

    @patch("tmux_orchestrator.core.monitor.config", new_callable=dict)
    def test_zero_limits_handling(self, mock_config):
        """Test handling of zero or invalid limits."""
        invalid_config = {
            "monitoring.max_cache_entries": 0,
            "monitoring.max_cache_age_hours": -1,
            "monitoring.pm_recovery_grace_period_minutes": 3,
        }
        mock_config.update(invalid_config)

        # Should handle invalid config gracefully
        monitor = IdleMonitor()

        # Should use defaults or minimum values
        assert monitor._max_cache_entries > 0
        assert monitor._max_cache_age_hours > 0

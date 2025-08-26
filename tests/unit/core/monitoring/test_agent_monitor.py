"""
Comprehensive tests for AgentMonitor class.

Tests the extracted agent discovery and monitoring functionality to ensure
no functionality loss during refactoring.
"""

import logging
import os
import tempfile
from unittest.mock import Mock, patch

from tmux_orchestrator.core.config import Config
from tmux_orchestrator.core.monitoring.agent_monitor import AgentMonitor
from tmux_orchestrator.core.monitoring.types import AgentInfo, IdleType
from tmux_orchestrator.utils.tmux import TMUXManager

# TMUXManager import removed - using comprehensive_mock_tmux fixture


class TestAgentMonitorInitialization:
    """Test AgentMonitor initialization and basic functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.original_env = os.environ.get("TMUX_ORCHESTRATOR_BASE_DIR")
        os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.test_dir

        self.tmux = Mock(spec=TMUXManager)
        self.config = Config.load()
        self.logger = Mock(spec=logging.Logger)

        self.agent_monitor = AgentMonitor(self.tmux, self.config, self.logger)

    def teardown_method(self):
        """Clean up test environment."""
        if self.original_env:
            os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.original_env
        elif "TMUX_ORCHESTRATOR_BASE_DIR" in os.environ:
            del os.environ["TMUX_ORCHESTRATOR_BASE_DIR"]

    def test_initialization_success(self):
        """Test successful AgentMonitor initialization."""
        # Mock successful discovery
        self.tmux.list_sessions.return_value = [{"name": "test-session"}]
        self.tmux.list_windows.return_value = [{"index": "1", "name": "claude-dev"}]

        result = self.agent_monitor.initialize()

        assert result is True
        # Just check that initialization succeeded, not the specific log message

    def test_initialization_failure(self):
        """Test AgentMonitor initialization failure."""
        # Mock discovery failure
        self.tmux.list_sessions.side_effect = Exception("Connection failed")

        result = self.agent_monitor.initialize()

        assert result is False

    def test_cleanup(self):
        """Test AgentMonitor cleanup."""
        # Add some data to cache
        self.agent_monitor._agent_cache["test:1"] = Mock()

        self.agent_monitor.cleanup()

        assert len(self.agent_monitor._agent_cache) == 0
        self.logger.info.assert_called_with("Cleaning up AgentMonitor")


class TestAgentDiscovery:
    """Test agent discovery functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.original_env = os.environ.get("TMUX_ORCHESTRATOR_BASE_DIR")
        os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.test_dir

        self.tmux = Mock(spec=TMUXManager)
        self.config = Config.load()
        self.logger = Mock(spec=logging.Logger)

        self.agent_monitor = AgentMonitor(self.tmux, self.config, self.logger)

    def teardown_method(self):
        """Clean up test environment."""
        if self.original_env:
            os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.original_env
        elif "TMUX_ORCHESTRATOR_BASE_DIR" in os.environ:
            del os.environ["TMUX_ORCHESTRATOR_BASE_DIR"]

    def test_discover_agents_multiple_sessions(self):
        """Test agent discovery across multiple sessions."""
        # Mock multiple sessions with agents
        self.tmux.list_sessions.return_value = [{"name": "frontend-team"}, {"name": "backend-team"}]

        # Mock list_windows to return different data based on session
        def mock_list_windows(session_name):
            if session_name == "frontend-team":
                return [
                    {"index": "0", "name": "shell"},
                    {"index": "1", "name": "claude-developer"},
                    {"index": "2", "name": "pm"},
                ]
            elif session_name == "backend-team":
                return [
                    {"index": "0", "name": "shell"},
                    {"index": "1", "name": "claude-qa"},
                    {"index": "2", "name": "devops"},
                ]
            else:
                return []

        self.tmux.list_windows.side_effect = mock_list_windows

        agents = self.agent_monitor.discover_agents()

        # Should find 4 agents (exclude shell windows)
        assert len(agents) == 4

        # Verify agent targets
        targets = [agent.target for agent in agents]
        assert "frontend-team:1" in targets  # claude-developer
        assert "frontend-team:2" in targets  # pm
        assert "backend-team:1" in targets  # claude-qa
        assert "backend-team:2" in targets  # devops

    def test_discover_agents_no_sessions(self):
        """Test agent discovery when no sessions exist."""
        self.tmux.list_sessions.return_value = []

        agents = self.agent_monitor.discover_agents()

        assert len(agents) == 0
        self.logger.debug.assert_called_with("Agent discovery complete: found 0 agents")

    def test_discover_agents_session_error(self):
        """Test agent discovery with session listing error."""
        self.tmux.list_sessions.side_effect = Exception("Tmux connection failed")

        agents = self.agent_monitor.discover_agents()

        assert len(agents) == 0
        self.logger.error.assert_called()

    def test_discover_agents_window_error(self):
        """Test agent discovery with window listing error."""
        self.tmux.list_sessions.return_value = [{"name": "test-session"}]
        self.tmux.list_windows.side_effect = Exception("Window listing failed")

        agents = self.agent_monitor.discover_agents()

        assert len(agents) == 0
        self.logger.warning.assert_called()

    def test_discover_agents_caching(self):
        """Test that discovered agents are cached."""
        self.tmux.list_sessions.return_value = [{"name": "test-session"}]
        self.tmux.list_windows.return_value = [{"index": "1", "name": "claude-dev"}]

        agents = self.agent_monitor.discover_agents()

        assert len(agents) == 1
        assert "test-session:1" in self.agent_monitor._agent_cache
        assert self.agent_monitor._last_discovery_time is not None


class TestAgentWindowDetection:
    """Test agent window detection logic."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.original_env = os.environ.get("TMUX_ORCHESTRATOR_BASE_DIR")
        os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.test_dir

        self.tmux = Mock(spec=TMUXManager)
        self.config = Config.load()
        self.logger = Mock(spec=logging.Logger)

        self.agent_monitor = AgentMonitor(self.tmux, self.config, self.logger)

    def teardown_method(self):
        """Clean up test environment."""
        if self.original_env:
            os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.original_env
        elif "TMUX_ORCHESTRATOR_BASE_DIR" in os.environ:
            del os.environ["TMUX_ORCHESTRATOR_BASE_DIR"]

    def test_is_agent_window_claude_prefix(self):
        """Test detection of Claude-prefixed agent windows."""
        self.tmux.list_windows.return_value = [
            {"index": "1", "name": "claude-developer"},
            {"index": "2", "name": "claude-qa"},
            {"index": "3", "name": "shell"},
        ]

        assert self.agent_monitor.is_agent_window("test:1") is True
        assert self.agent_monitor.is_agent_window("test:2") is True
        assert self.agent_monitor.is_agent_window("test:3") is False

    def test_is_agent_window_role_indicators(self):
        """Test detection of agent windows by role indicators."""
        self.tmux.list_windows.return_value = [
            {"index": "1", "name": "pm"},
            {"index": "2", "name": "developer"},
            {"index": "3", "name": "qa"},
            {"index": "4", "name": "devops"},
            {"index": "5", "name": "backend"},
            {"index": "6", "name": "frontend"},
            {"index": "7", "name": "shell"},
        ]

        # Should detect agent indicators
        assert self.agent_monitor.is_agent_window("test:1") is True  # pm
        assert self.agent_monitor.is_agent_window("test:2") is True  # developer
        assert self.agent_monitor.is_agent_window("test:3") is True  # qa
        assert self.agent_monitor.is_agent_window("test:4") is True  # devops
        assert self.agent_monitor.is_agent_window("test:5") is True  # backend
        assert self.agent_monitor.is_agent_window("test:6") is True  # frontend
        assert self.agent_monitor.is_agent_window("test:7") is False  # shell

    def test_is_agent_window_error_handling(self):
        """Test agent window detection error handling."""
        self.tmux.list_windows.side_effect = Exception("Window access failed")

        result = self.agent_monitor.is_agent_window("test:1")

        assert result is False
        self.logger.error.assert_called()

    def test_is_agent_window_invalid_target(self):
        """Test agent window detection with invalid target."""
        result = self.agent_monitor.is_agent_window("invalid-target")

        assert result is False
        self.logger.error.assert_called()


class TestAgentDisplayNames:
    """Test agent display name generation."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.original_env = os.environ.get("TMUX_ORCHESTRATOR_BASE_DIR")
        os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.test_dir

        self.tmux = Mock(spec=TMUXManager)
        self.config = Config.load()
        self.logger = Mock(spec=logging.Logger)

        self.agent_monitor = AgentMonitor(self.tmux, self.config, self.logger)

    def teardown_method(self):
        """Clean up test environment."""
        if self.original_env:
            os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.original_env
        elif "TMUX_ORCHESTRATOR_BASE_DIR" in os.environ:
            del os.environ["TMUX_ORCHESTRATOR_BASE_DIR"]

    def test_get_agent_display_name_success(self):
        """Test successful agent display name generation."""
        self.tmux.list_windows.return_value = [{"index": "1", "name": "claude-developer"}, {"index": "2", "name": "pm"}]

        name1 = self.agent_monitor.get_agent_display_name("test:1")
        name2 = self.agent_monitor.get_agent_display_name("test:2")

        assert name1 == "claude-developer[test:1]"
        assert name2 == "pm[test:2]"

    def test_get_agent_display_name_window_not_found(self):
        """Test display name when window not found."""
        self.tmux.list_windows.return_value = [{"index": "1", "name": "claude-developer"}]

        name = self.agent_monitor.get_agent_display_name("test:99")

        assert name == "Unknown[test:99]"

    def test_get_agent_display_name_error(self):
        """Test display name generation error handling."""
        self.tmux.list_windows.side_effect = Exception("Window access failed")

        name = self.agent_monitor.get_agent_display_name("test:1")

        assert name == "test:1"
        self.logger.error.assert_called()


class TestAgentContentAnalysis:
    """Test agent content analysis functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.original_env = os.environ.get("TMUX_ORCHESTRATOR_BASE_DIR")
        os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.test_dir

        self.tmux = Mock(spec=TMUXManager)
        self.config = Config.load()
        self.logger = Mock(spec=logging.Logger)

        self.agent_monitor = AgentMonitor(self.tmux, self.config, self.logger)

    def teardown_method(self):
        """Clean up test environment."""
        if self.original_env:
            os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.original_env
        elif "TMUX_ORCHESTRATOR_BASE_DIR" in os.environ:
            del os.environ["TMUX_ORCHESTRATOR_BASE_DIR"]

    @patch("time.sleep")
    def test_analyze_agent_content_active_agent(self, mock_sleep):
        """Test content analysis for an active agent."""
        # Mock changing content (active agent)
        self.tmux.capture_pane.side_effect = [
            "Initial content",
            "Content is changing",
            "More changes happening",
            "Final state with activity",
        ]

        analysis = self.agent_monitor.analyze_agent_content("test:1")

        assert analysis.target == "test:1"
        assert analysis.is_idle is False
        assert analysis.confidence == 0.9
        assert analysis.last_activity is not None

    @patch("time.sleep")
    def test_analyze_agent_content_idle_agent(self, mock_sleep):
        """Test content analysis for an idle agent."""
        # Mock static content (idle agent)
        static_content = "Static content - not changing"
        self.tmux.capture_pane.return_value = static_content

        analysis = self.agent_monitor.analyze_agent_content("test:1")

        assert analysis.target == "test:1"
        assert analysis.is_idle is True
        assert analysis.idle_type == IdleType.NEWLY_IDLE
        assert analysis.confidence == 0.8

    @patch("time.sleep")
    def test_analyze_agent_content_compaction_state(self, mock_sleep):
        """Test content analysis for agent in compaction state."""
        # Mock compaction content
        compaction_content = "Agent is compacting conversation to save memory..."
        self.tmux.capture_pane.return_value = compaction_content

        analysis = self.agent_monitor.analyze_agent_content("test:1")

        assert analysis.target == "test:1"
        assert analysis.is_idle is False  # Not idle during compaction
        assert analysis.idle_type == IdleType.COMPACTION_STATE

    @patch("time.sleep")
    def test_analyze_agent_content_error_state(self, mock_sleep):
        """Test content analysis for agent in error state."""
        # Mock error content
        error_content = "Error: Rate limit exceeded. Please try again later."
        self.tmux.capture_pane.return_value = error_content

        analysis = self.agent_monitor.analyze_agent_content("test:1")

        assert analysis.target == "test:1"
        assert analysis.is_idle is True
        assert analysis.idle_type == IdleType.ERROR_STATE
        assert analysis.error_detected is True
        assert analysis.error_type == "rate_limit"

    @patch("time.sleep")
    def test_analyze_agent_content_fresh_agent(self, mock_sleep):
        """Test content analysis for fresh agent."""
        # Mock fresh agent content
        fresh_content = "Welcome! How can I help you today?"
        self.tmux.capture_pane.return_value = fresh_content

        analysis = self.agent_monitor.analyze_agent_content("test:1")

        assert analysis.target == "test:1"
        assert analysis.is_idle is True
        assert analysis.idle_type == IdleType.FRESH_AGENT

    @patch("time.sleep")
    def test_analyze_agent_content_error_handling(self, mock_sleep):
        """Test content analysis error handling."""
        self.tmux.capture_pane.side_effect = Exception("Capture failed")

        analysis = self.agent_monitor.analyze_agent_content("test:1")

        assert analysis.target == "test:1"
        assert analysis.is_idle is True
        assert analysis.idle_type == IdleType.UNKNOWN
        assert analysis.confidence == 0.0
        assert analysis.error_detected is True
        assert analysis.error_type == "analysis_failed"


class TestAgentTypeDetection:
    """Test agent type detection from window names."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.original_env = os.environ.get("TMUX_ORCHESTRATOR_BASE_DIR")
        os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.test_dir

        self.tmux = Mock(spec=TMUXManager)
        self.config = Config.load()
        self.logger = Mock(spec=logging.Logger)

        self.agent_monitor = AgentMonitor(self.tmux, self.config, self.logger)

    def teardown_method(self):
        """Clean up test environment."""
        if self.original_env:
            os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.original_env
        elif "TMUX_ORCHESTRATOR_BASE_DIR" in os.environ:
            del os.environ["TMUX_ORCHESTRATOR_BASE_DIR"]

    def test_determine_agent_type_variations(self):
        """Test agent type determination for various window names."""
        test_cases = [
            ("pm", "Project Manager"),
            ("project-manager", "Project Manager"),
            ("developer", "Developer"),
            ("dev", "Developer"),
            ("engineer", "Developer"),
            ("qa", "QA Engineer"),
            ("test", "QA Engineer"),
            ("devops", "DevOps"),
            ("researcher", "Researcher"),
            ("research", "Researcher"),
            ("writer", "Documentation Writer"),
            ("doc", "Documentation Writer"),
            ("claude-anything", "Claude Agent"),
            ("unknown-role", "Agent"),
        ]

        for window_name, expected_type in test_cases:
            agent_type = self.agent_monitor._determine_agent_type(window_name)
            assert agent_type == expected_type, f"Failed for {window_name}"


class TestErrorDetection:
    """Test error pattern detection in agent content."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.original_env = os.environ.get("TMUX_ORCHESTRATOR_BASE_DIR")
        os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.test_dir

        self.tmux = Mock(spec=TMUXManager)
        self.config = Config.load()
        self.logger = Mock(spec=logging.Logger)

        self.agent_monitor = AgentMonitor(self.tmux, self.config, self.logger)

    def teardown_method(self):
        """Clean up test environment."""
        if self.original_env:
            os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.original_env
        elif "TMUX_ORCHESTRATOR_BASE_DIR" in os.environ:
            del os.environ["TMUX_ORCHESTRATOR_BASE_DIR"]

    def test_detect_api_error_patterns(self):
        """Test detection of various API error patterns."""
        error_contents = [
            "Rate limit exceeded",
            "API error occurred",
            "Connection error - please retry",
            "Request timeout",
            "Service overloaded",
            "503 Service Unavailable",
            "502 Bad Gateway",
            "500 Internal Server Error",
            "Too many requests",
            "Quota exceeded",
        ]

        for content in error_contents:
            assert self.agent_monitor._detect_api_error_patterns(content) is True

        # Test non-error content
        normal_content = "Agent is working on the task successfully"
        assert self.agent_monitor._detect_api_error_patterns(normal_content) is False

    def test_identify_error_type(self):
        """Test identification of specific error types."""
        error_test_cases = [
            ("Rate limit exceeded", "rate_limit"),
            ("Too many requests", "rate_limit"),
            ("Service overloaded", "service_overloaded"),
            ("503 Service Unavailable", "service_overloaded"),
            ("Connection timeout", "timeout"),
            ("Connection error", "connection_error"),
            ("Quota exceeded", "quota_exceeded"),
            ("Unknown error occurred", "unknown_error"),
        ]

        for content, expected_type in error_test_cases:
            error_type = self.agent_monitor._identify_error_type(content)
            assert error_type == expected_type


class TestCacheOperations:
    """Test agent cache operations."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.original_env = os.environ.get("TMUX_ORCHESTRATOR_BASE_DIR")
        os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.test_dir

        self.tmux = Mock(spec=TMUXManager)
        self.config = Config.load()
        self.logger = Mock(spec=logging.Logger)

        self.agent_monitor = AgentMonitor(self.tmux, self.config, self.logger)

    def teardown_method(self):
        """Clean up test environment."""
        if self.original_env:
            os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.original_env
        elif "TMUX_ORCHESTRATOR_BASE_DIR" in os.environ:
            del os.environ["TMUX_ORCHESTRATOR_BASE_DIR"]

    def test_cached_agent_info_operations(self):
        """Test cached agent info operations."""
        # Test empty cache
        assert self.agent_monitor.get_cached_agent_info("test:1") is None
        assert len(self.agent_monitor.get_all_cached_agents()) == 0

        # Add agent to cache
        agent_info = AgentInfo(
            target="test:1", session="test", window="1", name="claude-dev", type="Developer", status="active"
        )
        self.agent_monitor._agent_cache["test:1"] = agent_info

        # Test cache retrieval
        cached = self.agent_monitor.get_cached_agent_info("test:1")
        assert cached == agent_info

        all_cached = self.agent_monitor.get_all_cached_agents()
        assert len(all_cached) == 1
        assert all_cached[0] == agent_info

        # Test cache clearing
        self.agent_monitor.clear_cache()
        assert len(self.agent_monitor.get_all_cached_agents()) == 0


class TestFreshAgentDetection:
    """Test fresh agent detection logic."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.original_env = os.environ.get("TMUX_ORCHESTRATOR_BASE_DIR")
        os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.test_dir

        self.tmux = Mock(spec=TMUXManager)
        self.config = Config.load()
        self.logger = Mock(spec=logging.Logger)

        self.agent_monitor = AgentMonitor(self.tmux, self.config, self.logger)

    def teardown_method(self):
        """Clean up test environment."""
        if self.original_env:
            os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.original_env
        elif "TMUX_ORCHESTRATOR_BASE_DIR" in os.environ:
            del os.environ["TMUX_ORCHESTRATOR_BASE_DIR"]

    def test_is_agent_fresh(self):
        """Test fresh agent detection."""
        fresh_contents = [
            "Welcome! How can I help you?",
            "Getting started with the project",
            "How can I assist you today?",
            "Ready to assist with your tasks",
            "What would you like me to work on?",
            "Please provide initial prompt",
        ]

        for content in fresh_contents:
            assert self.agent_monitor._is_agent_fresh(content) is True

        # Test non-fresh content
        working_content = "I'm currently working on implementing the feature"
        assert self.agent_monitor._is_agent_fresh(working_content) is False

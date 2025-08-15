"""
Comprehensive tests for StateTracker class.

Tests the extracted state tracking functionality to ensure
no functionality loss during refactoring.
"""

import hashlib
import logging
import os
import tempfile
from datetime import datetime
from unittest.mock import Mock

from tmux_orchestrator.core.config import Config
from tmux_orchestrator.core.monitoring.state_tracker import StateTracker
from tmux_orchestrator.core.monitoring.types import AgentInfo
from tmux_orchestrator.utils.tmux import TMUXManager


class TestStateTrackerInitialization:
    """Test StateTracker initialization and basic functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.original_env = os.environ.get("TMUX_ORCHESTRATOR_BASE_DIR")
        os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.test_dir

        self.tmux = Mock(spec=TMUXManager)
        self.config = Config.load()
        self.logger = Mock(spec=logging.Logger)

        self.state_tracker = StateTracker(self.tmux, self.config, self.logger)

    def teardown_method(self):
        """Clean up test environment."""
        if self.original_env:
            os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.original_env
        elif "TMUX_ORCHESTRATOR_BASE_DIR" in os.environ:
            del os.environ["TMUX_ORCHESTRATOR_BASE_DIR"]

    def test_initialization_success(self):
        """Test successful StateTracker initialization."""
        result = self.state_tracker.initialize()

        assert result is True
        self.logger.info.assert_called_with("Initializing StateTracker")

    def test_initialization_failure(self):
        """Test StateTracker initialization failure."""
        # Patch to cause initialization failure
        mock_logger = Mock()
        mock_logger.info.side_effect = Exception("Init failed")
        self.state_tracker.logger = mock_logger

        result = self.state_tracker.initialize()

        assert result is False

    def test_cleanup(self):
        """Test StateTracker cleanup."""
        # Add some data to tracking
        self.state_tracker._agent_states["test:1"] = Mock()
        self.state_tracker._idle_agents["test:1"] = datetime.now()

        self.state_tracker.cleanup()

        assert len(self.state_tracker._agent_states) == 0
        assert len(self.state_tracker._idle_agents) == 0
        self.logger.info.assert_called_with("Cleaning up StateTracker")


class TestAgentStateTracking:
    """Test agent state tracking functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.original_env = os.environ.get("TMUX_ORCHESTRATOR_BASE_DIR")
        os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.test_dir

        self.tmux = Mock(spec=TMUXManager)
        self.config = Config.load()
        self.logger = Mock(spec=logging.Logger)

        self.state_tracker = StateTracker(self.tmux, self.config, self.logger)

    def teardown_method(self):
        """Clean up test environment."""
        if self.original_env:
            os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.original_env
        elif "TMUX_ORCHESTRATOR_BASE_DIR" in os.environ:
            del os.environ["TMUX_ORCHESTRATOR_BASE_DIR"]

    def test_update_agent_state_new_agent(self):
        """Test updating state for a new agent."""
        content = "Initial agent content"

        state = self.state_tracker.update_agent_state("test:1", content)

        assert state.target == "test:1"
        assert state.session == "test"
        assert state.window == "1"
        assert state.last_content == content
        assert state.is_fresh is True
        assert state.consecutive_idle_count == 0
        assert state.last_activity is not None

    def test_update_agent_state_content_changed(self):
        """Test updating state when content changes."""
        # First update
        content1 = "Initial content"
        state1 = self.state_tracker.update_agent_state("test:1", content1)

        # Second update with different content
        content2 = "Changed content"
        state2 = self.state_tracker.update_agent_state("test:1", content2)

        assert state2.last_content == content2
        assert state2.consecutive_idle_count == 0
        assert state2.is_fresh is False
        assert "test:1" not in self.state_tracker._idle_agents

    def test_update_agent_state_content_unchanged(self):
        """Test updating state when content doesn't change."""
        content = "Static content"

        # First update
        state1 = self.state_tracker.update_agent_state("test:1", content)

        # Second update with same content
        state2 = self.state_tracker.update_agent_state("test:1", content)

        assert state2.consecutive_idle_count == 1
        assert "test:1" in self.state_tracker._idle_agents

    def test_get_agent_state_exists(self):
        """Test getting existing agent state."""
        content = "Test content"
        self.state_tracker.update_agent_state("test:1", content)

        state = self.state_tracker.get_agent_state("test:1")

        assert state is not None
        assert state.target == "test:1"

    def test_get_agent_state_not_exists(self):
        """Test getting non-existent agent state."""
        state = self.state_tracker.get_agent_state("nonexistent:1")

        assert state is None

    def test_reset_agent_state(self):
        """Test resetting agent state."""
        # Set up state
        content = "Test content"
        self.state_tracker.update_agent_state("test:1", content)
        self.state_tracker._submission_attempts["test:1"] = 3

        # Reset state
        self.state_tracker.reset_agent_state("test:1")

        assert self.state_tracker.get_agent_state("test:1") is None
        assert "test:1" not in self.state_tracker._idle_agents
        assert "test:1" not in self.state_tracker._submission_attempts

    def test_get_session_agents(self):
        """Test getting all agents in a session."""
        # Add agents to different sessions
        self.state_tracker.update_agent_state("session1:1", "content1")
        self.state_tracker.update_agent_state("session1:2", "content2")
        self.state_tracker.update_agent_state("session2:1", "content3")

        session1_agents = self.state_tracker.get_session_agents("session1")
        session2_agents = self.state_tracker.get_session_agents("session2")

        assert len(session1_agents) == 2
        assert len(session2_agents) == 1

        targets = [agent.target for agent in session1_agents]
        assert "session1:1" in targets
        assert "session1:2" in targets


class TestSessionAgentRegistry:
    """Test session agent registry functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.original_env = os.environ.get("TMUX_ORCHESTRATOR_BASE_DIR")
        os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.test_dir

        self.tmux = Mock(spec=TMUXManager)
        self.config = Config.load()
        self.logger = Mock(spec=logging.Logger)

        self.state_tracker = StateTracker(self.tmux, self.config, self.logger)

    def teardown_method(self):
        """Clean up test environment."""
        if self.original_env:
            os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.original_env
        elif "TMUX_ORCHESTRATOR_BASE_DIR" in os.environ:
            del os.environ["TMUX_ORCHESTRATOR_BASE_DIR"]

    def test_track_session_agent(self):
        """Test tracking agent in session registry."""
        agent_info = AgentInfo(
            target="test:1", session="test", window="1", name="claude-dev", type="Developer", status="active"
        )

        self.state_tracker.track_session_agent(agent_info)

        registry = self.state_tracker.get_session_agent_registry("test")
        assert "test:1" in registry
        assert registry["test:1"]["name"] == "claude-dev"
        assert registry["test:1"]["type"] == "Developer"

    def test_get_session_agent_registry_empty(self):
        """Test getting empty session registry."""
        registry = self.state_tracker.get_session_agent_registry("nonexistent")

        assert registry == {}

    def test_track_multiple_session_agents(self):
        """Test tracking multiple agents in a session."""
        agent1 = AgentInfo(
            target="test:1", session="test", window="1", name="pm", type="Project Manager", status="active"
        )
        agent2 = AgentInfo(target="test:2", session="test", window="2", name="dev", type="Developer", status="active")

        self.state_tracker.track_session_agent(agent1)
        self.state_tracker.track_session_agent(agent2)

        registry = self.state_tracker.get_session_agent_registry("test")
        assert len(registry) == 2
        assert "test:1" in registry
        assert "test:2" in registry


class TestIdleTracking:
    """Test idle state tracking functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.original_env = os.environ.get("TMUX_ORCHESTRATOR_BASE_DIR")
        os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.test_dir

        self.tmux = Mock(spec=TMUXManager)
        self.config = Config.load()
        self.logger = Mock(spec=logging.Logger)

        self.state_tracker = StateTracker(self.tmux, self.config, self.logger)

    def teardown_method(self):
        """Clean up test environment."""
        if self.original_env:
            os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.original_env
        elif "TMUX_ORCHESTRATOR_BASE_DIR" in os.environ:
            del os.environ["TMUX_ORCHESTRATOR_BASE_DIR"]

    def test_is_agent_idle_false(self):
        """Test idle check for active agent."""
        assert self.state_tracker.is_agent_idle("test:1") is False

    def test_is_agent_idle_true(self):
        """Test idle check for idle agent."""
        # Make agent idle by updating with same content twice
        content = "Static content"
        self.state_tracker.update_agent_state("test:1", content)
        self.state_tracker.update_agent_state("test:1", content)

        assert self.state_tracker.is_agent_idle("test:1") is True

    def test_get_idle_duration_not_idle(self):
        """Test idle duration for non-idle agent."""
        duration = self.state_tracker.get_idle_duration("test:1")
        assert duration is None

    def test_get_idle_duration_idle(self):
        """Test idle duration for idle agent."""
        # Make agent idle
        content = "Static content"
        self.state_tracker.update_agent_state("test:1", content)
        self.state_tracker.update_agent_state("test:1", content)

        duration = self.state_tracker.get_idle_duration("test:1")
        assert duration is not None
        assert duration >= 0

    def test_get_all_idle_agents(self):
        """Test getting all idle agents."""
        # Make some agents idle
        content = "Static content"
        self.state_tracker.update_agent_state("test:1", content)
        self.state_tracker.update_agent_state("test:1", content)
        self.state_tracker.update_agent_state("test:2", content)
        self.state_tracker.update_agent_state("test:2", content)

        idle_agents = self.state_tracker.get_all_idle_agents()

        assert len(idle_agents) == 2
        assert "test:1" in idle_agents
        assert "test:2" in idle_agents


class TestSubmissionTracking:
    """Test submission attempt tracking functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.original_env = os.environ.get("TMUX_ORCHESTRATOR_BASE_DIR")
        os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.test_dir

        self.tmux = Mock(spec=TMUXManager)
        self.config = Config.load()
        self.logger = Mock(spec=logging.Logger)

        self.state_tracker = StateTracker(self.tmux, self.config, self.logger)

    def teardown_method(self):
        """Clean up test environment."""
        if self.original_env:
            os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.original_env
        elif "TMUX_ORCHESTRATOR_BASE_DIR" in os.environ:
            del os.environ["TMUX_ORCHESTRATOR_BASE_DIR"]

    def test_track_submission_attempt(self):
        """Test tracking submission attempts."""
        self.state_tracker.track_submission_attempt("test:1")

        attempts = self.state_tracker.get_submission_attempts("test:1")
        assert attempts == 1

        last_time = self.state_tracker.get_last_submission_time("test:1")
        assert last_time is not None

    def test_track_multiple_submission_attempts(self):
        """Test tracking multiple submission attempts."""
        self.state_tracker.track_submission_attempt("test:1")
        self.state_tracker.track_submission_attempt("test:1")
        self.state_tracker.track_submission_attempt("test:1")

        attempts = self.state_tracker.get_submission_attempts("test:1")
        assert attempts == 3

    def test_get_submission_attempts_no_attempts(self):
        """Test getting submission attempts for agent with no attempts."""
        attempts = self.state_tracker.get_submission_attempts("test:1")
        assert attempts == 0

    def test_get_last_submission_time_no_attempts(self):
        """Test getting last submission time for agent with no attempts."""
        last_time = self.state_tracker.get_last_submission_time("test:1")
        assert last_time is None

    def test_reset_submission_tracking(self):
        """Test resetting submission tracking."""
        # Track some attempts
        self.state_tracker.track_submission_attempt("test:1")
        self.state_tracker.track_submission_attempt("test:1")

        # Reset tracking
        self.state_tracker.reset_submission_tracking("test:1")

        attempts = self.state_tracker.get_submission_attempts("test:1")
        last_time = self.state_tracker.get_last_submission_time("test:1")

        assert attempts == 0
        assert last_time is None


class TestTeamIdleTracking:
    """Test team idle state tracking functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.original_env = os.environ.get("TMUX_ORCHESTRATOR_BASE_DIR")
        os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.test_dir

        self.tmux = Mock(spec=TMUXManager)
        self.config = Config.load()
        self.logger = Mock(spec=logging.Logger)

        self.state_tracker = StateTracker(self.tmux, self.config, self.logger)

    def teardown_method(self):
        """Clean up test environment."""
        if self.original_env:
            os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.original_env
        elif "TMUX_ORCHESTRATOR_BASE_DIR" in os.environ:
            del os.environ["TMUX_ORCHESTRATOR_BASE_DIR"]

    def test_set_team_idle(self):
        """Test setting team as idle."""
        self.state_tracker.set_team_idle("test")

        assert self.state_tracker.is_team_idle("test") is True

        duration = self.state_tracker.get_team_idle_duration("test")
        assert duration is not None
        assert duration >= 0

    def test_clear_team_idle(self):
        """Test clearing team idle status."""
        # Set team idle first
        self.state_tracker.set_team_idle("test")
        assert self.state_tracker.is_team_idle("test") is True

        # Clear idle status
        self.state_tracker.clear_team_idle("test")
        assert self.state_tracker.is_team_idle("test") is False

        duration = self.state_tracker.get_team_idle_duration("test")
        assert duration is None

    def test_is_team_idle_not_tracked(self):
        """Test team idle check for untracked session."""
        assert self.state_tracker.is_team_idle("untracked") is False

    def test_get_team_idle_duration_not_idle(self):
        """Test team idle duration for non-idle team."""
        duration = self.state_tracker.get_team_idle_duration("test")
        assert duration is None

    def test_set_team_idle_multiple_times(self):
        """Test setting team idle multiple times."""
        self.state_tracker.set_team_idle("test")
        first_time = self.state_tracker._team_idle_at["test"]

        # Setting again should not change the time
        self.state_tracker.set_team_idle("test")
        second_time = self.state_tracker._team_idle_at["test"]

        assert first_time == second_time


class TestMissingAgentTracking:
    """Test missing agent tracking functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.original_env = os.environ.get("TMUX_ORCHESTRATOR_BASE_DIR")
        os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.test_dir

        self.tmux = Mock(spec=TMUXManager)
        self.config = Config.load()
        self.logger = Mock(spec=logging.Logger)

        self.state_tracker = StateTracker(self.tmux, self.config, self.logger)

    def teardown_method(self):
        """Clean up test environment."""
        if self.original_env:
            os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.original_env
        elif "TMUX_ORCHESTRATOR_BASE_DIR" in os.environ:
            del os.environ["TMUX_ORCHESTRATOR_BASE_DIR"]

    def test_track_missing_agent(self):
        """Test tracking missing agent."""
        self.state_tracker.track_missing_agent("test:1")

        assert self.state_tracker.is_agent_missing("test:1") is True

        duration = self.state_tracker.get_missing_duration("test:1")
        assert duration is not None
        assert duration >= 0

    def test_clear_missing_agent(self):
        """Test clearing missing agent tracking."""
        # Track as missing first
        self.state_tracker.track_missing_agent("test:1")
        assert self.state_tracker.is_agent_missing("test:1") is True

        # Clear missing status
        self.state_tracker.clear_missing_agent("test:1")
        assert self.state_tracker.is_agent_missing("test:1") is False

        duration = self.state_tracker.get_missing_duration("test:1")
        assert duration is None

    def test_is_agent_missing_not_tracked(self):
        """Test missing check for untracked agent."""
        assert self.state_tracker.is_agent_missing("test:1") is False

    def test_get_missing_duration_not_missing(self):
        """Test missing duration for non-missing agent."""
        duration = self.state_tracker.get_missing_duration("test:1")
        assert duration is None

    def test_track_missing_agent_multiple_times(self):
        """Test tracking missing agent multiple times."""
        self.state_tracker.track_missing_agent("test:1")
        first_time = self.state_tracker._missing_agent_grace["test:1"]

        # Tracking again should not change the time
        self.state_tracker.track_missing_agent("test:1")
        second_time = self.state_tracker._missing_agent_grace["test:1"]

        assert first_time == second_time


class TestUtilityMethods:
    """Test utility methods and state summaries."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.original_env = os.environ.get("TMUX_ORCHESTRATOR_BASE_DIR")
        os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.test_dir

        self.tmux = Mock(spec=TMUXManager)
        self.config = Config.load()
        self.logger = Mock(spec=logging.Logger)

        self.state_tracker = StateTracker(self.tmux, self.config, self.logger)

    def teardown_method(self):
        """Clean up test environment."""
        if self.original_env:
            os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.original_env
        elif "TMUX_ORCHESTRATOR_BASE_DIR" in os.environ:
            del os.environ["TMUX_ORCHESTRATOR_BASE_DIR"]

    def test_get_all_sessions_empty(self):
        """Test getting all sessions when empty."""
        sessions = self.state_tracker.get_all_sessions()
        assert len(sessions) == 0

    def test_get_all_sessions_with_data(self):
        """Test getting all sessions with data."""
        # Add agents from different sessions
        self.state_tracker.update_agent_state("session1:1", "content1")
        self.state_tracker.update_agent_state("session1:2", "content2")
        self.state_tracker.update_agent_state("session2:1", "content3")

        sessions = self.state_tracker.get_all_sessions()

        assert len(sessions) == 2
        assert "session1" in sessions
        assert "session2" in sessions

    def test_get_state_summary_empty(self):
        """Test state summary when empty."""
        summary = self.state_tracker.get_state_summary()

        assert summary["total_agents"] == 0
        assert summary["idle_agents"] == 0
        assert summary["sessions"] == 0
        assert summary["missing_agents"] == 0
        assert summary["agents_with_submissions"] == 0

    def test_get_state_summary_with_data(self):
        """Test state summary with various data."""
        # Add some agents
        content = "Static content"
        self.state_tracker.update_agent_state("test:1", content)
        self.state_tracker.update_agent_state("test:2", "Different content")

        # Make one idle
        self.state_tracker.update_agent_state("test:1", content)  # Same content = idle

        # Track sessions
        agent_info = AgentInfo(
            target="test:1", session="test", window="1", name="agent1", type="Agent", status="active"
        )
        self.state_tracker.track_session_agent(agent_info)

        # Track missing agent
        self.state_tracker.track_missing_agent("test:3")

        # Track submissions
        self.state_tracker.track_submission_attempt("test:1")

        summary = self.state_tracker.get_state_summary()

        assert summary["total_agents"] == 2
        assert summary["idle_agents"] == 1
        assert summary["sessions"] == 1
        assert summary["missing_agents"] == 1
        assert summary["agents_with_submissions"] == 1


class TestContentCaching:
    """Test content caching and hash computation."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.original_env = os.environ.get("TMUX_ORCHESTRATOR_BASE_DIR")
        os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.test_dir

        self.tmux = Mock(spec=TMUXManager)
        self.config = Config.load()
        self.logger = Mock(spec=logging.Logger)

        self.state_tracker = StateTracker(self.tmux, self.config, self.logger)

    def teardown_method(self):
        """Clean up test environment."""
        if self.original_env:
            os.environ["TMUX_ORCHESTRATOR_BASE_DIR"] = self.original_env
        elif "TMUX_ORCHESTRATOR_BASE_DIR" in os.environ:
            del os.environ["TMUX_ORCHESTRATOR_BASE_DIR"]

    def test_content_hash_computation(self):
        """Test that content hashes are computed correctly."""
        content = "Test content for hashing"
        expected_hash = hashlib.md5(content.encode()).hexdigest()

        state = self.state_tracker.update_agent_state("test:1", content)

        assert state.last_content_hash == expected_hash

    def test_content_caching(self):
        """Test that content is cached for future comparisons."""
        content = "Test content"

        self.state_tracker.update_agent_state("test:1", content)

        assert "test:1" in self.state_tracker._content_cache
        assert self.state_tracker._content_cache["test:1"] == content
        assert "test:1" in self.state_tracker._content_hashes

    def test_content_change_detection(self):
        """Test content change detection using cached values."""
        content1 = "Initial content"
        content2 = "Changed content"

        # First update
        state1 = self.state_tracker.update_agent_state("test:1", content1)
        assert state1.consecutive_idle_count == 0

        # Second update with different content
        state2 = self.state_tracker.update_agent_state("test:1", content2)
        assert state2.consecutive_idle_count == 0  # Should reset due to change

        # Third update with same content as second
        state3 = self.state_tracker.update_agent_state("test:1", content2)
        assert state3.consecutive_idle_count == 1  # Should increment

"""Tests for agent type detection in TMUXManager."""

from unittest.mock import patch

import pytest

from tmux_orchestrator.utils.tmux import TMUXManager


class TestAgentTypeDetection:
    """Test cases for agent type detection logic."""

    @pytest.fixture
    def tmux_manager(self) -> TMUXManager:
        """Create TMUXManager instance."""
        return TMUXManager()

    def test_agent_type_with_claude_prefix(self, tmux_manager: TMUXManager) -> None:
        """Test that agents with Claude- prefix are properly typed."""
        # Mock the list_sessions and list_windows methods
        with patch.object(tmux_manager, "list_sessions") as mock_sessions:
            with patch.object(tmux_manager, "list_windows") as mock_windows:
                with patch.object(tmux_manager, "capture_pane") as mock_capture:
                    # Setup mock data
                    mock_sessions.return_value = [{"name": "project", "created": "123", "attached": "0"}]

                    # Test various Claude- prefixed window names
                    mock_windows.return_value = [
                        {"index": "0", "name": "Claude-pm"},
                        {"index": "1", "name": "Claude-backend-dev"},
                        {"index": "2", "name": "Claude-frontend-dev"},
                        {"index": "3", "name": "Claude-qa-engineer"},
                        {"index": "4", "name": "Claude-api-specialist"},
                        {"index": "5", "name": "Claude-researcher"},
                        {"index": "6", "name": "Claude-docs-writer"},
                        {"index": "7", "name": "Claude-security-expert"},
                        {"index": "8", "name": "Claude-database-admin"},
                        {"index": "9", "name": "Claude-devops"},
                        {"index": "10", "name": "Claude-code-reviewer"},
                    ]

                    # Mock capture_pane to return active content
                    mock_capture.return_value = "Human: Hello\nAssistant: Hi there!"

                    # Get agents
                    agents = tmux_manager.list_agents()

                    # Verify agent types are correctly detected
                    assert len(agents) == 11

                    # Check specific agent types
                    agent_types = {agent["window"]: agent["type"] for agent in agents}

                    assert agent_types["0"] == "PM"
                    assert agent_types["1"] == "Backend"
                    assert agent_types["2"] == "Frontend"
                    assert agent_types["3"] == "QA"
                    assert agent_types["4"] == "Api Specialist"  # Fallback to title case
                    assert agent_types["5"] == "Researcher"
                    assert agent_types["6"] == "Writer"
                    assert agent_types["7"] == "Security Expert"  # Fallback to title case
                    assert agent_types["8"] == "Database"
                    assert agent_types["9"] == "DevOps"
                    assert agent_types["10"] == "Reviewer"

                    # Verify no "Unknown" types
                    for agent in agents:
                        assert agent["type"] != "Unknown", f"Agent {agent['window']} has Unknown type"

    def test_agent_type_without_claude_prefix(self, tmux_manager: TMUXManager) -> None:
        """Test agent type detection for windows without Claude- prefix."""
        with patch.object(tmux_manager, "list_sessions") as mock_sessions:
            with patch.object(tmux_manager, "list_windows") as mock_windows:
                with patch.object(tmux_manager, "capture_pane") as mock_capture:
                    # Setup mock data
                    mock_sessions.return_value = [{"name": "dev-session", "created": "123", "attached": "0"}]

                    mock_windows.return_value = [
                        {"index": "0", "name": "pm"},
                        {"index": "1", "name": "developer"},
                        {"index": "2", "name": "qa"},
                        {"index": "3", "name": "Claude"},  # Generic Claude window
                    ]

                    mock_capture.return_value = "Active content"

                    agents = tmux_manager.list_agents()

                    assert len(agents) == 4
                    agent_types = {agent["window"]: agent["type"] for agent in agents}

                    assert agent_types["0"] == "PM"
                    assert agent_types["1"] == "Developer"
                    assert agent_types["2"] == "QA"
                    # Generic "Claude" window should not be Unknown
                    assert agent_types["3"] != "Unknown"

    def test_agent_type_session_based_detection(self, tmux_manager: TMUXManager) -> None:
        """Test that session names influence agent type detection."""
        with patch.object(tmux_manager, "list_sessions") as mock_sessions:
            with patch.object(tmux_manager, "list_windows") as mock_windows:
                with patch.object(tmux_manager, "capture_pane") as mock_capture:
                    # Setup mock data with typed sessions
                    mock_sessions.return_value = [
                        {"name": "frontend-app", "created": "123", "attached": "0"},
                        {"name": "backend-api", "created": "124", "attached": "0"},
                        {"name": "testing-suite", "created": "125", "attached": "0"},
                    ]

                    # Mock windows for each session
                    mock_windows.side_effect = [
                        # frontend-app session
                        [{"index": "0", "name": "Claude-specialist"}],
                        # backend-api session
                        [{"index": "0", "name": "Claude-engineer"}],
                        # testing-suite session
                        [{"index": "0", "name": "Claude-automation"}],
                    ]

                    mock_capture.return_value = "Active"

                    agents = tmux_manager.list_agents()

                    # Session name should override generic window names
                    assert len(agents) == 3

                    # Find agents by session
                    frontend_agent = next(a for a in agents if a["session"] == "frontend-app")
                    backend_agent = next(a for a in agents if a["session"] == "backend-api")
                    testing_agent = next(a for a in agents if a["session"] == "testing-suite")

                    assert frontend_agent["type"] == "Frontend"
                    assert backend_agent["type"] == "Backend"
                    assert testing_agent["type"] == "QA"

    def test_agent_type_edge_cases(self, tmux_manager: TMUXManager) -> None:
        """Test edge cases in agent type detection."""
        with patch.object(tmux_manager, "list_sessions") as mock_sessions:
            with patch.object(tmux_manager, "list_windows") as mock_windows:
                with patch.object(tmux_manager, "capture_pane") as mock_capture:
                    mock_sessions.return_value = [{"name": "misc", "created": "123", "attached": "0"}]

                    # Test edge cases
                    mock_windows.return_value = [
                        {"index": "0", "name": "Claude-project-manager"},  # Should be PM
                        {"index": "1", "name": "Claude-ui-designer"},  # Should be Frontend
                        {"index": "2", "name": "Claude-db-expert"},  # Should be Database
                        {"index": "3", "name": "Claude-ops-engineer"},  # Should be DevOps
                        {"index": "4", "name": "Claude-quality-analyst"},  # Should be QA
                        {"index": "5", "name": "Claude-code-review"},  # Should be Reviewer
                        {"index": "6", "name": "Claude-documentation"},  # Should be Writer
                        {"index": "7", "name": "Claude-data-scientist"},  # Should be Database
                        {"index": "8", "name": "Claude"},  # Empty after prefix
                        {"index": "9", "name": "claude-lowercase"},  # Lowercase prefix
                    ]

                    mock_capture.return_value = "Active"

                    agents = tmux_manager.list_agents()
                    agent_types = {agent["window"]: agent["type"] for agent in agents}

                    assert agent_types["0"] == "PM"
                    assert agent_types["1"] == "Frontend"
                    assert agent_types["2"] == "Database"
                    assert agent_types["3"] == "DevOps"
                    assert agent_types["4"] == "QA"
                    assert agent_types["5"] == "Reviewer"
                    assert agent_types["6"] == "Writer"
                    assert agent_types["7"] == "Database"
                    # Empty name after prefix removal should still get a type
                    assert agent_types["8"] != "Unknown"
                    # Should handle lowercase prefix too
                    assert agent_types["9"] != "Unknown"

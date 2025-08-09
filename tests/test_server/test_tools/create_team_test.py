"""Tests for create_team business logic."""

from unittest.mock import Mock

import pytest

from tmux_orchestrator.server.tools.create_team import (
    CreateTeamRequest,
    TeamMemberSpec,
    create_team,
)
from tmux_orchestrator.utils.tmux import TMUXManager


class TestCreateTeam:
    """Test cases for create_team function."""

    def test_create_team_empty_team_name(self) -> None:
        """Test create_team with empty team name returns error."""
        tmux = Mock(spec=TMUXManager)
        request = CreateTeamRequest(
            team_name="", team_members=[TeamMemberSpec(role="pm", count=1), TeamMemberSpec(role="developer", count=2)]
        )

        result = create_team(tmux, request)

        assert not result.success
        assert result.error_message is not None
        assert "Team name cannot be empty" in result.error_message
        assert result.team_name == ""
        assert len(result.created_agents) == 0

    def test_create_team_empty_members(self) -> None:
        """Test create_team with empty team members returns error."""
        tmux = Mock(spec=TMUXManager)
        request = CreateTeamRequest(team_name="test-team", team_members=[])

        result = create_team(tmux, request)

        assert not result.success
        assert result.error_message is not None
        assert "Team must have at least one member" in result.error_message

    def test_create_team_invalid_team_name_format(self) -> None:
        """Test create_team with invalid team name format returns error."""
        tmux = Mock(spec=TMUXManager)
        request = CreateTeamRequest(
            team_name="test team with spaces!", team_members=[TeamMemberSpec(role="developer", count=1)]
        )

        result = create_team(tmux, request)

        assert not result.success
        assert result.error_message is not None
        assert "Team name must contain only alphanumeric characters, hyphens, and underscores" in result.error_message

    def test_create_team_invalid_agent_role(self) -> None:
        """Test create_team with invalid agent role returns error."""
        tmux = Mock(spec=TMUXManager)
        request = CreateTeamRequest(team_name="test-team", team_members=[TeamMemberSpec(role="invalid-role", count=1)])

        result = create_team(tmux, request)

        assert not result.success
        assert result.error_message is not None
        assert "Invalid agent role 'invalid-role'" in result.error_message

    def test_create_team_invalid_agent_count(self) -> None:
        """Test create_team with invalid agent count returns error."""
        tmux = Mock(spec=TMUXManager)
        request = CreateTeamRequest(team_name="test-team", team_members=[TeamMemberSpec(role="developer", count=0)])

        result = create_team(tmux, request)

        assert not result.success
        assert result.error_message is not None
        assert "Agent count must be positive" in result.error_message

    def test_create_team_too_many_agents(self) -> None:
        """Test create_team with too many agents returns error."""
        tmux = Mock(spec=TMUXManager)
        request = CreateTeamRequest(
            team_name="test-team", team_members=[TeamMemberSpec(role="developer", count=21)]  # Exceeds max of 20
        )

        result = create_team(tmux, request)

        assert not result.success
        assert result.error_message is not None
        assert "Total agent count cannot exceed 20" in result.error_message

    def test_create_team_session_already_exists(self) -> None:
        """Test create_team when team session already exists returns error."""
        tmux = Mock(spec=TMUXManager)
        tmux.has_session.return_value = True

        request = CreateTeamRequest(team_name="existing-team", team_members=[TeamMemberSpec(role="developer", count=1)])

        result = create_team(tmux, request)

        assert not result.success
        assert result.error_message is not None
        assert "Team 'existing-team' already exists" in result.error_message

    def test_create_team_single_agent_success(self) -> None:
        """Test successful creation of team with single agent."""
        tmux = Mock(spec=TMUXManager)
        tmux.has_session.return_value = False
        tmux.create_session.return_value = True
        tmux.send_keys.return_value = True

        request = CreateTeamRequest(
            team_name="test-team", team_members=[TeamMemberSpec(role="developer", count=1)], project_path="/test/path"
        )

        result = create_team(tmux, request)

        assert result.success
        assert result.team_name == "test-team"
        assert len(result.created_agents) == 1
        assert result.created_agents[0]["role"] == "developer"
        assert result.created_agents[0]["session"] == "test-team"
        assert result.created_agents[0]["window"] == "Claude-developer-1"
        assert result.created_agents[0]["target"] == "test-team:Claude-developer-1"
        assert result.error_message is None

        # Verify tmux calls
        tmux.has_session.assert_called_once_with("test-team")
        tmux.create_session.assert_called_once_with("test-team", "Claude-developer-1", "/test/path")

    def test_create_team_multiple_agents_same_role_success(self) -> None:
        """Test successful creation of team with multiple agents of same role."""
        tmux = Mock(spec=TMUXManager)
        tmux.has_session.return_value = False
        tmux.create_session.return_value = True
        tmux.create_window.return_value = True
        tmux.send_keys.return_value = True

        request = CreateTeamRequest(team_name="test-team", team_members=[TeamMemberSpec(role="developer", count=3)])

        result = create_team(tmux, request)

        assert result.success
        assert len(result.created_agents) == 3

        # Check all agents have unique window names
        windows = [agent["window"] for agent in result.created_agents]
        assert windows == ["Claude-developer-1", "Claude-developer-2", "Claude-developer-3"]

        # Verify tmux calls - session created once, then 2 additional windows
        tmux.create_session.assert_called_once()
        assert tmux.create_window.call_count == 2

    def test_create_team_mixed_roles_success(self) -> None:
        """Test successful creation of team with mixed agent roles."""
        tmux = Mock(spec=TMUXManager)
        tmux.has_session.return_value = False
        tmux.create_session.return_value = True
        tmux.create_window.return_value = True
        tmux.send_keys.return_value = True

        request = CreateTeamRequest(
            team_name="mixed-team",
            team_members=[
                TeamMemberSpec(role="pm", count=1, briefing="Lead the team"),
                TeamMemberSpec(role="developer", count=2, briefing="Build features"),
                TeamMemberSpec(role="qa", count=1, briefing="Test everything"),
            ],
        )

        result = create_team(tmux, request)

        assert result.success
        assert len(result.created_agents) == 4

        # Check roles are correct
        roles = [agent["role"] for agent in result.created_agents]
        assert "pm" in roles
        assert roles.count("developer") == 2
        assert "qa" in roles

        # Check briefings are passed through
        for agent in result.created_agents:
            if agent["role"] == "pm":
                assert agent["briefing"] == "Lead the team"
            elif agent["role"] == "developer":
                assert agent["briefing"] == "Build features"
            elif agent["role"] == "qa":
                assert agent["briefing"] == "Test everything"

    def test_create_team_custom_session_assignments(self) -> None:
        """Test team creation with custom session assignments."""
        tmux = Mock(spec=TMUXManager)
        tmux.has_session.return_value = False
        tmux.create_session.return_value = True
        tmux.create_window.return_value = True
        tmux.send_keys.return_value = True

        request = CreateTeamRequest(
            team_name="custom-team",
            team_members=[
                TeamMemberSpec(role="pm", count=1, custom_session="pm-session"),
                TeamMemberSpec(role="developer", count=1, custom_session="dev-session"),
            ],
        )

        result = create_team(tmux, request)

        assert result.success
        assert len(result.created_agents) == 2

        # Check custom sessions are used
        sessions = [agent["session"] for agent in result.created_agents]
        assert "pm-session" in sessions
        assert "dev-session" in sessions

    def test_create_team_session_creation_fails(self) -> None:
        """Test create_team when session creation fails."""
        tmux = Mock(spec=TMUXManager)
        tmux.has_session.return_value = False
        tmux.create_session.return_value = False

        request = CreateTeamRequest(team_name="test-team", team_members=[TeamMemberSpec(role="developer", count=1)])

        result = create_team(tmux, request)

        assert not result.success
        assert result.error_message is not None
        assert "Failed to create session" in result.error_message

    def test_create_team_window_creation_fails(self) -> None:
        """Test create_team when window creation fails for additional agents."""
        tmux = Mock(spec=TMUXManager)
        tmux.has_session.return_value = False
        tmux.create_session.return_value = True
        tmux.create_window.return_value = False  # Fails on additional windows
        tmux.send_keys.return_value = True

        request = CreateTeamRequest(team_name="test-team", team_members=[TeamMemberSpec(role="developer", count=2)])

        result = create_team(tmux, request)

        # Should partially succeed - first agent created, second fails
        assert not result.success
        assert len(result.created_agents) == 1  # Only first agent succeeded
        assert result.error_message is not None
        assert "Failed to create window" in result.error_message

    def test_create_team_claude_start_fails(self) -> None:
        """Test create_team when Claude command start fails."""
        tmux = Mock(spec=TMUXManager)
        tmux.has_session.return_value = False
        tmux.create_session.return_value = True
        tmux.send_keys.return_value = False  # Claude command fails

        request = CreateTeamRequest(team_name="test-team", team_members=[TeamMemberSpec(role="developer", count=1)])

        result = create_team(tmux, request)

        assert not result.success
        assert result.error_message is not None
        assert "Failed to start Claude" in result.error_message

    def test_create_team_with_metadata(self) -> None:
        """Test create_team properly tracks team metadata."""
        tmux = Mock(spec=TMUXManager)
        tmux.has_session.return_value = False
        tmux.create_session.return_value = True
        tmux.send_keys.return_value = True

        request = CreateTeamRequest(
            team_name="metadata-team",
            team_members=[TeamMemberSpec(role="pm", count=1)],
            project_path="/test/path",
            coordination_strategy="hub_and_spoke",
        )

        result = create_team(tmux, request)

        assert result.success
        assert result.team_metadata is not None
        assert result.team_metadata["team_name"] == "metadata-team"
        assert result.team_metadata["project_path"] == "/test/path"
        assert result.team_metadata["coordination_strategy"] == "hub_and_spoke"
        assert result.team_metadata["total_agents"] == 1
        assert "created_at" in result.team_metadata

    def test_create_team_exception_handling(self) -> None:
        """Test create_team handles unexpected exceptions."""
        tmux = Mock(spec=TMUXManager)
        tmux.has_session.side_effect = Exception("Unexpected error")

        request = CreateTeamRequest(team_name="test-team", team_members=[TeamMemberSpec(role="developer", count=1)])

        result = create_team(tmux, request)

        assert not result.success
        assert result.error_message is not None
        assert "Unexpected error during team creation" in result.error_message
        assert "Unexpected error" in result.error_message

    @pytest.mark.parametrize(
        "role",
        ["pm", "developer", "qa", "devops", "reviewer", "researcher", "docs"],
    )
    def test_create_team_all_valid_roles(self, role: str) -> None:
        """Test create_team accepts all valid agent roles."""
        tmux = Mock(spec=TMUXManager)
        tmux.has_session.return_value = False
        tmux.create_session.return_value = True
        tmux.send_keys.return_value = True

        request = CreateTeamRequest(team_name="test-team", team_members=[TeamMemberSpec(role=role, count=1)])

        result = create_team(tmux, request)

        assert result.success
        assert len(result.created_agents) == 1
        assert result.created_agents[0]["role"] == role

    def test_create_team_coordination_strategies(self) -> None:
        """Test create_team accepts all valid coordination strategies."""
        tmux = Mock(spec=TMUXManager)
        tmux.has_session.return_value = False
        tmux.create_session.return_value = True
        tmux.send_keys.return_value = True

        strategies = ["hub_and_spoke", "peer_to_peer", "hierarchical"]

        for strategy in strategies:
            request = CreateTeamRequest(
                team_name=f"team-{strategy}",
                team_members=[TeamMemberSpec(role="developer", count=1)],
                coordination_strategy=strategy,
            )

            result = create_team(tmux, request)

            assert result.success
            assert result.team_metadata["coordination_strategy"] == strategy

    def test_create_team_edge_case_maximum_agents(self) -> None:
        """Test create_team with exactly maximum number of agents."""
        tmux = Mock(spec=TMUXManager)
        tmux.has_session.return_value = False
        tmux.create_session.return_value = True
        tmux.create_window.return_value = True
        tmux.send_keys.return_value = True

        request = CreateTeamRequest(
            team_name="max-team", team_members=[TeamMemberSpec(role="developer", count=20)]  # Max allowed
        )

        result = create_team(tmux, request)

        assert result.success
        assert len(result.created_agents) == 20
        assert result.team_metadata["total_agents"] == 20

    def test_create_team_duplicate_custom_sessions(self) -> None:
        """Test create_team handles duplicate custom session names."""
        tmux = Mock(spec=TMUXManager)
        tmux.has_session.return_value = False
        tmux.create_session.return_value = True
        tmux.create_window.return_value = True
        tmux.send_keys.return_value = True

        request = CreateTeamRequest(
            team_name="dup-session-team",
            team_members=[
                TeamMemberSpec(role="pm", count=1, custom_session="shared-session"),
                TeamMemberSpec(role="developer", count=1, custom_session="shared-session"),
            ],
        )

        result = create_team(tmux, request)

        # Should succeed - both agents can share the same session
        assert result.success
        assert len(result.created_agents) == 2
        assert all(agent["session"] == "shared-session" for agent in result.created_agents)

    def test_create_team_partial_failure_recovery(self) -> None:
        """Test create_team handles partial failures gracefully."""
        tmux = Mock(spec=TMUXManager)

        # Mock has_session to check different sessions
        def mock_has_session(session_name):
            return False  # No sessions exist initially

        tmux.has_session.side_effect = mock_has_session

        # First session creation succeeds, second fails, third not reached
        tmux.create_session.side_effect = [True, False]
        tmux.send_keys.return_value = True

        request = CreateTeamRequest(
            team_name="partial-fail-team",
            team_members=[
                TeamMemberSpec(role="pm", count=1, custom_session="pm-session"),
                TeamMemberSpec(role="developer", count=1, custom_session="dev-session"),
            ],
        )

        result = create_team(tmux, request)

        # Should report partial failure
        assert not result.success
        # Should have created first agent before failing on second
        assert len(result.created_agents) == 1
        assert result.created_agents[0]["role"] == "pm"
        assert result.error_message is not None
        assert "Failed to create session 'dev-session'" in result.error_message

    def test_create_team_metadata_persistence(self) -> None:
        """Test create_team metadata is properly structured for persistence."""
        tmux = Mock(spec=TMUXManager)
        tmux.has_session.return_value = False
        tmux.create_session.return_value = True
        tmux.send_keys.return_value = True

        request = CreateTeamRequest(
            team_name="persist-team",
            team_members=[
                TeamMemberSpec(role="pm", count=1, briefing="Project lead"),
                TeamMemberSpec(role="developer", count=2, briefing="Dev team"),
            ],
            project_path="/workspace/project",
            coordination_strategy="hub_and_spoke",
        )

        result = create_team(tmux, request)

        assert result.success
        metadata = result.team_metadata

        # Required metadata fields
        assert "team_name" in metadata
        assert "project_path" in metadata
        assert "coordination_strategy" in metadata
        assert "total_agents" in metadata
        assert "created_at" in metadata
        assert "agent_roles" in metadata

        # Validate metadata content
        assert metadata["total_agents"] == 3
        assert metadata["agent_roles"]["pm"] == 1
        assert metadata["agent_roles"]["developer"] == 2

    def test_create_team_validates_coordination_strategy(self) -> None:
        """Test create_team validates coordination strategy."""
        tmux = Mock(spec=TMUXManager)
        request = CreateTeamRequest(
            team_name="test-team",
            team_members=[TeamMemberSpec(role="developer", count=1)],
            coordination_strategy="invalid_strategy",
        )

        result = create_team(tmux, request)

        assert not result.success
        assert result.error_message is not None
        assert "Invalid coordination strategy" in result.error_message

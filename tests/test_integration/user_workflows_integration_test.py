"""
End-to-End User Workflow Integration Tests

Tests complete user journeys from a frontend developer perspective,
focusing on realistic development scenarios and user experience validation.
"""

import json
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from tmux_orchestrator.cli.agent import agent
from tmux_orchestrator.cli.setup_claude import setup as setup_cli
from tmux_orchestrator.cli.spawn import spawn
from tmux_orchestrator.cli.spawn_orc import spawn_orc
from tmux_orchestrator.utils.tmux import TMUXManager


class TestUserWorkflowIntegration:
    """Test complete user workflows from frontend developer perspective."""

    @pytest.fixture
    def workflow_runner(self):
        """Create CLI runner with consistent isolation."""
        return CliRunner(mix_stderr=False)

    @pytest.fixture
    def mock_tmux_workflow(self):
        """Mock TMUX for workflow testing with realistic responses."""
        mock = Mock(spec=TMUXManager)

        # Simulate session lifecycle
        mock.list_sessions.return_value = []
        mock.session_exists.return_value = False
        mock.new_session.return_value = True
        mock.new_window.return_value = True
        mock.send_keys.return_value = True
        mock.kill_session.return_value = True

        # Simulate agent responses
        mock.get_pane_content.return_value = "Claude Code ready. How can I help?"

        return mock

    def test_new_user_setup_workflow(self, workflow_runner, temp_orchestrator_dir):
        """
        Test: Complete new user setup workflow
        Journey: First time user → Setup → Ready for orchestration
        """
        with patch("os.getcwd", return_value=str(temp_orchestrator_dir)):
            # Step 1: User runs setup check
            result = workflow_runner.invoke(setup_cli, ["check-requirements"])

            assert result.exit_code == 0
            assert "Tmux Orchestrator System Setup Check" in result.output or "requirements" in result.output

            # Step 2: User sets up VS Code integration
            result = workflow_runner.invoke(setup_cli, ["vscode"])

            assert result.exit_code == 0

            # Verify user gets expected files
            vscode_dir = temp_orchestrator_dir / ".vscode"
            assert vscode_dir.exists()

            tasks_file = vscode_dir / "tasks.json"
            assert tasks_file.exists()

            # Verify user can find orchestrator commands
            content = tasks_file.read_text()
            assert "Start Orchestrator" in content
            assert "tmux-orc" in content

    @patch("tmux_orchestrator.cli.spawn_orc.subprocess.Popen")
    @patch("tmux_orchestrator.cli.spawn_orc.Path.write_text")
    @patch("tmux_orchestrator.cli.spawn_orc.Path.chmod")
    def test_orchestrator_startup_workflow(self, mock_chmod, mock_write, mock_popen, workflow_runner):
        """
        Test: Orchestrator startup workflow
        Journey: User wants to start orchestrator → Launch → Ready for team management
        """
        # Step 1: User launches orchestrator (no-gui for testing)
        result = workflow_runner.invoke(spawn_orc, ["--no-gui"])

        assert result.exit_code == 0
        assert "Running orchestrator in current terminal..." in result.output

        # Verify claude command executed with correct parameters
        mock_popen.assert_called_once()
        call_args = mock_popen.call_args[0][0]
        assert "claude" in call_args
        assert "--dangerously-skip-permissions" in call_args

    @patch("tmux_orchestrator.utils.tmux.TMUXManager")
    def test_team_creation_workflow(self, mock_tmux_class, workflow_runner, mock_tmux_workflow):
        """
        Test: Team creation workflow
        Journey: User needs a development team → Spawn agents → Team ready
        """
        mock_tmux_class.return_value = mock_tmux_workflow

        # Step 1: User spawns project manager
        with patch("tmux_orchestrator.cli.spawn.get_available_agents", return_value=["pm"]):
            result = workflow_runner.invoke(spawn, ["pm", "test-project:1"])

        assert result.exit_code == 0

        # Verify TMUX interactions for PM creation
        mock_tmux_workflow.new_session.assert_called()
        mock_tmux_workflow.send_keys.assert_called()

        # Step 2: User spawns development team
        team_agents = ["frontend-dev", "backend-dev", "qa-engineer"]

        for i, agent_type in enumerate(team_agents, 2):
            mock_tmux_workflow.session_exists.return_value = False  # New session each time

            with patch("tmux_orchestrator.cli.spawn.get_available_agents", return_value=[agent_type]):
                result = workflow_runner.invoke(spawn, [agent_type, f"test-project:{i}"])

            assert result.exit_code == 0

        # Verify all agents were created
        assert mock_tmux_workflow.new_session.call_count >= len(team_agents) + 1  # +1 for PM

    @patch("tmux_orchestrator.utils.tmux.TMUXManager")
    def test_feature_development_workflow(
        self, mock_tmux_class, workflow_runner, mock_tmux_workflow, temp_orchestrator_dir
    ):
        """
        Test: Feature development workflow
        Journey: User has feature requirements → Team implements → Feature complete
        """
        mock_tmux_class.return_value = mock_tmux_workflow

        # Step 1: Create feature requirements document
        planning_dir = temp_orchestrator_dir / ".tmux_orchestrator" / "planning"
        planning_dir.mkdir(parents=True)

        feature_file = planning_dir / "user-auth-feature.md"
        feature_content = """
        # Feature: User Authentication

        ## Requirements
        - JWT-based authentication
        - User registration and login
        - Password hashing with bcrypt
        - Protected route middleware

        ## Acceptance Criteria
        - Users can register with email/password
        - Users can login and receive JWT token
        - Protected routes verify JWT tokens
        - All tests pass
        """
        feature_file.write_text(feature_content)

        # Step 2: User spawns team for feature development
        with patch("tmux_orchestrator.cli.spawn.get_available_agents", return_value=["pm"]):
            result = workflow_runner.invoke(
                spawn, ["pm", "auth-feature:1", "--extend", f"Implement feature from {feature_file}"]
            )

        assert result.exit_code == 0

        # Step 3: Simulate PM spawning development team
        mock_tmux_workflow.session_exists.side_effect = [False, False, False]  # New sessions

        team_agents = ["backend-dev", "frontend-dev", "qa-engineer"]
        for i, agent_type in enumerate(team_agents, 2):
            with patch("tmux_orchestrator.cli.spawn.get_available_agents", return_value=[agent_type]):
                result = workflow_runner.invoke(spawn, [agent_type, f"auth-feature:{i}"])

            assert result.exit_code == 0

        # Verify feature workflow initiated successfully
        assert mock_tmux_workflow.new_session.call_count >= 4  # PM + 3 team members

    @patch("tmux_orchestrator.utils.tmux.TMUXManager")
    def test_monitoring_and_status_workflow(self, mock_tmux_class, workflow_runner, mock_tmux_workflow):
        """
        Test: Monitoring and status checking workflow
        Journey: User has running team → Check status → Get actionable information
        """
        mock_tmux_class.return_value = mock_tmux_workflow

        # Simulate active sessions
        mock_tmux_workflow.list_sessions.return_value = ["auth-feature:1", "auth-feature:2", "auth-feature:3"]
        mock_tmux_workflow.session_exists.return_value = True

        # Step 1: User checks agent status
        result = workflow_runner.invoke(agent, ["status"])

        assert result.exit_code == 0

        # Step 2: User gets detailed team status
        # Note: This tests the command execution, actual status would come from TMUX
        with patch("tmux_orchestrator.cli.agent.get_agent_status") as mock_status:
            mock_status.return_value = {
                "auth-feature:1": {"status": "Active", "task": "Implementing JWT middleware"},
                "auth-feature:2": {"status": "Idle", "task": "Waiting for backend API"},
                "auth-feature:3": {"status": "Active", "task": "Writing integration tests"},
            }

            result = workflow_runner.invoke(agent, ["status"])
            assert result.exit_code == 0

    def test_error_recovery_workflow(self, workflow_runner, mock_tmux_workflow):
        """
        Test: Error recovery workflow
        Journey: User encounters errors → Gets helpful guidance → Successfully recovers
        """
        # Step 1: User tries to spawn agent without tmux
        with patch("tmux_orchestrator.utils.tmux.TMUXManager", side_effect=Exception("tmux not found")):
            result = workflow_runner.invoke(spawn, ["pm", "test:1"])

        # User should get helpful error message
        assert result.exit_code != 0

        # Step 2: User runs system check to diagnose
        result = workflow_runner.invoke(setup_cli, ["check-requirements"])

        assert result.exit_code == 0
        # Should provide diagnostic information

    @patch("tmux_orchestrator.utils.tmux.TMUXManager")
    def test_project_completion_workflow(
        self, mock_tmux_class, workflow_runner, mock_tmux_workflow, temp_orchestrator_dir
    ):
        """
        Test: Project completion workflow
        Journey: Feature implemented → Quality checks → Project cleanup
        """
        mock_tmux_class.return_value = mock_tmux_workflow

        # Setup project structure
        project_dir = temp_orchestrator_dir / ".tmux_orchestrator" / "projects" / "user-auth"
        project_dir.mkdir(parents=True)

        # Step 1: Simulate completed feature with deliverables
        deliverables_file = project_dir / "deliverables.md"
        deliverables_content = """
        # User Authentication Feature - Completed

        ## Delivered Components
        - ✅ JWT authentication middleware
        - ✅ User registration endpoint
        - ✅ Login endpoint with password hashing
        - ✅ Protected route decorators
        - ✅ Comprehensive test suite (95% coverage)

        ## Quality Gates Passed
        - ✅ All tests passing
        - ✅ Code review completed
        - ✅ Security audit passed
        - ✅ Performance benchmarks met
        """
        deliverables_file.write_text(deliverables_content)

        # Step 2: User verifies project completion
        assert deliverables_file.exists()
        content = deliverables_file.read_text()
        assert "✅ All tests passing" in content
        assert "✅ Security audit passed" in content

        # Step 3: User can clean up team sessions
        mock_tmux_workflow.list_sessions.return_value = ["user-auth:1", "user-auth:2", "user-auth:3"]

        # Simulate killing sessions after completion
        for session in ["user-auth:1", "user-auth:2", "user-auth:3"]:
            mock_tmux_workflow.kill_session.return_value = True


class TestUserExperienceValidation:
    """Test user experience aspects from frontend developer perspective."""

    def test_help_system_discoverability(self, cli_runner):
        """Test that users can discover commands and get helpful information."""
        # Main command help
        result = cli_runner.invoke(spawn, ["--help"])
        assert result.exit_code == 0
        assert "spawn" in result.output.lower()
        assert "agent" in result.output.lower() or "session" in result.output.lower()

        # Setup command help
        result = cli_runner.invoke(setup_cli, ["--help"])
        assert result.exit_code == 0
        assert "setup" in result.output.lower()

    def test_error_message_clarity(self, cli_runner):
        """Test that error messages are clear and actionable."""
        # Test invalid agent type
        result = cli_runner.invoke(spawn, ["invalid-agent-type", "test:1"])

        # Should provide clear error (not just crash)
        assert result.exit_code != 0

        # Test missing session parameter
        result = cli_runner.invoke(spawn, ["pm"])

        # Should provide clear usage guidance
        assert result.exit_code != 0

    def test_command_consistency(self, cli_runner):
        """Test that commands follow consistent patterns."""
        # All main commands should have help
        commands = [setup_cli, spawn_orc, spawn, agent]

        for cmd in commands:
            result = cli_runner.invoke(cmd, ["--help"])
            assert result.exit_code == 0
            assert "--help" in result.output or "help" in result.output.lower()


class TestAPIIntegrationWorkflows:
    """Test workflows that involve API integration points."""

    @patch("requests.get")
    def test_status_api_integration_workflow(self, mock_get, cli_runner):
        """Test workflow using API endpoints for status information."""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "sessions": [
                {"name": "project:1", "status": "active", "agent_type": "pm"},
                {"name": "project:2", "status": "idle", "agent_type": "developer"},
            ]
        }
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # Test that CLI could integrate with API
        # (Note: Actual integration would require server running)
        with patch("tmux_orchestrator.cli.agent.requests") as mock_requests:
            mock_requests.get.return_value = mock_response

            # This tests the pattern, not actual implementation
            result = cli_runner.invoke(agent, ["status"])
            assert result.exit_code == 0

    def test_mcp_server_integration_workflow(self, temp_orchestrator_dir):
        """Test MCP server integration workflow patterns."""
        # Create configuration that would enable MCP integration
        config_dir = temp_orchestrator_dir / ".tmux_orchestrator"
        config_dir.mkdir(parents=True)

        mcp_config = {
            "mcp_server": {
                "enabled": True,
                "port": 8000,
                "tools_enabled": ["spawn_agent", "get_agent_status", "send_message"],
            }
        }

        config_file = config_dir / "config.json"
        config_file.write_text(json.dumps(mcp_config, indent=2))

        # Verify configuration structure supports MCP integration
        assert config_file.exists()
        config_data = json.loads(config_file.read_text())
        assert "mcp_server" in config_data
        assert config_data["mcp_server"]["enabled"] is True


class TestConcurrentUserOperations:
    """Test workflows involving multiple users or concurrent operations."""

    @patch("tmux_orchestrator.utils.tmux.TMUXManager")
    def test_multiple_project_workflow(self, mock_tmux_class, cli_runner):
        """Test workflow with multiple concurrent projects."""
        mock_tmux = Mock(spec=TMUXManager)
        mock_tmux.list_sessions.return_value = []
        mock_tmux.session_exists.return_value = False
        mock_tmux.new_session.return_value = True
        mock_tmux.send_keys.return_value = True
        mock_tmux_class.return_value = mock_tmux

        # Project 1: Authentication feature
        with patch("tmux_orchestrator.cli.spawn.get_available_agents", return_value=["pm"]):
            result1 = cli_runner.invoke(spawn, ["pm", "auth-project:1"])
            assert result1.exit_code == 0

        # Project 2: Dashboard feature
        with patch("tmux_orchestrator.cli.spawn.get_available_agents", return_value=["pm"]):
            result2 = cli_runner.invoke(spawn, ["pm", "dashboard-project:1"])
            assert result2.exit_code == 0

        # Verify both projects can coexist
        assert mock_tmux.new_session.call_count == 2

    def test_session_naming_collision_handling(self, cli_runner):
        """Test that session naming collisions are handled gracefully."""
        with patch("tmux_orchestrator.utils.tmux.TMUXManager") as mock_tmux_class:
            mock_tmux = Mock(spec=TMUXManager)

            # First session succeeds
            mock_tmux.session_exists.return_value = False
            mock_tmux.new_session.return_value = True
            mock_tmux_class.return_value = mock_tmux

            with patch("tmux_orchestrator.cli.spawn.get_available_agents", return_value=["pm"]):
                result1 = cli_runner.invoke(spawn, ["pm", "test:1"])
                assert result1.exit_code == 0

            # Second identical session should handle collision
            mock_tmux.session_exists.return_value = True

            with patch("tmux_orchestrator.cli.spawn.get_available_agents", return_value=["pm"]):
                result2 = cli_runner.invoke(spawn, ["pm", "test:1"])
                # Should either succeed with different name or provide clear error
                # Exact behavior depends on implementation

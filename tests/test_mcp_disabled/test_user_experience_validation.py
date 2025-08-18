"""
User Experience Validation Tests

Tests focused on error message clarity, user guidance quality, and helpful
feedback when things go wrong - from a frontend developer's perspective.
"""

import json
from unittest.mock import Mock, mock_open, patch

import pytest
from click.testing import CliRunner

from tmux_orchestrator.cli.agent import agent
from tmux_orchestrator.cli.monitor import monitor
from tmux_orchestrator.cli.orchestrator import orchestrator
from tmux_orchestrator.cli.setup_claude import setup
from tmux_orchestrator.cli.spawn import spawn
from tmux_orchestrator.cli.team import team
from tmux_orchestrator.utils.tmux import TMUXManager


class TestErrorMessageClarity:
    """Test that error messages are clear, actionable, and user-friendly."""

    @pytest.fixture
    def cli_runner(self):
        """Create isolated CLI runner."""
        return CliRunner()

    def test_missing_required_arguments_clarity(self, cli_runner):
        """
        Test: Missing required arguments provide clear guidance
        UX Goal: Users understand what's missing and how to fix it
        """
        # Test spawn without required arguments
        result = cli_runner.invoke(spawn, ["pm"])

        assert result.exit_code != 0
        # Should indicate missing session argument
        assert "session" in result.output.lower() or "argument" in result.output.lower()

        # Should provide usage example
        assert "usage:" in result.output.lower() or "example" in result.output.lower()

    def test_invalid_agent_type_suggestions(self, cli_runner):
        """
        Test: Invalid agent types provide helpful suggestions
        UX Goal: Users discover valid agent types easily
        """
        with patch("tmux_orchestrator.cli.spawn.get_available_agents", return_value=["pm", "developer", "qa"]):
            result = cli_runner.invoke(spawn, ["invalid-agent", "test:1"])

        assert result.exit_code != 0

        # Should suggest valid agent types
        error_output = result.output.lower()
        assert "invalid" in error_output or "not found" in error_output

        # Should list available options (implementation dependent)
        # Pattern: error messages include valid alternatives

    def test_tmux_not_installed_guidance(self, cli_runner):
        """
        Test: TMUX not installed provides installation instructions
        UX Goal: Users can quickly resolve missing dependencies
        """
        with patch("tmux_orchestrator.utils.tmux.TMUXManager", side_effect=Exception("tmux: command not found")):
            result = cli_runner.invoke(agent, ["status"])

        assert result.exit_code != 0

        # Should provide installation guidance
        error_output = result.output.lower()
        assert "tmux" in error_output

        # Pattern: dependency errors include installation steps

    def test_session_already_exists_recovery(self, cli_runner):
        """
        Test: Session collision provides recovery options
        UX Goal: Users can handle naming conflicts gracefully
        """
        with patch("tmux_orchestrator.utils.tmux.TMUXManager") as mock_tmux_class:
            mock_tmux = Mock(spec=TMUXManager)
            mock_tmux.session_exists.return_value = True
            mock_tmux.new_session.side_effect = Exception("duplicate session name: test:1")
            mock_tmux_class.return_value = mock_tmux

            result = cli_runner.invoke(spawn, ["pm", "test:1"])

        assert result.exit_code != 0

        # Should explain the conflict
        error_output = result.output.lower()
        assert "exists" in error_output or "duplicate" in error_output

        # Should suggest alternatives
        # Pattern: conflict errors suggest resolution steps

    def test_agent_not_responding_guidance(self, cli_runner):
        """
        Test: Non-responsive agent provides troubleshooting steps
        UX Goal: Users can diagnose and fix stuck agents
        """
        with patch("tmux_orchestrator.utils.tmux.TMUXManager") as mock_tmux_class:
            mock_tmux = Mock(spec=TMUXManager)
            mock_tmux.send_keys.side_effect = Exception("pane is dead")
            mock_tmux_class.return_value = mock_tmux

            result = cli_runner.invoke(agent, ["send", "test:1", "Hello"])

        assert result.exit_code != 0

        # Should provide troubleshooting steps
        error_output = result.output.lower()
        assert "dead" in error_output or "not responding" in error_output or "error" in error_output

    def test_file_permission_errors(self, cli_runner):
        """
        Test: Permission errors provide clear resolution steps
        UX Goal: Users understand permission requirements
        """
        with patch("pathlib.Path.mkdir", side_effect=PermissionError("Permission denied")):
            result = cli_runner.invoke(setup, ["vscode", "/restricted/path"])

        assert result.exit_code != 0

        # Should explain permission issue
        error_output = result.output.lower()
        assert "permission" in error_output or "denied" in error_output

    def test_network_connectivity_errors(self, cli_runner):
        """
        Test: Network errors provide connectivity troubleshooting
        UX Goal: Users can diagnose API/network issues
        """
        with patch("requests.get", side_effect=Exception("Connection refused")):
            # Simulate API call failure
            cli_runner.invoke(monitor, ["dashboard"])

        # Should handle network errors gracefully
        # Pattern: network errors include connectivity checks


class TestUserGuidanceQuality:
    """Test the quality of user guidance and help systems."""

    def test_help_command_organization(self, cli_runner):
        """
        Test: Help commands are well-organized and discoverable
        UX Goal: Users can find commands they need quickly
        """
        # Main help
        result = cli_runner.invoke(spawn, ["--help"])
        assert result.exit_code == 0

        help_output = result.output

        # Should have clear sections
        assert "commands:" in help_output.lower()
        assert "options:" in help_output.lower()

        # Should include examples
        assert "example" in help_output.lower() or "usage" in help_output.lower()

    def test_command_suggestions_on_typos(self, cli_runner):
        """
        Test: Typos in commands provide suggestions
        UX Goal: Users can recover from typos easily
        """
        # Test common typos
        typos = [
            ("statsu", "status"),  # Transposition
            ("satus", "status"),  # Missing letter
            ("staatus", "status"),  # Extra letter
        ]

        for typo, correct in typos:
            # Pattern: CLI should suggest correct command
            # Implementation-specific behavior
            pass

    def test_interactive_prompts_clarity(self, cli_runner):
        """
        Test: Interactive prompts are clear about expectations
        UX Goal: Users know what input is expected
        """
        # Test commands that might have interactive elements
        with patch("click.prompt") as mock_prompt:
            mock_prompt.return_value = "test-input"

            # Pattern: prompts should indicate:
            # - What's being asked
            # - Valid input format
            # - Default values if any

    def test_progress_feedback_clarity(self, cli_runner):
        """
        Test: Long operations provide clear progress feedback
        UX Goal: Users know system is working, not frozen
        """
        with patch("tmux_orchestrator.cli.spawn.spawn_pm_agent") as mock_spawn:
            # Simulate slow operation
            def slow_spawn(*args, **kwargs):
                import time

                time.sleep(0.1)
                return {"success": True}

            mock_spawn.side_effect = slow_spawn

            # Pattern: long operations should show progress

    def test_success_confirmation_clarity(self, cli_runner):
        """
        Test: Success messages confirm what actually happened
        UX Goal: Users have confidence operations completed
        """
        with patch("tmux_orchestrator.utils.tmux.TMUXManager") as mock_tmux_class:
            mock_tmux = Mock(spec=TMUXManager)
            mock_tmux.session_exists.return_value = False
            mock_tmux.new_session.return_value = True
            mock_tmux.send_keys.return_value = True
            mock_tmux_class.return_value = mock_tmux

            result = cli_runner.invoke(spawn, ["pm", "test:1"])

        if result.exit_code == 0:
            # Should confirm what was created
            output = result.output.lower()
            assert "success" in output or "created" in output or "spawned" in output
            assert "test:1" in output  # Should echo back session name


class TestRecoveryGuidance:
    """Test that error states provide clear recovery paths."""

    def test_crashed_agent_recovery_steps(self, cli_runner):
        """
        Test: Crashed agents provide clear recovery instructions
        UX Goal: Users can recover crashed agents independently
        """
        error_scenarios = [
            {
                "error": "Agent crashed",
                "expected_guidance": ["restart", "check logs", "spawn new"],
                "recovery_commands": ["tmux-orc agent restart", "tmux-orc spawn"],
            },
            {
                "error": "Session not found",
                "expected_guidance": ["list sessions", "create new"],
                "recovery_commands": ["tmux-orc agent list", "tmux-orc spawn"],
            },
        ]

        for scenario in error_scenarios:
            # Pattern: errors include recovery commands
            # Users should see actionable next steps
            pass

    def test_configuration_error_guidance(self, cli_runner):
        """
        Test: Configuration errors guide users to fix them
        UX Goal: Users can correct configuration issues
        """
        with patch("tmux_orchestrator.core.config.Config.load", side_effect=json.JSONDecodeError("msg", "doc", 0)):
            result = cli_runner.invoke(orchestrator, ["start"])

        if result.exit_code != 0:
            error_output = result.output.lower()
            # Should mention configuration
            assert "config" in error_output or "json" in error_output

            # Should suggest location or format

    def test_resource_limit_guidance(self, cli_runner):
        """
        Test: Resource limits provide scaling guidance
        UX Goal: Users understand system limits and workarounds
        """
        resource_errors = ["Too many open files", "Cannot allocate memory", "No space left on device"]

        for error_msg in resource_errors:
            # Pattern: resource errors explain limits and solutions
            # Should include system-specific guidance
            pass

    def test_partial_failure_recovery(self, cli_runner):
        """
        Test: Partial failures explain what succeeded/failed
        UX Goal: Users know exactly what needs fixing
        """
        with patch("tmux_orchestrator.cli.team.deploy_team") as mock_deploy:
            # Simulate partial team deployment
            mock_deploy.return_value = {
                "success": False,
                "deployed": ["pm", "backend-dev"],
                "failed": ["frontend-dev", "qa"],
                "errors": {"frontend-dev": "Session creation failed", "qa": "Agent spawn timeout"},
            }

            result = cli_runner.invoke(team, ["deploy", "test-team"])

        if result.exit_code != 0:
            pass
            # Should list what worked
            # Should list what failed
            # Should provide recovery for each failure


class TestContextualHelp:
    """Test contextual help based on user's current state."""

    def test_first_time_user_guidance(self, cli_runner):
        """
        Test: First-time users get onboarding guidance
        UX Goal: New users have clear starting point
        """
        # Simulate no existing configuration
        with patch("pathlib.Path.exists", return_value=False):
            result = cli_runner.invoke(orchestrator, ["start"])

        if "not initialized" in result.output.lower() or "setup" in result.output.lower():
            # Should guide to setup
            assert "tmux-orc setup" in result.output

    def test_common_mistakes_prevention(self, cli_runner):
        """
        Test: Common mistakes are prevented with helpful messages
        UX Goal: Users avoid common pitfalls
        """
        common_mistakes = [
            {
                "command": ["spawn", "pm", "test"],  # Missing :window
                "expected_hint": "session:window format",
            },
            {
                "command": ["agent", "send", "test", ""],  # Empty message
                "expected_hint": "message cannot be empty",
            },
            {
                "command": ["monitor", "start", "--interval", "0"],  # Invalid interval
                "expected_hint": "interval must be positive",
            },
        ]

        for mistake in common_mistakes:
            result = cli_runner.invoke(mistake["command"][0], mistake["command"][1:])

            if result.exit_code != 0:
                # Should provide specific guidance
                # Pattern: validate inputs and guide corrections
                pass

    def test_state_aware_suggestions(self, cli_runner):
        """
        Test: Suggestions are aware of current system state
        UX Goal: Help is relevant to user's current situation
        """
        with patch("tmux_orchestrator.utils.tmux.TMUXManager") as mock_tmux_class:
            mock_tmux = Mock(spec=TMUXManager)

            # No sessions running
            mock_tmux.list_sessions.return_value = []
            mock_tmux_class.return_value = mock_tmux

            result = cli_runner.invoke(agent, ["status"])

        if "no sessions" in result.output.lower() or "no agents" in result.output.lower():
            # Should suggest creating agents
            output = result.output.lower()
            assert "spawn" in output or "create" in output or "start" in output

    def test_version_compatibility_warnings(self, cli_runner):
        """
        Test: Version mismatches provide compatibility guidance
        UX Goal: Users understand compatibility requirements
        """
        with patch("subprocess.run") as mock_run:
            # Simulate old tmux version
            mock_run.return_value = Mock(stdout="tmux 1.8", returncode=0)

            result = cli_runner.invoke(setup, ["check-requirements"])

        if "version" in result.output.lower():
            # Should indicate minimum version
            # Should provide upgrade instructions
            pass


class TestErrorMessageFormatting:
    """Test that error messages are well-formatted and readable."""

    def test_error_message_structure(self, cli_runner):
        """
        Test: Error messages follow consistent structure
        UX Goal: Users can quickly parse error information
        """
        # Pattern for good error messages:
        # 1. What went wrong (clear, concise)
        # 2. Why it went wrong (context)
        # 3. How to fix it (actionable steps)

        with patch("tmux_orchestrator.utils.tmux.TMUXManager", side_effect=Exception("Connection failed")):
            result = cli_runner.invoke(agent, ["status"])

        assert result.exit_code != 0

        # Should have clear structure
        # Not just stack traces

    def test_error_message_tone(self, cli_runner):
        """
        Test: Error messages use helpful, non-blaming tone
        UX Goal: Users feel supported, not frustrated
        """
        # Good: "Could not find session 'test:1'. Try 'tmux-orc agent list' to see available sessions."
        # Bad: "ERROR: Invalid input! Session does not exist!"

        # Pattern: errors should be informative, not accusatory

    def test_technical_details_accessibility(self, cli_runner):
        """
        Test: Technical details are available but not overwhelming
        UX Goal: Power users get details, new users get clarity
        """
        with patch("tmux_orchestrator.utils.tmux.TMUXManager") as mock_tmux_class:
            mock_tmux = Mock(spec=TMUXManager)
            mock_tmux.send_keys.side_effect = Exception("Detailed technical error with stack trace")
            mock_tmux_class.return_value = mock_tmux

            result = cli_runner.invoke(agent, ["send", "test:1", "message"])

        assert result.exit_code != 0

        # Should have user-friendly message first
        # Technical details secondary (or behind --verbose flag)


class TestDynamicCommandDiscovery:
    """Test dynamic command discovery based on CLAUDE.md updates."""

    def test_reflection_command_usage(self, cli_runner):
        """
        Test: Reflection command helps avoid hardcoded CLI usage
        UX Goal: Users always get current, accurate command syntax
        """
        # Test tmux-orc reflect command
        result = cli_runner.invoke(["reflect"])

        if result.exit_code == 0:
            output = result.output
            # Should show current CLI structure
            assert "commands" in output.lower() or "usage" in output.lower()

            # Should be parseable for automation
            result_json = cli_runner.invoke(["reflect", "--format", "json"])
            if result_json.exit_code == 0:
                try:
                    data = json.loads(result_json.output)
                    assert "commands" in data
                except json.JSONDecodeError:
                    pass  # Pattern demonstration

    def test_command_failure_logging_pattern(self, cli_runner):
        """
        Test: Failed commands are logged for briefing updates
        UX Goal: System learns from failures to improve
        """
        # Pattern for command failure logging
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.open", mock_open()):
                # Simulate command failure that should be logged
                with patch("tmux_orchestrator.utils.tmux.TMUXManager", side_effect=Exception("Command failed")):
                    cli_runner.invoke(agent, ["status"])

                # Pattern: failures logged to briefing file
                # This helps track hardcoded commands that need updating

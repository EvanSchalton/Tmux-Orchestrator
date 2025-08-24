"""
Focused tests for the 5 specific MCP server fixes.

This test suite validates each of the 5 critical fixes implemented
to achieve 100% CLI parity:

1. Empty kwargs handling - Default actions for simple commands
2. Multi-word message parsing - Proper handling of args arrays
3. Force flag for interactive commands - Automatic --force addition
4. Selective JSON flag logic - Only add --json when supported
5. Daemon command detection - Non-blocking execution for long-running commands
"""

from unittest.mock import Mock, patch

import pytest

# Import mock configuration first
from conftest_mcp import EnhancedCLIToMCPServer


class TestFix1EmptyKwargsHandling:
    """Test Fix #1: Empty kwargs handling for simple commands."""

    @pytest.fixture
    def mcp_server(self):
        """Create MCP server with various command groups."""
        server = EnhancedCLIToMCPServer("test-server")
        server.hierarchical_groups = {
            "agent": ["list", "status", "deploy"],
            "team": ["status", "deploy", "broadcast"],
            "monitor": ["status", "dashboard"],
        }
        return server

    @pytest.mark.asyncio
    async def test_empty_kwargs_defaults_to_list(self, mcp_server):
        """Test that empty kwargs defaults to 'list' action when available."""
        tool = mcp_server._create_hierarchical_tool_function("agent", ["list", "status", "deploy"])

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="[]", stderr="")

            # Test with completely empty kwargs
            result = await tool(kwargs="")

            assert result["success"]
            assert result["action"] == "list"

            # Verify the command executed
            cmd_args = mock_run.call_args[0][0]
            assert cmd_args[:3] == ["tmux-orc", "agent", "list"]

    @pytest.mark.asyncio
    async def test_empty_kwargs_defaults_to_status(self, mcp_server):
        """Test that empty kwargs defaults to 'status' when no 'list' available."""
        tool = mcp_server._create_hierarchical_tool_function("monitor", ["status", "dashboard"])

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout='{"status": "running"}', stderr="")

            result = await tool(kwargs="")

            assert result["success"]
            assert result["action"] == "status"

    @pytest.mark.asyncio
    async def test_empty_kwargs_for_direct_commands(self, mcp_server):
        """Test empty kwargs for direct commands like 'list', 'status', 'reflect'."""
        # These are direct commands that should execute without subcommands
        for cmd_name in ["list", "status", "reflect"]:
            tool = mcp_server._create_hierarchical_tool_function(cmd_name, [])

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="{}", stderr="")

                result = await tool(kwargs="")

                assert result["success"]
                assert result["action"] == "execute"

                # Should execute the command directly
                cmd_args = mock_run.call_args[0][0]
                assert cmd_args[0:2] == ["tmux-orc", cmd_name]

    @pytest.mark.asyncio
    async def test_empty_kwargs_no_default_shows_error(self, mcp_server):
        """Test empty kwargs with no reasonable default shows helpful error."""
        tool = mcp_server._create_hierarchical_tool_function("spawn", ["agent", "pm", "orchestrator"])

        result = await tool(kwargs="")

        assert not result["success"]
        assert "Invalid kwargs format" in result["error"]
        assert "kwargs_examples" in result
        assert result["valid_actions"] == ["agent", "pm", "orchestrator"]


class TestFix2MultiWordMessageParsing:
    """Test Fix #2: Multi-word message parsing in args arrays."""

    @pytest.fixture
    def mcp_server(self):
        """Create MCP server instance."""
        return EnhancedCLIToMCPServer("test-server")

    @pytest.mark.asyncio
    async def test_parse_simple_multiword_message(self, mcp_server):
        """Test parsing simple multi-word messages."""
        result = mcp_server._parse_kwargs_string('action=send args=["This is a multi-word message"]')

        assert result == {"action": "send", "args": ["This is a multi-word message"]}

    @pytest.mark.asyncio
    async def test_parse_multiple_multiword_args(self, mcp_server):
        """Test parsing multiple multi-word arguments."""
        result = mcp_server._parse_kwargs_string('action=broadcast args=["First message here", "Second message there"]')

        assert result == {"action": "broadcast", "args": ["First message here", "Second message there"]}

    @pytest.mark.asyncio
    async def test_parse_messages_with_special_chars(self, mcp_server):
        """Test parsing messages with special characters."""
        test_cases = [
            # Quotes within messages
            ('action=send args=["He said \\"hello\\" to me"]', {"action": "send", "args": ['He said "hello" to me']}),
            # Apostrophes
            ('action=send args=["It\'s working perfectly!"]', {"action": "send", "args": ["It's working perfectly!"]}),
            # Mixed punctuation
            (
                'action=broadcast args=["Alert: System @ 90% CPU, check now!"]',
                {"action": "broadcast", "args": ["Alert: System @ 90% CPU, check now!"]},
            ),
        ]

        for kwargs_str, expected in test_cases:
            result = mcp_server._parse_kwargs_string(kwargs_str)
            assert result == expected

    @pytest.mark.asyncio
    async def test_multiword_message_execution(self, mcp_server):
        """Test that multi-word messages are properly passed to CLI."""
        tool = mcp_server._create_hierarchical_tool_function("agent", ["send"])

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout='{"sent": true}', stderr="")

            result = await tool(
                kwargs='action=send target=backend:1 args=["Please implement the new authentication system with OAuth2 support"]'
            )

            assert result["success"]

            # Check that the full message was passed as a single argument
            cmd_args = mock_run.call_args[0][0]
            assert "Please implement the new authentication system with OAuth2 support" in cmd_args

            # Ensure it wasn't split into multiple arguments
            message_index = cmd_args.index("Please implement the new authentication system with OAuth2 support")
            assert cmd_args[message_index] == "Please implement the new authentication system with OAuth2 support"


class TestFix3ForceFlag:
    """Test Fix #3: Automatic --force flag for interactive commands."""

    @pytest.fixture
    def mcp_server(self):
        """Create MCP server instance."""
        return EnhancedCLIToMCPServer("test-server")

    @pytest.mark.asyncio
    async def test_force_flag_for_kill_all_commands(self, mcp_server):
        """Test --force flag is added to kill-all commands."""
        # Test orchestrator kill-all
        orch_tool = mcp_server._create_hierarchical_tool_function("orchestrator", ["kill-all"])

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout='{"killed": 5}', stderr="")

            await orch_tool(kwargs="action=kill-all")

            cmd_args = mock_run.call_args[0][0]
            assert "--force" in cmd_args
            assert cmd_args == ["tmux-orc", "orchestrator", "kill-all", "--force"]

        # Test agent kill-all
        agent_tool = mcp_server._create_hierarchical_tool_function("agent", ["kill-all"])

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout='{"killed": 3}', stderr="")

            await agent_tool(kwargs="action=kill-all")

            cmd_args = mock_run.call_args[0][0]
            assert "--force" in cmd_args

    @pytest.mark.asyncio
    async def test_force_flag_for_setup_all(self, mcp_server):
        """Test --force flag is added to setup all command."""
        setup_tool = mcp_server._create_hierarchical_tool_function("setup", ["all", "status"])

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout='{"setup": "complete"}', stderr="")

            await setup_tool(kwargs="action=all")

            cmd_args = mock_run.call_args[0][0]
            assert "--force" in cmd_args

    @pytest.mark.asyncio
    async def test_no_force_flag_for_normal_commands(self, mcp_server):
        """Test that normal commands don't get --force flag."""
        agent_tool = mcp_server._create_hierarchical_tool_function("agent", ["list", "status"])

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="[]", stderr="")

            await agent_tool(kwargs="action=list")

            cmd_args = mock_run.call_args[0][0]
            assert "--force" not in cmd_args

    @pytest.mark.asyncio
    async def test_force_flag_not_duplicated(self, mcp_server):
        """Test that --force flag isn't added if already present."""
        agent_tool = mcp_server._create_hierarchical_tool_function("agent", ["kill"])

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout='{"killed": 1}', stderr="")

            # Manually add --force in options
            await agent_tool(kwargs='action=kill target=test:1 options={"force": true}')

            cmd_args = mock_run.call_args[0][0]
            # Should have exactly one --force
            assert cmd_args.count("--force") == 1


class TestFix4SelectiveJsonFlag:
    """Test Fix #4: Selective JSON flag logic."""

    @pytest.fixture
    def mcp_server(self):
        """Create MCP server instance."""
        return EnhancedCLIToMCPServer("test-server")

    @pytest.mark.asyncio
    async def test_json_flag_for_supported_commands(self, mcp_server):
        """Test JSON flag is added for commands that support it."""
        json_supporting_commands = [
            ("agent", ["list", "status"], "list"),
            ("team", ["status", "deploy"], "status"),
            ("spawn", ["agent", "pm"], "agent"),
        ]

        for group, actions, action in json_supporting_commands:
            tool = mcp_server._create_hierarchical_tool_function(group, actions)

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="{}", stderr="")

                await tool(kwargs=f"action={action} target=test:1")

                cmd_args = mock_run.call_args[0][0]
                assert "--json" in cmd_args, f"JSON flag missing for {group} {action}"

    @pytest.mark.asyncio
    async def test_no_json_flag_for_unsupported_commands(self, mcp_server):
        """Test JSON flag is NOT added for commands that don't support it."""
        no_json_commands = [
            ("monitor", ["status"], "status"),
            ("daemon", ["start", "stop"], "start"),
            ("context", ["show"], "show"),
            ("setup", ["all"], "all"),
        ]

        for group, actions, action in no_json_commands:
            tool = mcp_server._create_hierarchical_tool_function(group, actions)

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stdout="OK", stderr="")

                await tool(kwargs=f"action={action}")

                cmd_args = mock_run.call_args[0][0]
                assert "--json" not in cmd_args, f"JSON flag incorrectly added for {group} {action}"

    @pytest.mark.asyncio
    async def test_json_flag_not_duplicated(self, mcp_server):
        """Test that JSON flag isn't added if already present."""
        tool = mcp_server._create_hierarchical_tool_function("agent", ["list"])

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="[]", stderr="")

            # Manually add --json in options
            await tool(kwargs='action=list options={"json": true}')

            cmd_args = mock_run.call_args[0][0]
            # Should have exactly one --json
            assert cmd_args.count("--json") == 1


class TestFix5DaemonCommands:
    """Test Fix #5: Daemon command non-blocking execution."""

    @pytest.fixture
    def mcp_server(self):
        """Create MCP server instance."""
        return EnhancedCLIToMCPServer("test-server")

    @pytest.mark.asyncio
    async def test_daemon_command_uses_popen(self, mcp_server):
        """Test daemon commands use Popen for non-blocking execution."""
        daemon_commands = [
            ("recovery", ["start"], "start"),
            ("monitor", ["dashboard"], "dashboard"),
            ("daemon", ["start"], "start"),
            ("server", ["start"], "start"),
        ]

        for group, actions, action in daemon_commands:
            tool = mcp_server._create_hierarchical_tool_function(group, actions)

            with patch("subprocess.Popen") as mock_popen:
                mock_process = Mock()
                mock_process.poll.return_value = None  # Still running
                mock_process.pid = 12345
                mock_popen.return_value = mock_process

                result = await tool(kwargs=f"action={action}")

                assert result["success"]
                assert result["command_type"] == "daemon"
                assert result["pid"] == 12345
                assert "background" in result["note"]

                # Should use Popen, not run
                mock_popen.assert_called_once()

    @pytest.mark.asyncio
    async def test_daemon_command_failure_handling(self, mcp_server):
        """Test handling of daemon commands that fail to start."""
        tool = mcp_server._create_hierarchical_tool_function("monitor", ["dashboard"])

        with patch("subprocess.Popen") as mock_popen:
            mock_process = Mock()
            mock_process.poll.return_value = 1  # Process died immediately
            mock_process.stderr = Mock()
            mock_process.stderr.read.return_value = "Error: Port already in use"
            mock_popen.return_value = mock_process

            result = await tool(kwargs="action=dashboard")

            assert not result["success"]
            assert "failed to start" in result["error"]
            assert "Port already in use" in result["error"]

    @pytest.mark.asyncio
    async def test_non_daemon_commands_use_run(self, mcp_server):
        """Test that non-daemon commands use regular subprocess.run."""
        tool = mcp_server._create_hierarchical_tool_function("agent", ["list"])

        with patch("subprocess.run") as mock_run:
            with patch("subprocess.Popen") as mock_popen:
                mock_run.return_value = Mock(returncode=0, stdout="[]", stderr="")

                await tool(kwargs="action=list")

                # Should use run, not Popen
                mock_run.assert_called_once()
                mock_popen.assert_not_called()

    @pytest.mark.asyncio
    async def test_daemon_command_detachment(self, mcp_server):
        """Test daemon commands are properly detached from parent."""
        tool = mcp_server._create_hierarchical_tool_function("recovery", ["start"])

        with patch("subprocess.Popen") as mock_popen:
            mock_process = Mock()
            mock_process.poll.return_value = None
            mock_process.pid = 54321
            mock_popen.return_value = mock_process

            await tool(kwargs="action=start")

            # Check that start_new_session=True was used for detachment
            call_kwargs = mock_popen.call_args[1]
            assert call_kwargs.get("start_new_session")


class TestIntegrationOfAllFixes:
    """Test integration scenarios combining multiple fixes."""

    @pytest.fixture
    def mcp_server(self):
        """Create MCP server with full configuration."""
        server = EnhancedCLIToMCPServer("test-server")
        server.hierarchical_groups = {
            "agent": ["list", "send", "kill-all"],
            "monitor": ["dashboard", "status"],
            "spawn": ["agent", "pm"],
            "setup": ["all"],
        }
        return server

    @pytest.mark.asyncio
    async def test_complex_command_with_multiple_fixes(self, mcp_server):
        """Test command that requires multiple fixes."""
        # Test agent send with multi-word message and JSON flag
        tool = mcp_server._create_hierarchical_tool_function("agent", ["send", "list"])

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout='{"sent": true}', stderr="")

            # Empty kwargs should default to list with JSON
            result = await tool(kwargs="")

            assert result["success"]
            cmd_args = mock_run.call_args[0][0]
            assert "--json" in cmd_args
            assert cmd_args[2] == "list"

    @pytest.mark.asyncio
    async def test_spawn_with_cli_options_parsing(self, mcp_server):
        """Test spawn command with CLI options in args (Fix #2 advanced)."""
        tool = mcp_server._create_hierarchical_tool_function("spawn", ["pm"])

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout='{"spawned": true}', stderr="")

            # CLI options mixed with positional args
            result = await tool(
                kwargs='action=pm args=["--session", "project-x", "--briefing", "Senior PM for critical project"]'
            )

            assert result["success"]
            cmd_args = mock_run.call_args[0][0]

            # Options should be properly extracted
            assert "--session" in cmd_args
            assert "--briefing" in cmd_args
            # Multi-word briefing should be preserved
            assert "Senior PM for critical project" in cmd_args

    @pytest.mark.asyncio
    async def test_all_fixes_stress_test(self, mcp_server):
        """Stress test combining all 5 fixes in various scenarios."""
        test_scenarios = [
            # Fix 1 + 4: Empty kwargs with JSON support check
            ("agent", ["list"], "", ["tmux-orc", "agent", "list", "--json"]),
            # Fix 2 + 4: Multi-word with JSON
            (
                "agent",
                ["send"],
                'action=send target=test:1 args=["Complex message here"]',
                ["tmux-orc", "agent", "send", "test:1", "Complex message here", "--json"],
            ),
            # Fix 3 + 4: Force flag without JSON
            ("setup", ["all"], "action=all", ["tmux-orc", "setup", "all", "--force"]),
            # Fix 5: Daemon command
            ("monitor", ["dashboard"], "action=dashboard", None),  # Uses Popen
        ]

        for group, actions, kwargs, expected_cmd in test_scenarios:
            tool = mcp_server._create_hierarchical_tool_function(group, actions)

            if expected_cmd:  # Regular command
                with patch("subprocess.run") as mock_run:
                    mock_run.return_value = Mock(returncode=0, stdout="{}", stderr="")

                    result = await tool(kwargs=kwargs)

                    assert result["success"]
                    cmd_args = mock_run.call_args[0][0]
                    assert cmd_args == expected_cmd
            else:  # Daemon command
                with patch("subprocess.Popen") as mock_popen:
                    mock_process = Mock()
                    mock_process.poll.return_value = None
                    mock_process.pid = 99999
                    mock_popen.return_value = mock_process

                    result = await tool(kwargs=kwargs)

                    assert result["command_type"] == "daemon"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

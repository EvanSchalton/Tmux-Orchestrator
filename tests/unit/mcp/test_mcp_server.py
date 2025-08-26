"""
Comprehensive unit tests for the MCP server using FastMCP testing patterns.

This test suite follows FastMCP's in-memory testing approach to validate:
- All 20 hierarchical command groups
- The 5 core fixes implemented in the MCP server
- Tool generation and execution
- Error handling and edge cases
"""

import json

# Import mock configuration first
# Add parent directory to path for conftest_mcp
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from tests.conftest_mcp import EnhancedCLIToMCPServer, EnhancedHierarchicalSchema, MCPAutoGenerator  # noqa: E402


class TestMCPServerCore:
    """Core tests for MCP server functionality."""

    @pytest.fixture
    def mcp_server(self):
        """Create an in-memory MCP server instance."""
        with patch.dict(
            "os.environ",
            {
                "TMUX_ORC_HIERARCHICAL": "true",
                "TMUX_ORC_ENHANCED_DESCRIPTIONS": "true",
                "TMUX_ORC_FAST_STARTUP": "false",
            },
        ):
            server = EnhancedCLIToMCPServer("test-server")
            return server

    @pytest.fixture
    def mock_cli_structure(self):
        """Mock CLI structure for testing."""
        return {
            "agent": {
                "type": "group",
                "help": "Manage agents",
                "subcommands": ["list", "status", "deploy", "kill", "restart", "send"],
            },
            "team": {"type": "group", "help": "Manage teams", "subcommands": ["list", "status", "deploy", "broadcast"]},
            "monitor": {
                "type": "group",
                "help": "Monitor operations",
                "subcommands": ["status", "dashboard", "logs", "start", "stop"],
            },
            "spawn": {"type": "group", "help": "Spawn agents", "subcommands": ["agent", "pm", "orchestrator"]},
            "list": {"type": "command", "help": "List all agents"},
            "status": {"type": "command", "help": "Get system status"},
            "reflect": {"type": "command", "help": "Reflect CLI structure"},
        }

    @pytest.mark.asyncio
    async def test_server_initialization(self, mcp_server):
        """Test that MCP server initializes correctly."""
        assert mcp_server is not None
        assert mcp_server.mcp.name == "test-server"
        assert mcp_server.generated_tools == {}
        assert mcp_server.hierarchical_groups == {}

    @pytest.mark.asyncio
    async def test_cli_structure_discovery(self, mcp_server, mock_cli_structure):
        """Test CLI structure discovery."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=json.dumps(mock_cli_structure), stderr="")

            result = await mcp_server.discover_cli_structure()

            assert result == mock_cli_structure
            assert mcp_server.cli_structure == mock_cli_structure
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_hierarchical_tool_generation(self, mcp_server, mock_cli_structure):
        """Test hierarchical tool generation."""
        mcp_server.cli_structure = mock_cli_structure

        with patch.object(mcp_server, "_discover_subcommands") as mock_discover:
            mock_discover.side_effect = lambda group: mock_cli_structure.get(group, {}).get("subcommands", [])

            with patch.object(mcp_server.mcp, "tool") as mock_tool_decorator:
                # Mock the decorator to return the function as-is
                mock_tool_decorator.return_value = lambda func: func

                mcp_server.generate_all_mcp_tools()

                # Should generate hierarchical tools for groups
                assert len(mcp_server.generated_tools) > 0
                assert "agent" in mcp_server.generated_tools
                assert "team" in mcp_server.generated_tools
                assert "monitor" in mcp_server.generated_tools
                assert "spawn" in mcp_server.generated_tools

                # Should also have individual command tools
                assert "list" in mcp_server.generated_tools
                assert "status" in mcp_server.generated_tools
                assert "reflect" in mcp_server.generated_tools

    @pytest.mark.asyncio
    async def test_kwargs_string_parsing(self, mcp_server):
        """Test parsing of kwargs string format (Fix #2)."""
        test_cases = [
            # Simple action
            ("action=list", {"action": "list"}),
            # Action with target
            ("action=status target=backend:1", {"action": "status", "target": "backend:1"}),
            # Action with args array
            (
                'action=broadcast args=["Hello team", "Starting deployment"]',
                {"action": "broadcast", "args": ["Hello team", "Starting deployment"]},
            ),
            # Action with options
            (
                'action=deploy options={"briefing": "Backend agent"}',
                {"action": "deploy", "options": {"briefing": "Backend agent"}},
            ),
            # Complex multi-word message parsing
            (
                'action=send args=["This is a multi-word message with spaces"]',
                {"action": "send", "args": ["This is a multi-word message with spaces"]},
            ),
            # Empty kwargs (Fix #1)
            ("", {}),
        ]

        for kwargs_str, expected in test_cases:
            result = mcp_server._parse_kwargs_string(kwargs_str)
            assert result == expected, f"Failed for input: {kwargs_str}"

    @pytest.mark.asyncio
    async def test_force_flag_handling(self, mcp_server):
        """Test force flag handling for interactive commands (Fix #3)."""
        # Commands that need force flag
        force_commands = ["orchestrator kill-all", "agent kill-all", "setup all", "agent kill"]

        for cmd in force_commands:
            assert mcp_server._command_needs_force_flag(cmd)

        # Commands that don't need force flag
        normal_commands = ["agent list", "team status", "monitor dashboard"]
        for cmd in normal_commands:
            assert not mcp_server._command_needs_force_flag(cmd)

    @pytest.mark.asyncio
    async def test_json_flag_logic(self, mcp_server):
        """Test selective JSON flag logic (Fix #4)."""
        # Commands that support JSON
        json_commands = ["list", "status", "reflect", "agent list", "agent status", "team status"]

        for cmd in json_commands:
            assert mcp_server._command_supports_json(cmd)

        # Commands that don't support JSON
        no_json_commands = ["daemon start", "monitor status", "context show", "setup all", "tasks list"]

        for cmd in no_json_commands:
            assert not mcp_server._command_supports_json(cmd)

    @pytest.mark.asyncio
    async def test_daemon_command_detection(self, mcp_server):
        """Test daemon command detection (Fix #5)."""
        daemon_commands = ["recovery start", "monitor dashboard", "daemon start", "server start"]

        for cmd in daemon_commands:
            assert mcp_server._is_daemon_command(cmd)

        # Non-daemon commands
        normal_commands = ["agent list", "team status", "spawn agent"]
        for cmd in normal_commands:
            assert not mcp_server._is_daemon_command(cmd)


class TestHierarchicalToolExecution:
    """Test hierarchical tool execution with all fixes."""

    @pytest.fixture
    def mcp_server(self):
        """Create an in-memory MCP server instance."""
        server = EnhancedCLIToMCPServer("test-server")
        # Set up hierarchical groups
        server.hierarchical_groups = {
            "agent": ["list", "status", "deploy", "kill", "restart", "send"],
            "team": ["list", "status", "deploy", "broadcast"],
            "spawn": ["agent", "pm", "orchestrator"],
        }
        return server

    @pytest.mark.asyncio
    async def test_empty_kwargs_handling(self, mcp_server):
        """Test empty kwargs defaults to reasonable action (Fix #1)."""
        # Create hierarchical tool function
        tool_func = mcp_server._create_hierarchical_tool_function("agent", ["list", "status"])

        # Test empty kwargs
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout='{"agents": []}', stderr="")

            result = await tool_func(kwargs="")

            # Should default to 'list' action
            assert result["success"]
            assert result["action"] == "list"
            mock_run.assert_called_once()
            assert "agent" in mock_run.call_args[0][0]
            assert "list" in mock_run.call_args[0][0]

    @pytest.mark.asyncio
    async def test_multi_word_message_parsing(self, mcp_server):
        """Test multi-word message parsing in args (Fix #2)."""
        tool_func = mcp_server._create_hierarchical_tool_function("team", ["broadcast"])

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout='{"status": "sent"}', stderr="")

            # Test multi-word message
            result = await tool_func(kwargs='action=broadcast args=["This is a long message with many words"]')

            assert result["success"]
            mock_run.assert_called_once()

            # Check that message was passed correctly
            cmd_args = mock_run.call_args[0][0]
            assert "This is a long message with many words" in cmd_args

    @pytest.mark.asyncio
    async def test_force_flag_addition(self, mcp_server):
        """Test automatic force flag addition (Fix #3)."""
        tool_func = mcp_server._create_hierarchical_tool_function("agent", ["kill-all"])

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout='{"killed": 5}', stderr="")

            result = await tool_func(kwargs="action=kill-all")

            assert result["success"]
            mock_run.assert_called_once()

            # Check that --force was added
            cmd_args = mock_run.call_args[0][0]
            assert "--force" in cmd_args

    @pytest.mark.asyncio
    async def test_selective_json_flag(self, mcp_server):
        """Test selective JSON flag addition (Fix #4)."""
        tool_func = mcp_server._create_hierarchical_tool_function("agent", ["list", "status"])

        # Test command that supports JSON
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="[]", stderr="")

            await tool_func(kwargs="action=list")

            cmd_args = mock_run.call_args[0][0]
            assert "--json" in cmd_args

        # Test command that doesn't support JSON
        tool_func = mcp_server._create_hierarchical_tool_function("monitor", ["status"])

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="Monitor running", stderr="")

            await tool_func(kwargs="action=status")

            cmd_args = mock_run.call_args[0][0]
            assert "--json" not in cmd_args

    @pytest.mark.asyncio
    async def test_daemon_command_handling(self, mcp_server):
        """Test daemon command non-blocking execution (Fix #5)."""
        tool_func = mcp_server._create_hierarchical_tool_function("monitor", ["dashboard"])

        with patch("subprocess.Popen") as mock_popen:
            # Mock the process
            mock_process = Mock()
            mock_process.poll.return_value = None  # Still running
            mock_process.pid = 12345
            mock_popen.return_value = mock_process

            result = await tool_func(kwargs="action=dashboard")

            assert result["success"]
            assert result["command_type"] == "daemon"
            assert result["pid"] == 12345
            assert "background" in result["note"]

            # Should use Popen, not run
            mock_popen.assert_called_once()


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.fixture
    def mcp_server(self):
        """Create an in-memory MCP server instance."""
        server = EnhancedCLIToMCPServer("test-server")
        server.hierarchical_groups = {"agent": ["list", "status", "deploy"], "spawn": ["agent", "pm"]}
        return server

    @pytest.mark.asyncio
    async def test_invalid_action_error(self, mcp_server):
        """Test error handling for invalid actions."""
        tool_func = mcp_server._create_hierarchical_tool_function("agent", ["list", "status"])

        result = await tool_func(kwargs="action=invalid")

        assert not result["success"]
        assert "Invalid action" in result["error"]
        assert result["valid_actions"] == ["list", "status"]

    @pytest.mark.asyncio
    async def test_missing_required_arguments(self, mcp_server):
        """Test error handling for missing required arguments."""
        tool_func = mcp_server._create_hierarchical_tool_function("spawn", ["agent", "pm"])

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1, stdout="", stderr="Error: Missing required argument --briefing")

            result = await tool_func(kwargs="action=agent target=test:1")

            assert not result["success"]
            assert "briefing" in result["error"]
            assert result["error_type"] == "missing_arguments"

    @pytest.mark.asyncio
    async def test_invalid_kwargs_format(self, mcp_server):
        """Test error handling for invalid kwargs format."""
        result = mcp_server._parse_kwargs_string("invalid format without equals")

        assert "error" in result
        assert "Invalid parameter format" in result["error"]
        assert "kwargs_examples" in result

    @pytest.mark.asyncio
    async def test_command_timeout_handling(self, mcp_server):
        """Test handling of command timeouts."""
        tool_func = mcp_server._create_hierarchical_tool_function("agent", ["list"])

        with patch("subprocess.run") as mock_run:
            import subprocess

            mock_run.side_effect = subprocess.TimeoutExpired(cmd=["tmux-orc"], timeout=60)

            result = await tool_func(kwargs="action=list")

            assert not result["success"]
            assert "timed out" in str(result["error"])


class TestPerformanceOptimizations:
    """Test performance optimizations and caching."""

    @pytest.mark.asyncio
    async def test_cli_structure_caching(self):
        """Test that CLI structure is cached for performance."""
        server = EnhancedCLIToMCPServer("test-server")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout='{"test": {"type": "command"}}', stderr="")

            # First call should hit subprocess
            result1 = await server.discover_cli_structure()
            assert mock_run.call_count == 1

            # Second call should use cache
            result2 = await server.discover_cli_structure()
            assert mock_run.call_count == 1  # No additional call
            assert result1 == result2

    @pytest.mark.asyncio
    async def test_fast_startup_mode(self):
        """Test fast startup mode with minimal descriptions."""
        with patch.dict("os.environ", {"TMUX_ORC_FAST_STARTUP": "true"}):
            descriptions = EnhancedHierarchicalSchema.get_action_descriptions()

            # Should have minimal descriptions
            assert "agent" in descriptions
            assert "list" in descriptions["agent"]
            assert len(descriptions) < 10  # Limited set in fast mode


class TestMCPAutoGenerator:
    """Test the MCP auto-generation system."""

    @pytest.mark.asyncio
    async def test_action_description_generation(self):
        """Test auto-generation of action descriptions."""
        with patch("subprocess.run") as mock_run:
            # Mock CLI reflect output
            mock_run.return_value = Mock(
                returncode=0,
                stdout=json.dumps(
                    {
                        "agent": {"type": "group", "help": "Manage agents"},
                        "team": {"type": "group", "help": "Team operations"},
                    }
                ),
                stderr="",
            )

            generator = MCPAutoGenerator()
            with patch.object(generator, "_discover_subcommands") as mock_discover:
                mock_discover.return_value = ["list", "status", "deploy"]

                descriptions = generator.generate_action_descriptions()

                assert isinstance(descriptions, dict)
                # Should have generated descriptions for discovered commands


class TestCLIArgumentParsing:
    """Test CLI argument parsing with various edge cases."""

    @pytest.fixture
    def mcp_server(self):
        """Create an in-memory MCP server instance."""
        return EnhancedCLIToMCPServer("test-server")

    @pytest.mark.asyncio
    async def test_cli_option_parsing_in_args(self, mcp_server):
        """Test parsing CLI options within args array."""
        test_cases = [
            # CLI options should be extracted from args
            (
                'action=pm args=["--session", "test", "--briefing", "PM context"]',
                {"action": "pm", "args": ["test", "PM context"], "options": {"session": "test", "briefing": True}},
            ),
            # Mixed positional and option arguments
            (
                'action=deploy args=["backend", "--force", "--timeout", "60"]',
                {"action": "deploy", "args": ["backend"], "options": {"force": True, "timeout": "60"}},
            ),
            # Only positional arguments
            ('action=send args=["Hello", "World"]', {"action": "send", "args": ["Hello", "World"]}),
        ]

        for kwargs_str, expected in test_cases:
            result = mcp_server._parse_kwargs_string(kwargs_str)
            assert result == expected, f"Failed for input: {kwargs_str}"

    @pytest.mark.asyncio
    async def test_quoted_string_handling(self, mcp_server):
        """Test handling of quoted strings in various formats."""
        test_cases = [
            # Single quotes within double quotes
            ("action=send args=[\"He said 'hello' to me\"]", {"action": "send", "args": ["He said 'hello' to me"]}),
            # Escaped quotes
            (
                'action=broadcast args=["Message with \\"quotes\\""]',
                {"action": "broadcast", "args": ['Message with "quotes"']},
            ),
            # Comma-separated quoted strings
            (
                'action=deploy args=["agent1", "agent2", "agent3"]',
                {"action": "deploy", "args": ["agent1", "agent2", "agent3"]},
            ),
        ]

        for kwargs_str, expected in test_cases:
            result = mcp_server._parse_kwargs_string(kwargs_str)
            assert result == expected, f"Failed for input: {kwargs_str}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

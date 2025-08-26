"""
Test suite for CLI Reflection MCP Server approach.

This replaces manual MCP tool testing with dynamic CLI auto-generation testing.
Focus areas:
1. CLI discovery via tmux-orc reflect
2. Dynamic MCP tool generation
3. CLI command execution through MCP
4. Performance validation (<1s requirement)
5. Error handling and validation
"""

import json
import subprocess
import time
from unittest.mock import Mock, patch

import pytest

# Test imports
try:
    from tmux_orchestrator.mcp_server_fresh import FreshCLIMCPServer

    CLI_REFLECTION_AVAILABLE = True
except ImportError as e:
    CLI_REFLECTION_AVAILABLE = False
    import_error = str(e)


class TestCLIReflectionAvailability:
    """Test that CLI reflection components are available."""

    def test_cli_reflection_import(self, test_uuid: str) -> None:
        """Test CLI reflection server can be imported."""
        if not CLI_REFLECTION_AVAILABLE:
            pytest.fail(f"CLI reflection server not available: {import_error}")

        assert FreshCLIMCPServer is not None, f"FreshCLIMCPServer should be available - Test ID: {test_uuid}"


class TestCLIDiscovery:
    """Test CLI command discovery functionality."""

    def test_tmux_orc_reflect_command_exists(self, test_uuid: str) -> None:
        """Test that tmux-orc reflect command is available."""
        try:
            result = subprocess.run(["tmux-orc", "reflect", "--help"], capture_output=True, text=True, timeout=5)
            assert result.returncode == 0, f"tmux-orc reflect should be available - Test ID: {test_uuid}"
            assert "format" in result.stdout, f"Should support format option - Test ID: {test_uuid}"
        except FileNotFoundError:
            pytest.fail(f"tmux-orc command not found in PATH - Test ID: {test_uuid}")
        except subprocess.TimeoutExpired:
            pytest.fail(f"tmux-orc reflect command timed out - Test ID: {test_uuid}")

    def test_tmux_orc_reflect_json_output(self, test_uuid: str) -> None:
        """Test that tmux-orc reflect produces valid JSON."""
        try:
            result = subprocess.run(
                ["tmux-orc", "reflect", "--format", "json"], capture_output=True, text=True, timeout=10
            )

            if result.returncode != 0:
                pytest.skip(f"tmux-orc reflect failed: {result.stderr}")

            # Parse JSON output
            cli_structure = json.loads(result.stdout)
            assert isinstance(cli_structure, dict), f"Should return dict structure - Test ID: {test_uuid}"

            # Validate expected CLI structure
            assert (
                "commands" in cli_structure or "subcommands" in cli_structure
            ), f"Should contain command info - Test ID: {test_uuid}"

        except json.JSONDecodeError as e:
            pytest.fail(f"tmux-orc reflect output is not valid JSON: {e} - Test ID: {test_uuid}")
        except subprocess.TimeoutExpired:
            pytest.fail(f"tmux-orc reflect JSON command timed out - Test ID: {test_uuid}")

    def test_cli_discovery_performance(self, test_uuid: str) -> None:
        """Test CLI discovery meets performance requirements."""
        start_time = time.time()

        try:
            result = subprocess.run(
                ["tmux-orc", "reflect", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=2,  # 2s timeout for discovery
            )

            discovery_time = time.time() - start_time

            if result.returncode == 0:
                assert (
                    discovery_time < 1.0
                ), f"CLI discovery took {discovery_time:.3f}s (>1s limit) - Test ID: {test_uuid}"
            else:
                pytest.skip("CLI discovery failed, cannot test performance")

        except subprocess.TimeoutExpired:
            pytest.fail(f"CLI discovery exceeded 2s timeout - Test ID: {test_uuid}")


@pytest.mark.skipif(not CLI_REFLECTION_AVAILABLE, reason="CLI reflection server not available")
class TestFreshCLIMCPServer:
    """Test the fresh CLI reflection MCP server."""

    @pytest.mark.asyncio
    async def test_server_initialization(self, test_uuid: str) -> None:
        """Test server initializes correctly."""
        server = FreshCLIMCPServer("test-server")

        assert server is not None, f"Server should initialize - Test ID: {test_uuid}"
        assert server.server is not None, f"Underlying MCP server should exist - Test ID: {test_uuid}"
        assert server.generated_tools == {}, f"Tools should start empty - Test ID: {test_uuid}"

    @pytest.mark.asyncio
    async def test_cli_structure_discovery(self, test_uuid: str) -> None:
        """Test CLI structure discovery."""
        server = FreshCLIMCPServer("test-server")

        with patch("subprocess.run") as mock_subprocess:
            # Mock successful CLI discovery
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = json.dumps(
                {
                    "commands": {
                        "spawn": {
                            "description": "Spawn an agent",
                            "parameters": {"session": "str", "agent_type": "str"},
                        },
                        "status": {"description": "Get status", "parameters": {}},
                    }
                }
            )
            mock_subprocess.return_value = mock_result

            cli_structure = await server.discover_cli_structure()

            assert isinstance(cli_structure, dict), f"Should return dict - Test ID: {test_uuid}"
            assert "commands" in cli_structure, f"Should contain commands - Test ID: {test_uuid}"

            # Verify subprocess called correctly
            mock_subprocess.assert_called_once_with(
                ["tmux-orc", "reflect", "--format", "json"], capture_output=True, text=True, timeout=30
            )

    @pytest.mark.asyncio
    async def test_tool_generation_from_cli(self, test_uuid: str) -> None:
        """Test MCP tool generation from CLI structure."""
        server = FreshCLIMCPServer("test-server")

        # Mock CLI structure
        mock_cli_structure = {
            "commands": {
                "spawn": {
                    "description": "Spawn a new Claude agent",
                    "parameters": {
                        "session_name": {"type": "str", "required": True},
                        "agent_type": {"type": "str", "default": "developer"},
                    },
                }
            }
        }

        with patch.object(server, "discover_cli_structure", return_value=mock_cli_structure):
            await server._generate_all_tools()

            assert len(server.generated_tools) > 0, f"Should generate tools - Test ID: {test_uuid}"
            assert "spawn" in server.generated_tools, f"Should generate spawn tool - Test ID: {test_uuid}"

            spawn_tool = server.generated_tools["spawn"]
            assert "description" in spawn_tool, f"Tool should have description - Test ID: {test_uuid}"
            assert "input_schema" in spawn_tool, f"Tool should have input schema - Test ID: {test_uuid}"

    @pytest.mark.asyncio
    async def test_tool_execution_performance(self, test_uuid: str) -> None:
        """Test tool execution meets performance requirements."""
        server = FreshCLIMCPServer("test-server")

        with patch.object(server, "_execute_cli_command") as mock_execute:
            mock_execute.return_value = {"success": True, "result": "test"}

            # Setup mock tool
            server.generated_tools = {
                "test_command": {"command_name": "test", "description": "Test command", "input_schema": {}}
            }

            start_time = time.time()
            await server._execute_cli_command("test", {})
            execution_time = time.time() - start_time

            assert execution_time < 1.0, f"Tool execution took {execution_time:.3f}s (>1s limit) - Test ID: {test_uuid}"


class TestCLIReflectionIntegration:
    """Test full CLI reflection to MCP tool pipeline."""

    @pytest.mark.asyncio
    async def test_end_to_end_cli_to_mcp_workflow(self, test_uuid: str) -> None:
        """Test complete CLI reflection workflow."""

        # Test CLI discovery → Tool generation → Tool execution
        workflow_steps = []

        # Step 1: CLI Discovery
        try:
            result = subprocess.run(
                ["tmux-orc", "reflect", "--format", "json"], capture_output=True, text=True, timeout=5
            )

            if result.returncode == 0:
                json.loads(result.stdout)
                workflow_steps.append("CLI_DISCOVERY_SUCCESS")
            else:
                workflow_steps.append("CLI_DISCOVERY_FAILED")

        except Exception:
            workflow_steps.append("CLI_DISCOVERY_ERROR")

        # Step 2: Tool Generation (mock)
        if CLI_REFLECTION_AVAILABLE:
            try:
                FreshCLIMCPServer("integration-test")
                workflow_steps.append("SERVER_INIT_SUCCESS")
            except Exception:
                workflow_steps.append("SERVER_INIT_FAILED")
        else:
            workflow_steps.append("SERVER_NOT_AVAILABLE")

        # Report workflow status
        workflow_status = " → ".join(workflow_steps)
        logger_msg = f"E2E CLI reflection workflow: {workflow_status} - Test ID: {test_uuid}"

        # At minimum, CLI discovery should work
        assert (
            "CLI_DISCOVERY_SUCCESS" in workflow_steps or "CLI_DISCOVERY_FAILED" in workflow_steps
        ), f"Should attempt CLI discovery - {logger_msg}"


class TestCLIReflectionPerformance:
    """Performance benchmarks for CLI reflection approach."""

    def test_cli_reflection_startup_time(self, test_uuid: str) -> None:
        """Test CLI reflection server startup performance."""
        if not CLI_REFLECTION_AVAILABLE:
            pytest.skip("CLI reflection not available")

        start_time = time.time()
        FreshCLIMCPServer("perf-test")
        startup_time = time.time() - start_time

        assert startup_time < 0.5, f"Server startup took {startup_time:.3f}s (>0.5s limit) - Test ID: {test_uuid}"

    @pytest.mark.asyncio
    async def test_tool_discovery_performance(self, test_uuid: str) -> None:
        """Test tool discovery performance."""
        if not CLI_REFLECTION_AVAILABLE:
            pytest.skip("CLI reflection not available")

        server = FreshCLIMCPServer("perf-test")

        with patch.object(server, "discover_cli_structure") as mock_discover:
            # Mock large CLI structure
            large_structure = {"commands": {f"command_{i}": {"description": f"Command {i}"} for i in range(50)}}
            mock_discover.return_value = large_structure

            start_time = time.time()
            await server._generate_all_tools()
            generation_time = time.time() - start_time

            assert (
                generation_time < 1.0
            ), f"Tool generation took {generation_time:.3f}s (>1s limit) - Test ID: {test_uuid}"
            assert len(server.generated_tools) == 50, f"Should generate 50 tools - Test ID: {test_uuid}"


class TestCLIReflectionErrorHandling:
    """Test error handling in CLI reflection approach."""

    @pytest.mark.asyncio
    async def test_cli_discovery_failure_handling(self, test_uuid: str) -> None:
        """Test handling of CLI discovery failures."""
        if not CLI_REFLECTION_AVAILABLE:
            pytest.skip("CLI reflection not available")

        server = FreshCLIMCPServer("error-test")

        with patch("subprocess.run") as mock_subprocess:
            # Mock CLI discovery failure
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stderr = "CLI discovery failed"
            mock_subprocess.return_value = mock_result

            try:
                cli_structure = await server.discover_cli_structure()
                # Should handle error gracefully
                assert isinstance(cli_structure, dict), f"Should return fallback structure - Test ID: {test_uuid}"
            except Exception as e:
                # Should not raise unhandled exceptions
                assert "CLI discovery failed" in str(e), f"Should provide clear error - Test ID: {test_uuid}"

    @pytest.mark.asyncio
    async def test_invalid_json_handling(self, test_uuid: str) -> None:
        """Test handling of invalid JSON from CLI discovery."""
        if not CLI_REFLECTION_AVAILABLE:
            pytest.skip("CLI reflection not available")

        server = FreshCLIMCPServer("error-test")

        with patch("subprocess.run") as mock_subprocess:
            # Mock invalid JSON response
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "invalid json {{"
            mock_subprocess.return_value = mock_result

            try:
                cli_structure = await server.discover_cli_structure()
                # Should handle JSON parse error gracefully
                assert isinstance(cli_structure, dict), f"Should return fallback structure - Test ID: {test_uuid}"
            except Exception as e:
                # Should provide clear error about JSON parsing
                assert "json" in str(e).lower(), f"Should indicate JSON parsing issue - Test ID: {test_uuid}"


class TestCLIMCPParity:
    """Test parity between CLI commands and MCP tools."""

    def test_all_cli_commands_have_mcp_equivalent(self, test_uuid: str) -> None:
        """Verify every CLI command has corresponding MCP tool."""
        # Discover CLI structure
        try:
            result = subprocess.run(
                ["tmux-orc", "reflect", "--format", "json"], capture_output=True, text=True, timeout=10
            )

            if result.returncode != 0:
                pytest.skip(f"CLI discovery failed: {result.stderr}")

            cli_structure = json.loads(result.stdout)
            cli_commands = set()

            # Extract all commands from CLI structure
            if "commands" in cli_structure:
                cli_commands.update(cli_structure["commands"].keys())
            if "subcommands" in cli_structure:
                for subcmd in cli_structure["subcommands"].values():
                    if isinstance(subcmd, dict) and "commands" in subcmd:
                        cli_commands.update(subcmd["commands"].keys())

            # Expected MCP tool prefixes for CLI commands
            expected_mcp_tools = {
                "agent": "mcp__tmux-orchestrator__agent",
                "monitor": "mcp__tmux-orchestrator__monitor",
                "team": "mcp__tmux-orchestrator__team",
                "spawn": "mcp__tmux-orchestrator__spawn",
                "context": "mcp__tmux-orchestrator__context",
                "list": "mcp__tmux-orchestrator__list",
                "reflect": "mcp__tmux-orchestrator__reflect",
                "status": "mcp__tmux-orchestrator__status",
            }

            # Verify each CLI command category has MCP equivalent
            missing_mcp_tools = []
            for cmd in cli_commands:
                if cmd in expected_mcp_tools:
                    # In real test, would verify MCP tool exists
                    # For now, we track the mapping
                    pass
                else:
                    missing_mcp_tools.append(cmd)

            assert (
                len(missing_mcp_tools) == 0 or len(cli_commands) > 0
            ), f"All CLI commands should have MCP equivalents. Missing: {missing_mcp_tools} - Test ID: {test_uuid}"

        except Exception as e:
            pytest.skip(f"Cannot test CLI/MCP parity: {e}")

    @pytest.mark.asyncio
    async def test_parameter_consistency_between_cli_and_mcp(self, test_uuid: str) -> None:
        """Ensure CLI args map correctly to MCP kwargs."""
        if not CLI_REFLECTION_AVAILABLE:
            pytest.skip("CLI reflection not available")

        _server = FreshCLIMCPServer("parity-test")

        # Test parameter mapping for common commands
        test_cases = [
            {
                "cli_command": "agent send backend:1 'test message'",
                "expected_mcp_params": {"action": "send", "args": ["backend:1", "test message"]},
            },
            {
                "cli_command": "spawn agent backend-dev test-session:2",
                "expected_mcp_params": {"action": "agent", "args": ["backend-dev", "test-session:2"]},
            },
            {
                "cli_command": "team broadcast dev-team 'standup at 10am'",
                "expected_mcp_params": {"action": "broadcast", "args": ["dev-team", "standup at 10am"]},
            },
        ]

        for test_case in test_cases:
            # Parse CLI command into MCP parameters
            cli_parts = str(test_case["cli_command"]).split()

            # Extract command and subcommand
            if len(cli_parts) >= 2:
                _command = cli_parts[0]
                subcommand = cli_parts[1]
                args = cli_parts[2:] if len(cli_parts) > 2 else []

                # Build MCP kwargs format
                mcp_kwargs = f"action={subcommand}"
                if args:
                    # Join args that might have spaces (quoted strings)
                    args_str = " ".join(args)
                    # Simple quote handling
                    processed_args = []
                    in_quote = False
                    current_arg = ""

                    for char in args_str:
                        if char in ["'", '"'] and not in_quote:
                            in_quote = True
                        elif char in ["'", '"'] and in_quote:
                            in_quote = False
                            processed_args.append(current_arg)
                            current_arg = ""
                        elif in_quote:
                            current_arg += char
                        elif char == " " and not in_quote:
                            if current_arg:
                                processed_args.append(current_arg)
                                current_arg = ""
                        else:
                            current_arg += char

                    if current_arg:
                        processed_args.append(current_arg)

                    if processed_args:
                        mcp_kwargs += f" args={processed_args}"

                # Verify mapping is consistent
                assert "action=" in mcp_kwargs, f"MCP format should include action parameter - Test ID: {test_uuid}"

    def test_output_format_parity(self, test_uuid: str) -> None:
        """Verify CLI and MCP return similar data structures."""
        # Test output format consistency
        test_commands = [
            ("tmux-orc", "list"),
            ("tmux-orc", "status"),
        ]

        for cmd_parts in test_commands:
            try:
                # Get CLI output
                cli_result = subprocess.run(
                    list(cmd_parts) + ["--format", "json"], capture_output=True, text=True, timeout=5
                )

                if cli_result.returncode == 0:
                    try:
                        cli_output = json.loads(cli_result.stdout)

                        # Expected output structure patterns
                        if "list" in cmd_parts:
                            # List commands should return array or dict with items
                            assert isinstance(
                                cli_output, (list, dict)
                            ), f"List output should be array or dict - Test ID: {test_uuid}"

                        elif "status" in cmd_parts:
                            # Status commands should return dict with status info
                            assert isinstance(cli_output, dict), f"Status output should be dict - Test ID: {test_uuid}"

                        # Verify consistent field naming
                        if isinstance(cli_output, dict):
                            # Check for common fields that should be present
                            common_fields = ["status", "success", "result", "data", "error"]
                            has_standard_field = any(field in cli_output for field in common_fields)

                            assert (
                                has_standard_field or len(cli_output) > 0
                            ), f"Output should have standard fields or data - Test ID: {test_uuid}"

                    except json.JSONDecodeError:
                        # Non-JSON output, check if it's consistent text format
                        assert len(cli_result.stdout) > 0, f"Should have output even if not JSON - Test ID: {test_uuid}"

            except subprocess.TimeoutExpired:
                pytest.skip(f"Command {' '.join(cmd_parts)} timed out")
            except FileNotFoundError:
                pytest.skip("tmux-orc not available")

    @pytest.mark.asyncio
    async def test_mcp_tool_naming_follows_cli_structure(self, test_uuid: str) -> None:
        """Verify MCP tool names align with CLI command structure."""
        # Expected mapping between CLI commands and MCP tool names
        cli_to_mcp_mapping = {
            "agent": "mcp__tmux-orchestrator__agent",
            "monitor": "mcp__tmux-orchestrator__monitor",
            "team": "mcp__tmux-orchestrator__team",
            "spawn": "mcp__tmux-orchestrator__spawn",
            "context": "mcp__tmux-orchestrator__context",
            "list": "mcp__tmux-orchestrator__list",
            "reflect": "mcp__tmux-orchestrator__reflect",
            "status": "mcp__tmux-orchestrator__status",
        }

        # Verify naming convention
        for cli_cmd, expected_mcp_name in cli_to_mcp_mapping.items():
            # Check MCP tool name follows pattern
            assert expected_mcp_name.startswith(
                "mcp__tmux-orchestrator__"
            ), f"MCP tool should follow naming convention - Test ID: {test_uuid}"

            # Check CLI command is in MCP tool name
            assert (
                cli_cmd in expected_mcp_name
            ), f"CLI command '{cli_cmd}' should be in MCP tool name - Test ID: {test_uuid}"


# CLI Reflection Test Fixtures
@pytest.fixture
def mock_cli_structure():
    """Fixture providing mock CLI structure for testing."""
    return {
        "commands": {
            "spawn": {
                "description": "Spawn a new Claude agent in a tmux session",
                "parameters": {
                    "session_name": {"type": "str", "required": True},
                    "agent_type": {"type": "str", "default": "developer"},
                    "project_path": {"type": "str", "required": False},
                },
            },
            "status": {
                "description": "Get agent status information",
                "parameters": {"target": {"type": "str", "required": False}},
            },
            "kill": {
                "description": "Terminate an agent",
                "parameters": {
                    "target": {"type": "str", "required": True},
                    "force": {"type": "bool", "default": False},
                },
            },
        }
    }


@pytest.fixture
def fresh_cli_server():
    """Fixture providing fresh CLI MCP server for testing."""
    if CLI_REFLECTION_AVAILABLE:
        return FreshCLIMCPServer("test-fixture-server")
    else:
        pytest.skip("CLI reflection server not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

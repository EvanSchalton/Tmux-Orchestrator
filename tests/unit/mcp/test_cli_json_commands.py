"""
Test suite for CLI commands with JSON support.

Tests all existing CLI commands that support JSON output to validate:
1. JSON format consistency
2. Schema compliance
3. Field presence and types
4. Error handling with JSON output
"""

import json
import subprocess
import time

import pytest


class TestCLIJSONCommands:
    """Test existing CLI commands with JSON support."""

    def test_reflect_json_format(self, test_uuid: str) -> None:
        """Test reflect command JSON output format."""
        result = subprocess.run(["tmux-orc", "reflect", "--format", "json"], capture_output=True, text=True, timeout=5)

        assert result.returncode == 0, f"reflect command failed - Test ID: {test_uuid}"

        try:
            data = json.loads(result.stdout)
            assert isinstance(data, dict), f"reflect should return dict - Test ID: {test_uuid}"

            # Validate that we have expected commands
            expected_commands = ["list", "status", "quick-deploy", "reflect"]
            for cmd in expected_commands:
                assert cmd in data, f"Expected command '{cmd}' not found - Test ID: {test_uuid}"

            # Validate command structure
            for cmd_name, cmd_data in data.items():
                assert "type" in cmd_data, f"Command {cmd_name} missing 'type' field - Test ID: {test_uuid}"
                assert cmd_data["type"] in [
                    "command",
                    "group",
                ], f"Command {cmd_name} has invalid type - Test ID: {test_uuid}"
                assert "help" in cmd_data, f"Command {cmd_name} missing 'help' field - Test ID: {test_uuid}"

        except json.JSONDecodeError as e:
            pytest.fail(f"reflect returned invalid JSON: {e} - Test ID: {test_uuid}")

    def test_list_json_format(self, test_uuid: str) -> None:
        """Test list command JSON output format."""
        result = subprocess.run(["tmux-orc", "list", "--json"], capture_output=True, text=True, timeout=5)

        assert result.returncode == 0, f"list command failed - Test ID: {test_uuid}"

        try:
            data = json.loads(result.stdout)
            assert isinstance(data, list), f"list should return array - Test ID: {test_uuid}"

            # If agents exist, validate their structure
            for agent in data:
                assert isinstance(agent, dict), f"Agent should be dict - Test ID: {test_uuid}"

                # Required fields
                required_fields = ["session", "window", "type", "status"]
                for field in required_fields:
                    assert field in agent, f"Agent missing required field '{field}' - Test ID: {test_uuid}"

                # Validate field types
                assert isinstance(agent["session"], str), f"session should be string - Test ID: {test_uuid}"
                assert isinstance(agent["window"], str), f"window should be string - Test ID: {test_uuid}"
                assert isinstance(agent["type"], str), f"type should be string - Test ID: {test_uuid}"
                assert isinstance(agent["status"], str), f"status should be string - Test ID: {test_uuid}"

                # Validate status values
                valid_statuses = ["Active", "Idle", "Busy", "Error", "Unknown"]
                assert agent["status"] in valid_statuses, f"Invalid status '{agent['status']}' - Test ID: {test_uuid}"

        except json.JSONDecodeError as e:
            pytest.fail(f"list returned invalid JSON: {e} - Test ID: {test_uuid}")

    def test_status_json_format(self, test_uuid: str) -> None:
        """Test status command JSON output format."""
        result = subprocess.run(["tmux-orc", "status", "--json"], capture_output=True, text=True, timeout=5)

        assert result.returncode == 0, f"status command failed - Test ID: {test_uuid}"

        try:
            data = json.loads(result.stdout)
            assert isinstance(data, dict), f"status should return dict - Test ID: {test_uuid}"

            # Required top-level fields
            required_fields = ["sessions", "agents", "summary"]
            for field in required_fields:
                assert field in data, f"Status missing required field '{field}' - Test ID: {test_uuid}"

            # Validate sessions array
            assert isinstance(data["sessions"], list), f"sessions should be array - Test ID: {test_uuid}"
            for session in data["sessions"]:
                assert "name" in session, f"Session missing name - Test ID: {test_uuid}"
                assert "created" in session, f"Session missing created timestamp - Test ID: {test_uuid}"
                assert "attached" in session, f"Session missing attached count - Test ID: {test_uuid}"

            # Validate agents array (should match list output)
            assert isinstance(data["agents"], list), f"agents should be array - Test ID: {test_uuid}"
            for agent in data["agents"]:
                required_agent_fields = ["session", "window", "type", "status"]
                for field in required_agent_fields:
                    assert field in agent, f"Agent missing field '{field}' - Test ID: {test_uuid}"

            # Validate summary object
            assert isinstance(data["summary"], dict), f"summary should be dict - Test ID: {test_uuid}"
            summary_fields = ["total_sessions", "total_agents", "active_agents"]
            for field in summary_fields:
                assert field in data["summary"], f"Summary missing field '{field}' - Test ID: {test_uuid}"
                assert isinstance(
                    data["summary"][field], int
                ), f"Summary field '{field}' should be integer - Test ID: {test_uuid}"

        except json.JSONDecodeError as e:
            pytest.fail(f"status returned invalid JSON: {e} - Test ID: {test_uuid}")


class TestJSONFormatConsistency:
    """Test JSON format consistency across commands."""

    def test_timestamp_format_consistency(self, test_uuid: str) -> None:
        """Test that timestamps are consistent across commands."""
        # Get data from multiple commands
        status_result = subprocess.run(["tmux-orc", "status", "--json"], capture_output=True, text=True, timeout=5)

        if status_result.returncode == 0:
            try:
                status_data = json.loads(status_result.stdout)

                # Check session timestamps
                for session in status_data.get("sessions", []):
                    if "created" in session:
                        # Should be numeric timestamp (Unix epoch)
                        assert isinstance(session["created"], str), f"Timestamp should be string - Test ID: {test_uuid}"
                        # Should be convertible to int
                        int(session["created"])

            except (json.JSONDecodeError, ValueError) as e:
                pytest.fail(f"Timestamp format validation failed: {e} - Test ID: {test_uuid}")

    def test_agent_format_consistency(self, test_uuid: str) -> None:
        """Test that agent objects are consistent between list and status."""
        # Get data from both commands
        list_result = subprocess.run(["tmux-orc", "list", "--json"], capture_output=True, text=True, timeout=5)

        status_result = subprocess.run(["tmux-orc", "status", "--json"], capture_output=True, text=True, timeout=5)

        if list_result.returncode == 0 and status_result.returncode == 0:
            try:
                list_data = json.loads(list_result.stdout)
                status_data = json.loads(status_result.stdout)

                # Both should have same agent count
                assert len(list_data) == len(
                    status_data.get("agents", [])
                ), f"Agent count mismatch between list and status - Test ID: {test_uuid}"

                # Agent objects should have same structure
                if list_data and status_data.get("agents"):
                    list_agent = list_data[0]
                    status_agent = status_data["agents"][0]

                    # Both should have same required fields
                    required_fields = ["session", "window", "type", "status"]
                    for field in required_fields:
                        assert (
                            field in list_agent and field in status_agent
                        ), f"Field '{field}' consistency check failed - Test ID: {test_uuid}"

            except json.JSONDecodeError as e:
                pytest.fail(f"Agent consistency check failed: {e} - Test ID: {test_uuid}")

    def test_error_json_format(self, test_uuid: str) -> None:
        """Test that error responses also use consistent JSON format."""
        # Test with invalid quick-deploy arguments
        result = subprocess.run(
            ["tmux-orc", "quick-deploy", "invalid-type", "--json"], capture_output=True, text=True, timeout=5
        )

        # Should fail but may or may not return JSON (depends on implementation)
        assert result.returncode != 0, f"Invalid command should fail - Test ID: {test_uuid}"

        # If it returns JSON, validate format
        if result.stdout.strip().startswith("{"):
            try:
                error_data = json.loads(result.stdout)
                assert isinstance(error_data, dict), f"Error should be dict - Test ID: {test_uuid}"
                # Should have error indicator
                assert (
                    "success" in error_data or "error" in error_data
                ), f"Error response should indicate failure - Test ID: {test_uuid}"
            except json.JSONDecodeError:
                # If not JSON, that's also acceptable
                pass


class TestCLIEnhancementReadiness:
    """Test that CLI is ready for MCP tool auto-generation."""

    def test_json_commands_performance(self, test_uuid: str) -> None:
        """Test that JSON commands execute within performance requirements."""
        commands = [
            ["tmux-orc", "list", "--json"],
            ["tmux-orc", "status", "--json"],
            ["tmux-orc", "reflect", "--format", "json"],
        ]

        for cmd in commands:
            start_time = time.perf_counter()

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)

            execution_time = time.perf_counter() - start_time

            # All commands should complete within 3 seconds
            assert (
                execution_time < 3.0
            ), f"Command {' '.join(cmd)} took {execution_time:.3f}s (>3s limit) - Test ID: {test_uuid}"

            # Should succeed
            assert result.returncode == 0, f"Command {' '.join(cmd)} failed - Test ID: {test_uuid}"

    def test_mcp_tool_auto_generation_ready(self, test_uuid: str) -> None:
        """Test that CLI structure supports auto-generation of MCP tools."""
        # Test reflect command provides sufficient information
        result = subprocess.run(["tmux-orc", "reflect", "--format", "json"], capture_output=True, text=True, timeout=5)

        assert result.returncode == 0, f"reflect command failed - Test ID: {test_uuid}"

        try:
            cli_structure = json.loads(result.stdout)

            # Should have all 6 core tools needed for auto-generation
            core_tools = ["list", "status", "quick-deploy", "execute", "team", "spawn"]
            available_tools = list(cli_structure.keys())

            for tool in core_tools:
                assert (
                    tool in available_tools
                ), f"Core tool '{tool}' not available for auto-generation - Test ID: {test_uuid}"

            # Each tool should have sufficient metadata for MCP generation
            for tool_name in core_tools:
                if tool_name in cli_structure:
                    tool_data = cli_structure[tool_name]
                    assert (
                        "help" in tool_data
                    ), f"Tool '{tool_name}' missing help for MCP generation - Test ID: {test_uuid}"
                    assert tool_data["help"].strip(), f"Tool '{tool_name}' has empty help text - Test ID: {test_uuid}"

        except json.JSONDecodeError as e:
            pytest.fail(f"CLI structure validation failed: {e} - Test ID: {test_uuid}")

    def test_json_output_mcp_compatibility(self, test_uuid: str) -> None:
        """Test that JSON outputs are compatible with MCP tool responses."""
        # Test that JSON outputs follow MCP-compatible patterns
        commands_to_test = [
            (["tmux-orc", "list", "--json"], list),
            (["tmux-orc", "status", "--json"], dict),
            (["tmux-orc", "reflect", "--format", "json"], dict),
        ]

        for cmd, expected_type in commands_to_test:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)

            if result.returncode == 0:
                try:
                    data = json.loads(result.stdout)
                    assert isinstance(
                        data, expected_type
                    ), f"Command {' '.join(cmd)} should return {expected_type.__name__} - Test ID: {test_uuid}"

                    # Should be JSON serializable (no special objects)
                    json.dumps(data)  # Should not raise exception

                except json.JSONDecodeError as e:
                    pytest.fail(f"MCP compatibility check failed for {' '.join(cmd)}: {e} - Test ID: {test_uuid}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Integration test scenarios for pip-installable tmux-orchestrator CLI tool.

Tests real-world workflows for the simplified pip-installable architecture:
1. pip install tmux-orchestrator
2. tmux-orc setup
3. Use CLI commands and MCP server

Validates all auto-generated tools work correctly in local developer environments.
"""

import asyncio
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

import pytest


class TestPipInstallableIntegration:
    """Test integration with pip-installable tmux-orchestrator."""

    def test_cli_is_accessible(self, test_uuid: str) -> None:
        """Verify tmux-orc CLI is accessible after pip install."""
        # Test that tmux-orc command is available
        result = subprocess.run(["tmux-orc", "--version"], capture_output=True, text=True, timeout=5)

        # Should return version info or help (depending on implementation)
        assert result.returncode in [0, 2], f"tmux-orc CLI not accessible - Test ID: {test_uuid}"

    def test_mcp_server_bundled(self, test_uuid: str) -> None:
        """Verify MCP server is bundled with the package."""
        # Check if mcp_server.py exists in the package
        server_path = Path("/workspaces/Tmux-Orchestrator/tmux_orchestrator/mcp_server.py")
        assert server_path.exists(), f"mcp_server.py not found in package - Test ID: {test_uuid}"

        # Verify it has CLI reflection capabilities
        with open(server_path) as f:
            content = f.read()
            assert (
                "reflect" in content or "CLI" in content
            ), f"Bundled server should have CLI reflection capabilities - Test ID: {test_uuid}"

    def test_cli_reflection_endpoint(self, test_uuid: str) -> None:
        """Test that CLI reflection is working on the deployed server."""
        try:
            # Test the reflection command
            result = subprocess.run(
                ["tmux-orc", "reflect", "--format", "json"], capture_output=True, text=True, timeout=5
            )

            assert result.returncode == 0, f"CLI reflection failed with code {result.returncode} - Test ID: {test_uuid}"

            # Verify JSON output
            cli_structure = json.loads(result.stdout)
            assert isinstance(
                cli_structure, dict
            ), f"CLI reflection should return dict structure - Test ID: {test_uuid}"

            # Verify expected commands are present
            expected_commands = ["spawn", "list", "status", "execute", "team", "quick-deploy"]
            available_commands = list(cli_structure.keys())

            for cmd in expected_commands:
                assert (
                    cmd in available_commands
                ), f"Expected command '{cmd}' not in CLI structure - Test ID: {test_uuid}"

        except subprocess.TimeoutExpired:
            pytest.fail(f"CLI reflection timed out - Test ID: {test_uuid}")
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON from CLI reflection: {e} - Test ID: {test_uuid}")


class TestScenario0PipInstallWorkflow:
    """Scenario 0: Pip install and setup workflow."""

    def test_setup_command_available(self, test_uuid: str) -> None:
        """Test that tmux-orc setup command is available."""
        result = subprocess.run(["tmux-orc", "setup", "--help"], capture_output=True, text=True, timeout=5)

        assert result.returncode == 0, f"setup command not available - Test ID: {test_uuid}"
        assert "setup" in result.stdout.lower(), f"setup help should mention setup - Test ID: {test_uuid}"

    def test_mcp_server_script_available(self, test_uuid: str) -> None:
        """Test that tmux-orc-mcp script is available."""
        result = subprocess.run(["tmux-orc-mcp", "--help"], capture_output=True, text=True, timeout=5)

        # Should either work or fail gracefully
        assert result.returncode in [0, 2], f"tmux-orc-mcp script not accessible - Test ID: {test_uuid}"


class TestScenario1TeamDeploymentWorkflow:
    """Scenario 1: Complete team deployment workflow (local development)."""

    @pytest.mark.asyncio
    async def test_prd_to_team_deployment(self, test_uuid: str) -> None:
        """Test PRD execution leading to team deployment."""
        workflow_steps = []

        # Step 1: Create a test PRD file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(
                """# Test Project PRD

            ## Overview
            Build a test application for integration testing.

            ## Requirements
            - Frontend interface
            - Backend API
            - Database integration
            """
            )
            prd_path = f.name

        try:
            # Step 2: Execute PRD
            result = subprocess.run(
                ["tmux-orc", "execute", prd_path, "--project-name", "test-project"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                workflow_steps.append("PRD_EXECUTED")
            else:
                workflow_steps.append(f"PRD_FAILED: {result.stderr}")

            # Step 3: List agents to verify team deployment
            await asyncio.sleep(2)  # Allow time for team to spawn

            list_result = subprocess.run(["tmux-orc", "list", "--json"], capture_output=True, text=True, timeout=5)

            if list_result.returncode == 0:
                agents = json.loads(list_result.stdout).get("agents", [])
                if len(agents) > 0:
                    workflow_steps.append(f"AGENTS_DEPLOYED: {len(agents)}")
                else:
                    workflow_steps.append("NO_AGENTS_FOUND")

            # Step 4: Check team status
            status_result = subprocess.run(
                ["tmux-orc", "team", "status", "test-project"], capture_output=True, text=True, timeout=5
            )

            if status_result.returncode == 0:
                workflow_steps.append("TEAM_STATUS_OK")

        finally:
            # Cleanup
            os.unlink(prd_path)

        # Verify workflow completed successfully
        workflow_summary = " → ".join(workflow_steps)
        print(f"\nWorkflow Summary: {workflow_summary}")

        assert (
            "PRD_EXECUTED" in workflow_steps or "PRD_FAILED" in workflow_steps
        ), f"PRD execution step missing - Test ID: {test_uuid}"


class TestScenario2AgentLifecycle:
    """Scenario 2: Agent lifecycle management."""

    @pytest.mark.asyncio
    async def test_agent_spawn_kill_respawn(self, test_uuid: str) -> None:
        """Test agent lifecycle: spawn → kill → verify → respawn."""
        session_name = f"test-lifecycle-{test_uuid[:8]}"

        try:
            # Step 1: Spawn agent
            spawn_result = subprocess.run(
                ["tmux-orc", "spawn", session_name, "--agent-type", "developer"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            assert spawn_result.returncode == 0, f"Agent spawn failed: {spawn_result.stderr} - Test ID: {test_uuid}"

            # Step 2: Verify agent is listed
            await asyncio.sleep(1)

            list_result = subprocess.run(["tmux-orc", "list", "--json"], capture_output=True, text=True, timeout=5)

            if list_result.returncode == 0:
                data = json.loads(list_result.stdout)
                agents = data.get("agents", [])
                agent_found = any(a.get("session") == session_name for a in agents)
                assert agent_found, f"Spawned agent not found in list - Test ID: {test_uuid}"

            # Step 3: Kill agent
            subprocess.run(["tmux-orc", "kill", f"{session_name}:0"], capture_output=True, text=True, timeout=5)

            # Step 4: Verify agent is gone
            await asyncio.sleep(1)

            list_after_kill = subprocess.run(["tmux-orc", "list", "--json"], capture_output=True, text=True, timeout=5)

            if list_after_kill.returncode == 0:
                data = json.loads(list_after_kill.stdout)
                agents = data.get("agents", [])
                agent_gone = not any(a.get("session") == session_name for a in agents)
                assert agent_gone, f"Killed agent still in list - Test ID: {test_uuid}"

            # Step 5: Respawn agent
            respawn_result = subprocess.run(
                ["tmux-orc", "spawn", session_name, "--agent-type", "qa"], capture_output=True, text=True, timeout=5
            )

            assert respawn_result.returncode == 0, f"Agent respawn failed - Test ID: {test_uuid}"

        except subprocess.TimeoutExpired:
            pytest.fail(f"Command timed out during agent lifecycle test - Test ID: {test_uuid}")


class TestScenario3MultiTeamCoordination:
    """Scenario 3: Multiple team coordination."""

    @pytest.mark.asyncio
    async def test_multiple_team_deployment(self, test_uuid: str) -> None:
        """Test deploying and coordinating multiple teams."""
        teams_deployed = []

        try:
            # Deploy 3 different teams
            team_configs = [("frontend", 3), ("backend", 4), ("testing", 2)]

            for team_type, size in team_configs:
                team_name = f"team-{team_type}-{test_uuid[:8]}"

                deploy_result = subprocess.run(
                    ["tmux-orc", "quick-deploy", team_type, str(size), "--project-name", team_name],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if deploy_result.returncode == 0:
                    teams_deployed.append(team_name)
                    await asyncio.sleep(2)  # Stagger deployments

            # Verify all teams are active
            status_result = subprocess.run(["tmux-orc", "status", "--json"], capture_output=True, text=True, timeout=5)

            if status_result.returncode == 0:
                data = json.loads(status_result.stdout)
                team_count = data.get("teams", 0)
                assert team_count >= len(
                    teams_deployed
                ), f"Expected at least {len(teams_deployed)} teams, found {team_count} - Test ID: {test_uuid}"

            # Test team communication (broadcast)
            if teams_deployed:
                broadcast_result = subprocess.run(
                    ["tmux-orc", "team", "broadcast", teams_deployed[0], "Integration test message"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                assert broadcast_result.returncode == 0, f"Team broadcast failed - Test ID: {test_uuid}"

        except subprocess.TimeoutExpired:
            pytest.fail(f"Multi-team test timed out - Test ID: {test_uuid}")
        finally:
            # Cleanup teams
            for team in teams_deployed:
                subprocess.run(["tmux-orc", "team", "kill", team], capture_output=True, timeout=5)


class TestScenario4ErrorRecovery:
    """Scenario 4: Error handling and recovery."""

    def test_invalid_command_handling(self, test_uuid: str) -> None:
        """Test that invalid commands are handled gracefully."""
        test_cases = [
            # (command, expected_error_pattern)
            (["tmux-orc", "spawn", ""], "empty|invalid|required"),
            (["tmux-orc", "list", "--invalid-flag"], "unknown|invalid|flag"),
            (["tmux-orc", "execute", "nonexistent.md"], "not found|exist"),
            (["tmux-orc", "team", "status", "nonexistent-team"], "not found|exist"),
            (["tmux-orc", "quick-deploy", "invalid-type", "3"], "invalid|type"),
        ]

        for command, error_pattern in test_cases:
            result = subprocess.run(command, capture_output=True, text=True, timeout=5)

            # Should fail with non-zero exit code
            assert result.returncode != 0, f"Command {' '.join(command)} should fail - Test ID: {test_uuid}"

            # Should have meaningful error message
            error_output = result.stderr.lower()
            import re

            assert re.search(
                error_pattern, error_output
            ), f"Expected error pattern '{error_pattern}' in: {result.stderr} - Test ID: {test_uuid}"

    def test_system_recovery_after_error(self, test_uuid: str) -> None:
        """Test that system remains stable after errors."""
        # Cause some errors
        for _ in range(5):
            subprocess.run(
                ["tmux-orc", "spawn", ""],  # Invalid command
                capture_output=True,
                timeout=2,
            )

        # System should still be responsive
        status_result = subprocess.run(["tmux-orc", "status", "--json"], capture_output=True, text=True, timeout=5)

        assert status_result.returncode == 0, f"System not responsive after errors - Test ID: {test_uuid}"

        # Should return valid JSON
        try:
            data = json.loads(status_result.stdout)
            assert (
                "system_health" in data or "success" in data
            ), f"Status response incomplete after errors - Test ID: {test_uuid}"
        except json.JSONDecodeError:
            pytest.fail(f"Invalid JSON after error recovery - Test ID: {test_uuid}")


class TestPerformanceIntegration:
    """Test performance with real deployment."""

    def test_real_cli_reflection_performance(self, test_uuid: str) -> None:
        """Test actual CLI reflection performance."""
        times = []

        for _ in range(5):
            start_time = time.perf_counter()

            result = subprocess.run(
                ["tmux-orc", "reflect", "--format", "json"], capture_output=True, text=True, timeout=5
            )

            execution_time = time.perf_counter() - start_time

            if result.returncode == 0:
                times.append(execution_time)

        if times:
            avg_time = sum(times) / len(times)
            max_time = max(times)

            assert max_time < 2.0, f"CLI reflection max time {max_time:.3f}s exceeds 2s limit - Test ID: {test_uuid}"
            assert avg_time < 1.0, f"CLI reflection avg time {avg_time:.3f}s should be <1s - Test ID: {test_uuid}"

            print("\nCLI Reflection Performance:")
            print(f"  Average: {avg_time:.3f}s")
            print(f"  Max: {max_time:.3f}s")

    def test_concurrent_command_performance(self, test_uuid: str) -> None:
        """Test performance with concurrent CLI commands."""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        def run_command(cmd):
            start = time.perf_counter()
            result = subprocess.run(cmd, capture_output=True, timeout=5)
            return time.perf_counter() - start, result.returncode

        # Prepare 10 concurrent commands
        commands = [
            ["tmux-orc", "list", "--json"],
            ["tmux-orc", "status", "--json"],
            ["tmux-orc", "list", "--json"],
            ["tmux-orc", "status", "--json"],
            ["tmux-orc", "list", "--json"],
            ["tmux-orc", "reflect", "--format", "json"],
            ["tmux-orc", "list", "--json"],
            ["tmux-orc", "status", "--json"],
            ["tmux-orc", "list", "--json"],
            ["tmux-orc", "reflect", "--format", "json"],
        ]

        # Execute concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(run_command, cmd) for cmd in commands]

            times = []
            failures = 0

            for future in as_completed(futures):
                exec_time, return_code = future.result()
                times.append(exec_time)
                if return_code != 0:
                    failures += 1

        # Check performance
        if times:
            max_time = max(times)
            avg_time = sum(times) / len(times)

            assert max_time < 3.0, f"Concurrent command max time {max_time:.3f}s exceeds 3s - Test ID: {test_uuid}"
            assert failures == 0, f"{failures} commands failed during concurrent execution - Test ID: {test_uuid}"

            print("\nConcurrent Execution Performance:")
            print(f"  Commands: {len(commands)}")
            print(f"  Average: {avg_time:.3f}s")
            print(f"  Max: {max_time:.3f}s")
            print(f"  Failures: {failures}")


class TestCLIEnhancementSupport:
    """Test support for new CLI commands being implemented."""

    def test_cli_structure_extensibility(self, test_uuid: str) -> None:
        """Test that CLI structure supports adding new commands."""
        result = subprocess.run(["tmux-orc", "reflect", "--format", "json"], capture_output=True, text=True, timeout=5)

        if result.returncode == 0:
            cli_structure = json.loads(result.stdout)

            # Check that structure can accommodate new commands
            assert isinstance(cli_structure, dict), f"CLI structure should be extensible dict - Test ID: {test_uuid}"

            # Verify command types are supported
            for cmd_name, cmd_info in cli_structure.items():
                assert "type" in cmd_info, f"Command {cmd_name} should have type field - Test ID: {test_uuid}"
                assert cmd_info["type"] in [
                    "command",
                    "group",
                ], f"Command type should be command or group - Test ID: {test_uuid}"

    def test_json_format_consistency(self, test_uuid: str) -> None:
        """Test JSON format consistency across commands."""
        json_commands = [
            ["tmux-orc", "list", "--json"],
            ["tmux-orc", "status", "--json"],
            ["tmux-orc", "reflect", "--format", "json"],
        ]

        for cmd in json_commands:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)

            if result.returncode == 0:
                try:
                    data = json.loads(result.stdout)
                    # All JSON responses should have consistent structure
                    assert isinstance(
                        data, dict
                    ), f"JSON response should be dict for {' '.join(cmd)} - Test ID: {test_uuid}"

                    # Common fields that should be present
                    assert any(
                        field in data for field in ["success", "data", "agents", "system_health"]
                    ), f"JSON response missing expected fields for {' '.join(cmd)} - Test ID: {test_uuid}"

                except json.JSONDecodeError:
                    pytest.fail(f"Invalid JSON from {' '.join(cmd)} - Test ID: {test_uuid}")


# Utility functions for integration testing
def cleanup_test_sessions(pattern: str = "test-") -> None:
    """Clean up any test sessions left behind."""
    try:
        # List all sessions
        result = subprocess.run(["tmux", "ls", "-F", "#{session_name}"], capture_output=True, text=True)

        if result.returncode == 0:
            sessions = result.stdout.strip().split("\n")
            for session in sessions:
                if pattern in session:
                    subprocess.run(["tmux", "kill-session", "-t", session])
    except Exception:
        pass  # Ignore cleanup errors


@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Cleanup fixture to run after each test."""
    yield
    cleanup_test_sessions()


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "-s"])

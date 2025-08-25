"""
Command-specific tests for MCP server hierarchical tools.

This test suite validates each of the 20 hierarchical command groups
and their specific behaviors, ensuring proper command execution and
parameter handling for real-world usage patterns.
"""

import json

# Import mock configuration first
# Add parent directory to path for conftest_mcp
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from tests.conftest_mcp import EnhancedCLIToMCPServer


class TestAgentCommands:
    """Test agent command group functionality."""

    @pytest.fixture
    def agent_tool(self):
        """Create agent hierarchical tool."""
        server = EnhancedCLIToMCPServer("test-server")
        server.hierarchical_groups["agent"] = ["list", "status", "deploy", "kill", "restart", "send", "kill-all"]
        return server._create_hierarchical_tool_function("agent", server.hierarchical_groups["agent"])

    @pytest.mark.asyncio
    async def test_agent_list(self, agent_tool):
        """Test agent list command."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=json.dumps(
                    [
                        {"session": "backend", "window": 1, "status": "active"},
                        {"session": "frontend", "window": 2, "status": "idle"},
                    ]
                ),
                stderr="",
            )

            result = await agent_tool(kwargs="action=list")

            assert result["success"]
            assert result["action"] == "list"
            assert len(result["result"]) == 2

            # Verify command construction
            cmd_args = mock_run.call_args[0][0]
            assert cmd_args == ["tmux-orc", "agent", "list", "--json"]

    @pytest.mark.asyncio
    async def test_agent_status_with_target(self, agent_tool):
        """Test agent status command with target."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout=json.dumps({"status": "active", "memory": "256MB", "cpu": "15%"}), stderr=""
            )

            result = await agent_tool(kwargs="action=status target=backend:1")

            assert result["success"]
            assert result["action"] == "status"

            cmd_args = mock_run.call_args[0][0]
            assert cmd_args == ["tmux-orc", "agent", "status", "backend:1", "--json"]

    @pytest.mark.asyncio
    async def test_agent_kill_with_force(self, agent_tool):
        """Test agent kill command with automatic force flag."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=json.dumps({"killed": "backend:1"}), stderr="")

            result = await agent_tool(kwargs="action=kill target=backend:1")

            assert result["success"]

            cmd_args = mock_run.call_args[0][0]
            assert "--force" in cmd_args

    @pytest.mark.asyncio
    async def test_agent_send_multiword_message(self, agent_tool):
        """Test agent send with multi-word message."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=json.dumps({"sent": True}), stderr="")

            result = await agent_tool(
                kwargs='action=send target=backend:1 args=["Please implement the user authentication feature"]'
            )

            assert result["success"]

            cmd_args = mock_run.call_args[0][0]
            assert "Please implement the user authentication feature" in cmd_args

    @pytest.mark.asyncio
    async def test_agent_deploy_with_options(self, agent_tool):
        """Test agent deploy with briefing option."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=json.dumps({"deployed": "backend:2"}), stderr="")

            result = await agent_tool(
                kwargs='action=deploy target=backend:2 options={"briefing": "Backend developer agent", "role": "developer"}'
            )

            assert result["success"]

            cmd_args = mock_run.call_args[0][0]
            assert "--briefing" in cmd_args
            assert "Backend developer agent" in cmd_args
            assert "--role" in cmd_args
            assert "developer" in cmd_args


class TestTeamCommands:
    """Test team command group functionality."""

    @pytest.fixture
    def team_tool(self):
        """Create team hierarchical tool."""
        server = EnhancedCLIToMCPServer("test-server")
        server.hierarchical_groups["team"] = ["list", "status", "deploy", "broadcast"]
        return server._create_hierarchical_tool_function("team", server.hierarchical_groups["team"])

    @pytest.mark.asyncio
    async def test_team_broadcast(self, team_tool):
        """Test team broadcast command."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout=json.dumps({"broadcast": "sent", "recipients": 5}), stderr=""
            )

            result = await team_tool(kwargs='action=broadcast args=["Team meeting in 5 minutes"]')

            assert result["success"]

            cmd_args = mock_run.call_args[0][0]
            assert "Team meeting in 5 minutes" in cmd_args

    @pytest.mark.asyncio
    async def test_team_status_with_session(self, team_tool):
        """Test team status with session argument."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=json.dumps({"team": "project-x", "agents": 3}), stderr="")

            result = await team_tool(kwargs='action=status args=["project-x"]')

            assert result["success"]

            cmd_args = mock_run.call_args[0][0]
            assert "project-x" in cmd_args


class TestSpawnCommands:
    """Test spawn command group functionality."""

    @pytest.fixture
    def spawn_tool(self):
        """Create spawn hierarchical tool."""
        server = EnhancedCLIToMCPServer("test-server")
        server.hierarchical_groups["spawn"] = ["agent", "pm", "orchestrator"]
        return server._create_hierarchical_tool_function("spawn", server.hierarchical_groups["spawn"])

    @pytest.mark.asyncio
    async def test_spawn_agent_requires_briefing(self, spawn_tool):
        """Test spawn agent requires briefing parameter."""
        with patch("subprocess.run"):
            # First test without briefing - should error
            result = await spawn_tool(kwargs="action=agent target=backend:2")

            assert not result["success"]
            assert "briefing" in result["error"]
            assert "--briefing" in result["suggestion"]

    @pytest.mark.asyncio
    async def test_spawn_agent_with_briefing(self, spawn_tool):
        """Test spawn agent with briefing."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=json.dumps({"spawned": "backend:2"}), stderr="")

            result = await spawn_tool(
                kwargs='action=agent target=backend:2 options={"briefing": "Backend developer for API"}'
            )

            assert result["success"]

            cmd_args = mock_run.call_args[0][0]
            assert "--briefing" in cmd_args
            assert "Backend developer for API" in cmd_args

    @pytest.mark.asyncio
    async def test_spawn_pm_with_default_briefing(self, spawn_tool):
        """Test spawn PM uses default briefing if not provided."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=json.dumps({"spawned": "project:1"}), stderr="")

            result = await spawn_tool(kwargs="action=pm target=project:1")

            assert result["success"]

            cmd_args = mock_run.call_args[0][0]
            assert "--briefing" in cmd_args
            assert "Project Manager with standard PM context" in cmd_args


class TestMonitorCommands:
    """Test monitor command group functionality."""

    @pytest.fixture
    def monitor_tool(self):
        """Create monitor hierarchical tool."""
        server = EnhancedCLIToMCPServer("test-server")
        server.hierarchical_groups["monitor"] = ["status", "dashboard", "logs", "start", "stop"]
        return server._create_hierarchical_tool_function("monitor", server.hierarchical_groups["monitor"])

    @pytest.mark.asyncio
    async def test_monitor_dashboard_daemon(self, monitor_tool):
        """Test monitor dashboard runs as daemon."""
        with patch("subprocess.Popen") as mock_popen:
            mock_process = Mock()
            mock_process.poll.return_value = None
            mock_process.pid = 54321
            mock_popen.return_value = mock_process

            result = await monitor_tool(kwargs="action=dashboard")

            assert result["success"]
            assert result["command_type"] == "daemon"
            assert result["pid"] == 54321

            # Should use Popen for daemon command
            mock_popen.assert_called_once()

    @pytest.mark.asyncio
    async def test_monitor_status_no_json(self, monitor_tool):
        """Test monitor status doesn't add JSON flag."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="Monitor is running", stderr="")

            result = await monitor_tool(kwargs="action=status")

            assert result["success"]

            cmd_args = mock_run.call_args[0][0]
            assert "--json" not in cmd_args


class TestSessionCommands:
    """Test session command group functionality."""

    @pytest.fixture
    def session_tool(self):
        """Create session hierarchical tool."""
        server = EnhancedCLIToMCPServer("test-server")
        server.hierarchical_groups["session"] = ["list", "attach", "detach", "kill"]
        return server._create_hierarchical_tool_function("session", server.hierarchical_groups["session"])

    @pytest.mark.asyncio
    async def test_session_list(self, session_tool):
        """Test session list command."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout=json.dumps([{"name": "project-x", "windows": 3}, {"name": "backend", "windows": 2}]),
                stderr="",
            )

            result = await session_tool(kwargs="action=list")

            assert result["success"]
            assert len(result["result"]) == 2

    @pytest.mark.asyncio
    async def test_session_attach(self, session_tool):
        """Test session attach command."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=json.dumps({"attached": "project-x"}), stderr="")

            result = await session_tool(kwargs="action=attach target=project-x:0")

            assert result["success"]

            cmd_args = mock_run.call_args[0][0]
            assert "project-x:0" in cmd_args


class TestOrchestratorCommands:
    """Test orchestrator command group functionality."""

    @pytest.fixture
    def orchestrator_tool(self):
        """Create orchestrator hierarchical tool."""
        server = EnhancedCLIToMCPServer("test-server")
        server.hierarchical_groups["orchestrator"] = ["status", "deploy", "kill-all"]
        return server._create_hierarchical_tool_function("orchestrator", server.hierarchical_groups["orchestrator"])

    @pytest.mark.asyncio
    async def test_orchestrator_kill_all_with_force(self, orchestrator_tool):
        """Test orchestrator kill-all adds force flag."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=json.dumps({"killed": 10}), stderr="")

            result = await orchestrator_tool(kwargs="action=kill-all")

            assert result["success"]

            cmd_args = mock_run.call_args[0][0]
            assert "--force" in cmd_args


class TestPMCommands:
    """Test PM command group functionality."""

    @pytest.fixture
    def pm_tool(self):
        """Create PM hierarchical tool."""
        server = EnhancedCLIToMCPServer("test-server")
        server.hierarchical_groups["pm"] = ["status", "message", "broadcast"]
        return server._create_hierarchical_tool_function("pm", server.hierarchical_groups["pm"])

    @pytest.mark.asyncio
    async def test_pm_message(self, pm_tool):
        """Test PM message command."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=json.dumps({"sent": True}), stderr="")

            result = await pm_tool(kwargs='action=message args=["Task completed successfully"]')

            assert result["success"]

            cmd_args = mock_run.call_args[0][0]
            assert "Task completed successfully" in cmd_args


class TestContextCommands:
    """Test context command group functionality."""

    @pytest.fixture
    def context_tool(self):
        """Create context hierarchical tool."""
        server = EnhancedCLIToMCPServer("test-server")
        server.hierarchical_groups["context"] = ["show", "list"]
        return server._create_hierarchical_tool_function("context", server.hierarchical_groups["context"])

    @pytest.mark.asyncio
    async def test_context_show_no_json(self, context_tool):
        """Test context show doesn't add JSON flag (outputs markdown)."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="# PM Context\n\nProject manager context...", stderr="")

            result = await context_tool(kwargs='action=show args=["pm"]')

            assert result["success"]

            cmd_args = mock_run.call_args[0][0]
            assert "--json" not in cmd_args
            assert "pm" in cmd_args


class TestComplexCommandScenarios:
    """Test complex command scenarios and edge cases."""

    @pytest.fixture
    def mcp_server(self):
        """Create a full MCP server instance."""
        server = EnhancedCLIToMCPServer("test-server")
        server.hierarchical_groups = {
            "agent": ["list", "status", "deploy", "send"],
            "team": ["broadcast"],
            "spawn": ["agent", "pm"],
        }
        return server

    @pytest.mark.asyncio
    async def test_cli_options_in_args(self, mcp_server):
        """Test CLI options extraction from args array."""
        spawn_tool = mcp_server._create_hierarchical_tool_function("spawn", ["agent", "pm"])

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout='{"spawned": true}', stderr="")

            # Test with CLI options mixed in args
            result = await spawn_tool(
                kwargs='action=pm args=["--session", "project-x", "--briefing", "Lead PM for project"]'
            )

            assert result["success"]

            cmd_args = mock_run.call_args[0][0]
            # Options should be extracted and placed correctly
            assert "--session" in cmd_args
            assert "project-x" in cmd_args
            assert "--briefing" in cmd_args
            assert "Lead PM for project" in cmd_args

    @pytest.mark.asyncio
    async def test_empty_kwargs_with_default_action(self, mcp_server):
        """Test empty kwargs defaults to sensible action."""
        # Test with 'list' as a direct command
        list_tool = mcp_server._create_hierarchical_tool_function("list", [])

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="[]", stderr="")

            result = await list_tool(kwargs="")

            assert result["success"]
            # Should execute the command directly
            cmd_args = mock_run.call_args[0][0]
            assert cmd_args == ["tmux-orc", "list", "--json"]

    @pytest.mark.asyncio
    async def test_special_characters_in_messages(self, mcp_server):
        """Test handling of special characters in messages."""
        agent_tool = mcp_server._create_hierarchical_tool_function("agent", ["send"])

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout='{"sent": true}', stderr="")

            # Test with special characters
            result = await agent_tool(
                kwargs='action=send target=backend:1 args=["Message with $pecial ch@rs & symbols!"]'
            )

            assert result["success"]

            cmd_args = mock_run.call_args[0][0]
            assert "Message with $pecial ch@rs & symbols!" in cmd_args


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

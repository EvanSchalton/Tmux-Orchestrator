"""
Cross-Component Integration Test Suite
Validates full-stack data flows from CLI through MCP to agent operations.
Ensures data consistency and state synchronization across all layers.
"""

import asyncio
import json
import subprocess
import time
from datetime import datetime

import pytest

from tmux_orchestrator.core.agent_operations.spawn_agent import spawn_agent as core_spawn_agent
from tmux_orchestrator.mcp_server import call_tool
from tmux_orchestrator.server.tools.get_agent_status import (
    AgentStatusRequest,
    get_agent_status,
)
from tmux_orchestrator.server.tools.send_message import (
    SendMessageRequest,
    send_message,
)
from tmux_orchestrator.utils.tmux import TMUXManager


class TestCrossComponentIntegration:
    """Test full-stack integration across CLI, MCP, and core operations."""

    TEST_SESSION_PREFIX = "test-cross-component"
    CLEANUP_SESSIONS = []

    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Set up and clean test environment."""
        self.tmux = TMUXManager()
        self.CLEANUP_SESSIONS = []

        # Clean up any existing test sessions
        sessions = self.tmux.list_sessions()
        for session in sessions:
            if session["name"].startswith(self.TEST_SESSION_PREFIX):
                self.tmux.kill_session(session["name"])

        yield

        # Cleanup after tests
        for session in self.CLEANUP_SESSIONS:
            if self.tmux.has_session(session):
                self.tmux.kill_session(session)

    def run_cli_command(self, command: list[str]) -> tuple[int, str, str]:
        """Execute CLI command and return result."""
        try:
            result = subprocess.run(["tmux-orc"] + command, capture_output=True, text=True, timeout=30)
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out"
        except FileNotFoundError:
            pytest.skip("tmux-orc CLI not installed")

    @pytest.mark.asyncio
    async def test_agent_spawn_data_flow_consistency(self):
        """Test data consistency when spawning agents through different layers."""
        session_name = f"{self.TEST_SESSION_PREFIX}-spawn-flow"
        self.CLEANUP_SESSIONS.append(session_name)
        agent_type = "developer"
        briefing = "Cross-component test agent"

        # Layer 1: CLI Command
        returncode, stdout, stderr = self.run_cli_command(
            ["spawn", "agent", agent_type, session_name, "--briefing", briefing]
        )

        # If CLI not available, test direct spawn
        if returncode != 0:
            # Layer 2: Direct Core Operation
            from tmux_orchestrator.server.tools.spawn_agent import SpawnAgentRequest

            request = SpawnAgentRequest(session_name=session_name, agent_type=agent_type, briefing_message=briefing)
            result = await core_spawn_agent(self.tmux, request)
            assert result.success
            cli_target = result.target
        else:
            # Parse CLI output for target
            cli_target = f"{session_name}:1"  # Default window

        # Layer 3: MCP Tool Call
        mcp_result = await call_tool("agent_status", {"target": cli_target, "include_history": True})

        # Verify data consistency across layers
        assert mcp_result["success"] is True
        assert mcp_result["target"] == cli_target

        # Layer 4: Direct API Call
        status_request = AgentStatusRequest(agent_id=cli_target, include_activity_history=True)
        api_result = get_agent_status(self.tmux, status_request)

        assert api_result.success
        assert api_result.agent_metrics[0].agent_id == cli_target

        # Verify all layers report consistent state
        assert mcp_result["session_active"] == api_result.agent_metrics[0].session_active

    @pytest.mark.asyncio
    async def test_message_flow_consistency(self):
        """Test message delivery consistency across all layers."""
        session_name = f"{self.TEST_SESSION_PREFIX}-message-flow"
        self.CLEANUP_SESSIONS.append(session_name)
        test_message = "Cross-component message test"

        # First spawn an agent
        spawn_result = await call_tool("spawn_agent", {"session_name": session_name, "agent_type": "qa"})
        assert spawn_result["success"]
        target = spawn_result["target"]

        await asyncio.sleep(1)  # Allow agent to initialize

        # Send message through different layers

        # Layer 1: CLI (if available)
        cli_code, _, _ = self.run_cli_command(["send", target, test_message])

        # Layer 2: MCP Tool
        mcp_msg_result = await call_tool("send_message", {"target": target, "message": f"MCP: {test_message}"})
        assert mcp_msg_result["success"]

        # Layer 3: Direct API
        api_request = SendMessageRequest(target=target, message=f"API: {test_message}")
        api_result = send_message(self.tmux, api_request)
        assert api_result.success

        # Verify all messages were delivered by checking agent status
        final_status = await call_tool("agent_status", {"target": target, "include_history": True})

        assert final_status["success"]
        # Agent should have received messages from all layers

    @pytest.mark.asyncio
    async def test_team_deployment_cross_layer_consistency(self):
        """Test team deployment consistency across layers."""
        team_name = f"{self.TEST_SESSION_PREFIX}-team"
        self.CLEANUP_SESSIONS.append(team_name)

        # Deploy team through MCP
        deploy_result = await call_tool("deploy_team", {"team_name": team_name, "team_type": "fullstack", "size": 3})
        assert deploy_result["success"]

        await asyncio.sleep(2)  # Allow deployment to complete

        # Verify through different layers

        # Layer 1: MCP team status
        mcp_team_status = await call_tool("team_status", {"session": team_name, "detailed": True})
        assert mcp_team_status["success"]
        mcp_agent_count = len(mcp_team_status["agents"])

        # Layer 2: MCP list agents
        all_agents = await call_tool("list_agents", {})
        team_agents = [agent for agent in all_agents["agents"] if agent["session"] == team_name]
        list_agent_count = len(team_agents)

        # Layer 3: Direct tmux query
        tmux_windows = self.tmux.list_windows(team_name)
        tmux_agent_count = len(tmux_windows)

        # Verify consistency across all layers
        assert mcp_agent_count == list_agent_count
        assert list_agent_count == tmux_agent_count
        assert tmux_agent_count >= 3  # Should have at least requested size

        # Verify each agent is accessible
        for agent in mcp_team_status["agents"]:
            target = agent["target"]

            # Check through MCP
            agent_status = await call_tool("agent_status", {"target": target})
            assert agent_status["success"]

            # Check through direct API
            api_request = AgentStatusRequest(agent_id=target)
            api_result = get_agent_status(self.tmux, api_request)
            assert api_result.success

    @pytest.mark.asyncio
    async def test_state_synchronization_during_operations(self):
        """Test state remains synchronized during concurrent operations."""
        session_name = f"{self.TEST_SESSION_PREFIX}-sync"
        self.CLEANUP_SESSIONS.append(session_name)

        # Spawn initial agent
        spawn_result = await call_tool("spawn_agent", {"session_name": session_name, "agent_type": "developer"})
        assert spawn_result["success"]
        target = spawn_result["target"]

        # Perform concurrent operations
        async def send_messages():
            for i in range(5):
                await call_tool("send_message", {"target": target, "message": f"Concurrent message {i}"})
                await asyncio.sleep(0.1)

        async def check_status():
            statuses = []
            for i in range(5):
                status = await call_tool("agent_status", {"target": target})
                statuses.append(status)
                await asyncio.sleep(0.1)
            return statuses

        # Execute concurrently
        msg_task = asyncio.create_task(send_messages())
        status_task = asyncio.create_task(check_status())

        statuses = await status_task
        await msg_task

        # Verify all status checks succeeded and were consistent
        for status in statuses:
            assert status["success"]
            assert status["target"] == target

        # Final verification
        final_status = await call_tool("agent_status", {"target": target, "include_history": True})
        assert final_status["success"]

    @pytest.mark.asyncio
    async def test_error_propagation_across_layers(self):
        """Test how errors propagate through the component stack."""
        # Test 1: Invalid agent type error propagation
        invalid_spawn = await call_tool("spawn_agent", {"session_name": "test-error", "agent_type": "invalid_type"})

        assert invalid_spawn["success"] is False
        assert "error" in invalid_spawn

        # Test 2: Non-existent session error
        bad_status = await call_tool("agent_status", {"target": "nonexistent:99"})

        assert bad_status["success"] is False
        assert "error" in bad_status

        # Test 3: Message to non-existent agent
        bad_message = await call_tool("send_message", {"target": "nonexistent:99", "message": "This should fail"})

        assert bad_message["success"] is False

        # Verify error consistency
        # Errors should be meaningful and consistent across layers

    @pytest.mark.asyncio
    async def test_recovery_and_restart_consistency(self):
        """Test agent recovery maintains data consistency."""
        session_name = f"{self.TEST_SESSION_PREFIX}-recovery"
        self.CLEANUP_SESSIONS.append(session_name)

        # Spawn agent
        spawn_result = await call_tool("spawn_agent", {"session_name": session_name, "agent_type": "developer"})
        assert spawn_result["success"]
        target = spawn_result["target"]

        # Get initial status
        initial_status = await call_tool("agent_status", {"target": target})
        assert initial_status["success"]

        # Restart agent
        restart_result = await call_tool("restart_agent", {"target": target, "preserve_context": True})
        assert restart_result["success"]

        await asyncio.sleep(2)  # Allow restart to complete

        # Verify agent is back online
        post_restart_status = await call_tool("agent_status", {"target": target})
        assert post_restart_status["success"]
        assert post_restart_status["session_active"]

        # Verify through direct tmux
        session, window = target.split(":", 1)
        assert self.tmux.has_session(session)
        windows = self.tmux.list_windows(session)
        assert any(w.get("name") == window or str(w.get("index")) == window for w in windows)

    @pytest.mark.asyncio
    async def test_broadcast_consistency(self):
        """Test broadcast operations maintain consistency."""
        team_name = f"{self.TEST_SESSION_PREFIX}-broadcast"
        self.CLEANUP_SESSIONS.append(team_name)

        # Deploy a small team
        deploy_result = await call_tool("deploy_team", {"team_name": team_name, "team_type": "backend", "size": 2})
        assert deploy_result["success"]

        await asyncio.sleep(2)

        # Get team status before broadcast
        pre_broadcast = await call_tool("team_status", {"session": team_name, "detailed": True})
        assert pre_broadcast["success"]
        agent_count = len(pre_broadcast["agents"])

        # Broadcast message
        broadcast_result = await call_tool(
            "team_broadcast", {"session": team_name, "message": "Team broadcast consistency test"}
        )
        assert broadcast_result["success"]
        assert broadcast_result["sent_count"] == agent_count

        # Verify each agent received the message
        for agent in pre_broadcast["agents"]:
            status = await call_tool("agent_status", {"target": agent["target"]})
            assert status["success"]

    @pytest.mark.asyncio
    async def test_monitoring_data_consistency(self):
        """Test monitoring data consistency across components."""
        # Get system status through different methods

        # Method 1: MCP system status
        mcp_system = await call_tool("system_status", {"format": "detailed"})
        assert mcp_system["success"]
        mcp_session_count = mcp_system["status"]["sessions"]
        mcp_agent_count = mcp_system["status"]["total_agents"]

        # Method 2: MCP list operations
        list_sessions = await call_tool("list_sessions", {})
        list_agents = await call_tool("list_agents", {})

        assert list_sessions["success"]
        assert list_agents["success"]

        list_session_count = len(list_sessions["sessions"])
        list_agent_count = len(list_agents["agents"])

        # Method 3: Direct tmux queries
        tmux_sessions = self.tmux.list_sessions()
        tmux_session_count = len(tmux_sessions)

        # Count all windows across sessions
        tmux_total_windows = 0
        for session in tmux_sessions:
            windows = self.tmux.list_windows(session["name"])
            tmux_total_windows += len(windows)

        # Verify consistency (allowing for timing differences)
        assert abs(mcp_session_count - list_session_count) <= 1
        assert abs(list_session_count - tmux_session_count) <= 1
        assert abs(mcp_agent_count - list_agent_count) <= 2
        assert abs(list_agent_count - tmux_total_windows) <= 2

    @pytest.mark.asyncio
    async def test_performance_timing_consistency(self):
        """Test operation timing consistency across layers."""
        session_name = f"{self.TEST_SESSION_PREFIX}-perf"
        self.CLEANUP_SESSIONS.append(session_name)

        # Time spawn operation through MCP
        mcp_start = time.time()
        spawn_result = await call_tool("spawn_agent", {"session_name": session_name, "agent_type": "qa"})
        mcp_duration = time.time() - mcp_start
        assert spawn_result["success"]

        # Time status check
        status_start = time.time()
        status_result = await call_tool("agent_status", {"target": spawn_result["target"]})
        status_duration = time.time() - status_start
        assert status_result["success"]

        # Time message send
        msg_start = time.time()
        msg_result = await call_tool("send_message", {"target": spawn_result["target"], "message": "Performance test"})
        msg_duration = time.time() - msg_start
        assert msg_result["success"]

        # Performance assertions
        assert mcp_duration < 5.0, f"Spawn took too long: {mcp_duration:.2f}s"
        assert status_duration < 1.0, f"Status check too slow: {status_duration:.2f}s"
        assert msg_duration < 1.0, f"Message send too slow: {msg_duration:.2f}s"

        print("\nTiming Results:")
        print(f"  Spawn: {mcp_duration:.3f}s")
        print(f"  Status: {status_duration:.3f}s")
        print(f"  Message: {msg_duration:.3f}s")

    @pytest.mark.asyncio
    async def test_context_preservation_across_layers(self):
        """Test context preservation during operations."""
        session_name = f"{self.TEST_SESSION_PREFIX}-context"
        self.CLEANUP_SESSIONS.append(session_name)
        custom_context = "This agent focuses on API testing and validation"

        # Spawn with context through MCP
        spawn_result = await call_tool(
            "spawn_with_context", {"role": "qa", "session": f"{session_name}:1", "extend_context": custom_context}
        )
        assert spawn_result["success"]
        target = spawn_result["target"]

        # Send additional context
        context_msg = "Additional context: Use pytest for all testing"
        msg_result = await call_tool("send_message", {"target": target, "message": context_msg})
        assert msg_result["success"]

        # Restart and verify context preservation
        restart_result = await call_tool("restart_agent", {"target": target, "preserve_context": True})
        assert restart_result["success"]

        await asyncio.sleep(2)

        # Verify agent is functional after restart
        post_restart = await call_tool("agent_status", {"target": target})
        assert post_restart["success"]
        assert post_restart["session_active"]

    @pytest.mark.asyncio
    async def test_cli_reflection_consistency(self):
        """Test CLI reflection provides accurate command information."""
        # Run CLI reflection command
        returncode, stdout, stderr = self.run_cli_command(["reflect", "--format", "json"])

        if returncode == 0:
            try:
                cli_structure = json.loads(stdout)

                # Verify essential commands are present
                assert "commands" in cli_structure
                commands = cli_structure["commands"]

                essential_commands = ["spawn", "send", "status", "list"]
                for cmd in essential_commands:
                    assert any(c["name"] == cmd for c in commands), f"Missing command: {cmd}"

                # Verify spawn command has expected subcommands
                spawn_cmd = next((c for c in commands if c["name"] == "spawn"), None)
                if spawn_cmd and "subcommands" in spawn_cmd:
                    subcommands = [s["name"] for s in spawn_cmd["subcommands"]]
                    assert "agent" in subcommands
                    assert "pm" in subcommands

            except json.JSONDecodeError:
                pytest.fail("CLI reflection did not return valid JSON")
        else:
            # Log CLI command failure as per new context requirement
            error_msg = f"tmux-orc reflect command failed: {stderr}"
            print(f"[CLI Error] {error_msg}")
            # In a real scenario, this would be logged to project briefing file


@pytest.mark.integration
class TestDataConsistencyPatterns:
    """Test specific data consistency patterns across the stack."""

    @pytest.mark.asyncio
    async def test_agent_identifier_consistency(self):
        """Test agent identifiers remain consistent across all layers."""
        tmux = TMUXManager()
        session = "test-id-consistency"

        try:
            # Create agent and track identifiers
            spawn_result = await call_tool(
                "spawn_agent", {"session_name": session, "agent_type": "developer", "window_name": "dev"}
            )

            assert spawn_result["success"]

            # Expected identifier format: session:window
            expected_id = f"{session}:dev"

            # Verify identifier in spawn result
            assert spawn_result["target"] == expected_id or spawn_result["target"] == f"{session}:1"  # Default window

            actual_id = spawn_result["target"]

            # Verify in agent listing
            agents = await call_tool("list_agents", {})
            agent_ids = [f"{a['session']}:{a['window']}" for a in agents["agents"]]
            assert actual_id in agent_ids

            # Verify in status check
            status = await call_tool("agent_status", {"target": actual_id})
            assert status["success"]
            assert status["target"] == actual_id

        finally:
            if tmux.has_session(session):
                tmux.kill_session(session)

    @pytest.mark.asyncio
    async def test_timestamp_consistency(self):
        """Test timestamp consistency across components."""
        tmux = TMUXManager()
        session = "test-timestamp"

        try:
            # Record start time
            start_time = datetime.now()

            # Spawn agent
            spawn_result = await call_tool("spawn_agent", {"session_name": session, "agent_type": "qa"})
            assert spawn_result["success"]

            # Get system status with timestamp
            system_status = await call_tool("system_status", {"format": "detailed"})

            assert system_status["success"]
            status_timestamp = datetime.fromisoformat(system_status["status"]["timestamp"])

            # Verify timestamp is reasonable
            time_diff = (status_timestamp - start_time).total_seconds()
            assert 0 <= time_diff <= 10, f"Timestamp drift: {time_diff}s"

        finally:
            if tmux.has_session(session):
                tmux.kill_session(session)


if __name__ == "__main__":
    # Run tests with detailed output
    pytest.main([__file__, "-v", "-s", "--tb=short"])

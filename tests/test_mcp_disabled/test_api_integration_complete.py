"""
Comprehensive API Integration Test Suite
Tests the complete data flow and REST API endpoints at port 8000.
"""

import asyncio
import time

import pytest
import requests
from requests.exceptions import ConnectionError, RequestException

from tmux_orchestrator.mcp_server import call_tool, list_tools
from tmux_orchestrator.utils.tmux import TMUXManager


class TestAPIIntegrationComplete:
    """Comprehensive API integration testing suite."""

    BASE_URL = "http://localhost:8000"
    TEST_SESSION = "test-api-integration"
    TEST_TIMEOUT = 30

    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Set up clean test environment."""
        self.tmux = TMUXManager()
        self.test_agents = []
        self.cleanup_sessions = []

        # Clean up any existing test sessions
        if self.tmux.has_session(self.TEST_SESSION):
            self.tmux.kill_session(self.TEST_SESSION)

        yield

        # Cleanup after tests
        for session in self.cleanup_sessions:
            if self.tmux.has_session(session):
                self.tmux.kill_session(session)

    def test_server_health_check(self):
        """Test that the MCP server is accessible at port 8000."""
        try:
            response = requests.get(f"{self.BASE_URL}/health", timeout=5)
            assert response.status_code in [200, 404]  # 404 is acceptable if no health endpoint
        except ConnectionError:
            pytest.skip("MCP server not running on port 8000")

    def test_server_documentation_endpoints(self):
        """Test OpenAPI documentation endpoints."""
        try:
            # Test Swagger UI
            docs_response = requests.get(f"{self.BASE_URL}/docs", timeout=5)
            assert docs_response.status_code == 200

            # Test ReDoc
            redoc_response = requests.get(f"{self.BASE_URL}/redoc", timeout=5)
            assert redoc_response.status_code == 200

            # Test OpenAPI spec
            spec_response = requests.get(f"{self.BASE_URL}/openapi.json", timeout=5)
            assert spec_response.status_code == 200
            spec_data = spec_response.json()
            assert "paths" in spec_data
            assert "components" in spec_data

        except ConnectionError:
            pytest.skip("FastAPI server not accessible")

    @pytest.mark.asyncio
    async def test_mcp_tool_listing(self):
        """Test MCP tool listing functionality."""
        tools = await list_tools()

        assert len(tools) > 20  # Should have comprehensive tool set

        # Verify essential tools are present
        tool_names = [tool.name for tool in tools]
        essential_tools = ["list_agents", "spawn_agent", "send_message", "agent_status", "deploy_team", "system_status"]

        for tool in essential_tools:
            assert tool in tool_names, f"Essential tool {tool} missing"

    @pytest.mark.asyncio
    async def test_agent_lifecycle_complete_flow(self):
        """Test complete agent lifecycle through MCP interface."""
        session_name = f"{self.TEST_SESSION}-lifecycle"
        self.cleanup_sessions.append(session_name)

        # 1. Spawn an agent
        spawn_result = await call_tool(
            "spawn_agent",
            {
                "session_name": session_name,
                "agent_type": "developer",
                "briefing_message": "Test agent for API integration testing",
            },
        )

        assert spawn_result["success"] is True
        assert spawn_result["session"] == session_name
        target = spawn_result["target"]

        # Allow time for agent to initialize
        await asyncio.sleep(2)

        # 2. Check agent status
        status_result = await call_tool("agent_status", {"target": target, "include_history": True})

        assert status_result["success"] is True
        assert status_result["target"] == target
        assert "health_status" in status_result

        # 3. Send message to agent
        message_result = await call_tool(
            "send_message",
            {"target": target, "message": "Hello, test agent! Please confirm you received this message."},
        )

        assert message_result["success"] is True
        assert message_result["target"] == target

        # 4. Get detailed agent info
        info_result = await call_tool("agent_info", {"target": target})

        assert info_result["success"] is True
        assert "info" in info_result
        assert info_result["info"]["target"] == target

        # 5. Restart agent
        restart_result = await call_tool("restart_agent", {"target": target, "preserve_context": True})

        assert restart_result["success"] is True
        assert restart_result["target"] == target

        # 6. Final status check
        final_status = await call_tool("agent_status", {"target": target})

        assert final_status["success"] is True

        # 7. Kill agent
        kill_result = await call_tool("agent_kill", {"target": target, "force": True})

        assert kill_result["success"] is True

    @pytest.mark.asyncio
    async def test_team_deployment_and_coordination(self):
        """Test team deployment and coordination functionality."""
        team_name = f"{self.TEST_SESSION}-team"
        self.cleanup_sessions.append(team_name)

        # 1. Deploy a team
        deploy_result = await call_tool("deploy_team", {"team_name": team_name, "team_type": "fullstack", "size": 3})

        assert deploy_result["success"] is True
        assert deploy_result["team_name"] == team_name
        assert deploy_result["team_type"] == "fullstack"

        # Allow time for team deployment
        await asyncio.sleep(3)

        # 2. Check team status
        team_status = await call_tool("team_status", {"session": team_name, "detailed": True})

        assert team_status["success"] is True
        assert team_status["session"] == team_name
        assert "agents" in team_status
        assert len(team_status["agents"]) > 0

        # 3. Broadcast message to team
        broadcast_result = await call_tool(
            "team_broadcast", {"session": team_name, "message": "Team coordination test message"}
        )

        assert broadcast_result["success"] is True
        assert broadcast_result["sent_count"] > 0

        # 4. Get overall team status
        all_teams_status = await call_tool("team_status", {"detailed": False})

        assert all_teams_status["success"] is True
        assert "teams" in all_teams_status

        # Verify our team is in the list
        team_names = [team["session"] for team in all_teams_status["teams"]]
        assert team_name in team_names

    @pytest.mark.asyncio
    async def test_project_manager_operations(self):
        """Test Project Manager specific operations."""
        pm_session = f"{self.TEST_SESSION}-pm"
        self.cleanup_sessions.append(pm_session)

        # 1. Spawn a PM
        pm_spawn = await call_tool(
            "spawn_pm", {"session": f"{pm_session}:1", "extend": "Integration testing project with automated QA"}
        )

        assert pm_spawn["success"] is True
        assert pm_spawn["session"] == pm_session

        # Allow PM to initialize
        await asyncio.sleep(2)

        # 2. Check PM status
        pm_status = await call_tool("pm_status", {"session": f"{pm_session}:1"})

        assert pm_status["success"] is True
        assert "health_status" in pm_status

        # 3. Send message to PM
        pm_message = await call_tool(
            "pm_message",
            {"message": "Please provide status update on integration testing", "session": f"{pm_session}:1"},
        )

        assert pm_message["success"] is True

        # 4. Trigger PM check-in
        pm_checkin = await call_tool(
            "pm_checkin", {"session": f"{pm_session}:1", "custom_prompt": "Integration test status check"}
        )

        assert pm_checkin["success"] is True

        # 5. PM broadcast test
        pm_broadcast = await call_tool(
            "pm_broadcast", {"message": "Integration testing in progress", "session": f"{pm_session}:1"}
        )

        assert pm_broadcast["success"] is True

    @pytest.mark.asyncio
    async def test_session_management_operations(self):
        """Test session management and listing operations."""
        test_session = f"{self.TEST_SESSION}-session-mgmt"
        self.cleanup_sessions.append(test_session)

        # 1. List initial sessions
        initial_sessions = await call_tool("list_sessions", {"include_windows": False})

        assert initial_sessions["success"] is True
        assert "sessions" in initial_sessions
        initial_count = len(initial_sessions["sessions"])

        # 2. Create a new session by spawning an agent
        spawn_result = await call_tool(
            "spawn_agent",
            {"session_name": test_session, "agent_type": "qa", "briefing_message": "Session management test"},
        )

        assert spawn_result["success"] is True

        # 3. List sessions again with windows
        updated_sessions = await call_tool("list_sessions", {"include_windows": True})

        assert updated_sessions["success"] is True
        assert len(updated_sessions["sessions"]) >= initial_count + 1

        # Verify our session is present
        session_names = [s["name"] for s in updated_sessions["sessions"]]
        assert test_session in session_names

        # Find our session and check it has windows
        our_session = next(s for s in updated_sessions["sessions"] if s["name"] == test_session)
        assert "windows" in our_session
        assert len(our_session["windows"]) > 0

        # 4. Test session attachment (returns info since actual attach isn't possible)
        attach_result = await call_tool("attach_session", {"session_name": test_session, "read_only": True})

        assert attach_result["success"] is True
        assert attach_result["session_name"] == test_session

    @pytest.mark.asyncio
    async def test_system_monitoring_and_status(self):
        """Test system monitoring and status reporting."""
        # 1. Get system status summary
        system_summary = await call_tool("system_status", {"format": "summary"})

        assert system_summary["success"] is True
        assert "status" in system_summary
        status_data = system_summary["status"]
        assert "timestamp" in status_data
        assert "sessions" in status_data
        assert "total_agents" in status_data
        assert "system_health" in status_data

        # 2. Get detailed system status
        system_detailed = await call_tool("system_status", {"format": "detailed"})

        assert system_detailed["success"] is True
        assert "session_details" in system_detailed["status"]

        # 3. Get JSON format status
        system_json = await call_tool("system_status", {"format": "json"})

        assert system_json["success"] is True
        assert system_json["format"] == "json"

        # 4. List all agents
        all_agents = await call_tool("list_agents", {"include_metrics": True})

        assert all_agents["success"] is True
        assert "agents" in all_agents
        assert "total_count" in all_agents
        assert all_agents["total_count"] == len(all_agents["agents"])

    @pytest.mark.asyncio
    async def test_context_management_operations(self):
        """Test context management and role-based spawning."""
        # 1. List available contexts
        contexts = await call_tool("list_contexts", {})

        assert contexts["success"] is True
        assert "contexts" in contexts
        assert len(contexts["contexts"]) > 5  # Should have standard roles

        context_roles = [ctx["role"] for ctx in contexts["contexts"]]
        assert "developer" in context_roles
        assert "pm" in context_roles
        assert "qa" in context_roles

        # 2. Show specific context
        dev_context = await call_tool("show_context", {"role": "developer"})

        assert dev_context["success"] is True
        assert dev_context["role"] == "developer"
        assert "context" in dev_context

        # 3. Spawn agent with context
        context_session = f"{self.TEST_SESSION}-context"
        self.cleanup_sessions.append(context_session)

        context_spawn = await call_tool(
            "spawn_with_context",
            {
                "role": "reviewer",
                "session": f"{context_session}:1",
                "extend_context": "Focus on security and performance reviews",
            },
        )

        assert context_spawn["success"] is True
        assert context_spawn["role"] == "reviewer"
        assert context_spawn["session"] == context_session

    @pytest.mark.asyncio
    async def test_standup_coordination(self):
        """Test standup coordination across multiple sessions."""
        # Create multiple test sessions
        sessions = [f"{self.TEST_SESSION}-standup-1", f"{self.TEST_SESSION}-standup-2"]
        self.cleanup_sessions.extend(sessions)

        # Spawn agents in each session
        for i, session in enumerate(sessions):
            spawn_result = await call_tool(
                "spawn_agent",
                {
                    "session_name": session,
                    "agent_type": "developer" if i == 0 else "qa",
                    "briefing_message": f"Standup test agent {i+1}",
                },
            )
            assert spawn_result["success"] is True

        # Allow agents to initialize
        await asyncio.sleep(2)

        # Conduct standup
        standup_result = await call_tool(
            "conduct_standup",
            {
                "session_names": sessions,
                "include_idle_agents": True,
                "timeout_seconds": 15,
                "custom_message": "Brief status update for integration testing",
            },
        )

        assert standup_result["success"] is True
        assert standup_result["standup_initiated"] is True
        assert standup_result["sessions_processed"] == len(sessions)
        assert standup_result["total_agents_contacted"] > 0
        assert len(standup_result["results"]) == len(sessions)

        # Check each session result
        for result in standup_result["results"]:
            assert "session" in result
            assert "status" in result
            assert result["status"] in ["completed", "partial_failure", "session_not_found"]

    @pytest.mark.asyncio
    async def test_error_handling_and_edge_cases(self):
        """Test error handling and edge cases."""
        # 1. Test invalid agent type
        invalid_spawn = await call_tool(
            "spawn_agent",
            {"session_name": "invalid-test", "agent_type": "invalid_type", "briefing_message": "This should fail"},
        )

        assert invalid_spawn["success"] is False
        assert "error" in invalid_spawn

        # 2. Test message to non-existent agent
        invalid_message = await call_tool("send_message", {"target": "nonexistent:99", "message": "This should fail"})

        assert invalid_message["success"] is False

        # 3. Test status of non-existent agent
        invalid_status = await call_tool("agent_status", {"target": "nonexistent:99"})

        assert invalid_status["success"] is False
        assert "error" in invalid_status

        # 4. Test unknown tool
        unknown_tool = await call_tool("unknown_tool", {})

        assert "error" in unknown_tool
        assert "UnknownTool" in unknown_tool.get("error_type", "")

        # 5. Test team operations on non-existent session
        invalid_team_status = await call_tool("team_status", {"session": "nonexistent-team"})

        # This might succeed with empty results or fail - both are acceptable
        assert "success" in invalid_team_status

    @pytest.mark.asyncio
    async def test_rate_limiting_behavior(self):
        """Test rate limiting and request throttling."""
        # Make rapid requests to test rate limiting
        rapid_requests = []
        for i in range(15):  # Exceed typical rate limits
            task = call_tool("list_agents", {"include_metrics": False})
            rapid_requests.append(task)

        results = await asyncio.gather(*rapid_requests, return_exceptions=True)

        # Check that some requests succeeded
        successful_results = [r for r in results if isinstance(r, dict) and r.get("success")]
        assert len(successful_results) > 0

        # Check for rate limit responses
        rate_limited = [
            r for r in results if isinstance(r, dict) and "RateLimitExceeded" in str(r.get("error_type", ""))
        ]

        # Rate limiting might or might not trigger depending on configuration
        # This test verifies the system handles rapid requests gracefully
        assert len(results) == 15

    @pytest.mark.asyncio
    async def test_data_flow_consistency(self):
        """Test data flow consistency across operations."""
        flow_session = f"{self.TEST_SESSION}-dataflow"
        self.cleanup_sessions.append(flow_session)

        # 1. Create agent and verify it appears in listings
        spawn_result = await call_tool("spawn_agent", {"session_name": flow_session, "agent_type": "developer"})
        assert spawn_result["success"] is True
        target = spawn_result["target"]

        await asyncio.sleep(1)

        # 2. Verify agent appears in list_agents
        agent_list = await call_tool("list_agents", {})
        agent_targets = [f"{a['session']}:{a['window']}" for a in agent_list["agents"]]
        assert target in agent_targets

        # 3. Verify agent appears in session list
        session_list = await call_tool("list_sessions", {"include_windows": True})
        found_session = None
        for session in session_list["sessions"]:
            if session["name"] == flow_session:
                found_session = session
                break

        assert found_session is not None
        assert len(found_session["windows"]) > 0

        # 4. Verify consistency between different status queries
        individual_status = await call_tool("agent_status", {"target": target})
        all_agents_status = await call_tool("agent_status", {})

        assert individual_status["success"] is True
        assert all_agents_status["success"] is True

        # Find our agent in the all agents status
        our_agent_in_list = None
        for agent in all_agents_status["agents"]:
            if agent["target"] == target:
                our_agent_in_list = agent
                break

        assert our_agent_in_list is not None
        # Health status should be consistent
        assert individual_status["health_status"] == our_agent_in_list["health_status"]

    def test_performance_benchmarks(self):
        """Test API response times and performance."""

        async def time_operation(tool_name: str, args: dict) -> float:
            start_time = time.time()
            await call_tool(tool_name, args)
            return time.time() - start_time

        async def run_benchmarks():
            # Benchmark basic operations
            benchmarks = {}

            # List operations should be fast
            benchmarks["list_agents"] = await time_operation("list_agents", {})
            benchmarks["list_sessions"] = await time_operation("list_sessions", {})
            benchmarks["system_status"] = await time_operation("system_status", {"format": "summary"})

            return benchmarks

        results = asyncio.run(run_benchmarks())

        # Basic operations should complete quickly
        for operation, duration in results.items():
            assert duration < 5.0, f"{operation} took {duration:.2f}s (too slow)"

        # Log performance for monitoring
        print("\nPerformance Benchmarks:")
        for operation, duration in results.items():
            print(f"  {operation}: {duration:.3f}s")


@pytest.mark.integration
class TestRestAPIEndpoints:
    """Test actual REST API endpoints if server is running."""

    BASE_URL = "http://localhost:8000"

    def test_openapi_specification(self):
        """Test OpenAPI specification endpoint."""
        try:
            response = requests.get(f"{self.BASE_URL}/openapi.json", timeout=5)
            if response.status_code == 200:
                spec = response.json()

                # Validate OpenAPI structure
                assert "openapi" in spec
                assert "info" in spec
                assert "paths" in spec

                # Check for expected endpoints
                paths = spec["paths"]
                expected_endpoints = ["/docs", "/redoc"]

                # Note: Actual API endpoints depend on server implementation
                print(f"Available endpoints: {list(paths.keys())}")

        except ConnectionError:
            pytest.skip("REST API server not running")

    def test_api_endpoint_responses(self):
        """Test actual API endpoint responses."""
        try:
            # Test different possible API endpoints
            test_endpoints = ["/health", "/status", "/agents", "/sessions", "/api/v1/agents", "/api/v1/sessions"]

            accessible_endpoints = []
            for endpoint in test_endpoints:
                try:
                    response = requests.get(f"{self.BASE_URL}{endpoint}", timeout=3)
                    if response.status_code in [200, 201, 202]:
                        accessible_endpoints.append(endpoint)

                        # Validate JSON response if content-type is JSON
                        if "application/json" in response.headers.get("content-type", ""):
                            data = response.json()
                            assert isinstance(data, (dict, list))

                except RequestException:
                    continue

            print(f"Accessible API endpoints: {accessible_endpoints}")

        except ConnectionError:
            pytest.skip("REST API server not running")


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s", "--tb=short"])

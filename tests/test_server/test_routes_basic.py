"""Basic tests for MCP server routes existence and basic functionality."""

import pytest
from fastapi.testclient import TestClient

from tmux_orchestrator.server import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestRouteExistence:
    """Test that all expected routes exist and respond appropriately."""

    def test_monitor_routes_exist(self, client):
        """Test monitoring routes exist."""
        # These should return either 200 with data or 422/500 due to missing dependencies
        # but NOT 404 (which would mean route doesn't exist)

        monitor_routes = [
            "/monitor/health",
            "/monitor/sessions",
            "/monitor/agents/idle",
            "/monitor/agents/active",
        ]

        for route in monitor_routes:
            response = client.get(route)
            assert response.status_code != 404, f"Route {route} should exist"

    def test_messages_routes_exist(self, client):
        """Test message routes exist."""
        # Test POST routes exist (will return 422 for missing body, but not 404)
        post_routes = [
            "/messages/send",
            "/messages/broadcast",
            "/messages/interrupt",
        ]

        for route in post_routes:
            response = client.post(route, json={})
            assert response.status_code != 404, f"POST route {route} should exist"

        # Test GET routes
        get_routes = [
            "/messages/history?session=test&window=test&lines=10",
        ]

        for route in get_routes:
            response = client.get(route)
            assert response.status_code != 404, f"GET route {route} should exist"

    def test_coordination_routes_exist(self, client):
        """Test coordination routes exist."""
        post_routes = [
            "/coordination/deploy-team",
            "/coordination/standup",
            "/coordination/recover-team",
        ]

        for route in post_routes:
            response = client.post(route, json={})
            assert response.status_code != 404, f"Route {route} should exist"

        get_routes = [
            "/coordination/list-teams",
        ]

        for route in get_routes:
            response = client.get(route)
            assert response.status_code != 404, f"Route {route} should exist"

    def test_agents_routes_exist(self, client):
        """Test agent management routes exist."""
        post_routes = [
            "/agents/spawn",
            "/agents/restart",
        ]

        for route in post_routes:
            response = client.post(route, json={})
            assert response.status_code != 404, f"Route {route} should exist"

        get_routes = [
            "/agents/list",
            "/agents/status",
        ]

        for route in get_routes:
            response = client.get(route)
            assert response.status_code != 404, f"Route {route} should exist"

    def test_tasks_routes_exist(self, client):
        """Test task management routes exist."""
        post_routes = ["/tasks/create"]

        for route in post_routes:
            response = client.post(route, json={})
            assert response.status_code != 404, f"Route {route} should exist"

        get_routes = [
            "/tasks/list",
        ]

        for route in get_routes:
            response = client.get(route)
            assert response.status_code != 404, f"Route {route} should exist"


class TestErrorHandling:
    """Test error handling across routes."""

    def test_invalid_json_handling(self, client):
        """Test routes handle invalid JSON properly."""
        response = client.post("/messages/send", content="invalid json", headers={"Content-Type": "application/json"})

        # Should return 422 (validation error) not 500 (server error)
        assert response.status_code == 422

    def test_missing_route_404(self, client):
        """Test that non-existent routes return 404."""
        response = client.get("/nonexistent/route")
        assert response.status_code == 404

        response = client.post("/nonexistent/route")
        assert response.status_code == 404

    def test_method_not_allowed(self, client):
        """Test method not allowed errors."""
        # Try POST on a GET-only route
        response = client.post("/monitor/health")
        assert response.status_code == 405  # Method not allowed


class TestHealthEndpoints:
    """Test the basic health endpoints that should always work."""

    def test_root_endpoint(self, client):
        """Test root endpoint returns server info."""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "status" in data
        assert data["status"] == "running"

    def test_health_endpoint(self, client):
        """Test health endpoint."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"

    def test_openapi_endpoints(self, client):
        """Test OpenAPI documentation endpoints."""
        # OpenAPI JSON
        response = client.get("/openapi.json")
        assert response.status_code == 200

        # Interactive docs
        response = client.get("/docs")
        assert response.status_code == 200

        # ReDoc
        response = client.get("/redoc")
        assert response.status_code == 200

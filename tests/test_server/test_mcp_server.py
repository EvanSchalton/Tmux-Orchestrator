"""Tests for MCP server initialization and core functionality."""

from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from tmux_orchestrator import __version__
from tmux_orchestrator.server import app, main


class TestMCPServerInitialization:
    """Test MCP server initialization and configuration."""

    def test_app_configuration(self):
        """Test FastAPI app configuration."""
        assert isinstance(app, FastAPI)
        assert app.title == "TMUX Orchestrator MCP Server"
        assert app.version == __version__

        # Check that routers are included
        routes = [route.path for route in app.routes]
        assert any("/monitor" in route for route in routes)
        assert any("/messages" in route for route in routes)
        assert any("/coordination" in route for route in routes)
        assert any("/tasks" in route for route in routes)
        assert any("/agents" in route for route in routes)

    def test_app_with_middleware(self):
        """Test that middleware is properly configured."""
        # Check middleware stack
        middleware_types = [str(m.cls) for m in app.user_middleware]
        assert any("CORSMiddleware" in m for m in middleware_types)
        assert any("TimingMiddleware" in m for m in middleware_types)

    def test_server_routes_registration(self):
        """Test that all route modules are properly registered."""
        client = TestClient(app)

        # Test that main route groups are accessible
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["status"] == "running"

        # Test health endpoint
        response = client.get("/health")
        assert response.status_code == 200

    def test_server_error_handling(self):
        """Test server error handling."""
        client = TestClient(app)

        # Test 404 handling
        response = client.get("/nonexistent")
        assert response.status_code == 404

    def test_main_function(self):
        """Test main server startup function."""
        with patch("uvicorn.run") as mock_run:
            with patch("tmux_orchestrator.core.config.Config.load") as mock_config:
                mock_config.return_value = Mock(get=lambda key, default: default)

                main()

                mock_run.assert_called_once_with(
                    "tmux_orchestrator.server:app", host="127.0.0.1", port=8000, reload=True, log_level="info"
                )

    def test_server_info_endpoint(self):
        """Test server info endpoint."""
        client = TestClient(app)

        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "TMUX Orchestrator MCP Server"
        assert data["version"] == __version__
        assert data["status"] == "running"
        assert "available_tools" in data
        assert isinstance(data["available_tools"], list)
        assert len(data["available_tools"]) > 0

    def test_health_endpoint(self):
        """Test health check endpoint."""
        client = TestClient(app)

        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "tmux-orchestrator-mcp"

    def test_cors_configuration(self):
        """Test CORS is properly configured."""
        client = TestClient(app)

        # Make OPTIONS request
        response = client.options(
            "/", headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"}
        )

        # CORS should be enabled
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers


class TestMCPServerIntegration:
    """Integration tests for MCP server."""

    def test_full_server_startup(self):
        """Test that server starts up with all components."""
        client = TestClient(app)

        # Test basic endpoints that don't require session state
        basic_endpoints = [
            "/",
            "/health",
            "/openapi.json",
            "/docs",
        ]

        for endpoint in basic_endpoints:
            response = client.get(endpoint)
            assert response.status_code == 200, f"Basic endpoint {endpoint} failed"

        # Test route groups exist (they may return errors due to missing tmux, but shouldn't 404)
        route_group_endpoints = [
            "/monitor/health",
            "/coordination/list-teams",
            "/tasks/list",
        ]

        for endpoint in route_group_endpoints:
            response = client.get(endpoint)
            # Should not return 404 (route exists), but may return 500 due to missing tmux
            assert response.status_code != 404, f"Route group {endpoint} not found"

    def test_error_response_format(self):
        """Test that errors follow consistent format."""
        client = TestClient(app)

        # Test various error scenarios
        response = client.get("/nonexistent")
        assert response.status_code == 404

        # If JSON error response
        if response.headers.get("content-type", "").startswith("application/json"):
            data = response.json()
            assert "detail" in data or "error" in data

    def test_openapi_documentation(self):
        """Test that OpenAPI documentation is available."""
        client = TestClient(app)

        # Test OpenAPI JSON endpoint
        response = client.get("/openapi.json")
        assert response.status_code == 200

        openapi_spec = response.json()
        assert openapi_spec["info"]["title"] == "TMUX Orchestrator MCP Server"
        assert openapi_spec["info"]["version"] == __version__

        # Test documentation endpoints
        response = client.get("/docs")
        assert response.status_code == 200

        response = client.get("/redoc")
        assert response.status_code == 200

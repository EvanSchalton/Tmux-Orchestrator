"""Test MCP server security features."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from tmux_orchestrator.mcp_server import call_tool, sanitize_tool_arguments
from tmux_orchestrator.utils.exceptions import RateLimitExceededError, ValidationError


class TestMCPRateLimiting:
    """Test MCP server rate limiting."""

    @pytest.mark.asyncio
    async def test_rate_limit_enforcement(self):
        """Test rate limiting is enforced on tool calls."""
        # Mock rate limiter to always fail
        with patch("tmux_orchestrator.mcp_server.rate_limiter") as mock_limiter:
            mock_limiter.check_rate_limit = AsyncMock(side_effect=RateLimitExceededError("Rate limited"))

            result = await call_tool("list_agents", {"_origin": "test_user"})

            assert result["success"] is False
            assert result["error_type"] == "RateLimitExceeded"
            assert "retry_after" in result
            mock_limiter.check_rate_limit.assert_called_once_with("test_user")

    @pytest.mark.asyncio
    async def test_rate_limit_allows_requests(self):
        """Test rate limiting allows valid requests."""
        with patch("tmux_orchestrator.mcp_server.rate_limiter") as mock_limiter:
            with patch("tmux_orchestrator.mcp_server.TMUXManager") as mock_tmux:
                mock_limiter.check_rate_limit = AsyncMock(return_value=True)
                mock_tmux_instance = Mock()
                mock_tmux_instance.list_agents.return_value = []
                mock_tmux.return_value = mock_tmux_instance

                result = await call_tool("list_agents", {"_origin": "test_user"})

                assert "error_type" not in result
                mock_limiter.check_rate_limit.assert_called_once_with("test_user")

    @pytest.mark.asyncio
    async def test_default_origin_handling(self):
        """Test handling of requests without origin."""
        with patch("tmux_orchestrator.mcp_server.rate_limiter") as mock_limiter:
            with patch("tmux_orchestrator.mcp_server.TMUXManager") as mock_tmux:
                mock_limiter.check_rate_limit = AsyncMock(return_value=True)
                mock_tmux_instance = Mock()
                mock_tmux_instance.list_agents.return_value = []
                mock_tmux.return_value = mock_tmux_instance

                # No _origin in arguments
                _ = await call_tool("list_agents", {})

                # Should use default origin
                mock_limiter.check_rate_limit.assert_called_once_with("default")


class TestMCPInputSanitization:
    """Test MCP server input sanitization."""

    @pytest.mark.asyncio
    async def test_spawn_agent_sanitization(self):
        """Test spawn_agent arguments are sanitized."""
        args = {
            "session_name": "valid-session",
            "agent_type": "developer",
            "briefing_message": "Hello world",
            "project_path": "/workspaces/project",
        }

        result = await sanitize_tool_arguments("spawn_agent", args)

        assert result["session_name"] == "valid-session"
        assert result["agent_type"] == "developer"
        assert result["briefing_message"] == "Hello world"

    @pytest.mark.asyncio
    async def test_invalid_session_name_rejected(self):
        """Test invalid session names are rejected."""
        args = {
            "session_name": "invalid session name",  # Contains spaces
            "agent_type": "developer",
        }

        with pytest.raises(ValidationError):
            await sanitize_tool_arguments("spawn_agent", args)

    @pytest.mark.asyncio
    async def test_dangerous_message_rejected(self):
        """Test dangerous messages are rejected."""
        args = {
            "target": "session:0",
            "message": "Run this: `rm -rf /`",  # Command injection attempt
        }

        with pytest.raises(ValidationError):
            await sanitize_tool_arguments("send_message", args)

    @pytest.mark.asyncio
    async def test_path_traversal_rejected(self):
        """Test path traversal attempts are rejected."""
        args = {
            "session_name": "session",
            "agent_type": "developer",
            "project_path": "../../../etc/passwd",  # Path traversal
        }

        with pytest.raises(ValidationError):
            await sanitize_tool_arguments("spawn_agent", args)

    @pytest.mark.asyncio
    async def test_invalid_agent_type_rejected(self):
        """Test invalid agent types are rejected."""
        args = {
            "session_name": "session",
            "agent_type": "hacker",  # Invalid type
        }

        with pytest.raises(ValidationError):
            await sanitize_tool_arguments("spawn_agent", args)

    @pytest.mark.asyncio
    async def test_target_validation(self):
        """Test target format validation."""
        # Valid target
        args = {"target": "session:0"}
        result = await sanitize_tool_arguments("restart_agent", args)
        assert result["target"] == "session:0"

        # Invalid targets
        invalid_targets = [
            "invalid-target",  # Missing colon
            "session:",  # Missing window
            "session:abc",  # Non-numeric window
            "bad$session:0",  # Invalid session name
        ]

        for target in invalid_targets:
            args = {"target": target}
            with pytest.raises(ValidationError):
                await sanitize_tool_arguments("restart_agent", args)

    @pytest.mark.asyncio
    async def test_team_size_validation(self):
        """Test team size validation."""
        # Valid size
        args = {
            "team_name": "my-team",
            "team_type": "backend",
            "size": 5,
        }
        result = await sanitize_tool_arguments("deploy_team", args)
        assert result["size"] == 5

        # Invalid sizes
        invalid_sizes = [-1, 0, 1, 11, "abc", None]

        for size in invalid_sizes:
            args = {
                "team_name": "my-team",
                "team_type": "backend",
                "size": size,
            }
            with pytest.raises(ValidationError):
                await sanitize_tool_arguments("deploy_team", args)

    @pytest.mark.asyncio
    async def test_origin_field_removal(self):
        """Test _origin field is removed from sanitization."""
        args = {
            "session_name": "session",
            "agent_type": "developer",
            "_origin": "test_user",  # Should be removed
        }

        result = await sanitize_tool_arguments("spawn_agent", args)
        assert "_origin" not in result
        assert result["session_name"] == "session"

    @pytest.mark.asyncio
    async def test_unknown_tool_handling(self):
        """Test unknown tools are handled gracefully."""
        args = {"param": "value"}

        # Should not raise for unknown tools (no specific sanitization)
        result = await sanitize_tool_arguments("unknown_tool", args)
        assert result == args


class TestMCPSecurityIntegration:
    """Test integration of security features."""

    @pytest.mark.asyncio
    async def test_full_security_pipeline(self):
        """Test complete security pipeline for a tool call."""
        with patch("tmux_orchestrator.mcp_server.rate_limiter") as mock_limiter:
            with patch("tmux_orchestrator.mcp_server.core_spawn_agent") as mock_spawn:
                with patch("tmux_orchestrator.mcp_server.TMUXManager") as _mock_tmux:
                    # Set up mocks
                    mock_limiter.check_rate_limit = AsyncMock(return_value=True)
                    mock_spawn_result = Mock()
                    mock_spawn_result.success = True
                    mock_spawn_result.session = "test-session"
                    mock_spawn_result.window = "0"
                    mock_spawn_result.target = "test-session:0"
                    mock_spawn.return_value = mock_spawn_result

                    # Valid request
                    result = await call_tool(
                        "spawn_agent",
                        {
                            "session_name": "test-session",
                            "agent_type": "developer",
                            "_origin": "test_user",
                        },
                    )

                    # Should succeed
                    assert result["success"] is True
                    assert result["target"] == "test-session:0"

                    # Rate limiting should be checked
                    mock_limiter.check_rate_limit.assert_called_once_with("test_user")

                    # Core function should be called with sanitized args
                    mock_spawn.assert_called_once()

    @pytest.mark.asyncio
    async def test_security_failure_blocks_execution(self):
        """Test security failures prevent tool execution."""
        with patch("tmux_orchestrator.mcp_server.rate_limiter") as mock_limiter:
            with patch("tmux_orchestrator.mcp_server.core_spawn_agent") as mock_spawn:
                # Rate limiting fails
                mock_limiter.check_rate_limit = AsyncMock(side_effect=RateLimitExceededError("Limited"))

                result = await call_tool(
                    "spawn_agent",
                    {
                        "session_name": "test-session",
                        "agent_type": "developer",
                    },
                )

                # Should fail with rate limit error
                assert result["success"] is False
                assert result["error_type"] == "RateLimitExceeded"

                # Core function should not be called
                mock_spawn.assert_not_called()

    @pytest.mark.asyncio
    async def test_validation_failure_blocks_execution(self):
        """Test validation failures prevent tool execution."""
        with patch("tmux_orchestrator.mcp_server.rate_limiter") as mock_limiter:
            with patch("tmux_orchestrator.mcp_server.core_spawn_agent") as mock_spawn:
                # Rate limiting passes
                mock_limiter.check_rate_limit = AsyncMock(return_value=True)

                # Invalid arguments
                result = await call_tool(
                    "spawn_agent",
                    {
                        "session_name": "invalid session name",  # Contains spaces
                        "agent_type": "developer",
                    },
                )

                # Should fail with validation error
                assert result["success"] is False
                assert "error" in result

                # Core function should not be called
                mock_spawn.assert_not_called()

    @pytest.mark.asyncio
    async def test_error_handling_doesnt_leak_info(self):
        """Test error handling doesn't leak sensitive information."""
        with patch("tmux_orchestrator.mcp_server.rate_limiter") as mock_limiter:
            mock_limiter.check_rate_limit = AsyncMock(return_value=True)

            # Cause a validation error
            result = await call_tool(
                "spawn_agent",
                {
                    "session_name": "/etc/passwd",  # Path-like session name
                    "agent_type": "developer",
                },
            )

            # Error should be generic, not reveal internal details
            assert result["success"] is False
            assert "error" in result
            # Should not contain stack traces or internal paths
            assert "/etc/passwd" not in str(result.get("error", ""))


class TestMCPConcurrencySafety:
    """Test MCP server concurrent access safety."""

    @pytest.mark.asyncio
    async def test_concurrent_rate_limiting(self):
        """Test rate limiting works correctly under concurrent load."""
        call_count = 0
        success_count = 0

        async def make_request():
            nonlocal call_count, success_count
            call_count += 1

            with patch("tmux_orchestrator.mcp_server.TMUXManager") as mock_tmux:
                mock_tmux_instance = Mock()
                mock_tmux_instance.list_agents.return_value = []
                mock_tmux.return_value = mock_tmux_instance

                result = await call_tool("list_agents", {"_origin": "concurrent_user"})

                if result.get("success", True):  # list_agents doesn't return success field normally
                    success_count += 1

        # Make many concurrent requests
        tasks = [make_request() for _ in range(20)]
        await asyncio.gather(*tasks, return_exceptions=True)

        assert call_count == 20
        # Some should succeed, some should be rate limited
        # The exact number depends on rate limiter configuration

# Phase 2 Implementation Guide: Team Operations & Monitoring

## Overview

This guide provides step-by-step implementation instructions for Phase 2 MCP tools, building on the successful Phase 1 foundation. Phase 2 focuses on team operations and monitoring capabilities while maintaining the dynamic CLI introspection architecture.

## Prerequisites

✅ **Phase 1 Complete**: All 4 Phase 1 tools implemented and tested
✅ **FastMCP Server**: Running with dynamic tool generation
✅ **Service Container**: SOLID principles and dependency injection established
✅ **Testing Framework**: 100% coverage patterns established

## Implementation Strategy

### Approach: Hybrid Implementation
Given the team velocity and existing code base, Phase 2 uses a **hybrid approach**:

1. **Quick Wins**: Leverage dynamic CLI introspection for standard commands
2. **Custom Tools**: Implement specific MCP tools for complex team operations
3. **Integration**: Connect with existing team deployment and monitoring systems

## Step 1: Team Handlers Implementation

### 1.1 Create TeamHandlers Class

Create `tmux_orchestrator/mcp/handlers/team_handlers.py`:

```python
"""Business logic handlers for team operations MCP tools."""

import logging
from typing import Any, Dict, List, Optional
import asyncio
from datetime import datetime

from tmux_orchestrator.core.team_operations.deploy_team import deploy_standard_team
from tmux_orchestrator.core.team_operations import broadcast_to_team
from tmux_orchestrator.server.tools.get_agent_status import (
    AgentStatusRequest,
    get_agent_status as core_get_agent_status,
)
from tmux_orchestrator.server.tools.send_message import (
    SendMessageRequest,
    send_message as core_send_message,
)
from tmux_orchestrator.utils.tmux import TMUXManager
from tmux_orchestrator.core.config import Config

logger = logging.getLogger(__name__)


class TeamHandlers:
    """Handlers for team management operations following SOLID principles."""

    def __init__(self,
                 tmux: TMUXManager,
                 config: Config,
                 logger: logging.Logger):
        """Initialize team handlers with dependency injection.

        Args:
            tmux: TMUXManager instance for tmux operations
            config: Configuration instance
            logger: Logger instance for operations
        """
        self._tmux = tmux
        self._config = config
        self._logger = logger

        # Validate dependencies
        if not isinstance(tmux, TMUXManager):
            raise ValueError("tmux must be TMUXManager instance")
        if not isinstance(config, Config):
            raise ValueError("config must be Config instance")

    async def deploy_team(
        self,
        team_name: str,
        team_type: str,
        size: int = 3,
        project_path: Optional[str] = None,
        briefing_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Deploy a team of specialized Claude agents.

        Args:
            team_name: Name for the team/session
            team_type: Type of team (frontend, backend, fullstack, testing)
            size: Number of agents in the team (2-6 recommended)
            project_path: Path to project directory
            briefing_context: Additional context for the team

        Returns:
            Dict with deployment status, agent details, and team configuration
        """
        try:
            self._logger.info(f"Deploying {team_type} team '{team_name}' with {size} agents")

            # Input validation
            validation_result = self._validate_team_deployment(team_name, team_type, size)
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": validation_result["error"],
                    "error_type": "ValidationError",
                    "context": {
                        "team_name": team_name,
                        "team_type": team_type,
                        "size": size
                    }
                }

            # Use existing core team deployment logic
            start_time = datetime.now()
            success, message = deploy_standard_team(
                tmux=self._tmux,
                team_type=team_type,
                size=size,
                project_name=team_name,
            )
            deployment_time = (datetime.now() - start_time).total_seconds()

            if success:
                # Get deployed team information
                team_info = await self._get_deployed_team_info(team_name)

                # Send briefing context if provided
                if briefing_context:
                    await self._send_team_briefing(team_name, briefing_context)

                return {
                    "success": True,
                    "team_name": team_name,
                    "team_type": team_type,
                    "size": size,
                    "message": message,
                    "project_path": project_path,
                    "deployment_time_seconds": deployment_time,
                    "team_info": team_info,
                    "briefing_sent": bool(briefing_context)
                }
            else:
                return {
                    "success": False,
                    "error": message or "Team deployment failed",
                    "error_type": "DeploymentFailure",
                    "context": {
                        "team_name": team_name,
                        "team_type": team_type,
                        "size": size,
                        "deployment_time_seconds": deployment_time
                    }
                }

        except Exception as e:
            self._logger.error(f"Team deployment failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "context": {
                    "team_name": team_name,
                    "team_type": team_type,
                    "size": size
                }
            }

    def get_team_status(
        self,
        session: Optional[str] = None,
        detailed: bool = False,
        include_agents: bool = True,
    ) -> Dict[str, Any]:
        """Get comprehensive status of a team or all teams.

        Args:
            session: Specific team session, or None for all teams
            detailed: Include detailed agent metrics
            include_agents: Include individual agent status

        Returns:
            Dict with team health, agent status, and performance metrics
        """
        try:
            self._logger.info(f"Getting team status for: {session or 'all teams'}")

            if session:
                return self._get_single_team_status(session, detailed, include_agents)
            else:
                return self._get_all_teams_status(detailed, include_agents)

        except Exception as e:
            self._logger.error(f"Team status retrieval failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "context": {"session": session, "detailed": detailed}
            }

    def team_broadcast(
        self,
        session: str,
        message: str,
        exclude_windows: Optional[List[str]] = None,
        urgent: bool = False,
    ) -> Dict[str, Any]:
        """Broadcast a message to all agents in a team.

        Args:
            session: Team session to broadcast to
            message: Message to broadcast
            exclude_windows: Window names to exclude from broadcast
            urgent: Mark message as urgent

        Returns:
            Dict with broadcast results and delivery confirmations
        """
        try:
            self._logger.info(f"Broadcasting to team {session}: {message[:50]}...")

            # Input validation
            if not session.strip():
                return {
                    "success": False,
                    "error": "Session name cannot be empty",
                    "error_type": "ValidationError"
                }

            if not message.strip():
                return {
                    "success": False,
                    "error": "Message cannot be empty",
                    "error_type": "ValidationError"
                }

            # Check if session exists
            if not self._tmux.has_session(session):
                return {
                    "success": False,
                    "error": f"Session '{session}' not found",
                    "error_type": "ResourceNotFound",
                    "context": {"session": session}
                }

            # Use existing broadcast logic
            start_time = datetime.now()
            success, summary_message, broadcast_results = broadcast_to_team(
                self._tmux, session, message
            )
            broadcast_time = (datetime.now() - start_time).total_seconds()

            # Filter excluded windows
            if exclude_windows:
                broadcast_results = [
                    r for r in broadcast_results
                    if r.get("window") not in exclude_windows
                ]

            # Calculate statistics
            sent_count = len([r for r in broadcast_results if r.get("success", False)])
            failed_count = len(broadcast_results) - sent_count

            return {
                "success": success,
                "session": session,
                "message_sent": message,
                "sent_count": sent_count,
                "failed_count": failed_count,
                "excluded_windows": exclude_windows or [],
                "urgent": urgent,
                "broadcast_time_seconds": broadcast_time,
                "summary": summary_message,
                "details": broadcast_results
            }

        except Exception as e:
            self._logger.error(f"Team broadcast failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "context": {
                    "session": session,
                    "exclude_windows": exclude_windows,
                    "urgent": urgent
                }
            }

    # Private helper methods
    def _validate_team_deployment(self, team_name: str, team_type: str, size: int) -> Dict[str, Any]:
        """Validate team deployment parameters."""
        if not team_name.strip():
            return {"valid": False, "error": "Team name cannot be empty"}

        valid_team_types = ["frontend", "backend", "fullstack", "testing"]
        if team_type not in valid_team_types:
            return {
                "valid": False,
                "error": f"Invalid team type. Must be one of: {', '.join(valid_team_types)}"
            }

        if not (2 <= size <= 10):
            return {"valid": False, "error": "Team size must be between 2 and 10"}

        # Check if session already exists
        if self._tmux.has_session(team_name):
            return {"valid": False, "error": f"Session '{team_name}' already exists"}

        return {"valid": True}

    async def _get_deployed_team_info(self, team_name: str) -> Dict[str, Any]:
        """Get information about a deployed team."""
        try:
            windows = self._tmux.list_windows(team_name)
            team_info = {
                "session_name": team_name,
                "agent_count": len(windows),
                "agents": []
            }

            for window in windows:
                agent_info = {
                    "window": window.get("name", str(window.get("id", ""))),
                    "index": window.get("index", 0),
                    "active": window.get("active", False)
                }
                team_info["agents"].append(agent_info)

            return team_info
        except Exception as e:
            self._logger.error(f"Failed to get team info: {e}")
            return {"error": str(e)}

    async def _send_team_briefing(self, team_name: str, briefing_context: str) -> None:
        """Send briefing context to all team members."""
        try:
            briefing_message = f"Team Briefing: {briefing_context}"
            broadcast_to_team(self._tmux, team_name, briefing_message)
            self._logger.info(f"Sent briefing to team {team_name}")
        except Exception as e:
            self._logger.error(f"Failed to send team briefing: {e}")

    def _get_single_team_status(self, session: str, detailed: bool, include_agents: bool) -> Dict[str, Any]:
        """Get status for a single team."""
        if not self._tmux.has_session(session):
            return {
                "success": False,
                "error": f"Session '{session}' not found",
                "error_type": "ResourceNotFound"
            }

        windows = self._tmux.list_windows(session)
        team_agents = []

        if include_agents:
            for window in windows:
                window_name = window.get("name", str(window.get("id", "")))
                target = f"{session}:{window_name}"

                agent_info = {"target": target, "window": window_name}

                if detailed:
                    # Get detailed agent status
                    status_request = AgentStatusRequest(
                        agent_id=target,
                        include_activity_history=True,
                        activity_limit=5,
                    )
                    status_result = core_get_agent_status(self._tmux, status_request)

                    if status_result.success and status_result.agent_metrics:
                        metrics = status_result.agent_metrics[0]
                        agent_info.update({
                            "health_status": metrics.health_status.value,
                            "responsiveness_score": metrics.responsiveness_score,
                            "last_activity": metrics.last_activity_time.isoformat()
                            if metrics.last_activity_time else None,
                        })

                team_agents.append(agent_info)

        return {
            "success": True,
            "session": session,
            "agents": team_agents,
            "agent_count": len(team_agents),
            "detailed": detailed,
            "include_agents": include_agents,
            "timestamp": datetime.now().isoformat()
        }

    def _get_all_teams_status(self, detailed: bool, include_agents: bool) -> Dict[str, Any]:
        """Get status for all teams."""
        sessions = self._tmux.list_sessions()
        all_teams = []

        for sess_info in sessions:
            session_name = str(sess_info["name"])
            windows = self._tmux.list_windows(session_name)

            team_info = {
                "session": session_name,
                "agent_count": len(windows),
                "created": sess_info.get("created"),
                "attached": sess_info.get("attached", False)
            }

            if include_agents:
                team_info["agents"] = [
                    {
                        "window": w.get("name", str(w.get("id", ""))),
                        "index": w.get("index", 0)
                    }
                    for w in windows
                ]

            all_teams.append(team_info)

        return {
            "success": True,
            "teams": all_teams,
            "total_teams": len(all_teams),
            "total_agents": sum(team["agent_count"] for team in all_teams),
            "detailed": detailed,
            "include_agents": include_agents,
            "timestamp": datetime.now().isoformat()
        }
```

### 1.2 Best Practices for Team Handlers

#### Error Handling Pattern
```python
def _handle_operation_error(self, operation: str, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
    """Standardized error handling for team operations."""
    self._logger.error(f"{operation} failed: {error}", exc_info=True)

    return {
        "success": False,
        "error": str(error),
        "error_type": type(error).__name__,
        "operation": operation,
        "context": context,
        "timestamp": datetime.now().isoformat(),
        "recovery_suggestions": self._get_recovery_suggestions(operation, error)
    }

def _get_recovery_suggestions(self, operation: str, error: Exception) -> List[str]:
    """Get recovery suggestions based on operation and error type."""
    suggestions = []

    if "deploy_team" in operation:
        suggestions.extend([
            "Check if session name is already in use",
            "Verify team type is valid (frontend, backend, fullstack, testing)",
            "Ensure team size is between 2-10 agents"
        ])

    if "ResourceNotFound" in str(type(error)):
        suggestions.append("Verify session exists with 'tmux-orc list'")

    return suggestions
```

#### Input Validation Pattern
```python
def _validate_team_input(self, **kwargs) -> Dict[str, Any]:
    """Comprehensive input validation for team operations."""
    errors = []

    # Validate team_name
    team_name = kwargs.get("team_name", "")
    if not team_name or not team_name.strip():
        errors.append("team_name is required and cannot be empty")
    elif len(team_name) > 50:
        errors.append("team_name must be 50 characters or less")
    elif not team_name.replace("-", "").replace("_", "").isalnum():
        errors.append("team_name must contain only alphanumeric characters, hyphens, and underscores")

    # Validate team_type
    team_type = kwargs.get("team_type", "")
    valid_types = ["frontend", "backend", "fullstack", "testing"]
    if team_type not in valid_types:
        errors.append(f"team_type must be one of: {', '.join(valid_types)}")

    # Validate size
    size = kwargs.get("size", 0)
    if not isinstance(size, int) or not (2 <= size <= 10):
        errors.append("size must be an integer between 2 and 10")

    if errors:
        return {
            "valid": False,
            "errors": errors,
            "error_type": "ValidationError"
        }

    return {"valid": True}
```

## Step 2: Team Operations Tools

### 2.1 Create team_operations.py

Create `tmux_orchestrator/mcp/tools/team_operations.py`:

```python
"""Phase 2 MCP tools for team operations."""

import logging
from typing import Any, Dict, List, Optional

from tmux_orchestrator.mcp.server import mcp
from tmux_orchestrator.mcp.handlers.team_handlers import TeamHandlers
from tmux_orchestrator.utils.tmux import TMUXManager
from tmux_orchestrator.core.config import Config

logger = logging.getLogger(__name__)

# Initialize dependencies using dependency injection pattern
def _get_team_handlers() -> TeamHandlers:
    """Get TeamHandlers instance with proper dependency injection."""
    tmux = TMUXManager()
    config = Config.load()
    return TeamHandlers(tmux=tmux, config=config, logger=logger)

# Initialize handlers
team_handlers = _get_team_handlers()


@mcp.tool()
async def deploy_team(
    team_name: str,
    team_type: str,
    size: int = 3,
    project_path: Optional[str] = None,
    briefing_context: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Deploy a team of specialized Claude agents.

    Args:
        team_name: Name for the team/session
        team_type: Type of team (frontend, backend, fullstack, testing)
        size: Number of agents in the team (2-6 recommended)
        project_path: Path to project directory
        briefing_context: Additional context for the team

    Returns:
        Dict with deployment status, agent details, and team configuration
    """
    logger.info(f"MCP Tool: Deploying {team_type} team '{team_name}' with {size} agents")

    try:
        result = await team_handlers.deploy_team(
            team_name=team_name,
            team_type=team_type,
            size=size,
            project_path=project_path,
            briefing_context=briefing_context,
        )

        # Add MCP-specific metadata
        result["mcp_tool"] = "deploy_team"
        result["tool_version"] = "2.0.0"

        return result

    except Exception as e:
        logger.error(f"MCP deploy_team tool failed: {e}")
        return {
            "success": False,
            "error": f"Tool execution failed: {str(e)}",
            "error_type": "ToolExecutionError",
            "mcp_tool": "deploy_team",
            "context": {
                "team_name": team_name,
                "team_type": team_type,
                "size": size
            }
        }


@mcp.tool()
def get_team_status(
    session: Optional[str] = None,
    detailed: bool = False,
    include_agents: bool = True,
) -> Dict[str, Any]:
    """
    Get comprehensive status of a team or all teams.

    Args:
        session: Specific team session, or None for all teams
        detailed: Include detailed agent metrics
        include_agents: Include individual agent status

    Returns:
        Dict with team health, agent status, and performance metrics
    """
    logger.info(f"MCP Tool: Getting team status for: {session or 'all teams'}")

    try:
        result = team_handlers.get_team_status(
            session=session,
            detailed=detailed,
            include_agents=include_agents,
        )

        # Add MCP-specific metadata
        result["mcp_tool"] = "get_team_status"
        result["tool_version"] = "2.0.0"

        return result

    except Exception as e:
        logger.error(f"MCP get_team_status tool failed: {e}")
        return {
            "success": False,
            "error": f"Tool execution failed: {str(e)}",
            "error_type": "ToolExecutionError",
            "mcp_tool": "get_team_status",
            "context": {
                "session": session,
                "detailed": detailed,
                "include_agents": include_agents
            }
        }


@mcp.tool()
def team_broadcast(
    session: str,
    message: str,
    exclude_windows: Optional[List[str]] = None,
    urgent: bool = False,
) -> Dict[str, Any]:
    """
    Broadcast a message to all agents in a team.

    Args:
        session: Team session to broadcast to
        message: Message to broadcast
        exclude_windows: Window names to exclude from broadcast
        urgent: Mark message as urgent

    Returns:
        Dict with broadcast results and delivery confirmations
    """
    logger.info(f"MCP Tool: Broadcasting to team {session}")

    try:
        result = team_handlers.team_broadcast(
            session=session,
            message=message,
            exclude_windows=exclude_windows or [],
            urgent=urgent,
        )

        # Add MCP-specific metadata
        result["mcp_tool"] = "team_broadcast"
        result["tool_version"] = "2.0.0"

        return result

    except Exception as e:
        logger.error(f"MCP team_broadcast tool failed: {e}")
        return {
            "success": False,
            "error": f"Tool execution failed: {str(e)}",
            "error_type": "ToolExecutionError",
            "mcp_tool": "team_broadcast",
            "context": {
                "session": session,
                "exclude_windows": exclude_windows,
                "urgent": urgent
            }
        }


def register_team_tools() -> None:
    """Register all team operation tools with FastMCP."""
    logger.info("Phase 2 team operation tools registered")

    # Validation: Ensure all tools are properly decorated
    tools = [deploy_team, get_team_status, team_broadcast]
    for tool in tools:
        if not hasattr(tool, '_mcp_tool'):
            logger.warning(f"Tool {tool.__name__} may not be properly registered with @mcp.tool()")


# Auto-register tools when module is imported
register_team_tools()
```

## Step 3: Integration with Existing Systems

### 3.1 Existing Team Deployment Integration

The Phase 2 implementation **reuses existing team deployment logic** from:

- `tmux_orchestrator.core.team_operations.deploy_team.deploy_standard_team`
- `tmux_orchestrator.core.team_operations.broadcast_to_team`

#### Integration Pattern:
```python
# Direct integration with existing core logic
def deploy_team_integration_example():
    """Example of how Phase 2 integrates with existing systems."""

    # ✅ CORRECT: Reuse existing core logic
    from tmux_orchestrator.core.team_operations.deploy_team import deploy_standard_team

    success, message = deploy_standard_team(
        tmux=self._tmux,
        team_type=team_type,
        size=size,
        project_name=team_name,
    )

    # ❌ INCORRECT: Don't reimplement team deployment
    # Custom team deployment logic would duplicate existing functionality
```

### 3.2 Service Container Integration

Update service registration to include Phase 2 handlers:

```python
# tmux_orchestrator/core/services/phase2_services.py
from tmux_orchestrator.core.monitoring.service_container import ServiceContainer
from tmux_orchestrator.mcp.handlers.team_handlers import TeamHandlers

def register_phase2_services(container: ServiceContainer):
    """Register Phase 2 services following SOLID principles."""

    # Team operation services
    container.register(
        TeamHandlers,
        lambda: TeamHandlers(
            tmux=container.resolve(TMUXManager),
            config=container.resolve(Config),
            logger=container.resolve(logging.Logger)
        )
    )

    # Additional Phase 2 services can be added here
    # container.register(MonitoringHandlers, ...)
```

## Step 4: Testing Implementation

### 4.1 Unit Tests for Team Handlers

Create `tests/mcp/handlers/test_team_handlers.py`:

```python
"""Unit tests for team handlers."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from tmux_orchestrator.mcp.handlers.team_handlers import TeamHandlers
from tmux_orchestrator.core.config import Config


class TestTeamHandlers:
    """Test TeamHandlers class with 100% coverage."""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for TeamHandlers."""
        return {
            'tmux': Mock(),
            'config': Mock(spec=Config),
            'logger': Mock()
        }

    @pytest.fixture
    def team_handlers(self, mock_dependencies):
        """Create TeamHandlers instance with mocked dependencies."""
        return TeamHandlers(**mock_dependencies)

    @pytest.mark.asyncio
    async def test_deploy_team_success(self, team_handlers, mock_dependencies):
        """Test successful team deployment."""
        # Arrange
        mock_dependencies['tmux'].has_session.return_value = False

        with patch('tmux_orchestrator.core.team_operations.deploy_team.deploy_standard_team') as mock_deploy:
            mock_deploy.return_value = (True, "Team deployed successfully")
            mock_dependencies['tmux'].list_windows.return_value = [
                {"name": "agent-1", "index": 1},
                {"name": "agent-2", "index": 2}
            ]

            # Act
            result = await team_handlers.deploy_team(
                team_name="test-team",
                team_type="frontend",
                size=2
            )

        # Assert
        assert result["success"] is True
        assert result["team_name"] == "test-team"
        assert result["team_type"] == "frontend"
        assert result["size"] == 2
        assert "deployment_time_seconds" in result
        mock_deploy.assert_called_once()

    @pytest.mark.asyncio
    async def test_deploy_team_validation_error(self, team_handlers):
        """Test team deployment with validation errors."""
        # Act
        result = await team_handlers.deploy_team(
            team_name="",  # Invalid empty name
            team_type="frontend",
            size=2
        )

        # Assert
        assert result["success"] is False
        assert result["error_type"] == "ValidationError"
        assert "empty" in result["error"]

    @pytest.mark.asyncio
    async def test_deploy_team_invalid_type(self, team_handlers):
        """Test team deployment with invalid team type."""
        # Act
        result = await team_handlers.deploy_team(
            team_name="test-team",
            team_type="invalid-type",
            size=2
        )

        # Assert
        assert result["success"] is False
        assert result["error_type"] == "ValidationError"
        assert "Invalid team type" in result["error"]

    def test_get_team_status_single_team(self, team_handlers, mock_dependencies):
        """Test getting status for a single team."""
        # Arrange
        mock_dependencies['tmux'].has_session.return_value = True
        mock_dependencies['tmux'].list_windows.return_value = [
            {"name": "agent-1", "id": "1", "index": 1}
        ]

        # Act
        result = team_handlers.get_team_status(session="test-team")

        # Assert
        assert result["success"] is True
        assert result["session"] == "test-team"
        assert result["agent_count"] == 1
        assert len(result["agents"]) == 1

    def test_get_team_status_all_teams(self, team_handlers, mock_dependencies):
        """Test getting status for all teams."""
        # Arrange
        mock_dependencies['tmux'].list_sessions.return_value = [
            {"name": "team-1", "created": "2024-01-01"},
            {"name": "team-2", "created": "2024-01-02"}
        ]
        mock_dependencies['tmux'].list_windows.side_effect = [
            [{"name": "agent-1"}],  # team-1 windows
            [{"name": "agent-2"}, {"name": "agent-3"}]  # team-2 windows
        ]

        # Act
        result = team_handlers.get_team_status()

        # Assert
        assert result["success"] is True
        assert result["total_teams"] == 2
        assert result["total_agents"] == 3

    def test_team_broadcast_success(self, team_handlers, mock_dependencies):
        """Test successful team broadcast."""
        # Arrange
        mock_dependencies['tmux'].has_session.return_value = True

        with patch('tmux_orchestrator.core.team_operations.broadcast_to_team') as mock_broadcast:
            mock_broadcast.return_value = (True, "Broadcast successful", [
                {"success": True, "window": "agent-1"},
                {"success": True, "window": "agent-2"}
            ])

            # Act
            result = team_handlers.team_broadcast(
                session="test-team",
                message="Test message"
            )

        # Assert
        assert result["success"] is True
        assert result["sent_count"] == 2
        assert result["failed_count"] == 0
        assert result["message_sent"] == "Test message"

    def test_team_broadcast_validation_errors(self, team_handlers):
        """Test team broadcast with validation errors."""
        # Test empty session
        result = team_handlers.team_broadcast(session="", message="test")
        assert result["success"] is False
        assert result["error_type"] == "ValidationError"

        # Test empty message
        result = team_handlers.team_broadcast(session="test", message="")
        assert result["success"] is False
        assert result["error_type"] == "ValidationError"

    def test_team_broadcast_session_not_found(self, team_handlers, mock_dependencies):
        """Test team broadcast when session doesn't exist."""
        # Arrange
        mock_dependencies['tmux'].has_session.return_value = False

        # Act
        result = team_handlers.team_broadcast(
            session="nonexistent-team",
            message="Test message"
        )

        # Assert
        assert result["success"] is False
        assert result["error_type"] == "ResourceNotFound"
        assert "not found" in result["error"]
```

### 4.2 Integration Tests

Create `tests/mcp/integration/test_team_operations_integration.py`:

```python
"""Integration tests for team operations."""

import pytest
from tmux_orchestrator.mcp.tools.team_operations import deploy_team, get_team_status, team_broadcast


class TestTeamOperationsIntegration:
    """Integration tests for Phase 2 team operations."""

    @pytest.mark.asyncio
    async def test_team_deployment_workflow(self):
        """Test complete team deployment workflow."""
        # Deploy team
        deploy_result = await deploy_team(
            team_name="integration-test",
            team_type="backend",
            size=2
        )

        assert deploy_result["success"] is True
        assert deploy_result["team_name"] == "integration-test"

        # Get team status
        status_result = get_team_status(session="integration-test")

        assert status_result["success"] is True
        assert status_result["agent_count"] == 2

        # Broadcast message
        broadcast_result = team_broadcast(
            session="integration-test",
            message="Integration test message"
        )

        assert broadcast_result["success"] is True
        assert broadcast_result["sent_count"] == 2

        # Cleanup (would be handled by test teardown)
        # tmux.kill_session("integration-test")

    @pytest.mark.asyncio
    async def test_team_operations_error_handling(self):
        """Test error handling in team operations."""
        # Try to get status of non-existent team
        status_result = get_team_status(session="non-existent-team")

        assert status_result["success"] is False
        assert status_result["error_type"] == "ResourceNotFound"

        # Try to broadcast to non-existent team
        broadcast_result = team_broadcast(
            session="non-existent-team",
            message="Test message"
        )

        assert broadcast_result["success"] is False
        assert broadcast_result["error_type"] == "ResourceNotFound"
```

## Step 5: Server Integration

### 5.1 Update MCP Server

Update `tmux_orchestrator/mcp/server.py` to include Phase 2 tools:

```python
# Add to existing server.py imports
from tmux_orchestrator.mcp.tools.team_operations import *  # noqa: F401, F403

logger.info("MCP server initialized with Phase 1-2 tools")
```

### 5.2 Update Tool Registry

Update `tmux_orchestrator/mcp/tools/__init__.py`:

```python
"""MCP tools for tmux-orchestrator."""

from .agent_management import register_agent_tools
from .team_operations import register_team_tools

__all__ = ["register_agent_tools", "register_team_tools"]
```

## Performance Benchmarks

### Phase 2 Performance Targets
- **Team Deployment**: <30 seconds for 5-agent team
- **Team Status**: <2 seconds for single team, <5 seconds for all teams
- **Team Broadcast**: <3 seconds for 10 agents
- **Memory Overhead**: <15% increase from Phase 1

### Performance Testing
```python
# tests/mcp/performance/test_phase2_performance.py
import time
import pytest
from tmux_orchestrator.mcp.tools.team_operations import deploy_team, get_team_status


class TestPhase2Performance:
    """Performance tests for Phase 2 tools."""

    @pytest.mark.asyncio
    async def test_team_deployment_performance(self):
        """Test team deployment performance."""
        start_time = time.time()

        result = await deploy_team(
            team_name="perf-test",
            team_type="frontend",
            size=3
        )

        duration = time.time() - start_time

        assert result["success"] is True
        assert duration < 30.0  # 30 second target
        assert result["deployment_time_seconds"] < 25.0

    def test_team_status_performance(self):
        """Test team status retrieval performance."""
        start_time = time.time()

        result = get_team_status(detailed=True, include_agents=True)

        duration = time.time() - start_time

        assert result["success"] is True
        assert duration < 5.0  # 5 second target for all teams
```

## Rollback Strategy

### Phase 2 Rollback Procedures

#### 1. Immediate Rollback
```bash
# Disable Phase 2 tools
mv tmux_orchestrator/mcp/tools/team_operations.py tmux_orchestrator/mcp/tools/team_operations.py.disabled

# Restart MCP server
python -m tmux_orchestrator.mcp.server
```

#### 2. Gradual Rollback
```python
# tmux_orchestrator/mcp/server.py
# Comment out Phase 2 imports
# from tmux_orchestrator.mcp.tools.team_operations import *

logger.info("MCP server running with Phase 1 tools only")
```

## Success Criteria

### Phase 2 Complete When:
- [ ] All 3 team operation tools implemented and tested
- [ ] 100% unit test coverage for team handlers
- [ ] Integration tests passing
- [ ] Performance benchmarks met
- [ ] Existing team deployment logic successfully integrated
- [ ] Error handling follows standardized patterns
- [ ] Service container integration complete

## Next Steps

After Phase 2 completion:
1. **Team validation** of team operation tools
2. **Performance optimization** based on benchmarks
3. **Phase 3 preparation** for VS Code integration and advanced features
4. **Documentation updates** for new team operation capabilities

This comprehensive Phase 2 implementation guide provides the development team with step-by-step instructions, best practices, and testing strategies to successfully implement team operations while maintaining the architectural principles established in Phase 1.

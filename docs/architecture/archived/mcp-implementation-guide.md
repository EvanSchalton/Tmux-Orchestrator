# MCP Implementation Guide for Tmux Orchestrator

## Overview

This guide provides detailed implementation instructions for migrating tmux-orchestrator to a pure FastMCP architecture. The migration is structured in 5 phases, with Phase 1 already implemented.

## Phase 2 Implementation Guide: Team Operations & Monitoring

### Prerequisites
- Phase 1 must be fully implemented and tested
- All Phase 1 tests passing
- FastMCP server running successfully

### Step 1: Create Team Handlers

Create `tmux_orchestrator/mcp/handlers/team_handlers.py`:

```python
"""Business logic handlers for team operations MCP tools."""

import logging
from typing import Any, Dict

from tmux_orchestrator.core.team_operations.deploy_team import deploy_standard_team
from tmux_orchestrator.core.team_operations import broadcast_to_team
from tmux_orchestrator.utils.tmux import TMUXManager

logger = logging.getLogger(__name__)


class TeamHandlers:
    """Handlers for team management operations."""

    def __init__(self):
        self.tmux = TMUXManager()

    async def deploy_team(
        self,
        team_name: str,
        team_type: str,
        size: int = 3,
        project_path: str | None = None,
        briefing_context: str | None = None,
    ) -> Dict[str, Any]:
        """Handle team deployment operation."""
        try:
            # Delegate to core team deployment logic
            success, message = deploy_standard_team(
                tmux=self.tmux,
                team_type=team_type,
                size=size,
                project_name=team_name,
            )

            if success:
                return {
                    "success": True,
                    "team_name": team_name,
                    "team_type": team_type,
                    "size": size,
                    "message": message,
                    "project_path": project_path,
                }
            else:
                return {
                    "success": False,
                    "error": message or "Team deployment failed",
                    "error_type": "TeamDeploymentFailure",
                    "context": {
                        "team_name": team_name,
                        "team_type": team_type,
                        "size": size,
                    },
                }

        except Exception as e:
            logger.error(f"Team deployment failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "context": {
                    "team_name": team_name,
                    "team_type": team_type,
                },
            }

    def get_team_status(
        self,
        session: str | None = None,
        detailed: bool = False,
        include_agents: bool = True,
    ) -> Dict[str, Any]:
        """Handle team status retrieval operation."""
        try:
            if session:
                # Single team status
                windows = self.tmux.list_windows(session)
                team_agents = []

                for window in windows:
                    window_name = window.get("name", str(window.get("id", "")))
                    target = f"{session}:{window_name}"

                    if include_agents:
                        # Get agent status if requested
                        team_agents.append({"target": target})

                return {
                    "success": True,
                    "session": session,
                    "agents": team_agents,
                    "agent_count": len(team_agents),
                    "detailed": detailed,
                }
            else:
                # All teams status
                sessions = self.tmux.list_sessions()
                all_teams = []

                for sess_info in sessions:
                    session_name = str(sess_info["name"])
                    windows = self.tmux.list_windows(session_name)
                    all_teams.append({
                        "session": session_name,
                        "agent_count": len(windows),
                        "created": sess_info.get("created"),
                    })

                return {
                    "success": True,
                    "teams": all_teams,
                    "total_teams": len(all_teams),
                }

        except Exception as e:
            logger.error(f"Team status retrieval failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "context": {"session": session},
            }

    def team_broadcast(
        self,
        session: str,
        message: str,
        exclude_windows: list[str] | None = None,
        urgent: bool = False,
    ) -> Dict[str, Any]:
        """Handle team broadcast operation."""
        try:
            # Delegate to core broadcast logic
            success, summary_message, broadcast_results = broadcast_to_team(
                self.tmux, session, message
            )

            if exclude_windows:
                # Filter out excluded windows
                broadcast_results = [
                    r for r in broadcast_results
                    if r.get("window") not in exclude_windows
                ]

            sent_count = len([r for r in broadcast_results if r.get("success", False)])
            failed_count = len(broadcast_results) - sent_count

            return {
                "success": success,
                "session": session,
                "sent_count": sent_count,
                "failed_count": failed_count,
                "message": summary_message,
                "urgent": urgent,
                "details": broadcast_results,
            }

        except Exception as e:
            logger.error(f"Team broadcast failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "context": {
                    "session": session,
                    "exclude_windows": exclude_windows,
                },
            }
```

### Step 2: Create Monitoring Handlers

Create `tmux_orchestrator/mcp/handlers/monitoring_handlers.py`:

```python
"""Business logic handlers for monitoring operations MCP tools."""

import logging
from datetime import datetime
from typing import Any, Dict

from tmux_orchestrator.core.monitoring.daemon_manager import DaemonManager
from tmux_orchestrator.utils.tmux import TMUXManager

logger = logging.getLogger(__name__)


class MonitoringHandlers:
    """Handlers for monitoring operations."""

    def __init__(self):
        self.tmux = TMUXManager()
        self.daemon_manager = DaemonManager()

    def start_monitoring(
        self,
        interval: int = 30,
        supervised: bool = False,
        auto_recovery: bool = True,
    ) -> Dict[str, Any]:
        """Handle monitoring daemon start operation."""
        try:
            # Start monitoring daemon
            success = self.daemon_manager.start_monitoring(
                interval=interval,
                supervised=supervised,
            )

            if auto_recovery:
                # Also start recovery daemon
                recovery_success = self.daemon_manager.start_recovery()
            else:
                recovery_success = True

            return {
                "success": success and recovery_success,
                "monitoring_started": success,
                "recovery_started": auto_recovery and recovery_success,
                "interval": interval,
                "supervised": supervised,
                "auto_recovery": auto_recovery,
                "message": "Monitoring daemon started successfully" if success else "Failed to start monitoring daemon",
            }

        except Exception as e:
            logger.error(f"Monitoring start failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "context": {
                    "interval": interval,
                    "supervised": supervised,
                },
            }

    def get_system_status(
        self,
        format_type: str = "summary",
        include_metrics: bool = True,
        include_health: bool = True,
    ) -> Dict[str, Any]:
        """Handle system status retrieval operation."""
        try:
            # Get basic system info
            sessions = self.tmux.list_sessions()
            total_agents = sum(len(self.tmux.list_windows(s["name"])) for s in sessions)

            status_data = {
                "timestamp": datetime.now().isoformat(),
                "sessions": len(sessions),
                "total_agents": total_agents,
                "system_health": "operational",
                "monitoring_active": self.daemon_manager.is_monitoring_active(),
                "recovery_active": self.daemon_manager.is_recovery_active(),
            }

            if format_type == "detailed" and include_metrics:
                # Add detailed session breakdown
                session_details = []
                for session_dict in sessions:
                    windows = self.tmux.list_windows(session_dict["name"])
                    session_details.append({
                        "name": session_dict["name"],
                        "agent_count": len(windows),
                        "created": session_dict.get("created"),
                    })
                status_data["session_details"] = session_details

            if include_health:
                # Add health indicators
                status_data["health_indicators"] = {
                    "sessions_healthy": len(sessions) > 0,
                    "agents_active": total_agents > 0,
                    "monitoring_operational": self.daemon_manager.is_monitoring_active(),
                }

            return {
                "success": True,
                "format": format_type,
                "status": status_data,
            }

        except Exception as e:
            logger.error(f"System status retrieval failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "context": {"format_type": format_type},
            }

    def stop_monitoring(
        self,
        stop_recovery: bool = True,
        graceful: bool = True,
    ) -> Dict[str, Any]:
        """Handle monitoring daemon stop operation."""
        try:
            # Stop monitoring daemon
            monitoring_stopped = self.daemon_manager.stop_monitoring(graceful=graceful)

            recovery_stopped = True
            if stop_recovery:
                recovery_stopped = self.daemon_manager.stop_recovery(graceful=graceful)

            return {
                "success": monitoring_stopped and recovery_stopped,
                "monitoring_stopped": monitoring_stopped,
                "recovery_stopped": stop_recovery and recovery_stopped,
                "graceful": graceful,
                "message": "Monitoring systems stopped successfully" if monitoring_stopped else "Failed to stop monitoring systems",
            }

        except Exception as e:
            logger.error(f"Monitoring stop failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "context": {
                    "stop_recovery": stop_recovery,
                    "graceful": graceful,
                },
            }
```

### Step 3: Create Team Operations Tools

Create `tmux_orchestrator/mcp/tools/team_operations.py`:

```python
"""Phase 2 MCP tools for team operations."""

import logging
from typing import Any, Dict

from tmux_orchestrator.mcp.server import mcp
from tmux_orchestrator.mcp.handlers.team_handlers import TeamHandlers

logger = logging.getLogger(__name__)

# Initialize handlers
team_handlers = TeamHandlers()


@mcp.tool()
async def deploy_team(
    team_name: str,
    team_type: str,
    size: int = 3,
    project_path: str | None = None,
    briefing_context: str | None = None,
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
    logger.info(f"Deploying team: {team_type} with {size} agents")
    return await team_handlers.deploy_team(
        team_name=team_name,
        team_type=team_type,
        size=size,
        project_path=project_path,
        briefing_context=briefing_context,
    )


@mcp.tool()
def get_team_status(
    session: str | None = None,
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
    logger.info(f"Getting team status for: {session or 'all teams'}")
    return team_handlers.get_team_status(
        session=session,
        detailed=detailed,
        include_agents=include_agents,
    )


@mcp.tool()
def team_broadcast(
    session: str,
    message: str,
    exclude_windows: list[str] | None = None,
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
    logger.info(f"Broadcasting to team {session}")
    return team_handlers.team_broadcast(
        session=session,
        message=message,
        exclude_windows=exclude_windows or [],
        urgent=urgent,
    )
```

### Step 4: Create Monitoring Tools

Create `tmux_orchestrator/mcp/tools/monitoring.py`:

```python
"""Phase 2 MCP tools for monitoring operations."""

import logging
from typing import Any, Dict

from tmux_orchestrator.mcp.server import mcp
from tmux_orchestrator.mcp.handlers.monitoring_handlers import MonitoringHandlers

logger = logging.getLogger(__name__)

# Initialize handlers
monitoring_handlers = MonitoringHandlers()


@mcp.tool()
def start_monitoring(
    interval: int = 30,
    supervised: bool = False,
    auto_recovery: bool = True,
) -> Dict[str, Any]:
    """
    Start the monitoring daemon for agent health tracking.

    Args:
        interval: Monitoring interval in seconds
        supervised: Run in supervised mode
        auto_recovery: Enable automatic recovery of failed agents

    Returns:
        Dict with monitoring daemon status and configuration
    """
    logger.info(f"Starting monitoring with interval {interval}s")
    return monitoring_handlers.start_monitoring(
        interval=interval,
        supervised=supervised,
        auto_recovery=auto_recovery,
    )


@mcp.tool()
def get_system_status(
    format_type: str = "summary",
    include_metrics: bool = True,
    include_health: bool = True,
) -> Dict[str, Any]:
    """
    Get comprehensive system status dashboard.

    Args:
        format_type: Status report format (summary, detailed, json)
        include_metrics: Include performance metrics
        include_health: Include health indicators

    Returns:
        Dict with system overview, health status, and performance data
    """
    logger.info(f"Getting system status in {format_type} format")
    return monitoring_handlers.get_system_status(
        format_type=format_type,
        include_metrics=include_metrics,
        include_health=include_health,
    )


@mcp.tool()
def stop_monitoring(
    stop_recovery: bool = True,
    graceful: bool = True,
) -> Dict[str, Any]:
    """
    Stop the monitoring daemon and related services.

    Args:
        stop_recovery: Also stop recovery daemon
        graceful: Graceful shutdown vs immediate termination

    Returns:
        Dict with shutdown status and final metrics
    """
    logger.info("Stopping monitoring systems")
    return monitoring_handlers.stop_monitoring(
        stop_recovery=stop_recovery,
        graceful=graceful,
    )
```

### Step 5: Update Server Configuration

Update `tmux_orchestrator/mcp/server.py` to include Phase 2 tools:

```python
# Add these imports after the Phase 1 import
from .tools.team_operations import *  # noqa: F401, F403
from .tools.monitoring import *  # noqa: F401, F403

logger.info("FastMCP server initialized with Phase 1-2 tools")
```

### Step 6: Update Package Exports

Update `tmux_orchestrator/mcp/tools/__init__.py`:

```python
"""MCP tools for tmux-orchestrator."""

from .agent_management import register_agent_tools
from .team_operations import *  # noqa: F401, F403
from .monitoring import *  # noqa: F401, F403

__all__ = ["register_agent_tools"]
```

Update `tmux_orchestrator/mcp/handlers/__init__.py`:

```python
"""Business logic handlers for MCP tools."""

from .agent_handlers import AgentHandlers
from .team_handlers import TeamHandlers
from .monitoring_handlers import MonitoringHandlers

__all__ = ["AgentHandlers", "TeamHandlers", "MonitoringHandlers"]
```

## Error Handling Patterns

### Standardized Error Response Format

All MCP tools should return errors in this standardized format:

```python
{
    "success": False,
    "error": "Human-readable error message",
    "error_type": "ErrorTypeName",
    "context": {
        "relevant": "debugging_info",
        "operation": "attempted_operation"
    },
    "retry_after": 30,  # Optional: seconds to wait before retry
    "recovery_suggestions": [  # Optional: suggested actions
        "Check if tmux session exists",
        "Verify agent is responsive"
    ]
}
```

### Error Categories

#### 1. Validation Errors
- **Type**: `ValidationError`
- **Causes**: Invalid parameters, missing required fields
- **Recovery**: Fix parameters and retry

```python
try:
    validate_team_type(team_type)
except ValidationError as e:
    return {
        "success": False,
        "error": f"Invalid team type: {team_type}",
        "error_type": "ValidationError",
        "context": {"team_type": team_type, "valid_types": ["frontend", "backend", "fullstack", "testing"]}
    }
```

#### 2. Resource Errors
- **Type**: `ResourceError`
- **Causes**: Session not found, agent unavailable
- **Recovery**: Check resource existence, create if needed

```python
if not self.tmux.has_session(session):
    return {
        "success": False,
        "error": f"Session '{session}' not found",
        "error_type": "ResourceNotFound",
        "context": {"session": session},
        "recovery_suggestions": ["Create session first", "Check session name spelling"]
    }
```

#### 3. Operation Errors
- **Type**: `OperationError`
- **Causes**: Failed tmux commands, network issues
- **Recovery**: Retry operation, check system state

```python
try:
    result = await core_operation()
except Exception as e:
    return {
        "success": False,
        "error": f"Operation failed: {str(e)}",
        "error_type": "OperationError",
        "context": {"operation": "deploy_team", "exception": type(e).__name__},
        "retry_after": 30
    }
```

#### 4. Rate Limit Errors
- **Type**: `RateLimitError`
- **Causes**: Too many requests
- **Recovery**: Wait and retry

```python
{
    "success": False,
    "error": "Rate limit exceeded. Please wait before retrying.",
    "error_type": "RateLimitError",
    "retry_after": 60,
    "context": {"requests_per_minute": 100, "current_requests": 105}
}
```

### Exception Handling Best Practices

#### 1. Handler Pattern
```python
def handler_method(self, ...):
    """Handler with proper error handling."""
    try:
        # Validate inputs
        if not param:
            raise ValidationError("Parameter required")

        # Perform operation
        result = self.core_operation()

        # Return success response
        return {"success": True, "data": result}

    except ValidationError as e:
        logger.error(f"Validation failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": "ValidationError"
        }
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return {
            "success": False,
            "error": "Internal error occurred",
            "error_type": type(e).__name__
        }
```

#### 2. Logging Standards
```python
# Error logging with context
logger.error(
    f"Team deployment failed: {e}",
    extra={
        "team_name": team_name,
        "team_type": team_type,
        "error_type": type(e).__name__
    },
    exc_info=True
)

# Success logging
logger.info(
    f"Team deployed successfully",
    extra={
        "team_name": team_name,
        "agent_count": agent_count,
        "duration_seconds": duration
    }
)
```

## Migration Strategy Details

### Pre-Migration Checklist
- [ ] Phase 1 fully implemented and tested
- [ ] All existing tests passing
- [ ] FastMCP server running stable
- [ ] Core business logic unchanged
- [ ] Backup of current implementation

### Migration Steps

#### Step 1: Implementation (1-2 days)
1. Create handlers (`team_handlers.py`, `monitoring_handlers.py`)
2. Create tools (`team_operations.py`, `monitoring.py`)
3. Update server configuration
4. Update package exports

#### Step 2: Testing (1 day)
1. Unit tests for handlers
2. Integration tests for tools
3. End-to-end CLI tests
4. Performance regression tests

#### Step 3: Deployment (0.5 days)
1. Deploy to staging environment
2. Run full test suite
3. Validate CLI compatibility
4. Deploy to production

### Rollback Procedures

#### Immediate Rollback
If critical issues are discovered:

1. **Revert Server Changes**:
   ```bash
   git checkout HEAD~1 tmux_orchestrator/mcp/server.py
   ```

2. **Remove Phase 2 Files**:
   ```bash
   rm tmux_orchestrator/mcp/tools/team_operations.py
   rm tmux_orchestrator/mcp/tools/monitoring.py
   rm tmux_orchestrator/mcp/handlers/team_handlers.py
   rm tmux_orchestrator/mcp/handlers/monitoring_handlers.py
   ```

3. **Restart Server**:
   ```bash
   python -m tmux_orchestrator.mcp.server
   ```

#### Gradual Rollback
For non-critical issues:

1. **Disable Phase 2 Tools**:
   ```python
   # Comment out imports in server.py
   # from .tools.team_operations import *
   # from .tools.monitoring import *
   ```

2. **Monitor and Fix**:
   - Monitor error logs
   - Fix issues incrementally
   - Re-enable tools gradually

### Testing Strategy

#### Unit Tests
```python
# tests/mcp/handlers/test_team_handlers.py
import pytest
from tmux_orchestrator.mcp.handlers.team_handlers import TeamHandlers

class TestTeamHandlers:
    @pytest.fixture
    def team_handlers(self):
        return TeamHandlers()

    async def test_deploy_team_success(self, team_handlers):
        result = await team_handlers.deploy_team(
            team_name="test-team",
            team_type="frontend",
            size=3
        )
        assert result["success"] is True
        assert result["team_type"] == "frontend"

    async def test_deploy_team_invalid_type(self, team_handlers):
        result = await team_handlers.deploy_team(
            team_name="test-team",
            team_type="invalid",
            size=3
        )
        assert result["success"] is False
        assert result["error_type"] == "ValidationError"
```

#### Integration Tests
```python
# tests/mcp/integration/test_team_operations.py
import pytest
from tmux_orchestrator.mcp.tools.team_operations import deploy_team

class TestTeamOperationsIntegration:
    async def test_deploy_team_end_to_end(self):
        # Test complete team deployment workflow
        result = await deploy_team(
            team_name="integration-test",
            team_type="backend",
            size=2
        )

        assert result["success"] is True

        # Verify team was actually created
        status_result = get_team_status(session="integration-test")
        assert status_result["success"] is True
        assert status_result["agent_count"] == 2
```

## Success Criteria

### Phase 2 Complete When:
- [ ] All 6 Phase 2 tools implemented
- [ ] All unit tests passing (>95% coverage)
- [ ] All integration tests passing
- [ ] CLI commands work through MCP tools
- [ ] Error handling follows standardized patterns
- [ ] Performance meets benchmarks
- [ ] Documentation updated

### Performance Benchmarks:
- Tool response time: <2 seconds
- Team deployment: <30 seconds
- System status: <5 seconds
- Memory usage: <10% increase from Phase 1

This completes the Phase 2 implementation guide. The pattern established here will be followed for Phases 3-5, ensuring consistency and maintainability across the entire MCP migration.

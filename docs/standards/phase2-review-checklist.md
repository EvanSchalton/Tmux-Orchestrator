# Phase 2 MCP Code Review Checklist - Team Coordination Tools

**Version**: 1.0
**Date**: 2025-08-16
**Applies To**: Phase 2 FastMCP team operations and monitoring tools

## Overview

This checklist extends the base MCP code review standards for Phase 2 team coordination tools. Focus areas include multi-agent coordination, system monitoring, and operational management tools.

## 1. Team Coordination Validation ✅

### 1.1 Team Deployment Validation

**✅ MANDATORY**: Team deployment tools MUST validate:

```python
# Team type validation
valid_team_types = ["frontend", "backend", "fullstack", "testing"]
if team_type not in valid_team_types:
    return {"success": False, "error": f"Invalid team type. Must be one of: {', '.join(valid_team_types)}", "error_type": "ValidationError"}

# Team size validation
if not 2 <= size <= 10:
    return {"success": False, "error": "Team size must be between 2 and 10", "error_type": "ValidationError"}

# Team name validation
if not team_name.strip():
    return {"success": False, "error": "Team name cannot be empty", "error_type": "ValidationError"}
```

**❌ FORBIDDEN**: Accepting invalid team configurations:
```python
# Don't allow
size = -1  # Invalid size
team_type = "invalid"  # Invalid type
team_name = ""  # Empty name
```

### 1.2 Session Management Validation

**✅ REQUIRED**: Session-based operations MUST validate:

```python
# Session name validation
if not session.strip():
    return {"success": False, "error": "Session name cannot be empty", "error_type": "ValidationError"}

# Session existence check (in handlers)
if not tmux.has_session(session):
    return {"success": False, "error": f"Session '{session}' not found", "error_type": "NotFoundError"}
```

### 1.3 Message Broadcasting Validation

**✅ MANDATORY**: Broadcast tools MUST validate:

```python
# Message content validation
if not message.strip():
    return {"success": False, "error": "Message cannot be empty", "error_type": "ValidationError"}

# Session validation
if not session.strip():
    return {"success": False, "error": "Session name cannot be empty", "error_type": "ValidationError"}

# Window exclusion list validation
if exclude_windows:
    if not isinstance(exclude_windows, list):
        return {"success": False, "error": "exclude_windows must be a list", "error_type": "ValidationError"}
```

## 2. Monitoring System Validation ✅

### 2.1 Monitoring Configuration Validation

**✅ REQUIRED**: Monitoring tools MUST validate intervals and options:

```python
# Monitoring interval validation
if not 5 <= interval <= 300:
    return {"success": False, "error": "Monitoring interval must be between 5 and 300 seconds", "error_type": "ValidationError"}

# Format type validation
valid_formats = ["summary", "detailed", "json"]
if format_type not in valid_formats:
    return {"success": False, "error": f"Invalid format type. Must be one of: {', '.join(valid_formats)}", "error_type": "ValidationError"}
```

### 2.2 System Status Response Standards

**✅ MANDATORY**: System status tools MUST return structured data:

```python
# Required response structure
{
    "success": True,
    "timestamp": "2024-01-01T00:00:00Z",
    "system_health": "healthy",  # healthy, warning, critical
    "total_sessions": 5,
    "total_agents": 12,
    "active_agents": 10,
    "metrics": {...},  # If include_metrics=True
    "health_details": {...}  # If include_health=True
}
```

## 3. Multi-Agent Coordination Patterns ✅

### 3.1 Concurrent Operation Handling

**✅ REQUIRED**: Tools affecting multiple agents MUST handle concurrency:

```python
@mcp.tool()
async def team_broadcast(...) -> dict[str, Any]:
    """Broadcast must handle multiple agents safely."""
    try:
        # Get all target agents
        agents = await get_team_agents(session)

        # Process concurrently but safely
        results = []
        for agent in agents:
            try:
                result = await send_to_agent(agent, message)
                results.append({"agent": agent, "success": True, "result": result})
            except Exception as e:
                results.append({"agent": agent, "success": False, "error": str(e)})

        # Return comprehensive results
        successful = sum(1 for r in results if r["success"])
        return {
            "success": successful > 0,
            "total_sent": len(results),
            "successful": successful,
            "failed": len(results) - successful,
            "results": results
        }
    except Exception as e:
        return {"success": False, "error": str(e), "error_type": type(e).__name__}
```

### 3.2 Agent State Coordination

**✅ REQUIRED**: Team status tools MUST aggregate agent states:

```python
# Agent state aggregation pattern
agent_states = {
    "healthy": 0,
    "idle": 0,
    "busy": 0,
    "error": 0,
    "unknown": 0
}

for agent in team_agents:
    state = agent.get("health_status", "unknown")
    agent_states[state] = agent_states.get(state, 0) + 1

team_health = determine_team_health(agent_states)
```

## 4. Resource Management Standards ✅

### 4.1 Team Size Limits

**✅ MANDATORY**: Enforce reasonable team size limits:

```python
# Team size constraints
MIN_TEAM_SIZE = 2
MAX_TEAM_SIZE = 10
DEFAULT_TEAM_SIZE = 3

if not MIN_TEAM_SIZE <= size <= MAX_TEAM_SIZE:
    return {
        "success": False,
        "error": f"Team size must be between {MIN_TEAM_SIZE} and {MAX_TEAM_SIZE}",
        "error_type": "ValidationError"
    }
```

### 4.2 Monitoring Resource Limits

**✅ REQUIRED**: Monitoring tools MUST respect system limits:

```python
# Monitoring constraints
MIN_INTERVAL = 5      # 5 seconds minimum
MAX_INTERVAL = 300    # 5 minutes maximum
DEFAULT_INTERVAL = 30 # 30 seconds default

# Resource usage validation
if supervised and not check_supervisor_available():
    return {"success": False, "error": "Supervisor not available", "error_type": "ResourceError"}
```

## 5. Team-Specific Error Handling ✅

### 5.1 Team Operation Error Categories

**✅ REQUIRED**: Phase 2 tools MUST handle specific error types:

```python
# Team deployment errors
"TeamDeploymentError"    # Team creation failed
"AgentSpawnError"        # Individual agent spawn failed
"ConfigurationError"     # Invalid team configuration
"ResourceError"          # Insufficient resources

# Team coordination errors
"BroadcastError"        # Message delivery failed
"CoordinationError"     # Team coordination failed
"SessionError"          # Session management failed

# Monitoring errors
"MonitoringError"       # Monitoring system error
"DaemonError"           # Daemon start/stop error
"MetricsError"          # Metrics collection error
```

### 5.2 Partial Success Handling

**✅ MANDATORY**: Tools affecting multiple targets MUST report partial success:

```python
@mcp.tool()
async def team_operation(...) -> dict[str, Any]:
    """Handle partial success scenarios."""
    results = []
    successful = 0
    failed = 0

    for target in targets:
        try:
            result = await process_target(target)
            results.append({"target": target, "success": True, "result": result})
            successful += 1
        except Exception as e:
            results.append({"target": target, "success": False, "error": str(e)})
            failed += 1

    return {
        "success": successful > 0,  # Success if ANY succeeded
        "total_operations": len(targets),
        "successful": successful,
        "failed": failed,
        "partial_success": 0 < successful < len(targets),
        "results": results
    }
```

## 6. Documentation Standards for Phase 2 ✅

### 6.1 Team Tool Documentation

**✅ MANDATORY**: Team coordination tools MUST document:

```python
@mcp.tool()
async def deploy_team(
    team_name: str,
    team_type: str,
    size: int = 3,
) -> dict[str, Any]:
    """
    Deploy a team of specialized Claude agents.

    Creates a coordinated team of agents with specific roles and
    configurations optimized for the specified team type.

    Args:
        team_name: Name for the team/session (must be unique)
        team_type: Type of team - determines agent composition
            - frontend: UI/UX, React, CSS specialists
            - backend: API, database, server specialists
            - fullstack: Mixed frontend/backend specialists
            - testing: QA, automation, performance specialists
        size: Number of agents (2-10, recommended 3-5)

    Returns:
        Dict containing:
        - success: Boolean operation result
        - team_name: Created team name
        - agents: List of spawned agents with details
        - team_config: Team configuration summary
        - deployment_time: Time taken to deploy

    Raises:
        ValidationError: Invalid team configuration
        ResourceError: Insufficient system resources
        TeamDeploymentError: Team creation failed

    Examples:
        Basic team deployment:
        >>> result = await deploy_team("proj-alpha", "frontend", 3)
        >>> assert result["success"] is True
        >>> assert len(result["agents"]) == 3

        Large backend team:
        >>> result = await deploy_team("api-service", "backend", 5)
        >>> assert result["team_config"]["type"] == "backend"
    """
```

### 6.2 Monitoring Tool Documentation

**✅ REQUIRED**: Monitoring tools MUST document operational impact:

```python
@mcp.tool()
async def start_monitoring(
    interval: int = 30,
    supervised: bool = False,
) -> dict[str, Any]:
    """
    Start the monitoring daemon for agent health tracking.

    Initiates system-wide monitoring of all agents with configurable
    health checks, performance tracking, and automatic recovery.

    Args:
        interval: Monitoring check interval in seconds (5-300)
            - 5-15s: High-frequency for critical systems
            - 30-60s: Standard monitoring (recommended)
            - 120-300s: Light monitoring for stable systems
        supervised: Run in supervised mode with process management
            - True: Automatic restart if daemon fails
            - False: Manual restart required

    Returns:
        Dict containing:
        - success: Boolean operation result
        - daemon_pid: Process ID of monitoring daemon
        - config: Active monitoring configuration
        - status: Current daemon status

    Side Effects:
        - Creates monitoring daemon process
        - Begins periodic health checks
        - May trigger agent recovery actions
        - Logs monitoring events to system log

    Examples:
        Standard monitoring:
        >>> result = await start_monitoring(30, False)
        >>> assert result["success"] is True

        High-frequency supervised monitoring:
        >>> result = await start_monitoring(10, True)
        >>> assert result["config"]["supervised"] is True
    """
```

## 7. Performance Standards for Phase 2 ✅

### 7.1 Team Operation Performance

**✅ REQUIRED**: Team operations MUST meet performance targets:

```python
# Team deployment performance targets
TEAM_DEPLOYMENT_TIMEOUT = 120  # 2 minutes max for team deployment
AGENT_SPAWN_TIMEOUT = 30       # 30 seconds max per agent
BROADCAST_TIMEOUT = 10         # 10 seconds max for team broadcast

# Status operation performance targets
TEAM_STATUS_TIMEOUT = 5        # 5 seconds max for team status
SYSTEM_STATUS_TIMEOUT = 10     # 10 seconds max for system status
```

### 7.2 Monitoring Performance

**✅ MANDATORY**: Monitoring tools MUST be efficient:

```python
# Monitoring performance requirements
MAX_MONITORING_OVERHEAD = 0.05  # 5% CPU overhead max
MAX_STATUS_RESPONSE_TIME = 1.0   # 1 second max response time
MAX_AGENTS_PER_CHECK = 50       # 50 agents max per check cycle
```

## 8. Integration Requirements ✅

### 8.1 Phase 1 Compatibility

**✅ REQUIRED**: Phase 2 tools MUST integrate cleanly with Phase 1:

```python
# Use Phase 1 tools in Phase 2 operations
async def deploy_team_member(session: str, agent_type: str) -> dict[str, Any]:
    """Deploy individual team member using Phase 1 spawn_agent."""
    from tmux_orchestrator.mcp.tools.agent_management import spawn_agent

    return await spawn_agent(
        session_name=session,
        agent_type=agent_type,
        use_context=True
    )
```

### 8.2 Handler Integration

**✅ MANDATORY**: Phase 2 tools MUST delegate to handlers:

```python
# Correct Phase 2 tool pattern
@mcp.tool()
async def team_operation(...) -> dict[str, Any]:
    """Team operation with proper delegation."""
    # 1. Input validation in tool
    if validation_fails:
        return error_response

    # 2. Delegate to handler
    return await team_handlers.operation(...)

# Handler implements business logic
class TeamHandlers:
    async def operation(self, ...) -> dict[str, Any]:
        # Business logic here
        result = await core_team_operation(...)
        return format_response(result)
```

## 9. Testing Requirements for Phase 2 ✅

### 9.1 Team Coordination Testing

**✅ REQUIRED**: Phase 2 tools MUST have comprehensive tests:

```python
# Team deployment testing
async def test_deploy_team_success():
    """Test successful team deployment."""
    result = await deploy_team("test-team", "frontend", 3)
    assert result["success"] is True
    assert len(result["agents"]) == 3
    assert result["team_config"]["type"] == "frontend"

async def test_deploy_team_validation():
    """Test team deployment validation."""
    # Invalid team type
    result = await deploy_team("test", "invalid", 3)
    assert result["success"] is False
    assert result["error_type"] == "ValidationError"

    # Invalid size
    result = await deploy_team("test", "frontend", 15)
    assert result["success"] is False
    assert "size must be between" in result["error"]

# Broadcasting testing
async def test_team_broadcast_partial_success():
    """Test broadcast with some failures."""
    result = await team_broadcast("test-session", "Hello team")
    # Should handle partial success gracefully
    assert "successful" in result
    assert "failed" in result
    assert "results" in result
```

### 9.2 Monitoring Testing

**✅ REQUIRED**: Monitoring tools MUST handle edge cases:

```python
async def test_monitoring_interval_validation():
    """Test monitoring interval validation."""
    # Too low
    result = await start_monitoring(1)
    assert result["success"] is False
    assert "interval must be between" in result["error"]

    # Too high
    result = await start_monitoring(500)
    assert result["success"] is False

async def test_system_status_formats():
    """Test all system status formats."""
    for format_type in ["summary", "detailed", "json"]:
        result = await get_system_status(format_type)
        assert result["success"] is True
        assert result["format"] == format_type
```

## 10. Phase 2 Review Checklist ✅

### 10.1 Pre-Review Checklist

- [ ] All team tools validate team configuration
- [ ] All monitoring tools validate intervals and options
- [ ] All tools handle multi-agent scenarios
- [ ] All tools report partial success appropriately
- [ ] All tools delegate to handlers properly
- [ ] All tools follow Phase 1 error patterns
- [ ] All tools have comprehensive docstrings
- [ ] All tools have modern type hints

### 10.2 Review Process for Phase 2

1. **Team Validation Review**: Check team configuration validation
2. **Monitoring Review**: Verify monitoring system integration
3. **Multi-Agent Review**: Test concurrent operation handling
4. **Performance Review**: Validate response times and resource usage
5. **Integration Review**: Ensure Phase 1 compatibility
6. **Documentation Review**: Verify operational documentation

### 10.3 Phase 2 Approval Criteria

**✅ APPROVED**: All standards met, team coordination working
**⚠️ CONDITIONAL**: Standards met with minor team operation issues
**❌ REJECTED**: Team coordination failures, must be fixed

## 11. Phase 2 Specific Failure Modes ✅

### 11.1 Team Coordination Failures

```python
# Common Phase 2 failure patterns to test
- Team deployment timeout
- Partial agent spawn failure
- Broadcast delivery failure
- Session coordination failure
- Agent state inconsistency
- Resource exhaustion during team creation
```

### 11.2 Monitoring System Failures

```python
# Monitoring failure patterns to handle
- Daemon startup failure
- Monitoring data corruption
- Agent health check timeout
- System resource exhaustion
- Concurrent monitoring conflicts
```

---

**This checklist is MANDATORY for all Phase 2 MCP implementations.**

**Focus**: Team coordination, multi-agent management, system monitoring
**Standards**: Extends base MCP standards with Phase 2 specifics

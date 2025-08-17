# MCP Code Review Standards

**Version**: 1.0
**Effective Date**: 2025-08-16
**Applies To**: All FastMCP tool implementations in tmux-orchestrator

## Overview

This document establishes mandatory standards for all FastMCP implementations in the tmux-orchestrator project. These standards ensure consistency, maintainability, and proper separation of concerns across all MCP tools.

## 1. FastMCP Decorator Standards

### 1.1 Required Decorator Pattern

**✅ MANDATORY**: All MCP tools MUST use the async decorator pattern:

```python
from tmux_orchestrator.mcp.server import mcp

@mcp.tool()
async def tool_name(
    param1: str,
    param2: int = 5,
    param3: str | None = None
) -> dict[str, Any]:
    """Tool description."""
```

**❌ FORBIDDEN**: Sync tools, incorrect decorator syntax:

```python
@mcp.tool  # Missing parentheses
def sync_tool():  # Not async
    pass

@tool()  # Wrong decorator
async def wrong_decorator():
    pass
```

### 1.2 Decorator Requirements

- **MUST** use `@mcp.tool()` with parentheses
- **MUST** declare functions as `async def`
- **MUST** import from `tmux_orchestrator.mcp.server import mcp`
- **MUST** have comprehensive docstring with Args/Returns sections

### 1.3 Tool Naming Conventions

```python
# ✅ Correct naming
@mcp.tool()
async def spawn_agent():  # Snake case, descriptive verb

@mcp.tool()
async def get_agent_status():  # Clear action and object

# ❌ Incorrect naming
@mcp.tool()
async def doStuff():  # CamelCase not allowed

@mcp.tool()
async def agent():  # Too vague, no action
```

## 2. Type Hint Requirements

### 2.1 Modern Type Syntax (MANDATORY)

**✅ REQUIRED**: Use Python 3.10+ union syntax:

```python
from typing import Any

async def tool_name(
    session_name: str,                    # Required string
    agent_type: str = "developer",       # Optional with default
    project_path: str | None = None,     # Optional nullable
    options: dict[str, Any] | None = None # Complex types
) -> dict[str, Any]:                      # Return type annotation
```

**❌ FORBIDDEN**: Old typing patterns:

```python
from typing import Optional, Dict, List, Union

async def tool_name(
    project_path: Optional[str] = None,   # Use str | None
    options: Dict[str, Any] = None,       # Use dict[str, Any]
    items: List[str] = [],                # Use list[str]
    value: Union[str, int] = 1            # Use str | int
) -> Dict[str, Any]:                      # Use dict[str, Any]
```

### 2.2 Type Annotation Rules

1. **ALL parameters MUST have type hints**
2. **ALL functions MUST have return type annotations**
3. **Use lowercase built-in types**: `dict`, `list`, `tuple`, not `Dict`, `List`, `Tuple`
4. **Union types use pipe syntax**: `str | int`, not `Union[str, int]`
5. **Optional types use pipe syntax**: `str | None`, not `Optional[str]`

### 2.3 Complex Type Examples

```python
# ✅ Correct complex types
from typing import Any

async def deploy_team(
    team_name: str,
    team_config: dict[str, str | int] = {},
    agent_list: list[dict[str, Any]] = [],
    metadata: dict[str, str | bool | None] = {}
) -> dict[str, Any]:
```

## 3. Error Handling Patterns

### 3.1 Mandatory Error Response Structure

**✅ REQUIRED**: All tools MUST return this exact error structure:

```python
# Success response
{
    "success": True,
    "data": {...},                    # Tool-specific data
    "message": "Operation completed"  # Optional success message
}

# Error response
{
    "success": False,
    "error": "Human-readable error message",
    "error_type": "ExceptionClassName",
    "context": {                      # Optional debugging context
        "parameter": "value",
        "operation": "spawn_agent"
    }
}
```

### 3.2 Exception Handling Pattern

**✅ MANDATORY**: All tools MUST use this exception handling pattern:

```python
@mcp.tool()
async def tool_name(param: str) -> dict[str, Any]:
    """Tool description."""
    try:
        # Tool implementation
        result = await handler.operation(param)
        return {
            "success": True,
            "data": result,
            "message": "Operation completed successfully"
        }

    except ValidationError as e:
        logger.error(f"Validation error in {tool_name.__name__}: {e}")
        return {
            "success": False,
            "error": f"Invalid input: {str(e)}",
            "error_type": "ValidationError",
            "context": {"parameter": param}
        }

    except TimeoutError as e:
        logger.error(f"Timeout in {tool_name.__name__}: {e}")
        return {
            "success": False,
            "error": "Operation timed out",
            "error_type": "TimeoutError",
            "context": {"timeout_seconds": 30}
        }

    except Exception as e:
        logger.error(f"Unexpected error in {tool_name.__name__}: {e}")
        return {
            "success": False,
            "error": f"Operation failed: {str(e)}",
            "error_type": type(e).__name__,
            "context": {"operation": tool_name.__name__}
        }
```

### 3.3 Error Handling Requirements

1. **ALL tools MUST wrap implementation in try/except**
2. **MUST log errors with appropriate level**
3. **MUST provide user-friendly error messages**
4. **MUST include error_type for programmatic handling**
5. **SHOULD include context for debugging**
6. **MUST NOT expose sensitive information in errors**

## 4. Tool vs Handler Separation Rules

### 4.1 Architecture Layers (MANDATORY)

```
MCP Tools (Interface) → Handlers (Logic) → Core (Operations)
```

**Each layer has STRICT responsibilities:**

### 4.2 Tool Layer Rules

**✅ TOOLS MAY ONLY:**
- Define MCP interface with `@mcp.tool()` decorator
- Validate input parameters via type hints
- Call handler methods
- Transform handler responses for MCP protocol
- Log tool invocations

**❌ TOOLS MUST NEVER:**
- Contain business logic
- Make direct TMUXManager calls
- Perform file operations
- Execute subprocess commands
- Handle complex data transformations

```python
# ✅ Correct tool implementation
@mcp.tool()
async def spawn_agent(session_name: str, agent_type: str) -> dict[str, Any]:
    """Spawn a new Claude agent."""
    logger.info(f"Tool invoked: spawn_agent({session_name}, {agent_type})")

    # ONLY delegate to handler
    return await agent_handlers.spawn_agent(
        session_name=session_name,
        agent_type=agent_type
    )

# ❌ Incorrect tool implementation
@mcp.tool()
async def spawn_agent_wrong(session_name: str) -> dict[str, Any]:
    """BAD: Tool contains business logic."""
    tmux = TMUXManager()  # ❌ Direct tmux operations

    if not tmux.has_session(session_name):  # ❌ Business logic
        tmux.create_session(session_name)   # ❌ Core operations

    subprocess.run(["claude", "--start"])   # ❌ Subprocess calls
    return {"success": True}
```

### 4.3 Handler Layer Rules

**✅ HANDLERS MAY:**
- Implement business logic
- Create request/response objects
- Delegate to core operations
- Transform data between layers
- Handle complex validation
- Coordinate multiple core operations

**❌ HANDLERS MUST NOT:**
- Handle MCP protocol specifics
- Be directly callable by external systems
- Contain tmux operation implementations

```python
# ✅ Correct handler implementation
class AgentHandlers:
    def __init__(self):
        self.tmux = TMUXManager()

    async def spawn_agent(
        self,
        session_name: str,
        agent_type: str
    ) -> dict[str, Any]:
        """Handle agent spawning business logic."""
        try:
            # Create request object
            request = SpawnAgentRequest(
                session_name=session_name,
                agent_type=agent_type
            )

            # Delegate to core
            result = await core_spawn_agent(self.tmux, request)

            # Transform response
            return {
                "success": result.success,
                "session": result.session,
                "window": result.window,
                "target": result.target
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
```

### 4.4 Core Layer Rules

**✅ CORE OPERATIONS:**
- Implement actual tmux operations
- Handle low-level system interactions
- Provide reusable business logic
- Return structured result objects

```python
# ✅ Core operation example
async def core_spawn_agent(
    tmux: TMUXManager,
    request: SpawnAgentRequest
) -> SpawnAgentResult:
    """Core agent spawning implementation."""
    # Actual tmux operations here
    success = tmux.create_session(request.session_name)
    # ... implementation details

    return SpawnAgentResult(
        success=success,
        session=request.session_name,
        window=window_name,
        target=f"{request.session_name}:{window_name}"
    )
```

## 5. Documentation Standards

### 5.1 Required Docstring Format

**✅ MANDATORY**: All tools MUST use this exact docstring format:

```python
@mcp.tool()
async def tool_name(
    param1: str,
    param2: int = 5,
    param3: str | None = None
) -> dict[str, Any]:
    """
    Brief description of what the tool does (one line).

    Longer description if needed, explaining the tool's purpose,
    behavior, and any important considerations.

    Args:
        param1: Description of the first parameter
        param2: Description with default value behavior
        param3: Description of optional parameter

    Returns:
        Dict containing:
        - success: Boolean indicating operation success
        - data: Tool-specific response data
        - message: Optional success/error message

    Examples:
        Basic usage:
        >>> result = await tool_name("session1", 3)
        >>> assert result["success"] is True

    Note:
        Any important notes about usage, limitations, or side effects.
    """
```

### 5.2 Documentation Requirements

1. **Brief description** (one line)
2. **Detailed description** (if needed)
3. **Args section** describing each parameter
4. **Returns section** describing response structure
5. **Examples section** (recommended)
6. **Note section** for important information

## 6. File Organization Standards

### 6.1 Directory Structure (MANDATORY)

```
tmux_orchestrator/mcp/
├── __init__.py                    # Package exports
├── server.py                     # FastMCP server setup
├── tools/
│   ├── __init__.py               # Tool registration
│   ├── agent_management.py       # Phase 1 tools
│   ├── team_operations.py        # Phase 2 tools
│   └── monitoring.py             # Phase 2 tools
└── handlers/
    ├── __init__.py               # Handler exports
    ├── agent_handlers.py         # Phase 1 handlers
    ├── team_handlers.py          # Phase 2 handlers
    └── monitoring_handlers.py    # Phase 2 handlers
```

### 6.2 File Naming Rules

- **Tools**: Noun describing the operation domain (`agent_management.py`)
- **Handlers**: Same name with `_handlers` suffix (`agent_handlers.py`)
- **Snake case only**: `team_operations.py`, not `TeamOperations.py`
- **Descriptive names**: `monitoring.py`, not `mon.py`

### 6.3 Import Standards

**✅ REQUIRED imports in tools:**

```python
import logging
from typing import Any

from tmux_orchestrator.mcp.server import mcp
from tmux_orchestrator.mcp.handlers.{handler_module} import {HandlerClass}

logger = logging.getLogger(__name__)
```

**✅ REQUIRED imports in handlers:**

```python
import logging
from typing import Any

from tmux_orchestrator.core.{module} import {core_function}
from tmux_orchestrator.utils.tmux import TMUXManager

logger = logging.getLogger(__name__)
```

## 7. Testing Requirements

### 7.1 Test File Structure

```
tests/mcp/
├── test_tools/
│   ├── test_agent_management.py
│   └── test_team_operations.py
└── test_handlers/
    ├── test_agent_handlers.py
    └── test_team_handlers.py
```

### 7.2 Required Test Coverage

1. **Unit tests for each tool**
2. **Unit tests for each handler method**
3. **Error condition testing**
4. **Parameter validation testing**
5. **Integration tests with core modules**

### 7.3 Test Patterns

```python
# Tool testing pattern
async def test_spawn_agent_success():
    """Test successful agent spawning."""
    result = await spawn_agent("test-session", "developer")

    assert result["success"] is True
    assert result["session"] == "test-session"
    assert "target" in result

async def test_spawn_agent_validation_error():
    """Test validation error handling."""
    result = await spawn_agent("", "developer")  # Invalid session

    assert result["success"] is False
    assert result["error_type"] == "ValidationError"
```

## 8. Performance Standards

### 8.1 Response Time Requirements

- **Individual operations**: < 1 second 95th percentile
- **Batch operations**: < 5 seconds for up to 10 items
- **Status operations**: < 500ms 95th percentile

### 8.2 Resource Management

```python
# ✅ Correct resource management
class AgentHandlers:
    def __init__(self):
        self.tmux = TMUXManager()  # Per-handler instance

    async def operation(self):
        # Use self.tmux, no global state

# ❌ Incorrect resource management
tmux = TMUXManager()  # Global instance

class BadHandlers:
    async def operation(self):
        global tmux  # Shared state
```

## 9. Security Standards

### 9.1 Input Validation

- **Type validation** via function signatures
- **Parameter sanitization** in handlers
- **No shell command construction** from user input
- **Path traversal protection** for file operations

### 9.2 Error Information Security

```python
# ✅ Safe error messages
return {
    "success": False,
    "error": "Session not found",  # Generic, safe
    "error_type": "NotFoundError"
}

# ❌ Unsafe error messages
return {
    "success": False,
    "error": f"Failed to execute: {internal_command}",  # Exposes internals
    "error_type": "SystemError"
}
```

## 10. Code Review Checklist

### 10.1 Pre-Review Requirements

- [ ] All tools use correct `@mcp.tool()` async pattern
- [ ] All functions have complete type hints
- [ ] All tools have comprehensive docstrings
- [ ] Error handling follows mandatory pattern
- [ ] Tool/handler separation is maintained
- [ ] No business logic in tools
- [ ] No MCP protocol handling in handlers

### 10.2 Review Process

1. **Architecture Review**: Verify layer separation
2. **Type Safety Review**: Check all type annotations
3. **Error Handling Review**: Verify exception patterns
4. **Documentation Review**: Check docstring completeness
5. **Security Review**: Validate input handling
6. **Performance Review**: Check resource usage

### 10.3 Approval Criteria

**✅ APPROVED**: All standards met, no high-priority issues
**⚠️ CONDITIONAL**: Standards met with minor recommendations
**❌ REJECTED**: Standards violations, must be fixed

## 11. Migration from Existing Code

### 11.1 Legacy Code Updates

When updating existing MCP code to meet these standards:

1. **Update decorator syntax** to async pattern
2. **Modernize type hints** to 3.10+ syntax
3. **Restructure error handling** to standard pattern
4. **Separate tools and handlers** if mixed
5. **Add comprehensive documentation**

### 11.2 Backward Compatibility

- Maintain existing tool names and signatures
- Preserve response formats for external consumers
- Add new features as optional parameters

## 12. Enforcement

### 12.1 Automated Checks

- **mypy**: Type hint validation
- **ruff**: Code style and import organization
- **pytest**: Test coverage requirements

### 12.2 Manual Review

All MCP code changes MUST be reviewed by designated Code Reviewer before merge.

### 12.3 Violations

Code that violates these standards will be rejected and must be updated before approval.

---

**This document is MANDATORY for all MCP implementations in tmux-orchestrator.**

**Last Updated**: 2025-08-16
**Next Review**: 2025-09-16

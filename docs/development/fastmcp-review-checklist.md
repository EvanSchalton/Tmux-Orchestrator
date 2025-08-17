# FastMCP Code Review Checklist

**Version**: 1.0
**Date**: 2025-08-16
**For**: tmux-orchestrator Phase 1 FastMCP Implementation

## Overview

This checklist ensures all FastMCP implementations follow the approved architecture and maintain code quality standards for Phase 1 development.

## 1. Type Safety Compliance ✅

### Required Type Annotations
- [ ] All tool functions have complete type hints for parameters
- [ ] All tool functions have return type annotations
- [ ] Use modern Python 3.10+ union syntax (`str | None` not `Optional[str]`)
- [ ] Async functions properly declared as `async def`
- [ ] Generic types properly specified (e.g., `dict[str, Any]` not `dict`)

### Example - Correct Type Usage:
```python
@mcp.tool()
async def spawn_agent(
    session_name: str,
    agent_type: str = "developer",
    project_path: str | None = None,
    briefing_message: str | None = None,
    use_context: bool = True,
    window_name: str | None = None
) -> dict[str, Any]:
```

### Common Type Issues to Flag:
- [ ] Missing return type annotations
- [ ] Using old `Optional[]` syntax
- [ ] Missing imports for type hints
- [ ] Using `dict` without type parameters

## 2. Error Handling Patterns ✅

### Required Error Response Structure
All tools must return consistent error responses:

```python
# Success response
{
    "success": True,
    "data": {...},
    "message": "Operation completed successfully"
}

# Error response
{
    "success": False,
    "error": "Human-readable error message",
    "error_type": "ExceptionClassName",
    "context": {"key": "value"}  # Optional debugging context
}
```

### Error Handling Checklist:
- [ ] All tools wrapped in try/catch blocks
- [ ] Consistent error response format used
- [ ] Error messages are user-friendly, not technical stack traces
- [ ] Error types include exception class names
- [ ] Context information provided for debugging
- [ ] No sensitive information leaked in error messages

### Exception Handling Pattern:
```python
@mcp.tool()
async def tool_name(...) -> dict[str, Any]:
    try:
        # Tool implementation
        return {"success": True, "data": result}
    except ValidationError as e:
        return {
            "success": False,
            "error": f"Invalid input: {str(e)}",
            "error_type": "ValidationError",
            "context": {"input_provided": "..."}
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Operation failed: {str(e)}",
            "error_type": type(e).__name__
        }
```

## 3. FastMCP Decorator Usage ✅

### Required Decorator Patterns
- [ ] Tools use `@mcp.tool()` decorator (not `@mcp.tool` without parentheses)
- [ ] Server instance is correctly named `mcp`
- [ ] Proper FastMCP import: `from fastmcp import FastMCP`
- [ ] Server initialization: `mcp = FastMCP("tmux-orchestrator")`

### Tool Definition Requirements:
- [ ] Each tool has comprehensive docstring with Args and Returns sections
- [ ] Parameter descriptions are clear and specific
- [ ] Default values are appropriate and documented
- [ ] Tool names follow snake_case convention

### Example - Correct Decorator Usage:
```python
from fastmcp import FastMCP

mcp = FastMCP("tmux-orchestrator")

@mcp.tool()
async def spawn_agent(
    session_name: str,
    agent_type: str = "developer"
) -> dict[str, Any]:
    """
    Spawn a new Claude agent in a tmux session.

    Args:
        session_name: Name for the tmux session
        agent_type: Type of agent (developer, pm, qa, devops, reviewer, researcher, docs)

    Returns:
        Dict with success status, session, window, and target information
    """
```

## 4. Separation of Concerns ✅

### Architecture Compliance
- [ ] Tools only handle MCP interface logic
- [ ] Business logic delegated to core modules
- [ ] No direct tmux operations in tool code
- [ ] No file system operations in tool code
- [ ] No complex business logic in tool functions

### Required Delegation Pattern:
```python
@mcp.tool()
async def spawn_agent(...) -> dict[str, Any]:
    try:
        tmux = TMUXManager()

        # Delegate to core business logic
        result = await core_spawn_agent(
            tmux=tmux,
            session_name=session_name,
            agent_type=agent_type
        )

        # Transform result for MCP response
        return {
            "success": result.success,
            "data": result.to_dict()
        }
    except Exception as e:
        # Error handling...
```

### Forbidden in Tools:
- [ ] Direct subprocess calls
- [ ] File I/O operations
- [ ] Complex business logic
- [ ] TMUXManager method calls beyond delegation
- [ ] Configuration file parsing

## 5. Package Structure Compliance ✅

### Required Directory Structure:
```
tmux_orchestrator/mcp/
├── __init__.py              # Exports main mcp instance
├── server.py               # FastMCP server setup
├── tools/
│   ├── __init__.py         # Tool registration
│   └── agent_management.py # Phase 1 tools
└── handlers/               # Future: business logic handlers
    └── __init__.py
```

### File Requirements:
- [ ] `server.py` creates single FastMCP instance
- [ ] `__init__.py` exports mcp instance
- [ ] Tools are organized by functional area
- [ ] No monolithic tool files (max 200 lines per file)
- [ ] Proper import patterns used

## 6. Integration Requirements ✅

### Core Module Integration:
- [ ] Tools import from existing core modules
- [ ] TMUXManager used for all tmux operations
- [ ] Existing business logic reused, not duplicated
- [ ] Core function signatures preserved
- [ ] Result objects properly transformed for MCP

### CLI Integration:
- [ ] CLI commands can call MCP tools
- [ ] Backward compatibility maintained
- [ ] Response formats consistent between CLI and MCP

## 7. Performance Considerations ✅

### Async/Await Usage:
- [ ] All tools declared as `async def`
- [ ] Proper await usage for async operations
- [ ] No blocking operations in tool code
- [ ] FastMCP server runs asynchronously

### Resource Management:
- [ ] TMUXManager instances created per request
- [ ] No global state in tool code
- [ ] Proper cleanup in error conditions

## 8. Documentation Requirements ✅

### Tool Documentation:
- [ ] Each tool has comprehensive docstring
- [ ] Parameters documented with types and descriptions
- [ ] Return values documented with structure
- [ ] Examples provided where helpful

### Code Comments:
- [ ] Complex logic explained with comments
- [ ] TODO items tracked appropriately
- [ ] Architecture decisions documented

## 9. Testing Requirements ✅

### Unit Test Coverage:
- [ ] Each tool has unit tests
- [ ] Error conditions tested
- [ ] Parameter validation tested
- [ ] Integration with core modules tested

### Test Patterns:
- [ ] Tests use proper async patterns
- [ ] Mocked TMUXManager for isolated testing
- [ ] Response structure validation
- [ ] Error response testing

## 10. Phase 1 Specific Requirements ✅

### Required Phase 1 Tools:
- [ ] `spawn_agent` - Agent creation
- [ ] `send_message` - Agent communication
- [ ] `get_agent_status` - Agent monitoring
- [ ] `kill_agent` - Agent termination

### Tool Signature Validation:
- [ ] All tools match approved design document signatures
- [ ] Parameter names and types match specification
- [ ] Return structures match specification
- [ ] Error handling follows specification

## Review Process

1. **Pre-Review**: Check file structure and imports
2. **Tool-by-Tool**: Review each tool against this checklist
3. **Integration**: Test with CLI and core modules
4. **Documentation**: Verify docstrings and comments
5. **Testing**: Ensure test coverage and quality

## Common Issues to Flag

### High Priority Issues:
- Missing error handling
- Incorrect type annotations
- Business logic in tools
- Incorrect FastMCP usage

### Medium Priority Issues:
- Missing docstrings
- Inconsistent response formats
- Poor parameter naming
- Missing test coverage

### Low Priority Issues:
- Code formatting
- Comment clarity
- Performance optimizations

## Approval Criteria

✅ **Pass**: All high-priority items addressed, most medium-priority items addressed
⚠️ **Conditional**: High-priority items addressed, some medium-priority issues remain
❌ **Fail**: High-priority issues remain unaddressed

---

**Remember**: Phase 1 focuses on the 4 core tools. Quality over quantity - these tools establish patterns for future phases.

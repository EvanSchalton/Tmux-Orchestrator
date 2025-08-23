# MCP Usability Issues - Orchestrator Experience
## Date: 2025-08-23

### MCP Command Invocation Confusion
**Issue**: Orchestrator struggling with proper MCP command syntax, particularly with hierarchical tools and parameter formatting.

**Specific Examples**:
1. `mcp__tmux-orchestrator__list` - Unclear how to pass options like `--format json`
2. `mcp__tmux-orchestrator__session` - Error messages show `action=list` format but actual invocation syntax unclear
3. Hierarchical tools show required actions but don't clarify the `kwargs` parameter format

**Current Error Pattern**:
```
{"success": false, "error": "Missing required 'action' parameter for Claude Code CLI agent",
 "valid_actions": ["attach", "list"],
 "example": "session(action='attach')",
 "environment": "Claude Code CLI"}
```

**Impact**:
- Orchestrator defaults to using tmux commands directly instead of MCP tools
- Violates the preferred tool hierarchy (MCP → tmux-orc → tmux)
- Reduces system efficiency and proper abstraction usage

**Root Cause**:
- MCP descriptions don't clearly explain the kwargs string format
- Examples in error messages use function syntax but actual parameter is a string
- No clear documentation on how to format complex commands with options

**Recommended Enhancement**:
1. Update MCP descriptions to include clear parameter format examples
2. Add kwargs format clarification: `"action=list target=session:window options..."`
3. Provide examples for common use cases in each tool description
4. Consider supporting both string and structured parameter formats

### Related Context
This confusion arose while trying to check session status and validate MCP implementation completion. The orchestrator should be using MCP tools as the primary interface but unclear syntax leads to falling back to direct tmux commands.

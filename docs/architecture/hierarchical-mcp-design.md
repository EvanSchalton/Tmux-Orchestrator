# Hierarchical MCP Tool Design

## Current State Analysis

### Flat Tool Generation
- **Total Tools**: 92 flat MCP tools
- **Structure**: 5 individual commands + 87 subcommands from 16 groups
- **Naming**: `command_subcommand` format (e.g., `agent_status`, `monitor_start`)

### Command Groups (16 total)
1. **agent** (10 subcommands): attach, deploy, info, kill, kill-all, list, message, restart, send, status
2. **monitor** (10 subcommands): monitoring and health management
3. **pm** (6 subcommands): project manager operations
4. **context** (4 subcommands): context briefings
5. **team** (5 subcommands): team management
6. **orchestrator** (7 subcommands): high-level system management
7. **setup** (7 subcommands): system setup and configuration
8. **spawn** (3 subcommands): agent spawning
9. **recovery** (4 subcommands): recovery operations
10. **session** (2 subcommands): session management
11. **pubsub** (4 subcommands): pub/sub operations
12. **pubsub-fast** (4 subcommands): optimized pub/sub
13. **daemon** (5 subcommands): daemon management
14. **tasks** (7 subcommands): task operations
15. **errors** (4 subcommands): error handling
16. **server** (5 subcommands): server operations

## Hierarchical Design

### Target Structure
Transform 92 flat tools into ~20 hierarchical tools:
- 5 top-level command tools (list, reflect, status, quick-deploy, + 1 catch-all)
- 16 group tools with nested subcommands

### Tool Schema Design

```python
# Example hierarchical tool schema
{
    "name": "agent",
    "description": "Manage individual agents across tmux sessions",
    "inputSchema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["attach", "deploy", "info", "kill", "kill-all", "list", "message", "restart", "send", "status"],
                "description": "The agent operation to perform"
            },
            "target": {
                "type": "string",
                "description": "Target agent in session:window format",
                "pattern": "^[^:]+:[0-9]+$"
            },
            "args": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Additional arguments for the action"
            },
            "options": {
                "type": "object",
                "description": "Action-specific options"
            }
        },
        "required": ["action"],
        "allOf": [
            {
                "if": {"properties": {"action": {"const": "attach"}}},
                "then": {"required": ["target"]}
            },
            {
                "if": {"properties": {"action": {"const": "message"}}},
                "then": {
                    "required": ["target"],
                    "properties": {
                        "message": {"type": "string", "description": "Message to send"}
                    }
                }
            }
        ]
    }
}
```

### Implementation Strategy

1. **Group Detection Enhancement**
   - Modify `generate_all_mcp_tools()` to create one tool per group
   - Each group tool handles all its subcommands via an `action` parameter

2. **Dynamic Schema Generation**
   - Create conditional schemas using JSON Schema's `if/then/else`
   - Generate parameter requirements based on subcommand help parsing
   - Support both positional args and options

3. **Tool Function Restructuring**
   ```python
   async def agent_tool(action: str, target: Optional[str] = None, **kwargs):
       """Execute agent operations."""
       # Route to appropriate subcommand based on action
       if action == "attach":
           return await execute_cli(["agent", "attach", target])
       elif action == "message":
           message = kwargs.get("message", "")
           return await execute_cli(["agent", "message", target, message])
       # ... etc
   ```

4. **Backward Compatibility**
   - Keep the reflection-based approach
   - Maintain auto-generation from CLI structure
   - Preserve all existing functionality

## Benefits

1. **Reduced Complexity**: 92 tools → ~20 tools
2. **Better Organization**: Logical grouping matches CLI structure
3. **Enhanced Discoverability**: Users explore actions within groups
4. **Improved Documentation**: Group-level help with action details
5. **Conditional Parameters**: Smart parameter validation per action
6. **Maintainability**: Easier to understand and modify

## Implementation Phases

### Phase 1 (Current)
- ✅ Analyze current structure
- ✅ Design hierarchical approach
- Document implementation plan

### Phase 2
- Implement group tool generation
- Create dynamic schema builder
- Add conditional parameter validation

### Phase 3
- Test all 92 operations
- Ensure backward compatibility
- Optimize performance

### Phase 4
- Add advanced features (autocomplete, validation)
- Enhance documentation generation
- Deploy and monitor

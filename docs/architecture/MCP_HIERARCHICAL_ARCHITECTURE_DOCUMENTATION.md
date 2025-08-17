# MCP Hierarchical Architecture Documentation

## Executive Summary

The Tmux Orchestrator project has undergone a significant architectural transformation in its MCP (Model Context Protocol) implementation, moving from a manual, file-based tool structure to an automated CLI reflection-based approach. This document details the hierarchical changes and their impact on the project structure.

## Architecture Evolution

### Phase 1: Manual MCP Implementation (Legacy)

The original MCP implementation followed a traditional file-based structure:

```
tmux_orchestrator/
├── server/                          # REST API approach (DELETED)
│   ├── __init__.py
│   ├── __main__.py
│   ├── middleware.py
│   ├── models/
│   │   ├── agent_models.py
│   │   ├── communication_models.py
│   │   ├── coordination_models.py
│   │   ├── monitoring_models.py
│   │   └── task_models.py
│   ├── routes/                      # FastAPI routes (WRONG APPROACH)
│   │   ├── agent_management.py
│   │   ├── agents.py
│   │   ├── communication.py
│   │   ├── contexts.py
│   │   ├── coordination.py
│   │   ├── messages.py
│   │   ├── monitor.py
│   │   ├── monitoring.py
│   │   └── tasks.py
│   └── tools/                       # Manual tool implementations
│       ├── assign_task.py
│       ├── broadcast_message.py
│       ├── create_pull_request.py
│       ├── create_team.py
│       ├── get_agent_status.py
│       ├── get_messages.py
│       ├── get_session_status.py
│       ├── handoff_work.py
│       ├── kill_agent.py
│       ├── report_activity.py
│       ├── restart_agent.py
│       ├── run_quality_checks.py
│       ├── schedule_checkin.py
│       ├── send_message.py
│       ├── spawn_agent.py
│       └── track_task_status.py
```

**Problems with this approach:**
- Incorrectly used FastAPI/REST architecture instead of MCP's JSON-RPC over stdio
- Manual implementation of each tool led to code duplication
- Maintenance burden of keeping CLI and MCP tools in sync
- Risk of behavioral divergence between interfaces

### Phase 2: CLI Reflection Architecture (Current)

The new architecture uses CLI introspection to automatically generate MCP tools:

```
tmux_orchestrator/
├── mcp_server.py                    # Fresh CLI reflection-based server
├── mcp/                            # Minimal MCP structure
│   └── __init__.py
├── mcp_manual_legacy/              # Legacy backup (TO BE REMOVED)
│   ├── handlers/
│   ├── tools/
│   └── server.py
├── server_legacy_backup/           # Backed up incorrect REST approach
│   └── [previous server structure]
└── cli/                           # Single source of truth
    ├── agent.py
    ├── monitor.py
    ├── orchestrator.py
    ├── pm.py
    ├── team.py
    └── [other CLI commands]
```

## Key Architectural Changes

### 1. **Elimination of Server Directory**

The entire `server/` directory was deleted because:
- It implemented the wrong protocol (REST/FastAPI instead of MCP's JSON-RPC)
- MCP uses stdio communication, not HTTP endpoints
- The correct implementation is in `mcp_server.py`

### 2. **From Manual to Automatic Tool Generation**

**Before (Manual):**
- Each MCP tool required manual implementation in `server/tools/`
- ~200 lines of code per tool
- Duplicate logic from CLI commands
- High maintenance burden

**After (CLI Reflection):**
- Tools automatically generated from CLI commands
- Zero manual tool implementation
- `tmux-orc reflect --format json` provides CLI structure
- Each CLI command becomes an MCP tool automatically

### 3. **Tool Generation Statistics**

- **Initial Manual Tools**: 6 tools
- **After CLI Reflection**: 92 tools (1,433% increase)
- **Current Structure**:
  - 5 top-level commands
  - 16 command groups
  - 87 subcommands

### 4. **Hierarchical Tool Organization**

The system now supports hierarchical command structures:

```
Top-Level Commands (5):
├── list
├── reflect
├── status
├── quick-deploy
└── execute

Command Groups (16):
├── agent (10 subcommands)
├── monitor (10 subcommands)
├── pm (6 subcommands)
├── context (4 subcommands)
├── team (5 subcommands)
├── orchestrator (7 subcommands)
├── setup (7 subcommands)
├── spawn (3 subcommands)
├── recovery (4 subcommands)
├── session (2 subcommands)
├── pubsub (8 subcommands)
├── daemon (5 subcommands)
├── tasks (7 subcommands)
├── errors (4 subcommands)
├── server (5 subcommands)
└── execute-fixed (various)
```

## Implementation Details

### CLI Reflection Process

1. **Discovery Phase**:
   ```python
   # MCP server discovers CLI structure
   result = subprocess.run(["tmux-orc", "reflect", "--format", "json"], ...)
   cli_structure = json.loads(result.stdout)
   ```

2. **Tool Generation**:
   ```python
   # For each CLI command, create an MCP tool
   for command_name, command_info in cli_structure.items():
       if command_info.get('type') == 'command':
           generate_tool_for_command(command_name, command_info)
       elif command_info.get('type') == 'group':
           generate_tools_for_group(command_name, command_info)
   ```

3. **Execution Model**:
   ```python
   # MCP tools execute CLI commands directly
   async def execute_cli_command(command, args):
       cmd = ["tmux-orc", command] + args
       if supports_json:
           cmd.append("--json")
       result = subprocess.run(cmd, ...)
       return parse_result(result)
   ```

### Benefits of New Architecture

1. **Zero Maintenance Burden**: CLI is the single source of truth
2. **Automatic Feature Parity**: New CLI commands instantly become MCP tools
3. **Reduced Codebase**: Eliminated ~2000+ lines of manual tool code
4. **Consistent Behavior**: MCP tools behave exactly like CLI commands
5. **Future-Proof**: Any new CLI command automatically generates an MCP tool

## Migration Path

### Completed Steps

1. ✅ Created fresh MCP server with CLI reflection (`mcp_server.py`)
2. ✅ Backed up legacy implementations to `*_legacy_backup/` directories
3. ✅ Deleted incorrect REST/FastAPI server implementation
4. ✅ Achieved 92 tool generation from CLI structure
5. ✅ Validated all tools work correctly

### Remaining Cleanup Tasks

1. **Remove Legacy Backups** (after stability confirmation):
   - `tmux_orchestrator/mcp_manual_legacy/`
   - `tmux_orchestrator/server_legacy_backup/`
   - `tmux_orchestrator/mcp.backup/`

2. **Consolidate MCP Files**:
   - Keep only `mcp_server.py` as the primary implementation
   - Remove `mcp_fresh.py` (duplicate)

3. **Update Documentation**:
   - Archive old MCP design documents
   - Update all references to manual tool implementation

## Deployment Model

The new architecture supports simple pip-based deployment:

```bash
# Install
pip install tmux-orchestrator

# Setup MCP with Claude
tmux-orc setup claude-code

# MCP server runs automatically when Claude needs it
```

## Future Enhancements

### Hierarchical Tool Design (Proposed)

To further optimize the 92 tools, a hierarchical structure is planned:

```python
# Instead of 92 flat tools, group by command
{
    "name": "agent",
    "inputSchema": {
        "properties": {
            "action": {
                "enum": ["attach", "deploy", "info", "kill", ...]
            },
            "target": {"type": "string"},
            "options": {"type": "object"}
        }
    }
}
```

This would reduce 92 tools to ~20 hierarchical tools while maintaining all functionality.

## Conclusion

The move from manual MCP tool implementation to CLI reflection represents a paradigm shift in multi-interface system design. By treating the CLI as the primary interface and automatically deriving MCP tools from it, the project has achieved unprecedented simplicity, maintainability, and consistency.

The deletion of the `server/` directory and consolidation around `mcp_server.py` corrects the fundamental architectural misunderstanding about MCP's protocol (JSON-RPC over stdio, not REST) and establishes a clean, maintainable structure for future development.

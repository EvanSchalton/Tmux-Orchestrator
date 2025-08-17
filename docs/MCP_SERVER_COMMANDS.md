# MCP Server Commands Documentation

## Overview

The MCP (Model Context Protocol) server commands enable Claude Desktop to interact with tmux-orchestrator through a standardized protocol. These commands provide the bridge between Claude's AI capabilities and tmux session management using a revolutionary CLI reflection-based architecture.

## Hierarchical Architecture Overview

The MCP server uses an innovative CLI reflection approach that automatically generates all MCP tools from the CLI command structure:
- **92 auto-generated tools** from CLI commands (1,433% increase from manual implementation)
- **Zero maintenance burden** - CLI is the single source of truth
- **Automatic feature parity** - New CLI commands instantly become MCP tools
- **Hierarchical organization** - Commands grouped by functionality

## Implementation Structure

The server commands are implemented across multiple components:
- **MCP Server**: `/tmux_orchestrator/mcp_server.py` - CLI reflection-based FastMCP server
- **CLI Commands**: `/tmux_orchestrator/cli/` - Source of truth for all functionality
- **Server Commands**: `/tmux_orchestrator/cli/server.py` - Server management commands
- **Legacy Backups**: `*_legacy_backup/` directories - Preserved for reference only

## Hierarchical Tool Structure

The MCP server exposes tools in a hierarchical structure that mirrors the CLI organization:

### Top-Level Commands (5)
- `tmux-orc_list` - List all active agents
- `tmux-orc_reflect` - Display CLI structure
- `tmux-orc_status` - System status overview
- `tmux-orc_quick-deploy` - Rapid team deployment
- `tmux-orc_execute` - Execute commands in sessions

### Command Groups (16)
Each group contains multiple subcommands:

| Group | Tool Count | Purpose |
|-------|------------|---------|
| agent | 10 | Agent lifecycle management |
| monitor | 10 | System monitoring and health |
| pm | 6 | Project Manager operations |
| context | 4 | Context management |
| team | 5 | Team coordination |
| orchestrator | 7 | High-level orchestration |
| setup | 7 | System configuration |
| spawn | 3 | Agent spawning variants |
| recovery | 4 | Error recovery operations |
| session | 2 | Session management |
| pubsub | 8 | Inter-agent communication |
| daemon | 5 | Background process control |
| tasks | 7 | Task tracking |
| errors | 4 | Error handling |
| server | 5 | MCP server management |
| execute-fixed | Various | Specialized execution |

### Tool Naming Convention
All tools follow the pattern: `tmux-orc_[group]_[action]`
- Example: `tmux-orc_agent_spawn`
- Example: `tmux-orc_monitor_start`
- Example: `tmux-orc_team_deploy`

## Available Commands

### 🚀 `tmux-orc server start`

Starts the MCP server in stdio mode for Claude Desktop integration.

**Usage:**
```bash
tmux-orc server start                 # Normal operation (Claude uses this)
tmux-orc server start --verbose       # Debug logging to stderr
tmux-orc server start --test          # Test mode with sample output
```

**Key Features:**
- Runs in **stdio mode** (reads stdin, writes stdout)
- Logging goes to stderr to avoid protocol interference
- Automatically discovers and exposes all CLI commands as MCP tools
- Test mode for verification without full server startup

**How Claude Uses This:**
Claude Desktop automatically executes `tmux-orc server start` when configured, establishing a bidirectional communication channel.

---

### 🔍 `tmux-orc server status`

Checks MCP server registration status with Claude Desktop.

**Usage:**
```bash
tmux-orc server status                # Human-readable status
tmux-orc server status --json         # Machine-readable JSON (planned)
```

**Status Information:**
- Claude Desktop installation detection
- MCP server registration status
- Configuration file location
- Server enabled/disabled state

**Example Output:**
```
Claude Desktop MCP Integration Status

✅ Claude Desktop: Installed
   Config path: ~/.config/Claude/claude_desktop_config.json
✅ MCP Server: Registered
   Command: tmux-orc server start
   Status: Active

Platform: darwin
```

---

### 🛠️ `tmux-orc server tools`

Lists all available MCP tools that Claude can use.

**Usage:**
```bash
tmux-orc server tools                 # Table view of tools
tmux-orc server tools --json          # JSON format for automation
```

**Features:**
- Dynamic tool discovery via CLI reflection
- Shows tool name, CLI command, and description
- JSON output for integration with other tools
- No server startup required (fast operation)

**Example Output:**
```
Available MCP Tools (25)
==================================================
cli_list             → tmux-orc list
                       List all active agents across sessions...
cli_status           → tmux-orc status
                       Display comprehensive system status...
cli_quick_deploy     → tmux-orc quick-deploy
                       Rapidly deploy optimized team configurations...
==================================================
Total: 25 tools available to Claude
```

---

### ⚙️ `tmux-orc server setup`

Configures Claude Desktop to use the tmux-orchestrator MCP server.

**Usage:**
```bash
tmux-orc server setup                 # Interactive setup
```

**Setup Process:**
1. Detects Claude Desktop installation
2. Adds tmux-orchestrator to MCP servers configuration
3. Sets appropriate command and environment variables
4. Verifies configuration

**Configuration Added:**
```json
{
  "tmux-orchestrator": {
    "command": "tmux-orc",
    "args": ["server", "start"],
    "env": {
      "TMUX_ORC_MCP_MODE": "claude"
    },
    "disabled": false
  }
}
```

---

### 🔄 `tmux-orc server toggle`

Enable or disable the MCP server in Claude Desktop.

**Usage:**
```bash
tmux-orc server toggle --enable       # Enable MCP server
tmux-orc server toggle --disable      # Disable MCP server
```

**Use Cases:**
- Temporarily disable tmux-orchestrator integration
- Troubleshooting Claude Desktop issues
- Testing different configurations

---

## Technical Implementation Details

### Architecture Evolution

The MCP implementation has undergone a revolutionary transformation:

#### Previous Architecture (Legacy - DELETED)
```
server/                    # Wrong approach - REST/FastAPI
├── routes/               # HTTP endpoints (not MCP protocol)
├── tools/                # Manual tool implementations
└── models/               # Unnecessary data models
```

#### Current Architecture (CLI Reflection)
```
mcp_server.py             # FastMCP server with CLI reflection
├── Discovers CLI via `tmux-orc reflect`
├── Auto-generates 92 MCP tools
├── Zero manual tool implementation
└── Single source of truth: CLI
```

**Key Components:**
1. **MCP Server** (`mcp_server.py`): FastMCP-based stdio protocol server
2. **CLI Reflection**: Dynamic discovery via `tmux-orc reflect --format json`
3. **Tool Generation**: Automatic mapping from CLI commands to MCP tools
4. **Configuration** (`utils/claude_config.py`): Claude Desktop integration

### Key Design Decisions

1. **CLI Reflection Architecture**: Revolutionary approach to MCP implementation
   - **Before**: 6 manually implemented tools, ~2000 lines of duplicate code
   - **After**: 92 auto-generated tools, zero manual implementation
   - **Benefit**: 1,433% increase in available tools with 100% code reduction

2. **stdio Protocol**: Correct MCP implementation (not REST)
   - Uses JSON-RPC over standard input/output
   - Separates protocol messages (stdout) from logs (stderr)
   - Native integration with Claude Desktop

3. **Single Source of Truth**: CLI drives everything
   - Zero maintenance burden for new features
   - Automatic feature parity between interfaces
   - No risk of behavioral divergence

4. **Hierarchical Organization**: Logical grouping of tools
   - 16 command groups for better discoverability
   - Consistent naming convention
   - Future-ready for hierarchical tool design

### Error Handling

All server commands implement robust error handling:

- **Import Errors**: Clear messages if dependencies missing
- **Configuration Errors**: Helpful guidance for manual fixes
- **Runtime Errors**: Graceful degradation with informative messages
- **Timeout Protection**: Prevents hanging operations

### Performance Optimizations

- **Lazy Imports**: Avoid circular dependencies and startup overhead
- **Tool Caching**: CLI structure discovered once per session
- **Fast Status Checks**: Direct config file reading
- **Test Mode**: Quick verification without full initialization

---

## Integration with Claude Desktop

### How Claude Uses These Commands

1. **Startup**: Claude runs `tmux-orc server start`
2. **Discovery**: Server advertises available tools via MCP protocol
3. **Execution**: Claude calls tools with parameters
4. **Response**: Server returns structured results

### Available MCP Tools

Every CLI command becomes an MCP tool:
- `cli_list` → List agents
- `cli_spawn` → Spawn new agents
- `cli_status` → System status
- `cli_quick_deploy` → Deploy teams
- And 20+ more...

### Troubleshooting

**Server won't start:**
```bash
# Check installation
which tmux-orc

# Test server
tmux-orc server start --test

# Check logs
tmux-orc server start --verbose
```

**Not registered with Claude:**
```bash
# Check status
tmux-orc server status

# Re-run setup
tmux-orc server setup
```

**Tools not appearing:**
```bash
# List available tools
tmux-orc server tools

# Check CLI reflection
tmux-orc reflect --format json
```

---

## Setup Integration

### Enhanced Setup Commands

The setup process has been enhanced with better MCP registration:

#### `tmux-orc setup claude-code`
Full Claude Code setup including MCP registration:
- Detects Claude Desktop installation
- Automatically registers MCP server
- Creates fallback local config if needed
- Provides platform-specific guidance

#### `tmux-orc setup mcp`
Dedicated MCP registration command:
```bash
tmux-orc setup mcp          # Register MCP server
tmux-orc setup mcp --force  # Force re-registration
```

Features:
- Checks current registration status
- Platform-specific Claude Desktop detection
- Manual registration instructions if auto-registration fails
- Useful for fixing registration issues

### Setup Enhancement Details

The enhanced setup includes:
1. **Automatic Claude Desktop Detection**:
   - macOS: `~/Library/Application Support/Claude/`
   - Windows: `%APPDATA%\Claude\`
   - Linux: `~/.config/Claude/`

2. **Improved Error Handling**:
   - Clear messages when Claude Desktop not found
   - Fallback to local MCP config creation
   - Manual registration instructions

3. **Better User Experience**:
   - Shows registration status after setup
   - Provides next steps for testing
   - Platform-specific installation guidance

---

## Future Enhancements

### Hierarchical Tool Redesign (Phase 3)
The next evolution will introduce truly hierarchical tools:

**Current State (92 flat tools):**
```
tmux-orc_agent_spawn
tmux-orc_agent_status
tmux-orc_agent_kill
tmux-orc_monitor_start
tmux-orc_monitor_stop
... (87 more tools)
```

**Future State (~20 hierarchical tools):**
```
tmux-orc_agent(action="spawn", ...)
tmux-orc_agent(action="status", ...)
tmux-orc_monitor(action="start", ...)
tmux-orc_team(action="deploy", ...)
```

**Benefits:**
- Reduce cognitive load for LLMs
- Better tool organization
- Easier discovery and navigation
- More intuitive parameter structure

### Planned Features
- **Hierarchical Tool Engine**: Group-based tools with action parameters
- **Smart Tool Routing**: Automatic parameter mapping
- **Tool Categories**: Logical grouping for LLM consumption
- **Performance Monitoring**: Tool usage analytics

### Integration Enhancements
- **VS Code Extension**: Native MCP support
- **Web UI Bridge**: Browser-based MCP access
- **Remote Mode**: Network-accessible MCP server
- **Multi-Model Support**: Beyond Claude integration

---

## Related Documentation

### New Hierarchical MCP Documentation
- [MCP Hierarchical Architecture](./architecture/MCP_HIERARCHICAL_ARCHITECTURE_DOCUMENTATION.md) - Complete architecture overview
- [MCP Migration Guide](./architecture/MCP_MIGRATION_GUIDE.md) - Migrate from legacy to new structure
- [MCP LLM Best Practices](./architecture/MCP_LLM_BEST_PRACTICES.md) - Optimal usage patterns for LLMs
- [MCP Command Examples](./architecture/MCP_COMMAND_EXAMPLES.md) - Complex workflow examples

### General Documentation
- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [Claude Desktop Integration Guide](../setup/claude-desktop.md)
- [CLI Command Reference](./cli-reference.md)
- [Architecture Overview](../architecture/mcp-integration.md)

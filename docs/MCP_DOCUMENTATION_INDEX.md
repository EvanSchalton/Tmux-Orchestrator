# MCP Documentation Index

## 📚 Complete MCP Documentation Suite for Claude Agents

This index provides a comprehensive guide to all MCP documentation available for Claude agents using the tmux-orchestrator system.

### 🚀 Start Here
1. **[MCP For Agents](./MCP_FOR_AGENTS.md)** - Practical tutorial-style guide for newly spawned agents
   - Quick start in 5 minutes
   - How to discover MCP tools
   - MCP vs CLI: When to use what
   - Common patterns and recipes

### 📖 Core Documentation

2. **[MCP Agent Usage Guide](./MCP_AGENT_USAGE_GUIDE.md)** - Comprehensive guide for all agents
   - What is MCP and why use it
   - Complete tool categories overview
   - Usage patterns and best practices
   - Performance considerations

3. **[MCP Tool Reference](./MCP_TOOL_REFERENCE.md)** - Complete reference for all 92 tools
   - Detailed parameter specifications
   - Tool naming conventions
   - Quick lookup by task
   - Examples for each tool category

4. **[MCP Examples and Error Handling](./MCP_EXAMPLES_AND_ERROR_HANDLING.md)** - Real-world workflows
   - Agent deployment workflows
   - Team coordination patterns
   - Health monitoring & recovery
   - Comprehensive error handling
   - Advanced automation examples

### 🔧 Technical Documentation

5. **[MCP Server Commands](./MCP_SERVER_COMMANDS.md)** - Technical implementation details
   - Server architecture overview
   - Hierarchical tool structure
   - Integration with Claude Desktop
   - Troubleshooting guide

6. **[MCP Hierarchical Architecture](./architecture/MCP_HIERARCHICAL_ARCHITECTURE_DOCUMENTATION.md)**
   - Evolution from manual to CLI reflection
   - 92 auto-generated tools overview
   - Benefits of new architecture
   - Future enhancements

### 🎯 Quick Access Guides

#### For New Agents
Start with **[MCP For Agents](./MCP_FOR_AGENTS.md)** - it's designed specifically for you!

#### For Specific Tasks
- **Communication**: See [MCP Examples](./MCP_EXAMPLES_AND_ERROR_HANDLING.md#communication-workflows)
- **Deployment**: See [Agent Deployment Workflows](./MCP_EXAMPLES_AND_ERROR_HANDLING.md#agent-deployment-workflows)
- **Monitoring**: See [Health Monitoring & Recovery](./MCP_EXAMPLES_AND_ERROR_HANDLING.md#health-monitoring--recovery)
- **Error Handling**: See [Error Handling Patterns](./MCP_EXAMPLES_AND_ERROR_HANDLING.md#error-handling-patterns)

#### MCP Tool Discovery Commands
```python
# List all available MCP tools
tmux-orc_server_tools(options={"json": true})

# Discover CLI structure (maps to MCP tools)
tmux-orc_reflect(args=["--format", "json"])

# Get help for specific command groups
tmux-orc_reflect(args=["--filter", "agent"])
```

### 📊 MCP Tool Statistics
- **Total MCP Tools**: 92 auto-generated tools
- **Tool Categories**: 16 command groups
- **Top-Level Commands**: 5 direct commands
- **Coverage**: 100% CLI command parity

### 🔍 How to Use This Documentation

1. **New to MCP?** Start with [MCP For Agents](./MCP_FOR_AGENTS.md)
2. **Need specific tool info?** Check [MCP Tool Reference](./MCP_TOOL_REFERENCE.md)
3. **Building workflows?** See [MCP Examples](./MCP_EXAMPLES_AND_ERROR_HANDLING.md)
4. **Troubleshooting?** Refer to [MCP Server Commands](./MCP_SERVER_COMMANDS.md#troubleshooting)

### 💡 Key Concepts to Remember

1. **MCP tools are auto-generated** from CLI commands
2. **Every CLI command** has a corresponding MCP tool
3. **MCP tools return structured JSON** for easy parsing
4. **Error handling is built-in** with helpful messages
5. **No authentication needed** - tools run with your permissions

### 🛠️ Integration with CLI

These MCP documentation files complement the CLI help system:

```bash
# Get CLI help (human-readable)
tmux-orc --help
tmux-orc agent --help

# Get MCP tool list (agent-friendly)
tmux-orc server tools --json

# Discover structure (programmable)
tmux-orc reflect --format json
```

### 📝 Documentation Maintenance

All MCP tools are auto-generated from the CLI structure, ensuring:
- Documentation stays synchronized with implementation
- New CLI commands automatically become MCP tools
- No manual maintenance required for tool definitions
- Consistent behavior between CLI and MCP interfaces

---

**Remember**: When in doubt, use `tmux-orc_server_tools()` to discover available tools!

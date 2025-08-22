# Architecture Terminology Guide

## Purpose
This guide ensures consistent terminology when documenting the tmux-orchestrator architecture vs. applications it manages.

## Core Architecture: tmux-orchestrator

### ✅ CORRECT Terminology
- **MCP Server** - tmux-orchestrator is an MCP (Model Context Protocol) server
- **MCP Tools** - Functions available to Claude Code through MCP protocol
- **JSON-RPC Protocol** - Communication protocol between Claude Code and tmux-orchestrator
- **stdio Transport** - How JSON-RPC messages are transported (NOT HTTP)
- **FastMCP Framework** - The underlying framework powering the MCP server
- **CLI Reflection** - How MCP tools are dynamically generated from CLI commands
- **Hierarchical Tools** - Organized MCP tools (agent, monitor, team, spawn, context)

### ❌ INCORRECT for tmux-orchestrator Architecture
- **REST API** - tmux-orchestrator is NOT a REST API
- **HTTP Endpoints** - tmux-orchestrator does NOT use HTTP
- **API Endpoints** - Avoid generic "API" when referring to MCP tools
- **REST Server** - tmux-orchestrator is an MCP server, not a REST server
- **Web API** - tmux-orchestrator is not web-based

## Applications That tmux-orchestrator Manages

### ✅ CORRECT - When Describing Managed Projects
These terms are acceptable when describing applications that tmux-orchestrator helps develop:

- "Implement user authentication endpoints" ✅ (project requirement)
- "Create REST API for user management" ✅ (project deliverable)
- "Test the login/logout endpoints" ✅ (testing managed applications)
- "Document public APIs" ✅ (documenting managed applications)

### Key Distinction
- **tmux-orchestrator architecture** → MCP tools, JSON-RPC, stdio
- **Applications being developed** → May use REST APIs, HTTP endpoints, etc.

## MCP Tool Interface Pattern

### Tool Structure
```json
{
  "action": "specific_operation",
  "target": "session:window",
  "args": ["positional", "arguments"],
  "options": {"flag": "value"}
}
```

### Tool Categories
- **agent** - Agent lifecycle (deploy, kill, list, status, restart)
- **monitor** - Monitoring daemon (start, stop, dashboard, recovery)
- **team** - Team coordination (deploy, status, broadcast, recover)
- **spawn** - Create agents (agent, pm, orchestrator)
- **context** - Documentation access (orchestrator, pm, list, show)

## Documentation Best Practices

### When Writing About tmux-orchestrator
1. **Always specify MCP server** - Not just "server"
2. **Use JSON-RPC over stdio** - Never mention HTTP
3. **Refer to MCP tools** - Not "endpoints" or generic "API"
4. **Emphasize CLI reflection** - Tools generated from CLI commands

### When Writing About Managed Projects
1. **Context is key** - Make clear you're describing the target application
2. **Use project-specific terms** - REST API, endpoints, etc. are fine for managed apps
3. **Separate concerns** - Don't mix tmux-orchestrator architecture with project requirements

## Common Mistakes to Avoid

### ❌ Mixed Terminology
```markdown
"The tmux-orchestrator REST API provides endpoints for spawning agents"
```

### ✅ Correct Version
```markdown
"The tmux-orchestrator MCP server provides tools for spawning agents"
```

### ❌ Generic References
```markdown
"Call the API to list agents"
```

### ✅ Specific References
```markdown
"Use the agent MCP tool with action='list'"
```

## Architecture Boundaries

### tmux-orchestrator (MCP Server)
- Provides MCP tools to Claude Code
- Uses JSON-RPC over stdio transport
- Built with FastMCP framework
- Manages tmux sessions and AI agents

### Projects Under Management
- May use any architecture (REST, GraphQL, etc.)
- Have their own APIs and endpoints
- Are developed by spawned AI agents
- Maintain their own terminology

## Update Guidelines

When updating documentation:

1. **Check context** - Architecture docs vs project requirements?
2. **Use correct terms** - MCP tools for orchestrator, API endpoints for projects
3. **Be specific** - "MCP server" not just "server"
4. **Maintain boundaries** - Don't conflate orchestrator with managed applications

## Quick Reference

| Context | Correct Term | Avoid |
|---------|-------------|--------|
| tmux-orchestrator | MCP server | REST API |
| Communication | JSON-RPC | HTTP |
| Transport | stdio | HTTP transport |
| Interface | MCP tools | endpoints |
| Framework | FastMCP | web framework |
| Managed apps | REST API ✅ | n/a |
| Project features | endpoints ✅ | n/a |

---

**Remember**: tmux-orchestrator = MCP server. Applications it manages = may use REST APIs.

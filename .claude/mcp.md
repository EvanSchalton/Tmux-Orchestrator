# MCP Server Configuration for Corporate Coach

This file contains the MCP (Model Context Protocol) server configurations for the Corporate Coach project.

## Quick Install

To install all recommended MCP servers at once:

```bash
./scripts/install-mcp-servers.sh
```

Or install individual servers using the commands below.

## Core MCP Servers

### Playwright (Browser Automation)
```bash
claude mcp add playwright -- npx -y @playwright/mcp@latest \
  --user-data-dir ~/.cache/claude-playwright \
  --storage-state ~/.cache/claude-playwright/auth-state.json \
  --save-trace \
  --output-dir ~/.cache/claude-playwright/screenshots
```

### Context7 (Documentation Retrieval)
```bash
claude mcp add --transport http context7 https://mcp.context7.com/mcp
```

## Database MCP Servers

### PostgreSQL
```bash
# PostgreSQL MCP server for direct database access
# Note: Adjust connection string based on your environment
# For devcontainer internal use:
claude mcp add postgres -- npx -y @modelcontextprotocol/server-postgres@latest \
  postgresql://postgres:postgres@postgres:5432/corporate_coach

# For external/host access (with port 45432):
# claude mcp add postgres -- npx -y @modelcontextprotocol/server-postgres@latest \
#   postgresql://postgres:postgres@localhost:45432/corporate_coach
```

### Neo4j
```bash
# Neo4j MCP server via Docker Hub
# For devcontainer internal use:
claude mcp add --transport http neo4j http://neo4j:7474

# For external/host access (with port 47474):
# claude mcp add --transport http neo4j http://localhost:47474
```

## Development Tools

### Filesystem (Enhanced File Operations)
```bash
# Provides advanced file operations beyond standard tools
claude mcp add filesystem -- npx -y @modelcontextprotocol/server-filesystem@latest \
  /workspaces/corporate-coach
```

### Git
```bash
# Enhanced Git operations
claude mcp add git -- npx -y @modelcontextprotocol/server-git@latest
```

### Memory (Persistent Memory Across Sessions)
```bash
# Useful for maintaining context across multiple sessions
claude mcp add memory -- npx -y @modelcontextprotocol/server-memory@latest
```

## AI/LLM Related

### Brave Search (Web Search)
```bash
# For up-to-date information retrieval
# Requires BRAVE_API_KEY environment variable
claude mcp add brave -- npx -y @modelcontextprotocol/server-brave@latest
```

### Fetch (Enhanced Web Fetching)
```bash
# Better web content fetching with more options
claude mcp add fetch -- npx -y @modelcontextprotocol/server-fetch@latest
```

## Project-Specific Recommendations

For the Corporate Coach project, these MCP servers are particularly useful:

1. **PostgreSQL** - Direct database access for testing and data manipulation
2. **Filesystem** - Enhanced file operations for managing the codebase
3. **Memory** - Maintaining context across development sessions
4. **Context7** - Retrieving documentation for frameworks and libraries
5. **Playwright** - Testing the web interface

## Usage Notes

- MCP servers provide direct access to external systems
- They can significantly enhance development capabilities
- Always ensure proper security when using database MCP servers
- Some servers may require API keys or additional configuration

## Troubleshooting

If an MCP server fails to connect:
1. Check that the service is running (for databases)
2. Verify connection strings and credentials
3. Ensure ports are properly forwarded in devcontainer
4. Check that required npm packages are installed

## Future Additions

As new MCP servers become available, consider adding:
- Neo4j MCP server for graph database operations
- Vector database MCP server for pgvector operations
- LangChain/LangGraph specific MCP servers
- Custom MCP server for Corporate Coach specific operations

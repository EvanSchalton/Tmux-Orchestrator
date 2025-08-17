"""Dynamic MCP server for tmux-orchestrator using CLI introspection.

This module creates a FastMCP server that automatically generates tools
from tmux-orc CLI commands, eliminating dual-implementation maintenance.
"""

import asyncio
import logging

from fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastMCP instance
mcp = FastMCP("tmux-orchestrator")

# Import Phase 1 tools to register them
logger.info("Loading Phase 1 manual tools")
from tmux_orchestrator.mcp.tools.agent_management import *  # noqa: F401, F403

logger.info("MCP server initialized with Phase 1 tools")


async def main():
    """Run the FastMCP server."""
    logger.info("Starting FastMCP tmux-orchestrator server with Phase 1 tools...")
    await mcp.run_stdio_async()


if __name__ == "__main__":
    asyncio.run(main())


__all__ = ["mcp", "main"]

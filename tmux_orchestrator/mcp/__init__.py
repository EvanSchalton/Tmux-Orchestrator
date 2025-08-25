"""MCP (Model Context Protocol) Server Implementation.

This module provides the CLI-reflection based MCP server that auto-generates
tools from tmux-orc CLI commands for Claude integration.
"""

from tmux_orchestrator.mcp.server import EnhancedCLIToMCPServer

__all__ = ["EnhancedCLIToMCPServer"]

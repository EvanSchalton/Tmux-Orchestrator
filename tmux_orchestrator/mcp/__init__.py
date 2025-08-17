"""Fresh CLI Reflection-Based MCP Implementation.

This module provides the new CLI-reflection based MCP server that auto-generates
tools from tmux-orc CLI commands, replacing all manual tool implementations.
"""

from tmux_orchestrator.mcp_server_fresh import FreshCLIMCPServer

__all__ = ["FreshCLIMCPServer"]

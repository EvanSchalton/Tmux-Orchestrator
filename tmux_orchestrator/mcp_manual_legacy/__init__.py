"""MCP (Model Context Protocol) package for tmux-orchestrator.

This package provides FastMCP-based tools for AI agents to interact with
tmux-orchestrator functionality directly via the MCP protocol.
"""

from .server import mcp

__all__ = ["mcp"]

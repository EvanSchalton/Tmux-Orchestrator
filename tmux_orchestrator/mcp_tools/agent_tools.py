"""
Agent Management Tools

Implements native MCP tools for agent lifecycle management with exact parameter
signatures from API Designer's specifications.
"""

from .agent import (
    agent_attach,
    agent_kill,
    agent_list,
    agent_restart,
    agent_send_message,
    agent_status,
)

__all__ = [
    "agent_list",
    "agent_status",
    "agent_send_message",
    "agent_restart",
    "agent_kill",
    "agent_attach",
]

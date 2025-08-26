"""
Native MCP Tools Module

This module provides hand-crafted MCP tools with native parameter definitions
to replace the auto-generated kwargs-based tools.

Key Features:
- Native parameter validation and schema
- Clear parameter names and types
- Better error handling
- Focused tool functions
- Cleaner integration with FastMCP
"""

# Agent Management Tools
from .agent_tools import (
    agent_attach,
    agent_kill,
    agent_list,
    agent_restart,
    agent_send_message,
    agent_status,
)

# Communication Tools
from .communication_tools import (
    broadcast_message,
    send_message,
    send_urgent_message,
    team_broadcast,
    team_notification,
)

# Context Tools
from .context_tools import (
    context_diff,
    context_validate,
    list_contexts,
    search_context,
    show_context,
)

# Core backward compatibility
from .core_tools import (
    get_status,
)

# Monitoring Tools
from .monitoring_tools import (
    get_monitor_logs,
    health_check,
    monitor_dashboard,
    system_status,
)

# Session Management Tools
from .session_tools import (
    session_attach,
    session_create,
    session_info,
    session_kill,
    session_list,
)

# Shared utilities
from .shared_logic import (
    CommandExecutor,
    execute_command,
    format_error_response,
    format_success_response,
    parse_target,
    validate_session_format,
)

# Spawning Tools
from .spawn_tools import (
    quick_deploy,
    spawn_agent,
    spawn_orchestrator,
    spawn_pm,
)

# Team Management Tools
from .team_tools import (
    team_deploy,
    team_kill,
    team_list,
    team_scale,
    team_status,
)

__all__ = [
    # Agent Management (6 tools)
    "agent_list",
    "agent_status",
    "agent_send_message",
    "agent_restart",
    "agent_kill",
    "agent_attach",
    # Spawning & Deployment (4 tools)
    "spawn_agent",
    "spawn_pm",
    "spawn_orchestrator",
    "quick_deploy",
    # Communication (5 tools)
    "send_message",
    "team_broadcast",
    "broadcast_message",
    "send_urgent_message",
    "team_notification",
    # Team Management (5 tools)
    "team_status",
    "team_deploy",
    "team_list",
    "team_kill",
    "team_scale",
    # Session Management (5 tools)
    "session_list",
    "session_attach",
    "session_kill",
    "session_create",
    "session_info",
    # Monitoring & Health (4 tools)
    "system_status",
    "monitor_dashboard",
    "health_check",
    "get_monitor_logs",
    # Context Management (5 tools)
    "show_context",
    "list_contexts",
    "search_context",
    "context_diff",
    "context_validate",
    # Core & Utilities
    "get_status",
    "execute_command",
    "parse_target",
    "validate_session_format",
    "CommandExecutor",
    "format_error_response",
    "format_success_response",
]

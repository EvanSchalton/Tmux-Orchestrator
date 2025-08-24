#!/usr/bin/env python3
"""
MCP Operations Inventory - Complete listing of all 92 operations.

This inventory serves as the source of truth for testing the hierarchical
MCP tool structure transformation.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class OperationType(Enum):
    """Types of operations in the MCP system."""

    CRUD = "crud"  # Create, Read, Update, Delete
    STATUS = "status"  # Status checking operations
    CONTROL = "control"  # Start, stop, restart operations
    MESSAGING = "messaging"  # Send, broadcast, publish operations
    CONFIGURATION = "configuration"  # Setup, configure operations
    DIAGNOSTIC = "diagnostic"  # Debug, logs, monitoring


@dataclass
class MCPOperation:
    """Represents a single MCP operation."""

    name: str
    cli_command: str
    group: str
    operation_type: OperationType
    parameters: list[str]
    description: str
    critical: bool = False  # Is this a critical operation?


class MCPOperationsInventory:
    """Complete inventory of all 92 MCP operations."""

    def __init__(self):
        self.operations = self._build_inventory()
        self.groups = self._organize_by_group()
        self.hierarchical_mapping = self._create_hierarchical_mapping()

    def _build_inventory(self) -> list[MCPOperation]:
        """Build the complete inventory of MCP operations."""
        operations = []

        # Agent Operations (10)
        operations.extend(
            [
                MCPOperation(
                    "agent_attach",
                    "agent attach",
                    "agent",
                    OperationType.CONTROL,
                    ["target"],
                    "Attach to agent session",
                    critical=True,
                ),
                MCPOperation(
                    "agent_deploy",
                    "agent deploy",
                    "agent",
                    OperationType.CRUD,
                    ["role", "session", "--briefing", "--extend"],
                    "Deploy new agent",
                ),
                MCPOperation(
                    "agent_info", "agent info", "agent", OperationType.STATUS, ["target"], "Get agent information"
                ),
                MCPOperation(
                    "agent_kill",
                    "agent kill",
                    "agent",
                    OperationType.CONTROL,
                    ["target"],
                    "Kill specific agent",
                    critical=True,
                ),
                MCPOperation(
                    "agent_kill_all",
                    "agent kill-all",
                    "agent",
                    OperationType.CONTROL,
                    [],
                    "Kill all agents",
                    critical=True,
                ),
                MCPOperation("agent_list", "agent list", "agent", OperationType.STATUS, [], "List all agents"),
                MCPOperation(
                    "agent_message",
                    "agent message",
                    "agent",
                    OperationType.MESSAGING,
                    ["target", "message"],
                    "Send message to agent",
                ),
                MCPOperation(
                    "agent_restart",
                    "agent restart",
                    "agent",
                    OperationType.CONTROL,
                    ["target"],
                    "Restart agent",
                    critical=True,
                ),
                MCPOperation(
                    "agent_send",
                    "agent send",
                    "agent",
                    OperationType.MESSAGING,
                    ["target", "keys"],
                    "Send keys to agent",
                ),
                MCPOperation(
                    "agent_status", "agent status", "agent", OperationType.STATUS, [], "Get agent status", critical=True
                ),
            ]
        )

        # Monitor Operations (10)
        operations.extend(
            [
                MCPOperation(
                    "monitor_dashboard",
                    "monitor dashboard",
                    "monitor",
                    OperationType.DIAGNOSTIC,
                    [],
                    "Show monitoring dashboard",
                ),
                MCPOperation(
                    "monitor_logs",
                    "monitor logs",
                    "monitor",
                    OperationType.DIAGNOSTIC,
                    ["--lines", "--follow"],
                    "View monitor logs",
                ),
                MCPOperation(
                    "monitor_performance",
                    "monitor performance",
                    "monitor",
                    OperationType.DIAGNOSTIC,
                    [],
                    "Show performance metrics",
                ),
                MCPOperation(
                    "monitor_recovery_logs",
                    "monitor recovery-logs",
                    "monitor",
                    OperationType.DIAGNOSTIC,
                    [],
                    "View recovery logs",
                ),
                MCPOperation(
                    "monitor_recovery_start",
                    "monitor recovery-start",
                    "monitor",
                    OperationType.CONTROL,
                    [],
                    "Start recovery monitoring",
                ),
                MCPOperation(
                    "monitor_recovery_status",
                    "monitor recovery-status",
                    "monitor",
                    OperationType.STATUS,
                    [],
                    "Check recovery status",
                ),
                MCPOperation(
                    "monitor_recovery_stop",
                    "monitor recovery-stop",
                    "monitor",
                    OperationType.CONTROL,
                    [],
                    "Stop recovery monitoring",
                ),
                MCPOperation(
                    "monitor_start",
                    "monitor start",
                    "monitor",
                    OperationType.CONTROL,
                    [],
                    "Start monitoring",
                    critical=True,
                ),
                MCPOperation(
                    "monitor_status",
                    "monitor status",
                    "monitor",
                    OperationType.STATUS,
                    [],
                    "Check monitor status",
                    critical=True,
                ),
                MCPOperation("monitor_stop", "monitor stop", "monitor", OperationType.CONTROL, [], "Stop monitoring"),
            ]
        )

        # PM Operations (6)
        operations.extend(
            [
                MCPOperation(
                    "pm_broadcast", "pm broadcast", "pm", OperationType.MESSAGING, ["message"], "Broadcast to all PMs"
                ),
                MCPOperation("pm_checkin", "pm checkin", "pm", OperationType.MESSAGING, ["target"], "PM check-in"),
                MCPOperation("pm_create", "pm create", "pm", OperationType.CRUD, ["name", "--extend"], "Create new PM"),
                MCPOperation(
                    "pm_custom_checkin",
                    "pm custom-checkin",
                    "pm",
                    OperationType.MESSAGING,
                    ["target", "message"],
                    "Custom PM check-in",
                ),
                MCPOperation(
                    "pm_message",
                    "pm message",
                    "pm",
                    OperationType.MESSAGING,
                    ["target", "message"],
                    "Send message to PM",
                ),
                MCPOperation("pm_status", "pm status", "pm", OperationType.STATUS, [], "Get PM status", critical=True),
            ]
        )

        # Context Operations (4)
        operations.extend(
            [
                MCPOperation(
                    "context_export", "context export", "context", OperationType.CRUD, ["output"], "Export context"
                ),
                MCPOperation(
                    "context_list", "context list", "context", OperationType.STATUS, [], "List available contexts"
                ),
                MCPOperation(
                    "context_show", "context show", "context", OperationType.STATUS, ["name"], "Show context details"
                ),
                MCPOperation(
                    "context_spawn",
                    "context spawn",
                    "context",
                    OperationType.CRUD,
                    ["name", "session"],
                    "Spawn with context",
                ),
            ]
        )

        # Team Operations (5)
        operations.extend(
            [
                MCPOperation(
                    "team_broadcast",
                    "team broadcast",
                    "team",
                    OperationType.MESSAGING,
                    ["message"],
                    "Broadcast to team",
                ),
                MCPOperation(
                    "team_deploy", "team deploy", "team", OperationType.CRUD, ["plan"], "Deploy team from plan"
                ),
                MCPOperation("team_list", "team list", "team", OperationType.STATUS, [], "List team members"),
                MCPOperation("team_recover", "team recover", "team", OperationType.CONTROL, ["plan"], "Recover team"),
                MCPOperation(
                    "team_status", "team status", "team", OperationType.STATUS, [], "Get team status", critical=True
                ),
            ]
        )

        # Orchestrator Operations (7)
        operations.extend(
            [
                MCPOperation(
                    "orchestrator_broadcast",
                    "orchestrator broadcast",
                    "orchestrator",
                    OperationType.MESSAGING,
                    ["message"],
                    "Broadcast to orchestrators",
                ),
                MCPOperation(
                    "orchestrator_kill",
                    "orchestrator kill",
                    "orchestrator",
                    OperationType.CONTROL,
                    ["target"],
                    "Kill orchestrator",
                ),
                MCPOperation(
                    "orchestrator_kill_all",
                    "orchestrator kill-all",
                    "orchestrator",
                    OperationType.CONTROL,
                    [],
                    "Kill all orchestrators",
                ),
                MCPOperation(
                    "orchestrator_list",
                    "orchestrator list",
                    "orchestrator",
                    OperationType.STATUS,
                    [],
                    "List orchestrators",
                ),
                MCPOperation(
                    "orchestrator_schedule",
                    "orchestrator schedule",
                    "orchestrator",
                    OperationType.CRUD,
                    ["cron", "command"],
                    "Schedule task",
                ),
                MCPOperation(
                    "orchestrator_start",
                    "orchestrator start",
                    "orchestrator",
                    OperationType.CONTROL,
                    [],
                    "Start orchestrator",
                ),
                MCPOperation(
                    "orchestrator_status",
                    "orchestrator status",
                    "orchestrator",
                    OperationType.STATUS,
                    [],
                    "Get orchestrator status",
                ),
            ]
        )

        # Setup Operations (7)
        operations.extend(
            [
                MCPOperation("setup_all", "setup all", "setup", OperationType.CONFIGURATION, [], "Run all setup steps"),
                MCPOperation("setup_check", "setup check", "setup", OperationType.DIAGNOSTIC, [], "Check setup status"),
                MCPOperation(
                    "setup_check_requirements",
                    "setup check-requirements",
                    "setup",
                    OperationType.DIAGNOSTIC,
                    [],
                    "Check requirements",
                ),
                MCPOperation(
                    "setup_claude_code",
                    "setup claude-code",
                    "setup",
                    OperationType.CONFIGURATION,
                    [],
                    "Setup Claude Code integration",
                ),
                MCPOperation("setup_mcp", "setup mcp", "setup", OperationType.CONFIGURATION, [], "Setup MCP server"),
                MCPOperation(
                    "setup_tmux", "setup tmux", "setup", OperationType.CONFIGURATION, [], "Setup tmux environment"
                ),
                MCPOperation(
                    "setup_vscode", "setup vscode", "setup", OperationType.CONFIGURATION, [], "Setup VSCode integration"
                ),
            ]
        )

        # Spawn Operations (3)
        operations.extend(
            [
                MCPOperation(
                    "spawn_agent",
                    "spawn agent",
                    "spawn",
                    OperationType.CRUD,
                    ["role", "session", "--briefing"],
                    "Spawn new agent",
                    critical=True,
                ),
                MCPOperation(
                    "spawn_orc", "spawn orc", "spawn", OperationType.CRUD, ["session", "--extend"], "Spawn orchestrator"
                ),
                MCPOperation(
                    "spawn_pm",
                    "spawn pm",
                    "spawn",
                    OperationType.CRUD,
                    ["--session", "--extend"],
                    "Spawn PM",
                    critical=True,
                ),
            ]
        )

        # Recovery Operations (4)
        operations.extend(
            [
                MCPOperation(
                    "recovery_start", "recovery start", "recovery", OperationType.CONTROL, [], "Start recovery system"
                ),
                MCPOperation(
                    "recovery_status", "recovery status", "recovery", OperationType.STATUS, [], "Check recovery status"
                ),
                MCPOperation(
                    "recovery_stop", "recovery stop", "recovery", OperationType.CONTROL, [], "Stop recovery system"
                ),
                MCPOperation(
                    "recovery_test", "recovery test", "recovery", OperationType.DIAGNOSTIC, [], "Test recovery system"
                ),
            ]
        )

        # Session Operations (2)
        operations.extend(
            [
                MCPOperation(
                    "session_attach",
                    "session attach",
                    "session",
                    OperationType.CONTROL,
                    ["target"],
                    "Attach to session",
                ),
                MCPOperation("session_list", "session list", "session", OperationType.STATUS, [], "List sessions"),
            ]
        )

        # PubSub Operations (8)
        operations.extend(
            [
                MCPOperation(
                    "pubsub_publish",
                    "pubsub publish",
                    "pubsub",
                    OperationType.MESSAGING,
                    ["channel", "message"],
                    "Publish message",
                ),
                MCPOperation(
                    "pubsub_read",
                    "pubsub read",
                    "pubsub",
                    OperationType.MESSAGING,
                    ["channel", "--last"],
                    "Read messages",
                ),
                MCPOperation(
                    "pubsub_search", "pubsub search", "pubsub", OperationType.STATUS, ["pattern"], "Search messages"
                ),
                MCPOperation("pubsub_status", "pubsub status", "pubsub", OperationType.STATUS, [], "Get pubsub status"),
                MCPOperation(
                    "pubsub_fast_publish",
                    "pubsub-fast publish",
                    "pubsub-fast",
                    OperationType.MESSAGING,
                    ["channel", "message"],
                    "Fast publish",
                ),
                MCPOperation(
                    "pubsub_fast_read",
                    "pubsub-fast read",
                    "pubsub-fast",
                    OperationType.MESSAGING,
                    ["channel"],
                    "Fast read",
                ),
                MCPOperation(
                    "pubsub_fast_stats",
                    "pubsub-fast stats",
                    "pubsub-fast",
                    OperationType.STATUS,
                    [],
                    "Get fast pubsub stats",
                ),
                MCPOperation(
                    "pubsub_fast_status",
                    "pubsub-fast status",
                    "pubsub-fast",
                    OperationType.STATUS,
                    [],
                    "Get fast pubsub status",
                ),
            ]
        )

        # Daemon Operations (5)
        operations.extend(
            [
                MCPOperation(
                    "daemon_logs", "daemon logs", "daemon", OperationType.DIAGNOSTIC, ["--lines"], "View daemon logs"
                ),
                MCPOperation("daemon_restart", "daemon restart", "daemon", OperationType.CONTROL, [], "Restart daemon"),
                MCPOperation(
                    "daemon_start", "daemon start", "daemon", OperationType.CONTROL, [], "Start daemon", critical=True
                ),
                MCPOperation(
                    "daemon_status",
                    "daemon status",
                    "daemon",
                    OperationType.STATUS,
                    [],
                    "Check daemon status",
                    critical=True,
                ),
                MCPOperation("daemon_stop", "daemon stop", "daemon", OperationType.CONTROL, [], "Stop daemon"),
            ]
        )

        # Tasks Operations (7)
        operations.extend(
            [
                MCPOperation(
                    "tasks_archive", "tasks archive", "tasks", OperationType.CRUD, [], "Archive completed tasks"
                ),
                MCPOperation(
                    "tasks_create", "tasks create", "tasks", OperationType.CRUD, ["description"], "Create new task"
                ),
                MCPOperation(
                    "tasks_distribute",
                    "tasks distribute",
                    "tasks",
                    OperationType.CRUD,
                    [],
                    "Distribute tasks to agents",
                ),
                MCPOperation("tasks_export", "tasks export", "tasks", OperationType.CRUD, ["format"], "Export tasks"),
                MCPOperation(
                    "tasks_generate",
                    "tasks generate",
                    "tasks",
                    OperationType.CRUD,
                    ["template"],
                    "Generate tasks from template",
                ),
                MCPOperation("tasks_list", "tasks list", "tasks", OperationType.STATUS, [], "List all tasks"),
                MCPOperation("tasks_status", "tasks status", "tasks", OperationType.STATUS, [], "Get tasks status"),
            ]
        )

        # Error Operations (4)
        operations.extend(
            [
                MCPOperation("errors_clear", "errors clear", "errors", OperationType.CRUD, [], "Clear error log"),
                MCPOperation(
                    "errors_recent", "errors recent", "errors", OperationType.STATUS, ["--count"], "Show recent errors"
                ),
                MCPOperation(
                    "errors_stats", "errors stats", "errors", OperationType.STATUS, [], "Show error statistics"
                ),
                MCPOperation(
                    "errors_summary", "errors summary", "errors", OperationType.STATUS, [], "Show error summary"
                ),
            ]
        )

        # Server Operations (5)
        operations.extend(
            [
                MCPOperation("server_setup", "server setup", "server", OperationType.CONFIGURATION, [], "Setup server"),
                MCPOperation("server_start", "server start", "server", OperationType.CONTROL, [], "Start server"),
                MCPOperation(
                    "server_status", "server status", "server", OperationType.STATUS, [], "Check server status"
                ),
                MCPOperation(
                    "server_toggle", "server toggle", "server", OperationType.CONTROL, [], "Toggle server state"
                ),
                MCPOperation("server_tools", "server tools", "server", OperationType.STATUS, [], "List server tools"),
            ]
        )

        # Standalone Operations (5)
        operations.extend(
            [
                MCPOperation(
                    "execute",
                    "execute",
                    "_standalone",
                    OperationType.CONTROL,
                    ["command"],
                    "Execute arbitrary command",
                    critical=True,
                ),
                MCPOperation("list", "list", "_standalone", OperationType.STATUS, [], "List all entities"),
                MCPOperation(
                    "quick_deploy", "quick-deploy", "_standalone", OperationType.CRUD, ["role"], "Quick deploy agent"
                ),
                MCPOperation(
                    "reflect", "reflect", "_standalone", OperationType.DIAGNOSTIC, ["--format"], "Reflect CLI structure"
                ),
                MCPOperation(
                    "status", "status", "_standalone", OperationType.STATUS, [], "System status", critical=True
                ),
            ]
        )

        return operations

    def _organize_by_group(self) -> dict[str, list[MCPOperation]]:
        """Organize operations by their groups."""
        groups = {}
        for op in self.operations:
            if op.group not in groups:
                groups[op.group] = []
            groups[op.group].append(op)
        return groups

    def _create_hierarchical_mapping(self) -> dict[str, dict[str, Any]]:
        """Create the proposed hierarchical mapping."""
        # This represents the target hierarchical structure
        # From 92 flat tools to ~20 hierarchical tools
        return {
            "agent": {
                "description": "Agent lifecycle and management",
                "operations": [
                    "attach",
                    "deploy",
                    "info",
                    "kill",
                    "kill-all",
                    "list",
                    "message",
                    "restart",
                    "send",
                    "status",
                ],
                "target_tool_count": 1,
            },
            "monitor": {
                "description": "System monitoring and recovery",
                "operations": [
                    "dashboard",
                    "logs",
                    "performance",
                    "recovery-logs",
                    "recovery-start",
                    "recovery-status",
                    "recovery-stop",
                    "start",
                    "status",
                    "stop",
                ],
                "target_tool_count": 1,
            },
            "pm": {
                "description": "Project manager operations",
                "operations": ["broadcast", "checkin", "create", "custom-checkin", "message", "status"],
                "target_tool_count": 1,
            },
            "context": {
                "description": "Context management",
                "operations": ["export", "list", "show", "spawn"],
                "target_tool_count": 1,
            },
            "team": {
                "description": "Team coordination",
                "operations": ["broadcast", "deploy", "list", "recover", "status"],
                "target_tool_count": 1,
            },
            "orchestrator": {
                "description": "Orchestrator management",
                "operations": ["broadcast", "kill", "kill-all", "list", "schedule", "start", "status"],
                "target_tool_count": 1,
            },
            "setup": {
                "description": "System setup and configuration",
                "operations": ["all", "check", "check-requirements", "claude-code", "mcp", "tmux", "vscode"],
                "target_tool_count": 1,
            },
            "spawn": {
                "description": "Spawn various entities",
                "operations": ["agent", "orc", "pm"],
                "target_tool_count": 1,
            },
            "recovery": {
                "description": "Recovery system management",
                "operations": ["start", "status", "stop", "test"],
                "target_tool_count": 1,
            },
            "session": {"description": "Session management", "operations": ["attach", "list"], "target_tool_count": 1},
            "pubsub": {
                "description": "Message publishing and subscription",
                "operations": ["publish", "read", "search", "status"],
                "target_tool_count": 1,
            },
            "pubsub_fast": {
                "description": "Fast pubsub operations",
                "operations": ["publish", "read", "stats", "status"],
                "target_tool_count": 1,
            },
            "daemon": {
                "description": "Daemon control",
                "operations": ["logs", "restart", "start", "status", "stop"],
                "target_tool_count": 1,
            },
            "tasks": {
                "description": "Task management",
                "operations": ["archive", "create", "distribute", "export", "generate", "list", "status"],
                "target_tool_count": 1,
            },
            "errors": {
                "description": "Error handling and reporting",
                "operations": ["clear", "recent", "stats", "summary"],
                "target_tool_count": 1,
            },
            "server": {
                "description": "MCP server management",
                "operations": ["setup", "start", "status", "toggle", "tools"],
                "target_tool_count": 1,
            },
            "system": {
                "description": "System-wide operations",
                "operations": ["execute", "list", "quick-deploy", "reflect", "status"],
                "target_tool_count": 1,
            },
        }

    def get_total_operations(self) -> int:
        """Get total number of operations."""
        return len(self.operations)

    def get_critical_operations(self) -> list[MCPOperation]:
        """Get all critical operations that must work perfectly."""
        return [op for op in self.operations if op.critical]

    def get_operations_by_type(self, op_type: OperationType) -> list[MCPOperation]:
        """Get operations by their type."""
        return [op for op in self.operations if op.operation_type == op_type]

    def get_hierarchical_tool_count(self) -> int:
        """Get the target number of hierarchical tools."""
        return sum(1 for group in self.hierarchical_mapping.values() if group.get("target_tool_count", 0) > 0)

    def get_reduction_percentage(self) -> float:
        """Calculate the tool count reduction percentage."""
        original = self.get_total_operations()
        hierarchical = self.get_hierarchical_tool_count()
        return ((original - hierarchical) / original) * 100


if __name__ == "__main__":
    # Generate inventory report
    inventory = MCPOperationsInventory()

    print("MCP OPERATIONS INVENTORY REPORT")
    print("=" * 60)
    print(f"Total Operations: {inventory.get_total_operations()}")
    print(f"Critical Operations: {len(inventory.get_critical_operations())}")
    print(f"Target Hierarchical Tools: {inventory.get_hierarchical_tool_count()}")
    print(f"Reduction: {inventory.get_reduction_percentage():.1f}%")

    print("\nOperations by Type:")
    for op_type in OperationType:
        count = len(inventory.get_operations_by_type(op_type))
        print(f"  {op_type.value}: {count}")

    print("\nGroups:")
    for group, ops in inventory.groups.items():
        print(f"  {group}: {len(ops)} operations")

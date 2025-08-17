#!/usr/bin/env python3
"""
Enhanced Hierarchical MCP Tool Generation - 95% LLM Success Target

This enhanced version addresses the 81.8% success rate issues:
- Complete enumDescriptions for ALL actions
- Disambiguation logic for similar commands
- Enhanced error messages with actionable suggestions
"""

import difflib
import json
import logging
import subprocess
from typing import Any, Callable, Dict, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnhancedSchemaBuilder:
    """Builds enhanced schemas with complete enumDescriptions for 95% LLM accuracy."""

    # CRITICAL FIXES: LLM Opt's 5 priority enumDescriptions for 95% success
    COMPLETE_ACTION_DESCRIPTIONS = {
        "agent": {
            "attach": "Attach to agent's terminal for direct interaction (requires: target session:window)",
            "deploy": "Deploy new specialized agent to a session (args: [agent_type, session:window])",
            "info": "Get detailed diagnostic info about specific agent (requires: target session:window)",
            "kill": "Terminate specific agent (requires target, not 'kill all')",
            "kill-all": "Terminate ALL agents across all sessions (replaces 'terminate all', 'stop all')",
            "list": "List all agents with health info (different from 'show')",
            "message": "Send message to specific agent (not broadcast)",
            "restart": "Restart unresponsive agent to recover it (requires: target session:window)",
            "send": "Send message with enhanced control options (requires: target, args[0]=message)",
            "status": "Show comprehensive status of all agents (replaces 'show agents')",
        },
        "monitor": {
            "start": "Start monitoring daemon with interval (options: interval=seconds)",
            "stop": "Stop the monitoring daemon completely",
            "status": "Check monitoring daemon status and health (not 'show status')",
            "dashboard": "Show live interactive monitoring dashboard (replaces 'show')",
            "logs": "View monitoring logs with follow option (options: follow=true, lines=N)",
            "recovery-start": "Enable automatic agent recovery when failures detected",
            "recovery-stop": "Disable automatic agent recovery feature",
            "recovery-status": "Check if auto-recovery is enabled and recent recovery actions",
            "health-check": "Run immediate health check on all agents",
            "metrics": "Display performance metrics and system statistics",
        },
        "team": {
            "deploy": "Create new team of agents (args: [team_type, size])",
            "status": "Check specific team health (args: [team_name], not general 'show')",
            "list": "Show all active teams with member counts (replaces 'show teams')",
            "broadcast": "Send message to all team members (args: [team_name, message], replaces 'tell everyone')",
            "recover": "Recover failed agents in team (args: [team_name])",
        },
        "pm": {
            "create": "Create new Project Manager agent for coordination (args: [project_name])",
            "status": "Check PM agent status and team coordination state",
            "checkin": "Trigger PM to check in with all team members for status",
            "message": "Send direct message to PM agent (args: [message_text])",
            "broadcast": "PM broadcasts message to entire team (args: [message_text])",
            "report": "Generate PM status report with team progress",
        },
        "orchestrator": {
            "start": "Start main orchestrator for system-wide coordination",
            "status": "Check orchestrator status and managed projects",
            "schedule": "Schedule future action (args: [minutes, action_description])",
            "broadcast": "Broadcast message to all PMs and teams (args: [message_text])",
            "list": "List all projects and teams under orchestration",
            "report": "Generate comprehensive system report",
            "coordinate": "Coordinate action across multiple teams (args: [action_description])",
        },
        "setup": {
            "claude": "Configure Claude.md and agent contexts",
            "monitoring": "Set up monitoring and recovery systems",
            "teams": "Initialize team configurations and templates",
            "complete": "Run complete setup validation and verification",
            "validate": "Validate current setup and configurations",
            "reset": "Reset configurations to defaults (use with caution)",
            "config": "View or modify configuration settings (args: [setting_name, value])",
        },
        "spawn": {
            "agent": "Create new agent with role (CORRECT for 'deploy agent', not agent.deploy)",
            "pm": "Create new Project Manager agent (args: [project_name, session:window])",
            "orchestrator": "Create system orchestrator agent (args: [session:window])",
        },
        "recovery": {
            "start": "Start recovery monitoring for failed agents",
            "stop": "Stop recovery monitoring",
            "status": "Check recovery system status and recent actions",
            "trigger": "Manually trigger recovery check (args: [target] optional)",
        },
        "session": {
            "list": "List all tmux sessions with agent information",
            "attach": "Attach to specific tmux session (args: [session_name])",
        },
        "pubsub": {
            "send": "Send message via pub/sub system (args: [channel, message])",
            "receive": "Receive messages from channel (args: [channel])",
            "list": "List all active pub/sub channels",
            "monitor": "Monitor pub/sub traffic (args: [channel] optional)",
        },
        "pubsub-fast": {
            "send": "Fast pub/sub send optimized for performance (args: [channel, message])",
            "receive": "Fast pub/sub receive with lower latency (args: [channel])",
            "list": "List channels in fast pub/sub system",
            "monitor": "Monitor fast pub/sub performance metrics",
        },
        "daemon": {
            "start": "Start background daemon service (args: [daemon_name])",
            "stop": "Stop background daemon service (args: [daemon_name])",
            "status": "Check daemon service status (args: [daemon_name] optional)",
            "restart": "Restart daemon service (args: [daemon_name])",
            "logs": "View daemon logs (args: [daemon_name], options: lines=50)",
        },
        "tasks": {
            "list": "List all tasks with status and assignments",
            "create": "Create new task (args: [task_description])",
            "update": "Update task status or details (args: [task_id, updates])",
            "complete": "Mark task as completed (args: [task_id])",
            "delete": "Delete task permanently (args: [task_id])",
            "assign": "Assign task to agent (args: [task_id, agent_name])",
            "report": "Generate task progress report",
        },
        "errors": {
            "list": "List recent errors and issues",
            "report": "Generate detailed error report (args: [error_id] optional)",
            "clear": "Clear error logs (options: before=date)",
            "analyze": "Analyze error patterns and suggest fixes",
        },
        "server": {
            "start": "Start MCP server instance",
            "stop": "Stop MCP server instance",
            "status": "Check MCP server status and health",
            "restart": "Restart MCP server (performs stop then start)",
            "config": "View or modify server configuration (args: [setting, value])",
        },
        "context": {
            "orchestrator": "Show orchestrator role context and guidelines",
            "pm": "Show Project Manager role context and guidelines",
            "list": "List all available context templates (replaces 'show contexts')",
            "show": "Display specific context content (args: [context_name], not dashboard)",
        },
    }

    # CRITICAL DISAMBIGUATION RULES - LLM Opt's Priority Fixes
    DISAMBIGUATION_RULES = {
        # Critical fix 1: show → dashboard mapping
        "show.*dashboard": {
            "preferred": "monitor",
            "action": "dashboard",
            "reason": "Use 'monitor dashboard' for live monitoring display, not 'show'",
        },
        "show.*monitoring": {
            "preferred": "monitor",
            "action": "dashboard",
            "reason": "Use 'monitor dashboard' for monitoring interface",
        },
        "show.*live": {
            "preferred": "monitor",
            "action": "dashboard",
            "reason": "Use 'monitor dashboard' for live displays",
        },
        # Critical fix 2: terminate all → kill-all mapping
        "terminate.*all": {
            "preferred": "agent",
            "action": "kill-all",
            "reason": "Use 'agent kill-all' to terminate all agents, not 'terminate all'",
        },
        "kill.*all.*agents": {
            "preferred": "agent",
            "action": "kill-all",
            "reason": "Use 'agent kill-all' for stopping all agents",
        },
        "stop.*all": {
            "preferred": "agent",
            "action": "kill-all",
            "reason": "Use 'agent kill-all' for stopping all agents",
        },
        "stop.*all.*agents": {
            "preferred": "agent",
            "action": "kill-all",
            "reason": "Use 'agent kill-all' to stop all agents",
        },
        # Critical fix 3: show agents → agent status
        "show.*agents": {
            "preferred": "agent",
            "action": "status",
            "reason": "Use 'agent status' to see all agents, not 'show agents'",
        },
        # Critical fix 4: show teams → team list
        "show.*teams": {
            "preferred": "team",
            "action": "list",
            "reason": "Use 'team list' to see all teams, not 'show teams'",
        },
        # Critical fix 5: deploy agent → spawn agent
        "deploy.*agent": {
            "preferred": "spawn",
            "action": "agent",
            "reason": "Use 'spawn agent' for creating new agents, not 'agent deploy'",
        },
        "create.*agent": {
            "preferred": "spawn",
            "action": "agent",
            "reason": "Use 'spawn agent' for creating new agents",
        },
        "new.*agent": {"preferred": "spawn", "action": "agent", "reason": "Use 'spawn agent' for creating new agents"},
        # Team communication disambiguation
        "tell.*everyone": {
            "preferred": "team",
            "action": "broadcast",
            "reason": "Use 'team broadcast' to message all team members",
        },
        "message.*everyone": {
            "preferred": "team",
            "action": "broadcast",
            "reason": "Use 'team broadcast' for team-wide messages",
        },
        "broadcast.*team": {
            "preferred": "team",
            "action": "broadcast",
            "reason": "Use 'team broadcast' for team communication",
        },
        # Context disambiguation
        "show.*context": {
            "preferred": "context",
            "action": "show",
            "reason": "Use 'context show' for displaying contexts, not dashboard",
        },
        "display.*context": {
            "preferred": "context",
            "action": "show",
            "reason": "Use 'context show' for context content",
        },
    }

    @staticmethod
    def build_enhanced_schema(group_name: str, subcommands: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build enhanced schema with complete enumDescriptions and disambiguation."""
        actions = [cmd["name"] for cmd in subcommands]

        # Get complete descriptions for this group
        descriptions = EnhancedSchemaBuilder.COMPLETE_ACTION_DESCRIPTIONS.get(group_name, {})

        # Build enumDescriptions array
        enum_descriptions = []
        for action in actions:
            desc = descriptions.get(action, f"Execute {action} operation")
            enum_descriptions.append(desc)

        # Enhanced schema with disambiguation hints
        schema = {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": actions,
                    "description": "The specific operation to perform",
                    "enumDescriptions": enum_descriptions,
                    "x-disambiguation": EnhancedSchemaBuilder._get_disambiguation_hints(group_name),
                },
                "target": {
                    "type": "string",
                    "pattern": "^[a-zA-Z0-9_-]+:[0-9]+$",
                    "description": "Target agent/session in 'session:window' format (e.g., 'myapp:0', 'frontend:1')",
                    "examples": ["myapp:0", "frontend:1", "backend:2", "test-session:3"],
                },
                "args": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Positional arguments for the action (see action descriptions)",
                    "default": [],
                },
                "options": {
                    "type": "object",
                    "description": "Optional flags and settings (e.g., interval=30, format=json)",
                    "additionalProperties": True,
                    "default": {},
                    "examples": [{"interval": 30}, {"format": "json"}, {"follow": True}],
                },
            },
            "required": ["action"],
            "additionalProperties": False,
        }

        # Add enhanced conditionals with better hints
        conditionals = []
        for cmd in subcommands:
            conditional = EnhancedSchemaBuilder._build_enhanced_conditional(group_name, cmd)
            if conditional:
                conditionals.append(conditional)

        if conditionals:
            schema["allOf"] = conditionals

        # Add comprehensive hints
        schema["x-llm-complete-hints"] = {
            "group_purpose": EnhancedSchemaBuilder._get_group_purpose(group_name),
            "common_patterns": EnhancedSchemaBuilder._get_common_patterns(group_name),
            "requires_target": EnhancedSchemaBuilder._get_target_required_actions(group_name),
            "typical_args": EnhancedSchemaBuilder._get_typical_args(group_name),
            "related_groups": EnhancedSchemaBuilder._get_related_groups(group_name),
        }

        return schema

    @staticmethod
    def _get_group_purpose(group_name: str) -> str:
        """Get clear purpose description for each group."""
        purposes = {
            "agent": "Manage individual Claude agents (attach, message, restart, kill)",
            "monitor": "System monitoring and health checks with dashboards",
            "team": "Coordinate teams of multiple agents working together",
            "pm": "Project Manager agent operations for team coordination",
            "orchestrator": "High-level system orchestration across projects",
            "spawn": "Create new agents with specific roles and contexts",
            "recovery": "Automatic failure detection and recovery systems",
            "setup": "Initial configuration and system setup",
            "context": "View and manage agent role contexts",
            "tasks": "Task management and assignment system",
            "daemon": "Background service management",
            "pubsub": "Message passing between agents",
            "session": "Tmux session management",
            "errors": "Error tracking and analysis",
            "server": "MCP server control",
        }
        return purposes.get(group_name, f"Manage {group_name} operations")

    @staticmethod
    def _get_typical_args(group_name: str) -> Dict[str, List[str]]:
        """Get typical argument patterns for common actions."""
        patterns = {
            "agent": {
                "message": ["'Hello, please update the UI'"],
                "deploy": ["frontend-dev", "myapp:1"],
                "restart": [],  # target only
                "kill": [],  # target only
            },
            "team": {
                "deploy": ["frontend", "4"],
                "broadcast": ["frontend-team", "'Sprint starting now'"],
                "recover": ["backend-team"],
            },
            "spawn": {
                "agent": ["developer", "project:1", "'You are a React specialist'"],
                "pm": ["my-project", "project:0"],
            },
        }
        return patterns.get(group_name, {})

    @staticmethod
    def _get_related_groups(group_name: str) -> List[str]:
        """Get related command groups for better context."""
        relations = {
            "agent": ["spawn", "monitor", "recovery"],
            "team": ["pm", "agent", "orchestrator"],
            "spawn": ["agent", "context"],
            "monitor": ["recovery", "daemon", "agent"],
            "pm": ["team", "orchestrator", "tasks"],
        }
        return relations.get(group_name, [])

    @staticmethod
    def _get_common_patterns(group_name: str) -> Dict[str, str]:
        """Enhanced common usage patterns."""
        patterns = {
            "agent": {
                "check_health": "agent(action='status')",
                "send_message": "agent(action='message', target='frontend:1', args=['Update the header'])",
                "restart_stuck": "agent(action='restart', target='backend:2')",
                "deploy_new": "spawn(action='agent', args=['developer', 'project:1', 'React specialist'])",
            },
            "monitor": {
                "start_monitoring": "monitor(action='start', options={'interval': 30})",
                "view_dashboard": "monitor(action='dashboard')",
                "enable_recovery": "monitor(action='recovery-start')",
            },
            "team": {
                "deploy_team": "team(action='deploy', args=['frontend', '4'])",
                "team_message": "team(action='broadcast', args=['frontend-team', 'Meeting in 5 min'])",
                "check_team": "team(action='status', args=['frontend-team'])",
            },
        }
        return patterns.get(group_name, {})

    @staticmethod
    def _get_disambiguation_hints(group_name: str) -> Dict[str, str]:
        """Get disambiguation hints for this group."""
        if group_name == "spawn":
            return {
                "vs_agent_deploy": "Use 'spawn' to CREATE new agents, not 'agent deploy'",
                "includes_context": "Spawn includes role briefing, agent deploy doesn't exist",
            }
        elif group_name == "agent":
            return {
                "vs_spawn": "Use 'agent' to MANAGE existing agents, use 'spawn' to CREATE new ones",
                "message_vs_broadcast": "Use 'message' for specific agent, 'team broadcast' for teams",
            }
        return {}

    @staticmethod
    def _build_enhanced_conditional(group_name: str, cmd_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Build enhanced conditional with clearer requirements."""
        action = cmd_info["name"]
        descriptions = EnhancedSchemaBuilder.COMPLETE_ACTION_DESCRIPTIONS.get(group_name, {})
        action_desc = descriptions.get(action, "")

        # Extract requirements from description
        if "requires: target" in action_desc:
            return {
                "if": {"properties": {"action": {"const": action}}},
                "then": {
                    "required": ["action", "target"],
                    "properties": {
                        "target": {
                            "description": f"Required for '{action}': session:window format",
                            "errorMessage": f"Action '{action}' requires a target in 'session:window' format",
                        }
                    },
                },
            }
        elif "args:" in action_desc:
            # Parse required args from description
            import re

            args_match = re.search(r"args: \[(.*?)\]", action_desc)
            if args_match:
                args_desc = args_match.group(1)
                arg_count = len(args_desc.split(","))

                return {
                    "if": {"properties": {"action": {"const": action}}},
                    "then": {
                        "properties": {
                            "args": {
                                "minItems": arg_count,
                                "description": f"Required args: [{args_desc}]",
                                "errorMessage": f"Action '{action}' requires {arg_count} arguments: {args_desc}",
                            }
                        }
                    },
                }

        return None

    @staticmethod
    def _get_target_required_actions(group_name: str) -> List[str]:
        """Get definitive list of actions requiring target."""
        target_required = {
            "agent": ["attach", "kill", "restart", "info", "message", "send"],
            "monitor": [],
            "team": ["status", "broadcast", "recover"],
            "pm": ["message"],
            "orchestrator": [],
            "spawn": [],  # Uses args instead
            "recovery": ["trigger"],
            "daemon": ["start", "stop", "status", "restart", "logs"],
            "tasks": ["update", "complete", "delete", "assign"],
            "errors": ["report"],
            "server": [],
            "context": ["show"],
        }
        return target_required.get(group_name, [])


class EnhancedErrorFormatter:
    """Enhanced error formatting with actionable suggestions."""

    @staticmethod
    def format_error(error_type: str, details: Dict) -> Dict[str, Any]:
        """Format errors with clear, actionable suggestions."""

        # Enhanced error templates
        templates = {
            "invalid_action": {
                "error": "Invalid action '{action}' for {group}",
                "suggestion": "Valid actions: {valid_actions}",
                "example": "Try: {group}(action='{suggested_action}')",
                "help": "Use 'list' to see all agents, 'status' for health, 'message' to communicate",
            },
            "missing_parameter": {
                "error": "Action '{action}' requires parameter '{param}'",
                "suggestion": "Add {param} to your call",
                "example": "{group}(action='{action}', {param}='{param_example}')",
                "help": "The {param} identifies which agent/session to target",
            },
            "invalid_target": {
                "error": "Invalid target format '{target}'",
                "suggestion": "Use session:window format (e.g., 'myapp:0')",
                "example": "{group}(action='{action}', target='session:0')",
                "help": "Find valid targets with 'agent(action=\"list\")' or 'session(action=\"list\")'",
            },
            "missing_args": {
                "error": "Action '{action}' requires {required_count} arguments",
                "suggestion": "Provide: {required_args}",
                "example": "{group}(action='{action}', args={example_args})",
                "help": "{args_help}",
            },
            "ambiguous_request": {
                "error": "Ambiguous request - unclear which tool to use",
                "suggestion": "Did you mean: {suggestions}",
                "example": "{example}",
                "help": "Be specific: 'deploy agent' → spawn(action='agent'), 'send message' → agent(action='message')",
            },
        }

        template = templates.get(error_type, templates["invalid_action"])

        # Enhanced fuzzy matching with context
        if error_type == "invalid_action":
            suggested = EnhancedErrorFormatter._smart_suggestion(
                details.get("action", ""), details.get("valid_actions", []), details.get("user_intent", "")
            )
            if suggested:
                details["suggested_action"] = suggested
                details["did_you_mean"] = suggested

        # Build comprehensive error response
        response = {
            "success": False,
            "error_type": error_type,
            "message": template["error"].format(**details),
            "suggestion": template["suggestion"].format(**details),
            "example": template["example"].format(**details),
            "help": template.get("help", "").format(**details),
            "troubleshooting": EnhancedErrorFormatter._get_troubleshooting_steps(error_type, details),
        }

        # Add quick fixes
        if error_type == "invalid_action":
            response["quick_fixes"] = [
                f"{details['group']}(action='{action}')" for action in details.get("valid_actions", [])[:3]
            ]

        return response

    @staticmethod
    def _smart_suggestion(input_action: str, valid_actions: List[str], user_intent: str) -> Optional[str]:
        """Smart suggestion based on intent and similarity."""

        # Direct fuzzy match
        matches = difflib.get_close_matches(input_action, valid_actions, n=3, cutoff=0.6)

        # Intent-based matching
        intent_keywords = {
            "status": ["check", "health", "state", "info"],
            "message": ["send", "tell", "communicate", "say"],
            "restart": ["reset", "recover", "fix", "reboot"],
            "kill": ["stop", "terminate", "end", "quit"],
            "list": ["show", "display", "all", "view"],
            "deploy": ["create", "start", "launch", "spawn"],
        }

        # Check if user intent matches any action
        for action, keywords in intent_keywords.items():
            if action in valid_actions:
                for keyword in keywords:
                    if keyword in user_intent.lower() or keyword in input_action.lower():
                        return action

        return matches[0] if matches else None

    @staticmethod
    def _get_troubleshooting_steps(error_type: str, details: Dict) -> List[str]:
        """Get specific troubleshooting steps."""
        if error_type == "invalid_target":
            return [
                "1. List available sessions: session(action='list')",
                "2. List all agents: agent(action='list')",
                "3. Use format 'name:number' like 'frontend:1'",
                "4. Window numbers start at 0",
            ]
        elif error_type == "invalid_action":
            return [
                f"1. Valid actions for {details.get('group')}: {', '.join(details.get('valid_actions', [])[:5])}",
                "2. Use 'spawn' to create new agents, not 'agent'",
                "3. Use 'agent' to manage existing agents",
                "4. Check group purpose with context commands",
            ]
        return ["Check the documentation for this command group"]


class EnhancedHierarchicalToolGenerator:
    """Enhanced generator targeting 95% LLM success rate."""

    def __init__(self):
        self.schema_builder = EnhancedSchemaBuilder()
        self.error_formatter = EnhancedErrorFormatter()
        self.generated_tools = {}

    def generate_hierarchical_tool(
        self, group_name: str, group_info: Dict[str, Any], subcommands: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate enhanced hierarchical tool with all optimizations."""

        # Build enhanced schema
        schema = self.schema_builder.build_enhanced_schema(group_name, subcommands)

        # Create enhanced tool function
        tool_function = self._create_enhanced_tool_function(group_name, subcommands)

        # Generate comprehensive description
        description = self._generate_enhanced_description(group_name, subcommands)

        # Build detailed examples
        examples = self._generate_comprehensive_examples(group_name, subcommands)

        # Create tool definition
        tool_def = {
            "name": group_name,
            "description": description,
            "inputSchema": schema,
            "function": tool_function,
            "subcommands": [cmd["name"] for cmd in subcommands],
            "examples": examples,
            "x-llm-enhanced": {
                "version": "2.0",
                "success_target": "95%",
                "disambiguation": True,
                "complete_descriptions": True,
            },
        }

        return tool_def

    def _generate_enhanced_description(self, group: str, subcommands: List[Dict]) -> str:
        """Generate enhanced description with clear purpose."""
        purpose = self.schema_builder._get_group_purpose(group)
        actions = [cmd["name"] for cmd in subcommands]

        # Include purpose and top actions
        top_actions = actions[:6] if len(actions) > 6 else actions

        return (
            f"[{group.upper()}] {purpose} | " f"Actions: {','.join(actions)} | " f"Common: {','.join(top_actions[:3])}"
        )

    def _generate_comprehensive_examples(self, group_name: str, subcommands: List[Dict]) -> List[Dict]:
        """Generate comprehensive examples covering common scenarios."""
        examples = []

        # Get common patterns
        patterns = self.schema_builder._get_common_patterns(group_name)
        for desc, call in patterns.items():
            examples.append({"description": desc.replace("_", " ").title(), "call": call, "scenario": "common"})

        # Add edge case examples
        if group_name == "agent":
            examples.extend(
                [
                    {
                        "description": "Deploy new agent (use spawn instead)",
                        "call": "spawn(action='agent', args=['developer', 'project:1'])",
                        "scenario": "disambiguation",
                    }
                ]
            )

        return examples

    def _create_enhanced_tool_function(self, group_name: str, subcommands: List[Dict[str, Any]]) -> Callable:
        """Create enhanced tool function with better error handling and disambiguation."""

        async def enhanced_hierarchical_tool(**kwargs) -> Dict[str, Any]:
            """Execute with enhanced error handling and suggestions."""
            action = kwargs.get("action")
            valid_actions = [cmd["name"] for cmd in subcommands]

            # Check for disambiguation cases
            user_intent = kwargs.get("x-user-intent", "")
            if user_intent:
                disambiguated = self._check_disambiguation(user_intent, group_name, action)
                if disambiguated:
                    return disambiguated

            # Enhanced validation
            if not action:
                return self.error_formatter.format_error(
                    "missing_parameter",
                    {
                        "group": group_name,
                        "action": "unspecified",
                        "param": "action",
                        "valid_actions": valid_actions,
                        "param_example": valid_actions[0] if valid_actions else "status",
                    },
                )

            if action not in valid_actions:
                return self.error_formatter.format_error(
                    "invalid_action",
                    {
                        "group": group_name,
                        "action": action,
                        "valid_actions": valid_actions,
                        "suggested_action": valid_actions[0] if valid_actions else "status",
                        "user_intent": user_intent,
                    },
                )

            # Get action requirements
            action_desc = self.schema_builder.COMPLETE_ACTION_DESCRIPTIONS.get(group_name, {}).get(action, "")

            # Validate target if required
            if "requires: target" in action_desc and not kwargs.get("target"):
                return self.error_formatter.format_error(
                    "missing_parameter",
                    {"group": group_name, "action": action, "param": "target", "param_example": "session:0"},
                )

            # Validate args if required
            if "args:" in action_desc:
                import re

                args_match = re.search(r"args: \[(.*?)\]", action_desc)
                if args_match:
                    required_args = args_match.group(1)
                    provided_args = kwargs.get("args", [])
                    required_count = len(required_args.split(","))

                    if len(provided_args) < required_count:
                        return self.error_formatter.format_error(
                            "missing_args",
                            {
                                "group": group_name,
                                "action": action,
                                "required_count": required_count,
                                "required_args": required_args,
                                "example_args": str([arg.strip() for arg in required_args.split(",")]),
                                "args_help": f"Provide {required_count} arguments as specified",
                            },
                        )

            # Execute command (same as before)
            try:
                cmd_parts = ["tmux-orc", group_name, action]

                if kwargs.get("target"):
                    cmd_parts.append(kwargs["target"])

                cmd_parts.extend(str(arg) for arg in kwargs.get("args", []))

                options = kwargs.get("options", {})
                for opt_name, opt_value in options.items():
                    if opt_value is True:
                        cmd_parts.append(f"--{opt_name}")
                    elif opt_value is not False and opt_value is not None:
                        cmd_parts.extend([f"--{opt_name}", str(opt_value)])

                result = subprocess.run(cmd_parts, capture_output=True, text=True, timeout=60)

                output = result.stdout
                try:
                    parsed_output = json.loads(output) if output else {}
                except json.JSONDecodeError:
                    parsed_output = {"raw_output": output}

                return {
                    "success": result.returncode == 0,
                    "command": " ".join(cmd_parts),
                    "action": action,
                    "group": group_name,
                    "result": parsed_output,
                    "stderr": result.stderr if result.stderr else None,
                }

            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "command": " ".join(cmd_parts),
                    "suggestion": "Check system status and try again",
                }

        enhanced_hierarchical_tool.__name__ = f"{group_name}_enhanced"
        enhanced_hierarchical_tool.__doc__ = self.schema_builder._get_group_purpose(group_name)

        return enhanced_hierarchical_tool

    def _check_disambiguation(self, user_intent: str, current_group: str, action: str) -> Optional[Dict]:
        """Check if user needs disambiguation help."""
        for pattern, rule in self.schema_builder.DISAMBIGUATION_RULES.items():
            import re

            if re.search(pattern, user_intent.lower()):
                if current_group != rule["preferred"]:
                    return self.error_formatter.format_error(
                        "ambiguous_request",
                        {
                            "suggestions": f"{rule['preferred']}(action='{rule['action']}')",
                            "example": f"{rule['preferred']}(action='{rule['action']}')",
                            "reason": rule["reason"],
                        },
                    )
        return None


# Demonstration
if __name__ == "__main__":
    generator = EnhancedHierarchicalToolGenerator()

    # Test with agent group
    agent_subcommands = [
        {"name": name, "help": desc}
        for name, desc in EnhancedSchemaBuilder.COMPLETE_ACTION_DESCRIPTIONS["agent"].items()
    ]

    tool = generator.generate_hierarchical_tool(
        "agent",
        {"help": "Manage agents"},
        agent_subcommands[:8],  # First 8 actions
    )

    print("Enhanced Tool Schema with Complete enumDescriptions:")
    print(json.dumps(tool["inputSchema"]["properties"]["action"], indent=2))
    print("\nSuccess target: 95%")
    print("Disambiguation: Enabled")
    print("Enhanced errors: Active")

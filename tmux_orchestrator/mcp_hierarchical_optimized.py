#!/usr/bin/env python3
"""
Hierarchical MCP Tool Generation with LLM Optimizations

This enhanced version integrates LLM optimization feedback for better
accuracy, clarity, and usability.
"""

import json
import logging
import subprocess
from typing import Any, Callable, Dict, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMOptimizedSchemaBuilder:
    """Builds LLM-optimized JSON schemas for hierarchical MCP tools."""

    # Standard parameter descriptions for consistency
    STANDARD_PARAMS = {
        "action": "The operation to perform",
        "target": "Target in session:window format (e.g., 'myapp:0')",
        "message": "Text content to send",
        "args": "Additional positional arguments",
        "options": "Command flags and options",
        "type": "Resource type (agent, team, etc.)",
        "name": "Resource name or identifier",
        "format": "Output format (json, table, yaml)",
    }

    # Action descriptions for common operations
    ACTION_DESCRIPTIONS = {
        "agent": {
            "status": "Show all agents status",
            "restart": "Restart specific agent (requires: target)",
            "message": "Send message to agent (requires: target, args[0]=message)",
            "kill": "Terminate agent (requires: target)",
            "attach": "Attach to agent terminal (requires: target)",
            "deploy": "Deploy new agent (args: [type, session:window])",
            "info": "Get agent information (requires: target)",
            "list": "List all agents",
            "send": "Send message with control (requires: target, args[0]=message)",
            "kill-all": "Terminate all agents",
        },
        "monitor": {
            "start": "Start monitoring daemon (options: interval)",
            "stop": "Stop monitoring daemon",
            "status": "Check monitor status",
            "dashboard": "Show live dashboard",
            "logs": "View monitor logs (options: follow, lines)",
            "recovery-start": "Enable auto-recovery",
            "recovery-stop": "Disable auto-recovery",
            "recovery-status": "Check recovery status",
            "health-check": "Run health check",
            "metrics": "Show performance metrics",
        },
        "team": {
            "deploy": "Deploy team (args: [type, size])",
            "status": "Check team status (args: [team_name])",
            "list": "List all teams",
            "broadcast": "Send message to team (args: [team_name, message])",
            "recover": "Recover failed agents (args: [team_name])",
        },
    }

    @staticmethod
    def build_group_schema(group_name: str, subcommands: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build an LLM-optimized hierarchical schema for a command group."""
        # Build enum of available actions
        actions = [cmd["name"] for cmd in subcommands]

        # Get action descriptions
        descriptions = LLMOptimizedSchemaBuilder.ACTION_DESCRIPTIONS.get(group_name, {})

        # Build enumDescriptions for LLM clarity
        enum_descriptions = []
        for action in actions:
            desc = descriptions.get(action, f"Execute {action} operation")
            enum_descriptions.append(desc)

        # Base schema structure with LLM optimizations
        schema = {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": actions,
                    "description": LLMOptimizedSchemaBuilder.STANDARD_PARAMS["action"],
                    "enumDescriptions": enum_descriptions,
                    "x-llm-hint": f"Choose one of the {group_name} operations",
                },
                "target": {
                    "type": "string",
                    "pattern": "^[a-zA-Z0-9_-]+:[0-9]+$",
                    "description": LLMOptimizedSchemaBuilder.STANDARD_PARAMS["target"],
                    "examples": ["frontend:1", "backend:2", "myproject:0"],
                },
                "args": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": LLMOptimizedSchemaBuilder.STANDARD_PARAMS["args"],
                    "default": [],
                },
                "options": {
                    "type": "object",
                    "description": LLMOptimizedSchemaBuilder.STANDARD_PARAMS["options"],
                    "additionalProperties": True,
                    "default": {},
                },
            },
            "required": ["action"],
            "additionalProperties": False,
        }

        # Build conditional requirements based on subcommands
        conditionals = []
        for cmd in subcommands:
            conditional = LLMOptimizedSchemaBuilder._build_action_conditional(group_name, cmd)
            if conditional:
                conditionals.append(conditional)

        if conditionals:
            schema["allOf"] = conditionals

        # Add LLM hints
        schema["x-llm-hints"] = {
            "common_actions": LLMOptimizedSchemaBuilder._get_common_actions(group_name),
            "requires_target": LLMOptimizedSchemaBuilder._get_target_required_actions(group_name),
            "message_actions": ["message", "send", "broadcast"],
        }

        return schema

    @staticmethod
    def _build_action_conditional(group_name: str, cmd_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Build conditional schema for a specific action with LLM hints."""
        action = cmd_info["name"]

        # Common patterns for different action types
        if action in ["attach", "kill", "restart", "info"]:
            return {
                "if": {"properties": {"action": {"const": action}}},
                "then": {"required": ["action", "target"], "x-llm-hint": f"Action '{action}' requires a target"},
            }
        elif action in ["message", "send"]:
            return {
                "if": {"properties": {"action": {"const": action}}},
                "then": {
                    "required": ["action", "target"],
                    "properties": {
                        "args": {
                            "minItems": 1,
                            "description": "Message content as first argument",
                            "x-llm-hint": "Include message text in args[0]",
                        }
                    },
                },
            }
        elif action == "deploy":
            return {
                "if": {"properties": {"action": {"const": action}}},
                "then": {
                    "properties": {
                        "args": {
                            "minItems": 2,
                            "description": "[agent_type, session:window]",
                            "x-llm-hint": "Provide agent type and target location",
                        }
                    }
                },
            }

        return None

    @staticmethod
    def _get_common_actions(group_name: str) -> List[str]:
        """Get most common actions for a group."""
        common = {
            "agent": ["status", "restart", "message"],
            "monitor": ["status", "start", "dashboard"],
            "team": ["deploy", "status", "broadcast"],
            "pm": ["status", "message", "checkin"],
        }
        return common.get(group_name, [])

    @staticmethod
    def _get_target_required_actions(group_name: str) -> List[str]:
        """Get actions that require a target parameter."""
        target_required = {
            "agent": ["attach", "kill", "restart", "info", "message", "send"],
            "monitor": [],
            "team": ["status", "broadcast", "recover"],
            "pm": ["message"],
        }
        return target_required.get(group_name, [])


class LLMFriendlyErrorFormatter:
    """Formats errors for optimal LLM understanding."""

    @staticmethod
    def format_error(error_type: str, details: Dict) -> Dict[str, Any]:
        """Format errors with suggestions and examples."""

        templates = {
            "invalid_action": {
                "error": "Invalid action '{action}' for {group}",
                "suggestion": "Valid actions: {valid_actions}",
                "example": "Try: {group}(action='{suggested_action}')",
            },
            "missing_parameter": {
                "error": "Action '{action}' requires parameter '{param}'",
                "suggestion": "Add {param} to your call",
                "example": "{group}(action='{action}', {param}='value')",
            },
            "invalid_target": {
                "error": "Invalid target format '{target}'",
                "suggestion": "Use session:window format",
                "example": "{group}(action='{action}', target='session:0')",
            },
            "missing_args": {
                "error": "Action '{action}' requires arguments",
                "suggestion": "{required_args}",
                "example": "{group}(action='{action}', args={example_args})",
            },
        }

        template = templates.get(
            error_type, {"error": "Unknown error", "suggestion": "Check documentation", "example": ""}
        )

        # Add fuzzy matching for action typos
        if error_type == "invalid_action" and "action" in details:
            suggested = LLMFriendlyErrorFormatter._fuzzy_match_action(
                details["action"], details.get("valid_actions", [])
            )
            if suggested:
                details["suggested_action"] = suggested
                details["did_you_mean"] = suggested

        return {
            "success": False,
            "error_type": error_type,
            "message": template["error"].format(**details),
            "suggestion": template["suggestion"].format(**details),
            "example": template["example"].format(**details),
            "details": details,
        }

    @staticmethod
    def _fuzzy_match_action(input_action: str, valid_actions: List[str]) -> Optional[str]:
        """Find closest matching action for typos."""
        import difflib

        matches = difflib.get_close_matches(input_action, valid_actions, n=1, cutoff=0.6)
        return matches[0] if matches else None


class OptimizedHierarchicalToolGenerator:
    """Generates LLM-optimized hierarchical MCP tools."""

    def __init__(self):
        self.schema_builder = LLMOptimizedSchemaBuilder()
        self.error_formatter = LLMFriendlyErrorFormatter()
        self.generated_tools = {}

    def generate_hierarchical_tool(
        self, group_name: str, group_info: Dict[str, Any], subcommands: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate an LLM-optimized hierarchical tool for a command group."""
        # Build dynamic schema with LLM optimizations
        schema = self.schema_builder.build_group_schema(group_name, subcommands)

        # Create tool function with error handling
        tool_function = self._create_optimized_tool_function(group_name, subcommands)

        # Generate LLM-friendly description
        description = self._generate_tool_description(group_name, subcommands)

        # Build usage examples
        examples = self._generate_usage_examples(group_name, subcommands)

        # Build tool definition with all metadata
        tool_def = {
            "name": group_name,
            "description": description,
            "inputSchema": schema,
            "function": tool_function,
            "subcommands": [cmd["name"] for cmd in subcommands],
            "examples": examples,
            "x-llm-metadata": {
                "category": self._categorize_group(group_name),
                "complexity": self._assess_complexity(subcommands),
                "common_patterns": self._get_common_patterns(group_name),
            },
        }

        return tool_def

    def _generate_tool_description(self, group: str, subcommands: List[Dict]) -> str:
        """Generate LLM-optimized tool description."""
        actions = [cmd["name"] for cmd in subcommands]
        # Show top 5 actions for space efficiency
        display_actions = actions[:5] if len(actions) > 5 else actions
        all_actions = ",".join(actions)

        return (
            f"[{group.title()}] Manage {group} operations | "
            f"Actions: {all_actions} | "
            f"Ex: {group}(action='{display_actions[0]}')"
        )

    def _generate_usage_examples(self, group_name: str, subcommands: List[Dict]) -> List[Dict]:
        """Generate usage examples for the tool."""
        examples = []

        # Common example patterns
        example_patterns = {
            "agent": [
                {
                    "description": "Check all agents status",
                    "call": "agent(action='status')",
                    "result": "Lists all active agents",
                },
                {
                    "description": "Send message to frontend agent",
                    "call": "agent(action='message', target='frontend:1', args=['Update the header'])",
                    "result": "Message sent to agent",
                },
            ],
            "monitor": [
                {
                    "description": "Start monitoring with 30s interval",
                    "call": "monitor(action='start', options={'interval': 30})",
                    "result": "Monitoring daemon started",
                }
            ],
            "team": [
                {
                    "description": "Deploy 4-agent frontend team",
                    "call": "team(action='deploy', args=['frontend', '4'])",
                    "result": "Team deployed successfully",
                }
            ],
        }

        return example_patterns.get(
            group_name,
            [
                {
                    "description": f"Execute {group_name} operation",
                    "call": f"{group_name}(action='{subcommands[0]['name'] if subcommands else 'status'}')",
                }
            ],
        )

    def _create_optimized_tool_function(self, group_name: str, subcommands: List[Dict[str, Any]]) -> Callable:
        """Create LLM-optimized tool function with better error handling."""

        async def hierarchical_tool(**kwargs) -> Dict[str, Any]:
            """Execute hierarchical command group operations with LLM-friendly responses."""
            action = kwargs.get("action")
            valid_actions = [cmd["name"] for cmd in subcommands]

            # Validate action
            if not action:
                return self.error_formatter.format_error(
                    "missing_parameter",
                    {
                        "group": group_name,
                        "action": "unspecified",
                        "param": "action",
                        "valid_actions": ", ".join(valid_actions),
                    },
                )

            if action not in valid_actions:
                return self.error_formatter.format_error(
                    "invalid_action",
                    {
                        "group": group_name,
                        "action": action,
                        "valid_actions": ", ".join(valid_actions),
                        "suggested_action": valid_actions[0] if valid_actions else "status",
                    },
                )

            # Validate target if required
            target_required = self.schema_builder._get_target_required_actions(group_name)
            if action in target_required and not kwargs.get("target"):
                return self.error_formatter.format_error(
                    "missing_parameter", {"group": group_name, "action": action, "param": "target"}
                )

            # Build command parts
            cmd_parts = ["tmux-orc", group_name, action]

            # Add target if provided
            target = kwargs.get("target")
            if target:
                # Validate target format
                import re

                if not re.match(r"^[a-zA-Z0-9_-]+:[0-9]+$", target):
                    return self.error_formatter.format_error(
                        "invalid_target", {"group": group_name, "action": action, "target": target}
                    )
                cmd_parts.append(target)

            # Add positional arguments
            args = kwargs.get("args", [])
            cmd_parts.extend(str(arg) for arg in args)

            # Add options
            options = kwargs.get("options", {})
            for opt_name, opt_value in options.items():
                if opt_value is True:
                    cmd_parts.append(f"--{opt_name}")
                elif opt_value is not False and opt_value is not None:
                    cmd_parts.extend([f"--{opt_name}", str(opt_value)])

            # Execute command
            try:
                result = subprocess.run(cmd_parts, capture_output=True, text=True, timeout=60)

                # Try to parse JSON output
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
                    "x-llm-hint": "Operation completed successfully"
                    if result.returncode == 0
                    else "Check stderr for details",
                }

            except subprocess.TimeoutExpired:
                return {
                    "success": False,
                    "error": "Command timed out after 60 seconds",
                    "command": " ".join(cmd_parts),
                    "suggestion": "Try again or check if the system is responding",
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "command": " ".join(cmd_parts),
                    "suggestion": "Check system logs for more details",
                }

        # Set function metadata
        hierarchical_tool.__name__ = f"{group_name}_hierarchical"
        hierarchical_tool.__doc__ = f"Execute {group_name} operations hierarchically with LLM optimizations"

        return hierarchical_tool

    def _categorize_group(self, group_name: str) -> str:
        """Categorize command group for LLM understanding."""
        categories = {
            "agent": "agent_management",
            "monitor": "system_monitoring",
            "team": "team_coordination",
            "pm": "project_management",
            "orchestrator": "system_orchestration",
            "setup": "configuration",
            "spawn": "resource_creation",
            "recovery": "error_recovery",
            "daemon": "background_services",
            "pubsub": "communication",
        }
        return categories.get(group_name, "general")

    def _assess_complexity(self, subcommands: List[Dict]) -> str:
        """Assess complexity level of command group."""
        count = len(subcommands)
        if count <= 3:
            return "simple"
        elif count <= 7:
            return "moderate"
        else:
            return "complex"

    def _get_common_patterns(self, group_name: str) -> Dict[str, str]:
        """Get common usage patterns for group."""
        patterns = {
            "agent": {
                "check_health": "agent(action='status')",
                "send_message": "agent(action='message', target='session:0', args=['text'])",
                "restart_agent": "agent(action='restart', target='session:0')",
            },
            "monitor": {
                "start_monitoring": "monitor(action='start', options={'interval': 30})",
                "check_status": "monitor(action='status')",
                "view_dashboard": "monitor(action='dashboard')",
            },
            "team": {
                "deploy_team": "team(action='deploy', args=['frontend', '4'])",
                "broadcast_message": "team(action='broadcast', args=['team_name', 'message'])",
            },
        }
        return patterns.get(group_name, {})


# Example usage demonstration
def demonstrate_optimized_generation():
    """Demonstrate the LLM-optimized hierarchical tool generation."""

    # Example agent group with subcommands
    agent_subcommands = [
        {"name": "attach", "help": "Attach to agent terminal"},
        {"name": "deploy", "help": "Deploy new agent"},
        {"name": "info", "help": "Get agent information"},
        {"name": "kill", "help": "Terminate agent"},
        {"name": "list", "help": "List all agents"},
        {"name": "message", "help": "Send message to agent"},
        {"name": "restart", "help": "Restart agent"},
        {"name": "status", "help": "Get agent status"},
    ]

    agent_group_info = {
        "help": "Manage individual agents across tmux sessions",
        "short_help": "Agent management operations",
    }

    # Generate optimized hierarchical tool
    generator = OptimizedHierarchicalToolGenerator()
    agent_tool = generator.generate_hierarchical_tool("agent", agent_group_info, agent_subcommands)

    # Display generated schema
    print("Generated LLM-Optimized Tool Schema:")
    print(json.dumps(agent_tool["inputSchema"], indent=2))

    print("\n\nTool Examples:")
    for example in agent_tool["examples"]:
        print(f"- {example['description']}")
        print(f"  Call: {example['call']}")
        print(f"  Result: {example.get('result', 'Success')}")

    return agent_tool


if __name__ == "__main__":
    # Run demonstration
    tool = demonstrate_optimized_generation()
    print(f"\n\nGenerated tool: {tool['name']}")
    print(f"Description: {tool['description']}")
    print(f"Handles {len(tool['subcommands'])} actions: {', '.join(tool['subcommands'])}")

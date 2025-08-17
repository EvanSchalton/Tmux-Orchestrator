#!/usr/bin/env python3
"""
Hierarchical MCP Tool Generation - Proof of Concept

This module demonstrates the hierarchical approach to MCP tool generation,
reducing 92 flat tools to ~20 hierarchical tools with smart parameter validation.
"""

import json
import logging
import subprocess
from typing import Any, Callable, Dict, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HierarchicalSchemaBuilder:
    """Builds dynamic JSON schemas for hierarchical MCP tools."""

    @staticmethod
    def build_group_schema(group_name: str, subcommands: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build a hierarchical schema for a command group.

        Args:
            group_name: Name of the command group (e.g., 'agent')
            subcommands: List of subcommand info dicts

        Returns:
            JSON Schema for the hierarchical tool
        """
        # Build enum of available actions
        actions = [cmd["name"] for cmd in subcommands]

        # Base schema structure
        schema = {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": actions, "description": f"The {group_name} operation to perform"},
                "target": {"type": "string", "description": "Target in session:window format (when required)"},
                "args": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Additional positional arguments",
                },
                "options": {"type": "object", "description": "Command-specific options", "additionalProperties": True},
            },
            "required": ["action"],
            "additionalProperties": False,
        }

        # Build conditional requirements based on subcommands
        conditionals = []
        for cmd in subcommands:
            conditional = HierarchicalSchemaBuilder._build_action_conditional(cmd)
            if conditional:
                conditionals.append(conditional)

        if conditionals:
            schema["allOf"] = conditionals

        return schema

    @staticmethod
    def _build_action_conditional(cmd_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Build conditional schema for a specific action."""
        action = cmd_info["name"]

        # Common patterns for different action types
        if action in ["attach", "kill", "restart", "info"]:
            # These typically require a target
            return {"if": {"properties": {"action": {"const": action}}}, "then": {"required": ["action", "target"]}}
        elif action in ["message", "send"]:
            # Message commands need target and message content
            return {
                "if": {"properties": {"action": {"const": action}}},
                "then": {
                    "required": ["action", "target"],
                    "properties": {"args": {"minItems": 1, "description": "Message content as first argument"}},
                },
            }
        elif action == "deploy":
            # Deploy needs agent type
            return {
                "if": {"properties": {"action": {"const": action}}},
                "then": {"properties": {"args": {"minItems": 2, "description": "[agent_type, session:window]"}}},
            }

        return None


class HierarchicalToolGenerator:
    """Generates hierarchical MCP tools from CLI structure."""

    def __init__(self):
        self.schema_builder = HierarchicalSchemaBuilder()
        self.generated_tools = {}

    def generate_hierarchical_tool(
        self, group_name: str, group_info: Dict[str, Any], subcommands: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate a single hierarchical tool for a command group.

        Args:
            group_name: Name of the command group
            group_info: Group metadata from CLI reflection
            subcommands: List of subcommand information

        Returns:
            Tool definition dict
        """
        # Build dynamic schema
        schema = self.schema_builder.build_group_schema(group_name, subcommands)

        # Create tool function
        tool_function = self._create_hierarchical_tool_function(group_name, subcommands)

        # Build tool definition
        tool_def = {
            "name": group_name,
            "description": group_info.get("short_help") or group_info.get("help", "").split("\n")[0],
            "inputSchema": schema,
            "function": tool_function,
            "subcommands": [cmd["name"] for cmd in subcommands],
        }

        return tool_def

    def _create_hierarchical_tool_function(self, group_name: str, subcommands: List[Dict[str, Any]]) -> Callable:
        """Create the actual function that handles hierarchical tool execution."""

        async def hierarchical_tool(**kwargs) -> Dict[str, Any]:
            """Execute hierarchical command group operations."""
            action = kwargs.get("action")
            if not action:
                return {
                    "success": False,
                    "error": "No action specified",
                    "available_actions": [cmd["name"] for cmd in subcommands],
                }

            # Build command parts
            cmd_parts = ["tmux-orc", group_name, action]

            # Add target if provided
            target = kwargs.get("target")
            if target:
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
                }

            except subprocess.TimeoutExpired:
                return {"success": False, "error": "Command timed out", "command": " ".join(cmd_parts)}
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "command": " ".join(cmd_parts),
                }

        # Set function metadata
        hierarchical_tool.__name__ = f"{group_name}_hierarchical"
        hierarchical_tool.__doc__ = f"Execute {group_name} operations hierarchically"

        return hierarchical_tool


# Example usage demonstration
def demonstrate_hierarchical_generation():
    """Demonstrate the hierarchical tool generation approach."""

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

    # Generate hierarchical tool
    generator = HierarchicalToolGenerator()
    agent_tool = generator.generate_hierarchical_tool("agent", agent_group_info, agent_subcommands)

    # Display generated schema
    print("Generated Hierarchical Tool Schema:")
    print(json.dumps(agent_tool["inputSchema"], indent=2))

    return agent_tool


if __name__ == "__main__":
    # Run demonstration
    tool = demonstrate_hierarchical_generation()
    print(f"\nGenerated tool: {tool['name']}")
    print(f"Handles {len(tool['subcommands'])} subcommands: {', '.join(tool['subcommands'])}")

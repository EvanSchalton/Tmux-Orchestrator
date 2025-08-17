"""Dynamic MCP tool generation from CLI introspection.

This module automatically generates FastMCP tools from tmux-orc CLI commands
using Click introspection, eliminating dual-implementation maintenance.
"""

import json
import logging
from typing import Any, Callable, Dict, List, Optional

import click
from fastmcp import FastMCP

from tmux_orchestrator.cli import cli as root_cli_group

logger = logging.getLogger(__name__)


class ClickToMCPGenerator:
    """Generates MCP tools from Click CLI commands using introspection."""

    def __init__(self, mcp_server: FastMCP):
        self.mcp = mcp_server
        self.cli_group = root_cli_group
        self.generated_tools = {}

    def generate_all_tools(self) -> Dict[str, Any]:
        """Generate all MCP tools from CLI commands.

        Returns:
            Dict mapping command names to generated tool info
        """
        logger.info("Starting dynamic MCP tool generation from CLI")

        # Process all CLI commands
        self._process_group(self.cli_group, prefix="")

        logger.info(f"Generated {len(self.generated_tools)} MCP tools")
        return self.generated_tools

    def _process_group(self, group: click.Group, prefix: str) -> None:
        """Process a Click group and its subcommands."""
        for name, command in group.commands.items():
            if isinstance(command, click.Group):
                # Recursively process subgroups
                new_prefix = f"{prefix}_{name}" if prefix else name
                self._process_group(command, new_prefix)
            else:
                # Generate MCP tool for individual commands
                tool_name = f"{prefix}_{name}" if prefix else name
                self._generate_tool_from_command(tool_name, command, group, name)

    def _generate_tool_from_command(
        self, tool_name: str, command: click.Command, parent_group: click.Group, command_name: str
    ) -> None:
        """Generate an MCP tool from a Click command."""
        try:
            # Extract command information
            help_text = command.help or f"Execute tmux-orc {command_name} command"
            short_help = getattr(command, "short_help", "") or help_text.split("\n")[0]

            # Build parameter schema from Click parameters
            input_schema = self._build_input_schema(command)

            # Create the actual tool function
            tool_func = self._create_tool_function(command, parent_group, command_name)

            # Register the tool with FastMCP
            decorated_tool = self.mcp.tool(name=tool_name, description=short_help, input_schema=input_schema)(tool_func)

            self.generated_tools[tool_name] = {
                "command_path": f"{parent_group.name}.{command_name}",
                "description": short_help,
                "input_schema": input_schema,
                "function": decorated_tool,
            }

            logger.debug(f"Generated MCP tool: {tool_name}")

        except Exception as e:
            logger.error(f"Failed to generate tool for {tool_name}: {e}")

    def _build_input_schema(self, command: click.Command) -> Dict[str, Any]:
        """Build JSON schema from Click command parameters."""
        properties = {}
        required = []

        for param in command.params:
            if isinstance(param, click.core.Option):
                # Handle Click options
                param_info = self._process_click_option(param)
            elif isinstance(param, click.core.Argument):
                # Handle Click arguments
                param_info = self._process_click_argument(param)
                if param.required:
                    required.append(param.name)
            else:
                continue

            if param_info:
                properties[param.name] = param_info

        return {"type": "object", "properties": properties, "required": required}

    def _process_click_option(self, option: click.core.Option) -> Optional[Dict[str, Any]]:
        """Process a Click option into JSON schema property."""
        param_info = {"description": option.help or f"Option: {option.name}"}

        # Determine type from Click type
        if isinstance(option.type, click.types.StringParamType):
            param_info["type"] = "string"
        elif isinstance(option.type, click.types.IntParamType):
            param_info["type"] = "integer"
        elif isinstance(option.type, click.types.FloatParamType):
            param_info["type"] = "number"
        elif isinstance(option.type, click.types.BoolParamType):
            param_info["type"] = "boolean"
        elif isinstance(option.type, click.types.Choice):
            param_info["type"] = "string"
            param_info["enum"] = option.type.choices
        elif isinstance(option.type, click.types.Path):
            param_info["type"] = "string"
            param_info["format"] = "path"
        else:
            param_info["type"] = "string"  # Default to string

        # Handle default values
        if option.default is not None and option.default != ():
            param_info["default"] = option.default

        # Handle flags (boolean options without values)
        if option.is_flag:
            param_info["type"] = "boolean"
            param_info["default"] = False

        return param_info

    def _process_click_argument(self, argument: click.core.Argument) -> Optional[Dict[str, Any]]:
        """Process a Click argument into JSON schema property."""
        param_info = {"description": f"Argument: {argument.name}"}

        # Determine type from Click type
        if isinstance(argument.type, click.types.StringParamType):
            param_info["type"] = "string"
        elif isinstance(argument.type, click.types.IntParamType):
            param_info["type"] = "integer"
        elif isinstance(argument.type, click.types.FloatParamType):
            param_info["type"] = "number"
        elif isinstance(argument.type, click.types.Choice):
            param_info["type"] = "string"
            param_info["enum"] = argument.type.choices
        else:
            param_info["type"] = "string"  # Default to string

        # Handle multiple arguments
        if argument.nargs == -1:  # Variable number of arguments
            param_info = {"type": "array", "items": param_info, "description": f"Multiple {argument.name} arguments"}
        elif argument.nargs > 1:  # Fixed number of multiple arguments
            param_info = {
                "type": "array",
                "items": param_info,
                "minItems": argument.nargs,
                "maxItems": argument.nargs,
                "description": f"{argument.nargs} {argument.name} arguments",
            }

        return param_info

    def _create_tool_function(self, command: click.Command, parent_group: click.Group, command_name: str) -> Callable:
        """Create the actual function that executes the CLI command."""

        async def tool_function(**kwargs) -> Dict[str, Any]:
            """Dynamically generated MCP tool function."""
            try:
                logger.info(f"Executing CLI command: {command_name} with args: {kwargs}")

                # Convert MCP tool arguments back to CLI format
                cli_args = self._convert_mcp_args_to_cli(command, kwargs)

                # Execute the CLI command in a safe context
                result = await self._execute_cli_command(parent_group, command_name, cli_args)

                return {
                    "success": True,
                    "command": command_name,
                    "arguments": kwargs,
                    "result": result,
                    "execution_time": result.get("execution_time"),
                }

            except Exception as e:
                logger.error(f"CLI command execution failed: {e}")
                return {
                    "success": False,
                    "command": command_name,
                    "arguments": kwargs,
                    "error": str(e),
                    "error_type": type(e).__name__,
                }

        # Set function metadata for better introspection
        tool_function.__name__ = f"cli_{command_name.replace('-', '_')}"
        tool_function.__doc__ = command.help or f"Execute tmux-orc {command_name}"

        return tool_function

    def _convert_mcp_args_to_cli(self, command: click.Command, mcp_args: Dict[str, Any]) -> List[str]:
        """Convert MCP tool arguments back to CLI format."""
        cli_args = []

        for param in command.params:
            if param.name in mcp_args:
                value = mcp_args[param.name]

                if isinstance(param, click.core.Option):
                    # Handle options
                    if param.is_flag:
                        if value:  # Only add flag if True
                            cli_args.extend(param.opts)
                    else:
                        # Add option with value
                        cli_args.append(param.opts[0])  # Use first option name
                        cli_args.append(str(value))

                elif isinstance(param, click.core.Argument):
                    # Handle arguments
                    if isinstance(value, list):
                        cli_args.extend([str(v) for v in value])
                    else:
                        cli_args.append(str(value))

        return cli_args

    async def _execute_cli_command(
        self, parent_group: click.Group, command_name: str, cli_args: List[str]
    ) -> Dict[str, Any]:
        """Execute CLI command and capture result."""
        import subprocess
        import time

        start_time = time.time()

        try:
            # Build full command
            cmd_parts = ["tmux-orc"]

            # Add parent group path if not root
            if parent_group.name != "tmux-orc":
                cmd_parts.append(parent_group.name)

            cmd_parts.append(command_name)
            cmd_parts.extend(cli_args)

            # Add JSON flag for parseable output
            if "--json" not in cli_args:
                cmd_parts.append("--json")

            # Execute command
            result = subprocess.run(
                cmd_parts,
                capture_output=True,
                text=True,
                timeout=60,  # 60 second timeout
            )

            execution_time = time.time() - start_time

            # Parse output
            output_data = {}
            if result.stdout:
                try:
                    output_data = json.loads(result.stdout)
                except json.JSONDecodeError:
                    output_data = {"output": result.stdout}

            return {
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "execution_time": execution_time,
                "parsed_output": output_data,
                "command_line": " ".join(cmd_parts),
            }

        except subprocess.TimeoutExpired:
            return {
                "return_code": -1,
                "error": "Command timed out after 60 seconds",
                "execution_time": time.time() - start_time,
            }
        except Exception as e:
            return {"return_code": -1, "error": str(e), "execution_time": time.time() - start_time}


def auto_generate_mcp_tools(mcp_server: FastMCP) -> Dict[str, Any]:
    """Auto-generate all MCP tools from CLI commands.

    This is the main entry point for dynamic tool generation.

    Args:
        mcp_server: FastMCP server instance to register tools with

    Returns:
        Dict of generated tool information
    """
    generator = ClickToMCPGenerator(mcp_server)
    return generator.generate_all_tools()


# Example of how specific command mappings work
def get_command_mapping() -> Dict[str, str]:
    """Get mapping of CLI commands to MCP tool names."""
    return {
        # Direct commands
        "list": "list_agents",
        "status": "get_system_status",
        "reflect": "reflect_cli_structure",
        # Agent commands
        "agent_spawn": "spawn_agent",
        "agent_message": "send_message",
        "agent_status": "get_agent_status",
        "agent_kill": "kill_agent",
        "agent_restart": "restart_agent",
        "agent_info": "get_agent_info",
        # Team commands
        "team_deploy": "deploy_team",
        "team_status": "get_team_status",
        "team_broadcast": "team_broadcast",
        "team_list": "list_teams",
        "team_recover": "recover_team",
        # Monitor commands
        "monitor_start": "start_monitoring",
        "monitor_stop": "stop_monitoring",
        "monitor_status": "get_monitoring_status",
        "monitor_dashboard": "show_monitoring_dashboard",
        # PM commands
        "pm_create": "create_pm",
        "pm_status": "get_pm_status",
        "pm_message": "send_pm_message",
        "pm_broadcast": "pm_broadcast_message",
        "pm_checkin": "trigger_pm_checkin",
        # Context commands
        "context_list": "list_contexts",
        "context_show": "show_context",
        "context_spawn": "spawn_with_context",
        # Session commands
        "session_list": "list_sessions",
        "session_attach": "attach_session",
        # Task commands
        "tasks_create": "create_project",
        "tasks_distribute": "distribute_tasks",
        "tasks_status": "get_task_status",
        "tasks_import_prd": "import_prd",
        # Setup commands
        "setup_claude_code": "setup_claude_code",
        "setup_vscode": "setup_vscode",
        "setup_tmux": "setup_tmux",
        "setup_all": "setup_all_tools",
        # Orchestrator commands
        "orchestrator_start": "start_orchestrator",
        "orchestrator_status": "get_orchestrator_status",
        "orchestrator_broadcast": "orchestrator_broadcast",
        "orchestrator_schedule": "schedule_orchestrator_task",
        # PubSub commands
        "publish": "publish_message",
        "subscribe": "subscribe_to_group",
        "read": "read_messages",
        # Error management
        "errors_summary": "get_error_summary",
        "errors_recent": "get_recent_errors",
        "errors_clear": "clear_error_logs",
        "errors_stats": "get_error_statistics",
        # Recovery commands
        "recovery_start": "start_recovery_daemon",
        "recovery_stop": "stop_recovery_daemon",
        "recovery_status": "get_recovery_status",
        # Quick deploy
        "quick_deploy": "quick_deploy_team",
        # Execute command
        "execute": "execute_prd",
        # Standup
        "conduct_standup": "conduct_team_standup",
    }

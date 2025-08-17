#!/usr/bin/env python3
"""
Fresh CLI Reflection-Based MCP Server for Tmux Orchestrator

Complete clean slate implementation using dynamic CLI introspection
to automatically generate all MCP tools from tmux-orc commands.

This replaces all manual tool implementations with pure auto-generation.
"""

import asyncio
import json
import logging

# CLI introspection imports
import subprocess
import sys
import time
from typing import Any, Dict, List

import mcp.types as types
from mcp.server import NotificationOptions, Server

# Standard MCP library
from mcp.server.models import InitializationOptions

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class FreshCLIMCPServer:
    """
    Fresh implementation of CLI-to-MCP auto-generation server.

    Uses standard MCP library and CLI introspection to create tools.
    """

    def __init__(self, server_name: str = "tmux-orchestrator-fresh"):
        """Initialize the fresh MCP server."""
        self.server = Server(server_name)
        self.generated_tools = {}
        self.cli_structure = None

        logger.info(f"Initializing fresh CLI reflection MCP server: {server_name}")

        # Register server handlers
        self._register_handlers()

    def _register_handlers(self):
        """Register MCP server handlers."""

        @self.server.list_tools()
        async def handle_list_tools() -> list[types.Tool]:
            """List all available tools."""
            if not self.generated_tools:
                await self._generate_all_tools()

            tools = []
            for tool_name, tool_info in self.generated_tools.items():
                tool = types.Tool(
                    name=tool_name, description=tool_info["description"], inputSchema=tool_info["input_schema"]
                )
                tools.append(tool)

            logger.info(f"Listed {len(tools)} tools")
            return tools

        @self.server.call_tool()
        async def handle_call_tool(
            name: str, arguments: dict | None
        ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
            """Handle tool execution."""
            if name not in self.generated_tools:
                raise ValueError(f"Unknown tool: {name}")

            tool_info = self.generated_tools[name]
            command_name = tool_info["command_name"]

            # Execute the CLI command
            result = await self._execute_cli_command(command_name, arguments or {})

            # Return result as text content
            result_text = json.dumps(result, indent=2)
            return [types.TextContent(type="text", text=result_text)]

    async def discover_cli_structure(self) -> Dict[str, Any]:
        """Discover CLI structure using tmux-orc reflect."""
        try:
            logger.info("Discovering CLI structure via tmux-orc reflect...")

            result = subprocess.run(
                ["tmux-orc", "reflect", "--format", "json"], capture_output=True, text=True, timeout=30
            )

            if result.returncode != 0:
                logger.error(f"CLI reflection failed: {result.stderr}")
                return {}

            # Parse CLI structure
            cli_structure = json.loads(result.stdout)

            # Extract commands (flat dict with command names as keys)
            commands = {k: v for k, v in cli_structure.items() if isinstance(v, dict) and v.get("type") == "command"}

            logger.info(f"Discovered {len(commands)} CLI commands")

            self.cli_structure = cli_structure
            return cli_structure

        except subprocess.TimeoutExpired:
            logger.error("CLI reflection timed out")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse CLI reflection JSON: {e}")
            return {}
        except Exception as e:
            logger.error(f"CLI discovery failed: {e}")
            return {}

    async def _generate_all_tools(self) -> Dict[str, Any]:
        """Generate all MCP tools from CLI structure."""
        if not self.cli_structure:
            await self.discover_cli_structure()

        if not self.cli_structure:
            logger.error("No CLI structure available for tool generation")
            return {}

        # Extract commands from CLI structure
        commands = {k: v for k, v in self.cli_structure.items() if isinstance(v, dict) and v.get("type") == "command"}

        logger.info(f"Generating MCP tools for {len(commands)} CLI commands...")

        for command_name, command_info in commands.items():
            try:
                self._generate_tool_for_command(command_name, command_info)
            except Exception as e:
                logger.error(f"Failed to generate tool for {command_name}: {e}")
                continue

        logger.info(f"Successfully generated {len(self.generated_tools)} MCP tools")
        return self.generated_tools

    def _generate_tool_for_command(self, command_name: str, command_info: Dict[str, Any]) -> None:
        """Generate tool metadata for a CLI command."""

        # Clean command name for MCP tool
        tool_name = command_name.replace("-", "_")

        # Extract command information
        description = command_info.get("help", f"Execute tmux-orc {command_name}")
        short_help = command_info.get("short_help", "")

        # Use short help if available, otherwise truncate full help
        tool_description = (
            short_help or description.split("\n")[0] if description else f"Execute tmux-orc {command_name}"
        )
        if len(tool_description) > 200:
            tool_description = tool_description[:197] + "..."

        # Create flexible input schema
        input_schema = {
            "type": "object",
            "properties": {
                "args": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Positional arguments for the command",
                    "default": [],
                },
                "options": {
                    "type": "object",
                    "description": "Command options as key-value pairs",
                    "additionalProperties": True,
                    "default": {},
                },
            },
            "required": [],
            "additionalProperties": False,
        }

        # Store tool information
        self.generated_tools[tool_name] = {
            "command_name": command_name,
            "description": tool_description,
            "input_schema": input_schema,
            "full_help": description,
        }

        logger.debug(f"Generated MCP tool: {tool_name} -> tmux-orc {command_name}")

    async def _execute_cli_command(self, command_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute CLI command with arguments."""
        start_time = time.time()

        try:
            # Convert arguments to CLI format
            cli_args = self._convert_arguments_to_cli(arguments)

            # Build complete command
            cmd_parts = ["tmux-orc", command_name] + cli_args

            # Add --json flag if command supports it
            if "--json" not in cli_args and self._command_supports_json(command_name):
                cmd_parts.append("--json")

            logger.info(f"Executing: {' '.join(cmd_parts)}")

            # Execute command
            result = subprocess.run(cmd_parts, capture_output=True, text=True, timeout=60)

            execution_time = time.time() - start_time

            # Parse output
            parsed_output = {}
            if result.stdout:
                try:
                    parsed_output = json.loads(result.stdout)
                except json.JSONDecodeError:
                    parsed_output = {"output": result.stdout}

            return {
                "success": result.returncode == 0,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "execution_time": execution_time,
                "parsed_output": parsed_output,
                "command_line": " ".join(cmd_parts),
                "mcp_tool": f"cli_{command_name.replace('-', '_')}",
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Command timed out after 60 seconds",
                "execution_time": time.time() - start_time,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "execution_time": time.time() - start_time,
            }

    def _convert_arguments_to_cli(self, arguments: Dict[str, Any]) -> List[str]:
        """Convert MCP arguments to CLI format."""
        cli_args = []

        # Handle positional arguments
        args = arguments.get("args", [])
        if args:
            cli_args.extend(str(arg) for arg in args)

        # Handle options
        options = arguments.get("options", {})
        for option_name, option_value in options.items():
            if option_value is True:
                # Boolean flag
                cli_args.append(f"--{option_name}")
            elif option_value is not False and option_value is not None:
                # Option with value
                cli_args.extend([f"--{option_name}", str(option_value)])

        return cli_args

    def _command_supports_json(self, command_name: str) -> bool:
        """Check if command supports JSON output."""
        json_commands = {
            "list",
            "status",
            "reflect",
            "spawn",
            "send",
            "kill",
            "agent-status",
            "team-status",
            "monitor-status",
        }
        return command_name in json_commands

    async def run(self):
        """Run the MCP server."""
        logger.info("Starting fresh CLI reflection MCP server...")

        # Generate tools on startup
        await self._generate_all_tools()

        if not self.generated_tools:
            logger.error("No tools generated! Check CLI availability")
            return

        # Log generated tools
        logger.info("Generated MCP Tools:")
        for tool_name in sorted(self.generated_tools.keys()):
            cmd_name = self.generated_tools[tool_name]["command_name"]
            logger.info(f"  • {tool_name} → tmux-orc {cmd_name}")

        # Run the server
        logger.info("Starting MCP server on stdio...")

        # Import the stdio transport from MCP
        from mcp.server.stdio import stdio_server

        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="tmux-orchestrator-fresh",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(), experimental_capabilities={}
                    ),
                ),
            )


async def main():
    """Main entry point."""
    try:
        # Check if tmux-orc is available
        result = subprocess.run(["tmux-orc", "--version"], capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            logger.error("tmux-orc command not available!")
            sys.exit(1)

        logger.info(f"Found tmux-orc: {result.stdout.strip()}")

        # Create and run server
        server = FreshCLIMCPServer()
        await server.run()

    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

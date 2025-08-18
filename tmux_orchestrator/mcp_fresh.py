#!/usr/bin/env python3
"""
Fresh CLI Reflection-Based MCP Server for Tmux Orchestrator

This is a complete clean slate implementation that uses dynamic CLI introspection
to automatically generate all MCP tools from tmux-orc commands.

Key Benefits:
- Zero dual implementation
- CLI is single source of truth
- All CLI commands become MCP tools automatically
- Future-proof: new CLI commands auto-generate tools
- No maintenance burden for MCP tools

Usage:
    python -m tmux_orchestrator.mcp_server_fresh
"""

import asyncio
import json
import logging
import subprocess
import sys
import time
from typing import Any

# CLI introspection imports
# FastMCP for MCP server implementation
from fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class FreshCLIToMCPServer:
    """
    Fresh implementation of CLI-to-MCP auto-generation server.

    This class introspects the tmux-orc CLI and automatically generates
    MCP tools for every available command.
    """

    def __init__(self, server_name: str = "tmux-orchestrator-fresh"):
        """Initialize the fresh MCP server."""
        self.mcp = FastMCP(server_name)
        self.generated_tools = {}
        self.cli_structure = None

        logger.info(f"Initializing fresh CLI reflection MCP server: {server_name}")

    async def discover_cli_structure(self) -> dict[str, Any]:
        """
        Discover the complete CLI structure using tmux-orc reflect.

        Returns:
            dict containing the complete CLI structure
        """
        try:
            logger.info("Discovering CLI structure via tmux-orc reflect...")

            # Use tmux-orc reflect to get complete CLI structure
            result = subprocess.run(
                ["tmux-orc", "reflect", "--format", "json"], capture_output=True, text=True, timeout=30
            )

            if result.returncode != 0:
                logger.error(f"CLI reflection failed: {result.stderr}")
                return {}

            # Parse CLI structure
            cli_structure = json.loads(result.stdout)

            # The CLI structure is a flat dict with command names as keys
            commands = {k: v for k, v in cli_structure.items() if isinstance(v, dict) and v.get("type") == "command"}

            logger.info(f"Discovered {len(commands)} CLI commands")

            # Store for later use
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

    def generate_all_mcp_tools(self) -> dict[str, Any]:
        """
        Generate all MCP tools from discovered CLI structure.

        Returns:
            dict of generated tool information
        """
        if not self.cli_structure:
            logger.error("No CLI structure available for tool generation")
            return {}

        # Extract both individual commands and command groups
        commands = {
            k: v for k, v in self.cli_structure.items() if isinstance(v, dict) and v.get("type") in ["command", "group"]
        }
        logger.info(f"Generating MCP tools for {len(commands)} CLI commands and groups...")

        for command_name, command_info in commands.items():
            try:
                if command_info.get("type") == "command":
                    # Generate tool for individual command
                    self._generate_tool_for_command(command_name, command_info)
                elif command_info.get("type") == "group":
                    # Generate tools for all subcommands in the group
                    self._generate_tools_for_group(command_name, command_info)
            except Exception as e:
                logger.error(f"Failed to generate tool for {command_name}: {e}")
                continue

        logger.info(f"Successfully generated {len(self.generated_tools)} MCP tools")
        return self.generated_tools

    def _generate_tool_for_command(self, command_name: str, command_info: dict[str, Any]) -> None:
        """Generate an MCP tool for a specific CLI command."""

        # Clean command name for MCP tool (replace hyphens with underscores)
        tool_name = command_name.replace("-", "_")

        # Extract command information
        description = command_info.get("help", f"Execute tmux-orc {command_name}")
        short_help = command_info.get("short_help", description.split("\n")[0] if description else "")

        # For now, create a simple schema since detailed parameter info isn't in reflect output
        # This is the strength of CLI reflection - we just pass arguments through
        input_schema = {
            "type": "object",
            "properties": {
                "args": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Command arguments as array of strings",
                    "default": [],
                },
                "options": {"type": "object", "description": "Command options as key-value pairs", "default": {}},
            },
            "required": [],
        }

        # Create the tool function
        tool_function = self._create_tool_function(command_name, command_info)

        # Use short help for description (limit length for MCP)
        tool_description = short_help or f"Execute tmux-orc {command_name}"
        if len(tool_description) > 200:
            tool_description = tool_description[:197] + "..."

        # Register with FastMCP (remove unsupported input_schema parameter)
        try:
            decorated_tool = self.mcp.tool(name=tool_name, description=tool_description)(tool_function)

            self.generated_tools[tool_name] = {
                "command_name": command_name,
                "description": description,
                "input_schema": input_schema,
                "function": decorated_tool,
            }

            logger.debug(f"Generated MCP tool: {tool_name} -> tmux-orc {command_name}")

        except Exception as e:
            logger.error(f"Failed to register tool {tool_name}: {e}")

    def _generate_tools_for_group(self, group_name: str, group_info: dict[str, Any]) -> None:
        """Generate MCP tools for all subcommands in a command group."""
        try:
            logger.debug(f"Discovering subcommands for group: {group_name}")

            # Use CLI help to discover subcommands
            result = subprocess.run(["tmux-orc", group_name, "--help"], capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                logger.error(f"Failed to get help for group {group_name}: {result.stderr}")
                return

            # Parse the help output to extract subcommands
            subcommands = self._parse_subcommands_from_help(result.stdout)

            logger.info(f"Found {len(subcommands)} subcommands in group {group_name}")

            # Generate tools for each subcommand
            for subcmd_name in subcommands:
                try:
                    # Create compound command name (e.g., "agent_status")
                    compound_name = f"{group_name}_{subcmd_name}".replace("-", "_")
                    full_command = f"{group_name} {subcmd_name}"

                    # Create synthetic command info for the subcommand
                    subcmd_info = {
                        "help": f"Execute tmux-orc {full_command}",
                        "short_help": f"Execute {full_command} subcommand",
                        "type": "subcommand",
                        "parent_group": group_name,
                        "subcommand": subcmd_name,
                    }

                    self._generate_tool_for_subcommand(compound_name, full_command, subcmd_info)

                except Exception as e:
                    logger.error(f"Failed to generate tool for {group_name} {subcmd_name}: {e}")
                    continue

        except subprocess.TimeoutExpired:
            logger.error(f"Timeout getting help for group {group_name}")
        except Exception as e:
            logger.error(f"Failed to process group {group_name}: {e}")

    def _parse_subcommands_from_help(self, help_text: str) -> list[str]:
        """Parse subcommand names from CLI help output."""
        subcommands = []
        in_commands_section = False

        for line in help_text.split("\n"):
            # Check for Commands: section (before stripping)
            if line.strip().lower() == "commands:":
                in_commands_section = True
                continue

            # Stop when we hit another section
            if in_commands_section and line.strip().startswith("Options:"):
                break

            # Extract command names (format: "  command_name  Description...")
            # Commands are indented with 2 spaces in Click's output
            if in_commands_section and line.startswith("  ") and not line.startswith("    "):
                # Get the first word after stripping the 2-space indent
                parts = line[2:].split()
                if parts:
                    cmd_name = parts[0]
                    # Ensure it's a valid command name (not a continuation of description)
                    if cmd_name and not cmd_name.startswith("-") and not cmd_name.startswith("("):
                        subcommands.append(cmd_name)

        return subcommands

    def _generate_tool_for_subcommand(self, tool_name: str, full_command: str, command_info: dict[str, Any]) -> None:
        """Generate an MCP tool for a subcommand."""

        # Extract command information
        description = command_info.get("help", f"Execute tmux-orc {full_command}")
        short_help = command_info.get("short_help", description.split("\n")[0] if description else "")

        # Create input schema for subcommands
        input_schema = {
            "type": "object",
            "properties": {
                "args": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Command arguments as array of strings",
                    "default": [],
                },
                "options": {"type": "object", "description": "Command options as key-value pairs", "default": {}},
            },
            "required": [],
        }

        # Create the tool function for subcommand
        tool_function = self._create_subcommand_tool_function(full_command, command_info)

        # Use short help for description (limit length for MCP)
        tool_description = short_help or f"Execute tmux-orc {full_command}"
        if len(tool_description) > 200:
            tool_description = tool_description[:197] + "..."

        # Register with FastMCP
        try:
            decorated_tool = self.mcp.tool(name=tool_name, description=tool_description)(tool_function)

            self.generated_tools[tool_name] = {
                "command_name": full_command,
                "description": description,
                "input_schema": input_schema,
                "function": decorated_tool,
            }

            logger.debug(f"Generated MCP tool: {tool_name} -> tmux-orc {full_command}")

        except Exception as e:
            logger.error(f"Failed to register subcommand tool {tool_name}: {e}")

    def _create_subcommand_tool_function(self, full_command: str, command_info: dict[str, Any]):
        """Create the actual function that executes a subcommand."""

        async def tool_function(**kwargs) -> dict[str, Any]:
            """Dynamically generated MCP tool function for subcommand."""
            try:
                logger.info(f"Executing CLI subcommand: {full_command} with args: {kwargs}")

                # Convert MCP arguments to CLI format
                cli_args = self._convert_kwargs_to_cli_args(kwargs)

                # Split the full command into parts
                cmd_parts = full_command.split()

                # Execute the CLI command
                result = await self._execute_cli_subcommand(cmd_parts, cli_args)

                return {
                    "success": result.get("return_code", -1) == 0,
                    "command": full_command,
                    "arguments": kwargs,
                    "result": result.get("parsed_output", {}),
                    "raw_output": result.get("stdout", ""),
                    "execution_time": result.get("execution_time", 0),
                    "mcp_tool": f"cli_{full_command.replace(' ', '_').replace('-', '_')}",
                }

            except Exception as e:
                logger.error(f"CLI subcommand execution failed: {e}")
                return {
                    "success": False,
                    "command": full_command,
                    "arguments": kwargs,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "mcp_tool": f"cli_{full_command.replace(' ', '_').replace('-', '_')}",
                }

        # Set function metadata
        tool_function.__name__ = f"cli_{full_command.replace(' ', '_').replace('-', '_')}"
        tool_function.__doc__ = command_info.get("help", f"Execute tmux-orc {full_command}")

        return tool_function

    async def _execute_cli_subcommand(self, cmd_parts: list[str], cli_args: list[str]) -> dict[str, Any]:
        """Execute CLI subcommand and return structured result."""
        start_time = time.time()

        try:
            # Build complete command
            full_cmd_parts = ["tmux-orc"] + cmd_parts + cli_args

            # Add --json flag if command supports it and not already present
            if "--json" not in cli_args and self._command_supports_json(" ".join(cmd_parts)):
                full_cmd_parts.append("--json")

            # Execute command
            result = subprocess.run(
                full_cmd_parts,
                capture_output=True,
                text=True,
                timeout=60,  # 60 second timeout
            )

            execution_time = time.time() - start_time

            # Parse JSON output if available
            parsed_output = {}
            if result.stdout:
                try:
                    parsed_output = json.loads(result.stdout)
                except json.JSONDecodeError:
                    parsed_output = {"output": result.stdout}

            return {
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "execution_time": execution_time,
                "parsed_output": parsed_output,
                "command_line": " ".join(full_cmd_parts),
            }

        except subprocess.TimeoutExpired:
            return {
                "return_code": -1,
                "error": "Command timed out after 60 seconds",
                "execution_time": time.time() - start_time,
            }
        except Exception as e:
            return {"return_code": -1, "error": str(e), "execution_time": time.time() - start_time}

    def _create_tool_function(self, command_name: str, command_info: dict[str, Any]):
        """Create the actual function that executes the CLI command."""

        async def tool_function(**kwargs) -> dict[str, Any]:
            """Dynamically generated MCP tool function."""
            try:
                logger.info(f"Executing CLI command: {command_name} with args: {kwargs}")

                # Convert MCP arguments to CLI format
                cli_args = self._convert_kwargs_to_cli_args(kwargs)

                # Execute the CLI command
                result = await self._execute_cli_command(command_name, cli_args)

                return {
                    "success": result.get("return_code", -1) == 0,
                    "command": command_name,
                    "arguments": kwargs,
                    "result": result.get("parsed_output", {}),
                    "raw_output": result.get("stdout", ""),
                    "execution_time": result.get("execution_time", 0),
                    "mcp_tool": f"cli_{command_name.replace('-', '_')}",
                }

            except Exception as e:
                logger.error(f"CLI command execution failed: {e}")
                return {
                    "success": False,
                    "command": command_name,
                    "arguments": kwargs,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "mcp_tool": f"cli_{command_name.replace('-', '_')}",
                }

        # Set function metadata
        tool_function.__name__ = f"cli_{command_name.replace('-', '_')}"
        tool_function.__doc__ = command_info.get("help", f"Execute tmux-orc {command_name}")

        return tool_function

    def _convert_kwargs_to_cli_args(self, kwargs: dict[str, Any]) -> list[str]:
        """Convert MCP keyword arguments to CLI arguments."""
        cli_args = []

        # Handle positional arguments from args array
        args = kwargs.get("args", [])
        if args:
            cli_args.extend(str(arg) for arg in args)

        # Handle options from options dict
        options = kwargs.get("options", {})
        for option_name, option_value in options.items():
            if option_value is True:
                # Boolean flag
                cli_args.append(f"--{option_name}")
            elif option_value is not False and option_value is not None:
                # Option with value
                cli_args.extend([f"--{option_name}", str(option_value)])

        # Also handle any direct keyword arguments (legacy support)
        for key, value in kwargs.items():
            if key not in ["args", "options"] and value is not None:
                if value is True:
                    cli_args.append(f"--{key}")
                elif value is not False:
                    cli_args.extend([f"--{key}", str(value)])

        return cli_args

    async def _execute_cli_command(self, command_name: str, cli_args: list[str]) -> dict[str, Any]:
        """Execute CLI command and return structured result."""
        start_time = time.time()

        try:
            # Build complete command
            cmd_parts = ["tmux-orc", command_name] + cli_args

            # Add --json flag if command supports it and not already present
            if "--json" not in cli_args and self._command_supports_json(command_name):
                cmd_parts.append("--json")

            # Execute command
            result = subprocess.run(
                cmd_parts,
                capture_output=True,
                text=True,
                timeout=60,  # 60 second timeout
            )

            execution_time = time.time() - start_time

            # Parse JSON output if available
            parsed_output = {}
            if result.stdout:
                try:
                    parsed_output = json.loads(result.stdout)
                except json.JSONDecodeError:
                    parsed_output = {"output": result.stdout}

            return {
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "execution_time": execution_time,
                "parsed_output": parsed_output,
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

    def _command_supports_json(self, command_name: str) -> bool:
        """Check if a command supports JSON output."""
        # Commands known to support --json flag
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
            "get-status",
            "agent-info",
        }
        return command_name in json_commands

    async def run_server(self):
        """Run the MCP server with auto-generated tools."""
        logger.info("Starting fresh CLI reflection MCP server...")

        # Discover CLI structure
        await self.discover_cli_structure()

        # Generate all tools
        self.generate_all_mcp_tools()

        if not self.generated_tools:
            logger.error("No tools generated! Check CLI availability and permissions")
            return

        # Log generated tools
        logger.info("Generated MCP Tools:")
        for tool_name in sorted(self.generated_tools.keys()):
            cmd_name = self.generated_tools[tool_name]["command_name"]
            logger.info(f"  • {tool_name} → tmux-orc {cmd_name}")

        # Start the server
        logger.info("Starting FastMCP server...")
        await self.mcp.run_stdio_async()


async def main():
    """Main entry point for the fresh MCP server."""
    try:
        # Check if tmux-orc is available
        result = subprocess.run(["tmux-orc", "--version"], capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            logger.error("tmux-orc command not available! Please ensure tmux-orchestrator is installed.")
            sys.exit(1)

        logger.info(f"Found tmux-orc: {result.stdout.strip()}")

        # Create and run the fresh MCP server
        server = FreshCLIToMCPServer("tmux-orchestrator-fresh")
        await server.run_server()

    except KeyboardInterrupt:
        logger.info("MCP server stopped by user")
    except Exception as e:
        logger.error(f"MCP server failed: {e}")
        sys.exit(1)


def sync_main():
    """Synchronous entry point for script execution."""
    asyncio.run(main())


if __name__ == "__main__":
    sync_main()

#!/usr/bin/env python3
"""
MCP Auto-Generation System for CLI Commands

This module implements the CLI parsing system that extracts <mcp>...</mcp> tags from CLI command docstrings
to automatically generate MCP tool descriptions, replacing the manual COMPLETE_ACTION_DESCRIPTIONS.
"""

import argparse
import importlib
import inspect
import json
import logging
import re
import subprocess
from typing import Any, Dict, List, Optional, cast

logger = logging.getLogger(__name__)


class MCPTagParser:
    """Parser for extracting <mcp>...</mcp> tags from docstrings."""

    MCP_TAG_PATTERN = re.compile(r"<mcp>(.*?)</mcp>", re.DOTALL | re.IGNORECASE)

    @classmethod
    def extract_mcp_description(cls, docstring: str) -> Optional[str]:
        """Extract MCP description from docstring.

        Args:
            docstring: The docstring to parse

        Returns:
            The extracted MCP description or None if no tag found
        """
        if not docstring:
            return None

        # Look for <mcp>...</mcp> tags
        matches = cls.MCP_TAG_PATTERN.findall(docstring)
        if matches:
            # Return the first match, stripped and cleaned
            description = matches[0].strip()
            # Clean up whitespace but preserve line breaks
            description = re.sub(r"\s+", " ", description)
            # Update terminology: orchestrator -> orc for consistency
            description = re.sub(r"\borchestrator\b", "orc", description, flags=re.IGNORECASE)

            return cast(str, description)

        return None

    @classmethod
    def fallback_to_cli_help(cls, docstring: str) -> Optional[str]:
        """Extract enhanced description from CLI help text (pure CLI sourcing).

        Args:
            docstring: The docstring to parse

        Returns:
            Enhanced description extracted from CLI docstring
        """
        if not docstring:
            return None

        # Get first meaningful line
        lines = [line.strip() for line in docstring.split("\n") if line.strip()]
        if not lines:
            return None

        first_line = lines[0]

        # Enhanced CLI help parsing for better descriptions
        # Remove common CLI prefixes but preserve action intent
        first_line = re.sub(r"^(Execute|Run|Show|Display|List|Create|Start|Stop)\s+", "", first_line)
        first_line = first_line.strip(".")

        # Look for additional context in following lines for better descriptions
        additional_context = ""
        for line in lines[1:4]:  # Check next 3 lines for context
            if any(keyword in line.lower() for keyword in ["agent", "session", "target", "requires", "args"]):
                # Extract useful context
                if "requires:" in line.lower():
                    context_match = re.search(r"requires?:?\s*([^.]+)", line, re.IGNORECASE)
                    if context_match:
                        additional_context = f" (requires: {context_match.group(1).strip()})"
                        break
                elif "args:" in line.lower() or "arguments:" in line.lower():
                    context_match = re.search(r"args?:?\s*([^.]+)", line, re.IGNORECASE)
                    if context_match:
                        additional_context = f" (args: {context_match.group(1).strip()})"
                        break

        # Apply terminology normalization
        result = first_line + additional_context
        result = re.sub(r"\borchestrator\b", "orc", result, flags=re.IGNORECASE)

        return result if result != first_line else first_line


class CLICommandIntrospector:
    """Introspects CLI command modules to extract command metadata."""

    # Module name mappings for commands that don't match file names
    MODULE_NAME_MAPPINGS = {
        "setup": "setup_claude",
        "spawn-orc": "spawn_orc",
    }

    def __init__(self, cli_package: str = "tmux_orchestrator.cli"):
        """Initialize the introspector.

        Args:
            cli_package: The CLI package to introspect
        """
        self.cli_package = cli_package
        self.parser = MCPTagParser()

    def discover_cli_commands(self) -> Dict[str, Any]:
        """Discover all CLI commands using tmux-orc reflect.

        Returns:
            Dictionary of command metadata
        """
        try:
            result = subprocess.run(
                ["tmux-orc", "reflect", "--format", "json"], capture_output=True, text=True, timeout=30
            )

            if result.returncode != 0:
                logger.error(f"CLI reflection failed: {result.stderr}")
                return {}

            parsed_result: Dict[str, Any] = json.loads(result.stdout)
            return parsed_result

        except Exception as e:
            logger.error(f"Failed to discover CLI commands: {e}")
            return {}

    def extract_command_docstrings(self, command_name: str) -> Dict[str, str | None]:
        """Extract docstrings for command and subcommands.

        Args:
            command_name: Name of the command group

        Returns:
            Dictionary mapping subcommand names to their docstrings
        """
        try:
            # Get the actual module name (handle mappings for mismatched names)
            actual_module_name = self.MODULE_NAME_MAPPINGS.get(command_name, command_name)
            module_name = f"{self.cli_package}.{actual_module_name}"
            module = importlib.import_module(module_name)

            docstrings: Dict[str, str | None] = {}

            # Find Click command functions - Check both __click_params__ and callable with decorators
            for name, obj in inspect.getmembers(module):
                if (
                    hasattr(obj, "__click_params__")  # Standard Click command detection
                    or (callable(obj) and hasattr(obj, "__wrapped__"))  # Decorated functions
                    or (callable(obj) and name != "click" and not name.startswith("_"))
                ):  # Other callables
                    docstring = inspect.getdoc(obj)
                    if docstring and name != command_name:  # Exclude the main group function
                        docstrings[name] = docstring
                        logger.debug(f"Found docstring for {command_name}.{name}: {len(docstring)} chars")

            return docstrings

        except ImportError as e:
            logger.warning(f"Could not import module {command_name}: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error extracting docstrings for {command_name}: {e}")
            return {}

    def generate_mcp_descriptions(self) -> Dict[str, Dict[str, str]]:
        """Generate MCP descriptions by parsing CLI commands.

        Returns:
            Dictionary in the same format as COMPLETE_ACTION_DESCRIPTIONS
        """
        cli_structure = self.discover_cli_commands()
        mcp_descriptions = {}

        for command_name, command_info in cli_structure.items():
            if not isinstance(command_info, dict) or command_info.get("type") != "group":
                continue

            logger.info(f"Processing command group: {command_name}")

            # Get subcommands for this group
            subcommands = self._get_subcommands(command_name)
            if not subcommands:
                continue

            # Extract docstrings from the CLI module
            docstrings = self.extract_command_docstrings(command_name)

            group_descriptions = {}

            for subcmd in subcommands:
                # Look for MCP description in docstring
                docstring = docstrings.get(subcmd)
                if docstring is not None:
                    mcp_desc = self.parser.extract_mcp_description(docstring)
                else:
                    mcp_desc = None

                if mcp_desc:
                    group_descriptions[subcmd] = mcp_desc
                    logger.debug(f"Found MCP tag for {command_name}.{subcmd}")
                else:
                    # Fallback to CLI help
                    if docstring is not None:
                        fallback_desc = self.parser.fallback_to_cli_help(docstring)
                    else:
                        fallback_desc = None
                    if fallback_desc:
                        group_descriptions[subcmd] = fallback_desc
                        logger.debug(f"Using fallback description for {command_name}.{subcmd}")
                    else:
                        # Last resort: generic description
                        group_descriptions[subcmd] = f"Execute {subcmd} operation"
                        logger.debug(f"Using generic description for {command_name}.{subcmd}")

            if group_descriptions:
                mcp_descriptions[command_name] = group_descriptions

        return mcp_descriptions

    def _get_subcommands(self, group_name: str) -> List[str]:
        """Get subcommands for a command group.

        Args:
            group_name: Name of the command group

        Returns:
            List of subcommand names
        """
        try:
            result = subprocess.run(["tmux-orc", group_name, "--help"], capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                return []

            return self._parse_subcommands_from_help(result.stdout)

        except Exception as e:
            logger.error(f"Failed to get subcommands for {group_name}: {e}")
            return []

    def _parse_subcommands_from_help(self, help_text: str) -> List[str]:
        """Parse subcommand names from CLI help output.

        Args:
            help_text: Raw help text from CLI

        Returns:
            List of subcommand names
        """
        subcommands = []
        in_commands_section = False

        for line in help_text.split("\n"):
            # Check for Commands: section
            if line.strip().lower() == "commands:":
                in_commands_section = True
                continue

            # Stop when we hit another section
            if in_commands_section and line.strip().startswith("Options:"):
                break

            # Extract command names (format: "  command_name  Description...")
            if in_commands_section and line.startswith("  ") and not line.startswith("    "):
                parts = line[2:].split()
                if parts:
                    cmd_name = parts[0]
                    if cmd_name and not cmd_name.startswith("-"):
                        subcommands.append(cmd_name)

        return subcommands


class MCPAutoGenerator:
    """Main class for auto-generating MCP descriptions from CLI commands."""

    def __init__(self):
        """Initialize the auto-generator."""
        self.introspector = CLICommandIntrospector()

    def generate_action_descriptions(self) -> Dict[str, Dict[str, str]]:
        """Generate action descriptions using PURE CLI sourcing only.

        Sources descriptions from:
        1. <mcp>...</mcp> tags in CLI command docstrings (preferred)
        2. Direct CLI help text parsing (fallback)

        NO hardcoded descriptions allowed.

        Returns:
            Dictionary of pure CLI-sourced MCP descriptions
        """
        logger.info("Starting PURE CLI-sourced MCP auto-generation...")

        # Generate descriptions from CLI introspection ONLY
        final_descriptions = self.introspector.generate_mcp_descriptions()

        logger.info(f"Generated PURE CLI-sourced descriptions for {len(final_descriptions)} command groups")

        typed_descriptions: Dict[str, Dict[str, str]] = final_descriptions
        return typed_descriptions


def main():
    """CLI entry point for testing the auto-generator."""
    parser = argparse.ArgumentParser(description="Test MCP auto-generation system")
    parser.add_argument("--output", help="Output file for generated descriptions")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    generator = MCPAutoGenerator()
    descriptions = generator.generate_action_descriptions()

    if args.output:
        with open(args.output, "w") as f:
            json.dump(descriptions, f, indent=2)
        print(f"Generated descriptions written to {args.output}")
    else:
        print(json.dumps(descriptions, indent=2))


if __name__ == "__main__":
    main()

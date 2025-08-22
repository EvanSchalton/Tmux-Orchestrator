"""MCP command group for Claude Code CLI integration."""

import asyncio
import logging
import sys

import click
from rich.console import Console

console = Console()
logger = logging.getLogger(__name__)


@click.group()
def mcp():
    """MCP protocol management for Claude Code CLI integration."""
    pass


@mcp.command()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--test", is_flag=True, help="Run in test mode with sample output")
def serve(verbose, test):
    """Start MCP server for Claude Code CLI integration.

    This command is designed for Claude Code CLI registration and will be
    executed when Claude Code needs MCP tools.

    Runs in stdio mode: reads from stdin, writes to stdout.
    """
    # Configure logging to stderr only (stdout is for MCP protocol)
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )

    if test:
        # Test mode for verification
        click.echo('{"status": "ready", "tools": ["list", "spawn", "status"], "mode": "claude_code_cli"}')
        return

    try:
        # Import here to avoid circular imports
        # Set environment to indicate Claude Code CLI mode
        import os

        from tmux_orchestrator.mcp_server import main

        os.environ["TMUX_ORC_MCP_MODE"] = "claude_code"

        # Run the server
        asyncio.run(main())

    except KeyboardInterrupt:
        logger.info("MCP server stopped by user")
    except Exception as e:
        logger.error(f"MCP server failed: {e}", exc_info=True)
        sys.exit(1)


# Export for CLI registration
__all__ = ["mcp"]

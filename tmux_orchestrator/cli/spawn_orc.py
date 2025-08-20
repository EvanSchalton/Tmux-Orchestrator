"""Spawn orchestrator command - entry point for human interaction.

This command is now available as 'tmux-orc spawn orc' for consistency
with other spawn commands. The implementation remains here as a module
that can be imported by the spawn command group.
"""

import json
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

import click
from rich.console import Console

console = Console()


@click.command()
@click.option("--profile", help="Claude Code profile to use (defaults to system default)")
@click.option(
    "--terminal", default="auto", help="Terminal to use: auto, gnome-terminal, konsole, xterm, screen, tmux, etc."
)
@click.option("--no-launch", is_flag=True, help="Create config but don't launch terminal")
@click.option("--no-gui", is_flag=True, help="Run in current terminal (for SSH/bash environments)")
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format")
def spawn_orc(profile: str | None, terminal: str, no_launch: bool, no_gui: bool, output_json: bool) -> None:
    """Launch Claude Code as an orchestrator in a new terminal.

    This is the primary entry point for humans to start working with tmux-orchestrator.
    It will:
    1. Create a new terminal window
    2. Launch Claude Code with the --dangerously-skip-permissions flag
    3. Automatically load the orchestrator context

    After launching, you'll be ready to create feature requests and use /create-prd
    to generate PRDs that will spawn autonomous agent teams.
    """

    # Validate profile parameter to prevent injection
    if profile:
        if not re.match(r"^[a-zA-Z0-9_-]+$", profile):
            console.print(
                "[red]Error: Invalid profile name. Profile must contain only alphanumeric characters, hyphens, and underscores.[/red]"
            )
            raise click.BadParameter("Profile name contains invalid characters")
        if len(profile) > 50:
            console.print("[red]Error: Profile name too long (max 50 characters).[/red]")
            raise click.BadParameter("Profile name too long")

    # Build Claude command
    claude_cmd = ["claude"]
    if profile:
        claude_cmd.extend(["--profile", profile])
    claude_cmd.append("--dangerously-skip-permissions")

    # Create startup script that will run in the new terminal
    startup_script = f"""#!/bin/bash
# Tmux Orchestrator Startup Script

echo "🚀 Starting Claude Code as Orchestrator..."
echo ""
echo "This will launch Claude Code with autonomous permissions."
echo "Claude will be instructed to load the orchestrator context."
echo ""
echo "Starting in 3 seconds..."
sleep 3

# Create initial instruction file
INSTRUCTION_FILE=$(mktemp /tmp/orc-instruction-XXXXXX.md)
cat > "$INSTRUCTION_FILE" << 'EOF'
Welcome! You are being launched as the Tmux Orchestrator.

Please run the following command to load your orchestrator context:

tmux-orc context show orchestrator

This will provide you with your role, responsibilities, and workflow for managing AI agent teams.
EOF

# Launch Claude with the instruction
{shlex.join(claude_cmd)} "$INSTRUCTION_FILE"

# Clean up
rm -f "$INSTRUCTION_FILE"

# Self-delete this startup script
rm -f "$0"
"""

    # Write temporary startup script
    script_path = Path("/tmp/tmux-orc-startup.sh")
    script_path.write_text(startup_script)
    script_path.chmod(0o755)

    if no_launch:
        if output_json:
            result = {
                "success": True,
                "data": {
                    "script_path": str(script_path),
                    "profile": profile,
                    "terminal": terminal,
                    "launch_command": str(script_path),
                    "instructions": ["Script created successfully", f"To launch manually, run: {script_path}"],
                },
                "timestamp": time.time(),
                "command": "spawn-orc",
            }
            console.print(json.dumps(result, indent=2))
        else:
            console.print("[green]Startup script created at:[/green]", script_path)
            console.print("\n[yellow]To launch manually, run:[/yellow]")
            console.print(f"  {script_path}")
        return

    # Handle non-GUI mode
    if no_gui:
        if not output_json:
            console.print("[green]Running orchestrator in current terminal...[/green]")
            console.print("[dim]Starting in 3 seconds...[/dim]")
            time.sleep(3)

        # Run claude directly without temp file
        instruction = """Welcome! You are being launched as the Tmux Orchestrator.

Please run the following command to load your orchestrator context:

tmux-orc context show orchestrator

This will provide you with your role, responsibilities, and workflow for managing AI agent teams."""

        try:
            # Launch Claude and send instruction via stdin
            process = subprocess.Popen(claude_cmd, stdin=subprocess.PIPE, text=True)
            process.communicate(input=instruction)

            if output_json:
                result = {
                    "success": True,
                    "data": {
                        "mode": "no-gui",
                        "profile": profile,
                        "instructions_sent": True,
                        "message": "Orchestrator launched in current terminal",
                    },
                    "timestamp": time.time(),
                    "command": "spawn-orc",
                }
                console.print(json.dumps(result, indent=2))

        except subprocess.CalledProcessError as e:
            if output_json:
                result = {
                    "success": False,
                    "error": str(e),
                    "error_type": "CalledProcessError",
                    "timestamp": time.time(),
                    "command": "spawn-orc",
                }
                console.print(json.dumps(result, indent=2))
            else:
                console.print(f"[red]Error running orchestrator: {e}[/red]")
            sys.exit(1)
        except KeyboardInterrupt:
            if not output_json:
                console.print("\n[yellow]Orchestrator session interrupted[/yellow]")
        return

    # Detect terminal emulator for GUI mode
    terminal_cmd = _get_terminal_command(terminal, str(script_path))

    if not terminal_cmd:
        if output_json:
            result = {
                "success": False,
                "error": "Could not detect terminal emulator",
                "error_type": "TerminalDetectionError",
                "suggestions": [
                    "Use --no-gui flag to run in current terminal (SSH/bash)",
                    "Specify --terminal explicitly (gnome-terminal, konsole, xterm, etc.)",
                    "Use --no-launch to create script and run manually",
                ],
                "timestamp": time.time(),
                "command": "spawn-orc",
            }
            console.print(json.dumps(result, indent=2))
        else:
            console.print("[red]Error: Could not detect terminal emulator[/red]")
            console.print("[yellow]Try one of these options:[/yellow]")
            console.print("  - Use --no-gui flag to run in current terminal (SSH/bash)")
            console.print("  - Specify --terminal explicitly (gnome-terminal, konsole, xterm, etc.)")
            console.print("  - Use --no-launch to create script and run manually")
        sys.exit(1)

    # Launch terminal
    try:
        if not output_json:
            console.print(f"[green]Launching orchestrator in new {terminal} window...[/green]")
        subprocess.Popen(terminal_cmd, start_new_session=True)

        if output_json:
            result = {
                "success": True,
                "data": {
                    "terminal": terminal,
                    "profile": profile,
                    "script_path": str(script_path),
                    "terminal_command": terminal_cmd,
                    "workflow_steps": [
                        "Create a feature request: planning/feature-xyz.md",
                        "Use Claude's /create-prd command with the file",
                        "Answer the PRD survey questions",
                        "The orchestrator will spawn a PM with the PRD",
                        "The PM will use /generate-tasks to create task list",
                        "The PM will spawn the team and begin work",
                    ],
                    "message": "Orchestrator terminal launched successfully",
                },
                "timestamp": time.time(),
                "command": "spawn-orc",
            }
            console.print(json.dumps(result, indent=2))
        else:
            # Give helpful instructions
            console.print("\n[bold cyan]🎉 Orchestrator terminal launched![/bold cyan]\n")
            console.print("In the new terminal window:")
            console.print("1. Claude Code will start with autonomous permissions")
            console.print("2. The orchestrator context will be automatically loaded")
            console.print("3. You'll be ready to manage AI agent teams")
            console.print("\n[yellow]Typical orchestrator workflow:[/yellow]")
            console.print("1. Create a feature request: `planning/feature-xyz.md`")
            console.print("2. Use Claude's `/create-prd` command with the file")
            console.print("3. Answer the PRD survey questions")
            console.print("4. The orchestrator will spawn a PM with the PRD")
            console.print("5. The PM will use `/generate-tasks` to create task list")
            console.print("6. The PM will spawn the team and begin work")

        # Note: The script self-deletes after execution, so no cleanup needed here

    except Exception as e:
        if output_json:
            result = {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "manual_instructions": ["Open a new terminal", f"Run: {script_path}", "OR use: spawn-orc --no-gui"],
                "timestamp": time.time(),
                "command": "spawn-orc",
            }
            console.print(json.dumps(result, indent=2))
        else:
            console.print(f"[red]Error launching terminal: {e}[/red]")
            console.print("\n[yellow]Manual launch instructions:[/yellow]")
            console.print("1. Open a new terminal")
            console.print(f"2. Run: {script_path}")
            console.print("   OR use: spawn-orc --no-gui")
        sys.exit(1)


def _get_terminal_command(terminal: str, script_path: str) -> list[str] | None:
    """Get the command to launch a terminal with our script.

    Args:
        terminal: Terminal name or "auto" for auto-detection
        script_path: Path to the startup script

    Returns:
        Command list to launch terminal, or None if not found
    """
    # Terminal commands that execute our script
    terminal_commands = {
        "gnome-terminal": ["gnome-terminal", "--", script_path],
        "konsole": ["konsole", "-e", script_path],
        "xfce4-terminal": ["xfce4-terminal", "-e", script_path],
        "mate-terminal": ["mate-terminal", "-e", script_path],
        "terminator": ["terminator", "-e", script_path],
        "kitty": ["kitty", script_path],
        "alacritty": ["alacritty", "-e", script_path],
        "xterm": ["xterm", "-e", script_path],
        "urxvt": ["urxvt", "-e", script_path],
        "st": ["st", "-e", script_path],
        # macOS
        "iterm2": ["open", "-a", "iTerm", script_path],
        "terminal": ["open", "-a", "Terminal", script_path],
    }

    if terminal != "auto":
        # User specified a terminal
        if terminal in terminal_commands:
            return terminal_commands[terminal]
        else:
            # Try generic command - sanitize terminal parameter
            # Validate terminal name to prevent injection
            if not terminal.replace("-", "").replace("_", "").isalnum():
                console.print(f"[red]Invalid terminal name: {terminal}[/red]")
                return None
            return [terminal, "-e", script_path]

    # Auto-detect terminal
    # First check if we're on macOS
    if sys.platform == "darwin":
        # Try iTerm2 first, then Terminal
        for term in ["iterm2", "terminal"]:
            if _command_exists(term.split()[0]):
                return terminal_commands[term]

    # Check common Linux terminals in order of preference
    for term in [
        "gnome-terminal",
        "konsole",
        "xfce4-terminal",
        "kitty",
        "alacritty",
        "mate-terminal",
        "terminator",
        "xterm",
    ]:
        if _command_exists(term):
            return terminal_commands[term]

    return None


def _command_exists(command: str) -> bool:
    """Check if a command exists in PATH."""
    try:
        subprocess.run(["which", command], capture_output=True, check=True)
        return True
    except subprocess.CalledProcessError:
        return False


if __name__ == "__main__":
    spawn_orc()

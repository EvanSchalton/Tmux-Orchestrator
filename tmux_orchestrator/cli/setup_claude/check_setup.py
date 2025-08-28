"""Check current setup status and configurations."""

import json
from pathlib import Path

from rich.console import Console
from rich.table import Table

console = Console()


def check_setup() -> None:
    """Check current setup status and configurations.

    Verifies:
    - Claude Code installation and configuration
    - VS Code tasks configuration
    - MCP server availability
    - Slash command installation

    Examples:
        tmux-orc setup check
    """
    console.print("[bold]Checking Tmux Orchestrator Setup[/bold]\n")

    checks = {
        "Claude Code Directory": False,
        "Slash Commands": False,
        "MCP Configuration": False,
        "MCP Server Running": False,
        "VS Code Tasks": False,
        "Claude Instructions": False,
        "Task Management Dir": False,
    }

    # Check Claude Code - auto-detect location
    project_claude = Path.cwd() / ".claude"
    home_claude = Path.home() / ".claude"

    if project_claude.exists():
        claude_dir = project_claude
    elif home_claude.exists():
        claude_dir = home_claude
    else:
        claude_dir = None

    if claude_dir and claude_dir.exists():
        checks["Claude Code Directory"] = True

        # Check slash commands
        commands_dir = claude_dir / "commands"
        if commands_dir.exists() and list(commands_dir.glob("*.md")):
            checks["Slash Commands"] = True

        # Check MCP config
        mcp_config = claude_dir / "config" / "mcp.json"
        if mcp_config.exists():
            with open(mcp_config) as f:
                config = json.load(f)
                if "tmux-orchestrator" in config.get("servers", {}):
                    checks["MCP Configuration"] = True

    # Check VS Code
    vscode_tasks = Path.cwd() / ".vscode" / "tasks.json"
    if vscode_tasks.exists():
        checks["VS Code Tasks"] = True

    # Check Claude instructions
    if claude_dir:
        claude_md = claude_dir / "CLAUDE.md"
        if claude_md.exists():
            checks["Claude Instructions"] = True

    # Check task management
    task_dir = Path.home() / "workspaces" / "Tmux-Orchestrator" / ".tmux_orchestrator"
    if task_dir.exists():
        checks["Task Management Dir"] = True

    # Check MCP server
    try:
        import requests  # type: ignore[import-untyped]

        response = requests.get("http://127.0.0.1:8000/health", timeout=1)
        if response.status_code == 200:
            checks["MCP Server Running"] = True
    except Exception:
        pass

    # Display results
    table = Table(title="Setup Status")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Location", style="blue")

    for component, status in checks.items():
        status_icon = "✓" if status else "✗"
        status_color = "green" if status else "red"

        location = ""
        if component == "Claude Code Directory":
            location = str(claude_dir) if claude_dir else "Not found"
        elif component == "Slash Commands":
            location = str(commands_dir) if "commands_dir" in locals() else "Not found"
        elif component == "MCP Configuration":
            location = str(mcp_config) if "mcp_config" in locals() else "Not found"
        elif component == "VS Code Tasks":
            location = str(vscode_tasks)
        elif component == "Claude Instructions":
            location = str(claude_dir / "CLAUDE.md") if claude_dir else "Not found"
        elif component == "Task Management Dir":
            location = str(task_dir)

        table.add_row(component, f"[{status_color}]{status_icon}[/{status_color}]", location)

    console.print(table)

    # Provide guidance
    missing = [k for k, v in checks.items() if not v]
    if missing:
        console.print("\n[yellow]Missing components:[/yellow]")
        if "Claude Code Directory" in missing:
            console.print("• Install Claude Code and run it once")
        if "Slash Commands" in missing or "MCP Configuration" in missing:
            console.print("• Run: tmux-orc setup claude-code")
        if "VS Code Tasks" in missing:
            console.print("• Run: tmux-orc setup vscode")
        if "Claude Instructions" in missing:
            console.print("• Run: tmux-orc setup claude-code --force")
    else:
        console.print("\n[green]✓ All components properly configured![/green]")

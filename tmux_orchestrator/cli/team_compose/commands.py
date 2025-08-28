"""CLI commands for team composition functionality."""

from pathlib import Path
from typing import Any

import click
import yaml
from rich.console import Console
from rich.table import Table

from .composer import generate_team_composition, interactive_team_composition, suggest_team_composition
from .deployer import deploy_team, show_team_status
from .template_manager import get_default_team_template, load_agent_templates, load_team_template
from .validators import validate_prd_path, validate_project_name

console = Console()


@click.group()
def team() -> None:
    """Team composition and deployment commands.

    Compose teams of specialized agents for complex projects.
    Create team composition documents with role assignments,
    custom briefings, and deployment instructions.
    """
    pass


@team.command()
@click.argument("project_name")
@click.option("--prd", help="Path to Project Requirements Document")
@click.option("--template", help="Use a predefined team template", default=None)
@click.option("--interactive", is_flag=True, help="Interactive team composition mode")
@click.option("--output", "-o", help="Output file path", default=None)
def compose(project_name: str, prd: str | None, template: str | None, interactive: bool, output: str | None) -> None:
    """Compose a team for a project.

    PROJECT_NAME: Name of the project to compose team for

    Creates a team composition document with agent roles, responsibilities,
    and deployment commands. The document serves as the blueprint for
    spawning a coordinated team of agents.

    Examples:
        tmux-orc team compose my-api-project --interactive
        tmux-orc team compose cli-tool --template api-heavy
        tmux-orc team compose web-app --prd requirements.md
    """
    # SECURITY: Validate inputs
    if not validate_project_name(project_name):
        console.print("[red]Invalid project name. Must not contain path separators or '..'[/red]")
        return

    if prd:
        prd_valid, prd_path = validate_prd_path(prd)
        if not prd_valid:
            console.print(f"[red]PRD file not found or invalid: {prd}[/red]")
            console.print("Supported formats: .md, .txt, .rst")
            return
        prd = str(prd_path) if prd_path else None

    # Create project directory
    project_dir = Path.home() / "workspaces" / "Tmux-Orchestrator" / ".tmux_orchestrator" / "projects" / project_name
    project_dir.mkdir(parents=True, exist_ok=True)

    # Determine output path
    if output:
        output_path = Path(output)
    else:
        output_path = project_dir / "team-composition.md"

    console.print(f"[blue]Composing team for: {project_name}[/blue]")

    # Load available templates
    templates = load_agent_templates()
    if not templates:
        console.print("[yellow]Warning: No agent templates found. Limited composition options.[/yellow]")

    agents: list[dict[str, Any]] = []

    if template:
        # Use predefined team template
        console.print(f"[cyan]Using team template: {template}[/cyan]")
        agents = load_team_template(template)
        if not agents:
            console.print(f"[red]Template '{template}' not found[/red]")
            return
    elif interactive:
        # Interactive composition
        agents = interactive_team_composition(templates)
    else:
        # Suggested composition
        agents = suggest_team_composition(project_name, prd, templates)

    if not agents:
        console.print("[red]No agents selected. Team composition cancelled.[/red]")
        return

    console.print(f"\n[green]Selected {len(agents)} team members:[/green]")
    for i, agent in enumerate(agents):
        console.print(f"  {i + 1}. {agent['role']} (Window {agent['window']}) - {agent['focus']}")

    # Load template content
    try:
        from .template_manager import TEAM_TEMPLATE

        if TEAM_TEMPLATE.exists():
            team_template_content = TEAM_TEMPLATE.read_text()
        else:
            team_template_content = get_default_team_template()
    except Exception:
        team_template_content = get_default_team_template()

    # Generate composition document
    generate_team_composition(project_name, agents, output_path, prd, team_template_content)

    console.print(f"\n[green]✓ Team composition created: {output_path}[/green]")
    console.print("\nNext steps:")
    console.print("1. Review the team composition document")
    console.print(f"2. Deploy the team: tmux-orc team deploy {project_name}")
    console.print(f"3. Monitor team status: tmux-orc team status {project_name}")


@team.command()
def list_templates() -> None:
    """List available agent templates.

    Shows all agent templates that can be used for team composition,
    including their roles, specializations, and key skills.

    Examples:
        tmux-orc team list-templates
    """
    from .template_manager import TEMPLATES_DIR

    if not TEMPLATES_DIR.exists():
        console.print("[yellow]No agent templates directory found[/yellow]")
        return

    templates = list(TEMPLATES_DIR.glob("*.yaml"))
    if not templates:
        console.print("[yellow]No agent templates found[/yellow]")
        return

    console.print("[bold]Available Agent Templates[/bold]\n")

    table = Table()
    table.add_column("Template", style="cyan")
    table.add_column("Role", style="green")
    table.add_column("Specialization", style="yellow")
    table.add_column("Key Skills", style="blue")

    for template_file in sorted(templates):
        try:
            with open(template_file) as f:
                data = yaml.safe_load(f)

                skills = data.get("skills", [])
                skills_str = ", ".join(skills[:3])
                if len(skills) > 3:
                    skills_str += f" (+{len(skills) - 3} more)"

                table.add_row(
                    template_file.stem,
                    data.get("role", "Unknown"),
                    data.get("specialization", "General"),
                    skills_str,
                )
        except Exception as e:
            console.print(f"[red]Error reading {template_file.name}: {e}[/red]")

    console.print(table)
    console.print(f"\nTotal templates: {len(templates)}")
    console.print("\nUse these templates when composing teams:")
    console.print("tmux-orc team compose <project> --interactive")


@team.command()
@click.argument("project_name")
@click.option("--custom", is_flag=True, help="Use custom team composition")
def deploy(project_name: str, custom: bool) -> None:
    """Deploy a team based on composition document.

    PROJECT_NAME: Project to deploy team for

    Reads the team composition document and deploys all specified agents
    with their custom configurations.

    Examples:
        tmux-orc team deploy my-project
        tmux-orc team deploy my-project --custom
    """
    deploy_team(project_name, custom)


@team.command()
@click.argument("project_name")
def status(project_name: str) -> None:
    """Show detailed team status and health.

    PROJECT_NAME: Project team to check

    Displays comprehensive team information including:
    - Team composition and roles
    - Agent health and activity
    - Task distribution
    - Communication patterns

    Examples:
        tmux-orc team status my-project
    """
    show_team_status(project_name)

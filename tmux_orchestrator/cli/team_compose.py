"""Team composition planning commands."""

from datetime import datetime
from pathlib import Path
from typing import Optional

import click
import yaml
from rich.console import Console
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table

console = Console()

# Paths
TEMPLATES_DIR = Path.home() / "workspaces" / "Tmux-Orchestrator" / ".tmux_orchestrator" / "agent-templates"
TEAM_TEMPLATE = (
    Path.home()
    / "workspaces"
    / "Tmux-Orchestrator"
    / ".tmux_orchestrator"
    / "templates"
    / "team-composition-template.md"
)


@click.group()
def team() -> None:
    """Team management and composition commands.

    The team command group provides tools for composing custom teams
    based on project requirements, managing team deployments, and
    tracking team performance.

    Key Features:
        • Dynamic team composition based on PRD
        • Custom agent configurations
        • Team interaction modeling
        • Recovery documentation
        • Performance tracking

    Examples:
        tmux-orc team compose my-project
        tmux-orc team deploy my-project
        tmux-orc team status my-project
        tmux-orc team list-templates
    """
    pass


@team.command()
@click.argument("project_name")
@click.option("--prd", help="Path to PRD for analysis")
@click.option("--interactive", is_flag=True, help="Interactive team composition")
@click.option("--template", help="Use predefined team template")
def compose(project_name: str, prd: Optional[str], interactive: bool, template: Optional[str]) -> None:
    """Compose a custom team for the project.

    PROJECT_NAME: Name of the project

    Creates a team composition document that defines:
    - Which agents to deploy
    - Their specialized roles
    - Interaction patterns
    - Recovery information

    Examples:
        tmux-orc team compose my-project --interactive
        tmux-orc team compose my-project --prd ./prd.md
        tmux-orc team compose my-project --template api-heavy
    """
    project_dir = Path.home() / "workspaces" / "Tmux-Orchestrator" / ".tmux_orchestrator" / "projects" / project_name

    if not project_dir.exists():
        console.print(f"[red]Project '{project_name}' not found[/red]")
        console.print("Create project first: tmux-orc tasks create " + project_name)
        return

    team_comp_path = project_dir / "team-composition.md"

    if team_comp_path.exists():
        if not Confirm.ask("Team composition already exists. Overwrite?"):
            return

    console.print(f"[blue]Composing team for: {project_name}[/blue]")

    # Load available agent templates
    agent_templates = {}
    if TEMPLATES_DIR.exists():
        for template_file in TEMPLATES_DIR.glob("*.yaml"):
            with open(template_file) as f:
                data = yaml.safe_load(f)
                agent_templates[template_file.stem] = data

    if not agent_templates:
        console.print("[yellow]No agent templates found[/yellow]")
        return

    # Interactive composition
    if interactive:
        selected_agents = _interactive_team_composition(agent_templates, project_name, prd)
    elif template:
        selected_agents = _load_team_template(template)
    else:
        # Default composition based on project type
        selected_agents = _suggest_team_composition(project_name, prd, agent_templates)

    # Generate team composition document
    _generate_team_composition(project_name, selected_agents, team_comp_path, prd)

    console.print(f"[green]✓ Team composition created: {team_comp_path}[/green]")
    console.print("\nNext steps:")
    console.print("1. Review team composition: " + str(team_comp_path))
    console.print("2. Deploy team: tmux-orc team deploy " + project_name)


def _interactive_team_composition(templates: dict, project_name: str, prd: Optional[str]) -> list[dict]:
    """Interactive team composition wizard."""
    console.print("\n[bold]Interactive Team Composition[/bold]")

    # Always include PM
    selected = [
        {
            "role": "Project Manager",
            "template": "project-manager",
            "window": 0,
            "focus": "Overall project coordination and quality enforcement",
        }
    ]

    # Show available templates
    console.print("\n[bold]Available Agent Types:[/bold]")

    # Categorize templates
    categories = {
        "Development": [],
        "Quality": [],
        "Specialized": [],
        "Architecture": [],
    }

    for name, data in templates.items():
        role = data.get("role", name)
        if "developer" in name:
            categories["Development"].append((name, role))
        elif "qa" in name or "test" in name:
            categories["Quality"].append((name, role))
        elif "architect" in name or "designer" in name:
            categories["Architecture"].append((name, role))
        else:
            categories["Specialized"].append((name, role))

    # Display by category
    for category, agents in categories.items():
        if agents:
            console.print(f"\n[cyan]{category}:[/cyan]")
            for template_name, role in agents:
                console.print(f"  • {template_name}: {role}")

    # Get team size
    team_size = IntPrompt.ask("\nHow many additional agents (besides PM)?", default=4)

    # Select agents
    console.print("\n[bold]Select agents for your team:[/bold]")
    window = 1

    for i in range(team_size):
        console.print(f"\n[yellow]Agent {i + 1} of {team_size}:[/yellow]")

        template_name = Prompt.ask("Template name (or 'list' to see options again)")

        if template_name == "list":
            for name, data in templates.items():
                console.print(f"  • {name}: {data.get('role', name)}")
            template_name = Prompt.ask("Template name")

        if template_name not in templates:
            console.print(f"[red]Template '{template_name}' not found, skipping[/red]")
            continue

        # Get customization
        focus = Prompt.ask(
            f"Specific focus for this {templates[template_name]['role']}",
            default=templates[template_name].get("specialization", ""),
        )

        selected.append(
            {
                "role": templates[template_name]["role"],
                "template": template_name,
                "window": window,
                "focus": focus,
            }
        )
        window += 1

    return selected


def _suggest_team_composition(project_name: str, prd: Optional[str], templates: dict) -> list[dict]:
    """Suggest team composition based on project analysis."""
    console.print("[yellow]Suggesting team composition based on project type...[/yellow]")

    # Default balanced team
    suggested = [
        {
            "role": "Project Manager",
            "template": "project-manager",
            "window": 0,
            "focus": "Coordination and quality enforcement",
        }
    ]

    # Analyze PRD or project name for hints
    is_api = "api" in project_name.lower()
    is_cli = "cli" in project_name.lower()
    _is_fullstack = "fullstack" in project_name.lower() or "full-stack" in project_name.lower()

    window = 1

    if is_api:
        # API-focused team
        if "api-designer" in templates:
            suggested.append(
                {
                    "role": "API Designer",
                    "template": "api-designer",
                    "window": window,
                    "focus": "RESTful API design and documentation",
                }
            )
            window += 1

        for _ in range(2):
            if "backend-developer" in templates:
                suggested.append(
                    {
                        "role": "Backend Developer",
                        "template": "backend-developer",
                        "window": window,
                        "focus": "API implementation and business logic",
                    }
                )
                window += 1

    elif is_cli:
        # CLI-focused team
        for _ in range(2):
            if "cli-developer" in templates:
                suggested.append(
                    {
                        "role": "CLI Developer",
                        "template": "cli-developer",
                        "window": window,
                        "focus": "Command-line interface implementation",
                    }
                )
                window += 1

    else:
        # Default balanced team
        if "backend-developer" in templates:
            suggested.append(
                {
                    "role": "Backend Developer",
                    "template": "backend-developer",
                    "window": window,
                    "focus": "Server-side implementation",
                }
            )
            window += 1

        if "frontend-developer" in templates:
            suggested.append(
                {
                    "role": "Frontend Developer",
                    "template": "frontend-developer",
                    "window": window,
                    "focus": "User interface implementation",
                }
            )
            window += 1

    # Always add QA if available and room
    if window <= 4 and "qa-engineer" in templates:
        suggested.append(
            {
                "role": "QA Engineer",
                "template": "qa-engineer",
                "window": window,
                "focus": "Quality assurance and testing",
            }
        )
        window += 1

    # Add test automation if room
    if window <= 5 and "test-automation" in templates:
        suggested.append(
            {
                "role": "Test Engineer",
                "template": "test-automation",
                "window": window,
                "focus": "Automated test development",
            }
        )

    return suggested


def _generate_team_composition(project_name: str, agents: list[dict], output_path: Path, prd: Optional[str]) -> None:
    """Generate team composition document."""

    # Load template
    if TEAM_TEMPLATE.exists():
        template_content = TEAM_TEMPLATE.read_text()
    else:
        template_content = _get_default_team_template()

    # Format team members section with system prompts
    team_members = []
    deployment_commands = []

    for i, agent in enumerate(agents):
        # Generate system prompt for this agent
        system_prompt = _generate_system_prompt(agent, project_name)

        # Create deployment command
        deploy_cmd = (
            f'tmux-orc agent spawn {agent["template"]} {project_name}:{agent["window"]} --briefing "{system_prompt}"'
        )
        deployment_commands.append(deploy_cmd)

        member = f"""### {i + 1}. {agent["role"]}
- **Session:Window**: {project_name}:{agent["window"]}
- **Template**: {agent["template"]}.yaml
- **Primary Focus**: {agent["focus"]}
- **Key Responsibilities**:
  - See template for full responsibilities
  - Project-specific focus on {agent["focus"]}

**System Prompt**:
```
{system_prompt}
```"""
        team_members.append(member)

    # Create interaction model
    interaction_model = _generate_interaction_diagram(agents)

    # Replace placeholders
    content = template_content
    content = content.replace("{Project Name}", project_name)
    content = content.replace("{Date}", datetime.now().strftime("%Y-%m-%d %H:%M"))
    content = content.replace("{PRD Location}", str(prd) if prd else "Not specified")
    content = content.replace("{Type}", _determine_project_type(project_name, agents))

    # Add team members
    members_section = "\n\n".join(team_members)
    content = content.replace(
        "### 1. Project Manager\n- **Session:Window**: {project}:0\n- **Template**: project-manager.yaml\n- **Customizations**: {Any project-specific adjustments}\n- **Primary Focus**: {Specific PM focus for this project}\n\n### 2. {Agent Role 1}\n- **Session:Window**: {project}:1\n- **Template**: {template-name}.yaml\n- **Customizations**: {Project-specific adjustments}\n- **Primary Focus**: {What this agent will focus on}\n- **Key Responsibilities**:\n  - {Responsibility 1}\n  - {Responsibility 2}\n  - {Responsibility 3}\n\n### 3. {Agent Role 2}\n- **Session:Window**: {project}:2\n- **Template**: {template-name}.yaml\n- **Customizations**: {Project-specific adjustments}\n- **Primary Focus**: {What this agent will focus on}\n- **Key Responsibilities**:\n  - {Responsibility 1}\n  - {Responsibility 2}\n  - {Responsibility 3}\n\n{Continue for all team members...}",
        members_section,
    )

    # Add rationale
    rationale = f"This team composition was selected to provide comprehensive coverage for {project_name}. "
    rationale += f"The team includes {len(agents)} specialized agents to handle different aspects of the project."
    content = content.replace(
        "{Explain why this specific team composition was chosen, what project aspects drove the decisions}",
        rationale,
    )

    # Update interaction model
    content = content.replace(
        """```mermaid
graph TD
    PM[Project Manager] --> |assigns tasks| Agent1[Agent 1]
    PM --> |assigns tasks| Agent2[Agent 2]
    PM --> |coordinates| Agent3[Agent 3]

    Agent1 --> |status updates| PM
    Agent2 --> |status updates| PM
    Agent3 --> |status updates| PM

    Agent1 <--> |API contracts| Agent2
    Agent2 <--> |test scenarios| Agent3

    PM --> |reports to| Orchestrator[Orchestrator]
    Orchestrator --> |strategic guidance| PM
```""",
        interaction_model,
    )

    # Add deployment commands section
    deployment_section = f"""## Deployment Commands

Execute these commands in order to deploy the team:

```bash
# Create the session
tmux-orc setup session {project_name}

# Deploy agents
"""
    for cmd in deployment_commands:
        deployment_section += f"{cmd}\n"

    deployment_section += "```\n"

    # Insert deployment commands after team members
    content = content.replace("## Interaction Model", deployment_section + "\n## Interaction Model")

    # Clean up remaining placeholders
    content = content.replace("{project}", project_name)

    # Write file
    output_path.write_text(content)


def _generate_system_prompt(agent: dict, project_name: str) -> str:
    """Generate a system prompt for an agent based on role and project context."""
    role = agent["role"]
    focus = agent["focus"]

    # Base prompts by role type
    if "Project Manager" in role:
        prompt = f"""You are a Project Manager for the {project_name} project.

**Core Responsibilities:**
- Monitor team progress and health
- Assign tasks based on agent availability and skills
- Ensure quality gates are met before progression
- Communicate status updates to the orchestrator
- Identify and resolve blockers

**Project Focus:**
{focus}

**Team Management:**
- Run daily standups
- Send idle alerts when agents need tasks
- Escalate critical issues immediately
- Provide progress summaries every 30 minutes

**Quality Standards:**
- All code must pass tests (minimum 80% coverage)
- Code reviews required for all changes
- Documentation must be updated
- Performance benchmarks must be met"""

    elif "Developer" in role:
        dev_type = "Frontend" if "Frontend" in role else "Backend" if "Backend" in role else "Full-Stack"
        prompt = f"""You are a {dev_type} Developer working on the {project_name} project.

**Core Responsibilities:**
- Write clean, efficient, and well-tested code
- Implement features according to specifications
- Follow project coding standards and conventions
- Collaborate with other team members
- Commit code every 30 minutes with meaningful messages

**Technical Focus:**
{focus}

**Development Standards:**
- Follow TDD approach when applicable
- Write comprehensive unit tests
- Document all public APIs
- Handle errors gracefully
- Optimize for performance

**Communication Protocol:**
- Provide status updates using the standard format
- Ask for clarification when requirements are unclear
- Report blockers immediately
- Coordinate with other developers on integration points"""

    elif "QA" in role or "Test" in role:
        prompt = f"""You are a QA Engineer ensuring quality for the {project_name} project.

**Core Responsibilities:**
- Create comprehensive test plans
- Write automated tests (unit, integration, e2e)
- Perform exploratory testing
- Report and track bugs
- Verify fixes and feature completeness

**Testing Focus:**
{focus}

**Quality Metrics:**
- Code coverage target: 80%+
- All critical paths must have tests
- Performance benchmarks must be met
- Security requirements must be validated

**Bug Reporting:**
- Clear reproduction steps
- Expected vs actual behavior
- Screenshots/logs when applicable
- Severity and priority assessment"""

    elif "DevOps" in role:
        prompt = f"""You are a DevOps Engineer for the {project_name} project.

**Core Responsibilities:**
- Manage CI/CD pipelines
- Infrastructure as Code (IaC)
- Monitor system health and performance
- Implement security best practices
- Automate deployment processes

**Infrastructure Focus:**
{focus}

**Operational Standards:**
- Zero-downtime deployments
- Automated rollback capabilities
- Comprehensive monitoring and alerting
- Disaster recovery procedures
- Security scanning in CI/CD"""

    elif "Designer" in role or "Architect" in role:
        prompt = f"""You are a {role} for the {project_name} project.

**Core Responsibilities:**
- Design system architecture and patterns
- Create technical specifications
- Review and approve technical decisions
- Ensure scalability and maintainability
- Document architectural decisions

**Design Focus:**
{focus}

**Standards:**
- Follow industry best practices
- Consider performance implications
- Plan for future extensibility
- Ensure security by design
- Document all major decisions"""

    else:
        # Generic prompt for specialized roles
        prompt = f"""You are a {role} working on the {project_name} project.

**Core Responsibilities:**
- Execute your specialized role effectively
- Collaborate with the team
- Maintain high quality standards
- Communicate progress regularly

**Specialization Focus:**
{focus}

**Work Standards:**
- Follow project conventions
- Document your work
- Test thoroughly
- Communicate proactively
- Deliver on time"""

    # Add common footer
    prompt += f"""

**Git Discipline:**
- Commit every 30 minutes
- Write meaningful commit messages
- Create feature branches for new work
- Keep commits focused and atomic

**Communication:**
- Report to: Project Manager at {project_name}:0
- Status updates: After each task completion
- Blockers: Report immediately
- Collaboration: Coordinate with team members as needed"""

    return prompt


def _generate_interaction_diagram(agents: list[dict]) -> str:
    """Generate Mermaid diagram for team interactions."""
    diagram = "```mermaid\ngraph TD\n"

    # Add nodes
    diagram += "    Orchestrator[Orchestrator]\n"
    for agent in agents:
        safe_id = agent["role"].replace(" ", "_")
        diagram += f"    {safe_id}[{agent['role']}]\n"

    diagram += "\n"

    # Add PM relationships
    diagram += "    Orchestrator --> |strategic guidance| Project_Manager\n"
    diagram += "    Project_Manager --> |reports to| Orchestrator\n"

    for agent in agents[1:]:  # Skip PM
        safe_id = agent["role"].replace(" ", "_")
        diagram += f"    Project_Manager --> |assigns tasks| {safe_id}\n"
        diagram += f"    {safe_id} --> |status updates| Project_Manager\n"

    # Add agent interactions based on roles
    developers = [a for a in agents if "Developer" in a["role"]]
    qa = [a for a in agents if "QA" in a["role"] or "Test" in a["role"]]

    if len(developers) > 1:
        diagram += f"\n    {developers[0]['role'].replace(' ', '_')} <--> |code coordination| {developers[1]['role'].replace(' ', '_')}\n"

    if developers and qa:
        for dev in developers:
            for tester in qa:
                diagram += f"    {dev['role'].replace(' ', '_')} <--> |testing| {tester['role'].replace(' ', '_')}\n"

    diagram += "```"

    return diagram


def _determine_project_type(project_name: str, agents: list[dict]) -> str:
    """Determine project type from name and team composition."""
    name_lower = project_name.lower()

    if "api" in name_lower:
        return "API Development"
    elif "cli" in name_lower:
        return "CLI Application"
    elif "frontend" in name_lower or "ui" in name_lower:
        return "Frontend Application"
    elif "backend" in name_lower:
        return "Backend Service"
    elif "fullstack" in name_lower:
        return "Full-Stack Application"

    # Determine from team composition
    has_frontend = any("Frontend" in a["role"] for a in agents)
    has_backend = any("Backend" in a["role"] for a in agents)

    if has_frontend and has_backend:
        return "Full-Stack Application"
    elif has_backend:
        return "Backend Application"
    elif has_frontend:
        return "Frontend Application"

    return "Software Project"


def _get_default_team_template() -> str:
    """Return default team composition template."""
    return """# Team Composition - {Project Name}

Generated: {Date}
PRD: {PRD Location}
Project Type: {Type}

## Team Overview

This document defines the agent team composition for the {project} project.

## Team Rationale

{Explain why this specific team composition was chosen, what project aspects drove the decisions}

## Team Members

{Continue for all team members...}

## Interaction Model

{interaction_diagram}

## Communication Protocols

### Status Updates
- Frequency: After each task completion
- Format: Standard STATUS UPDATE format
- Channel: tmux-orc publish --session pm:0

## Recovery Information

### Recovery Commands
```bash
# Check agent health
tmux-orc recovery check --session {project}

# Restart specific agent
tmux-orc agent restart {project}:{window}
```"""


def _load_team_template(template_name: str) -> list[dict]:
    """Load a predefined team template."""
    # Predefined team templates
    templates = {
        "api-heavy": [
            {
                "role": "Project Manager",
                "template": "project-manager",
                "window": 0,
                "focus": "API project coordination",
            },
            {
                "role": "API Designer",
                "template": "api-designer",
                "window": 1,
                "focus": "RESTful API architecture",
            },
            {
                "role": "Backend Developer",
                "template": "backend-developer",
                "window": 2,
                "focus": "API implementation",
            },
            {
                "role": "Backend Developer",
                "template": "backend-developer",
                "window": 3,
                "focus": "Database and business logic",
            },
            {
                "role": "Test Automation",
                "template": "test-automation",
                "window": 4,
                "focus": "API testing",
            },
        ],
        "cli-tool": [
            {
                "role": "Project Manager",
                "template": "project-manager",
                "window": 0,
                "focus": "CLI project coordination",
            },
            {
                "role": "CLI Developer",
                "template": "cli-developer",
                "window": 1,
                "focus": "Command structure and parsing",
            },
            {
                "role": "CLI Developer",
                "template": "cli-developer",
                "window": 2,
                "focus": "Terminal UI and output",
            },
            {
                "role": "Technical Writer",
                "template": "technical-writer",
                "window": 3,
                "focus": "CLI documentation",
            },
            {
                "role": "QA Engineer",
                "template": "qa-engineer",
                "window": 4,
                "focus": "CLI testing",
            },
        ],
    }

    return templates.get(template_name, [])


@team.command()
def list_templates() -> None:
    """List available agent templates.

    Shows all agent templates that can be used for team composition,
    including their roles, specializations, and key skills.

    Examples:
        tmux-orc team list-templates
    """
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
    project_dir = Path.home() / "workspaces" / "Tmux-Orchestrator" / ".tmux_orchestrator" / "projects" / project_name
    team_comp = project_dir / "team-composition.md"

    if custom or team_comp.exists():
        if not team_comp.exists():
            console.print(f"[red]No team composition found for '{project_name}'[/red]")
            console.print("Create one with: tmux-orc team compose " + project_name)
            return

        console.print(f"[blue]Deploying custom team for: {project_name}[/blue]")
        console.print(f"Team composition: {team_comp}")

        # Parse team composition and deploy
        # (This would read the markdown and extract agent configs)
        console.print("[yellow]Custom deployment from composition document coming soon[/yellow]")
        console.print("For now, use: tmux-orc team deploy-standard")
    else:
        # Fall back to standard deployment
        from tmux_orchestrator.cli.team import team as team_cli

        ctx = click.get_current_context()
        ctx.invoke(
            team_cli.commands["deploy-standard"],
            team_type="fullstack",
            size=5,
            project_name=project_name,
        )


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
    # This would be implemented to show team-specific status
    console.print(f"[blue]Team Status: {project_name}[/blue]")

    # For now, delegate to existing functionality
    from tmux_orchestrator.cli.team import team as team_cli

    ctx = click.get_current_context()
    if "status" in team_cli.commands:
        ctx.invoke(team_cli.commands["status"], session=project_name)

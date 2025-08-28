"""Team composition logic and generation functionality."""

import shlex
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.prompt import Prompt

from .validators import sanitize_for_template

console = Console()


def interactive_team_composition(templates: dict[str, Any]) -> list[dict]:
    """Interactively build team composition.

    Args:
        templates: Dictionary of available agent templates

    Returns:
        List of selected agent configurations
    """
    console.print("[yellow]Building team interactively...[/yellow]")
    console.print("Available templates:")
    for name, data in templates.items():
        console.print(f"  • {name}: {data.get('role', name)}")

    selected: list[dict[str, Any]] = []
    window = 0

    while True:
        if not selected:
            console.print("\n[bold]Select your first team member:[/bold]")
        else:
            add_more = Prompt.ask(
                f"\nAdd another team member? Current team size: {len(selected)}",
                choices=["yes", "no", "y", "n"],
                default="no",
            )
            if add_more.lower() in ["no", "n"]:
                break

        # Get template choice
        template_name = Prompt.ask("Template name (or 'list' to see options)")

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


def suggest_team_composition(project_name: str, prd: str | None, templates: dict) -> list[dict]:
    """Suggest team composition based on project analysis.

    Args:
        project_name: Name of the project
        prd: Path to PRD file if provided
        templates: Dictionary of available agent templates

    Returns:
        List of suggested agent configurations
    """
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


def generate_team_composition(
    project_name: str, agents: list[dict], output_path: Path, prd: str | None, team_template_content: str
) -> None:
    """Generate team composition document.

    Args:
        project_name: Name of the project
        agents: List of agent configurations
        output_path: Path where to write the composition file
        prd: Path to PRD file if provided
        team_template_content: Template content to use for generation
    """
    # Format team members section with system prompts
    team_members = []
    deployment_commands = []

    for i, agent in enumerate(agents):
        # Generate system prompt for this agent
        system_prompt = generate_system_prompt(agent, project_name)

        # Create deployment command with proper escaping
        # SECURITY: Use shlex.quote to prevent shell injection
        deploy_cmd = (
            f"tmux-orc spawn agent {shlex.quote(agent['template'])} "
            f"{shlex.quote(project_name)}:{shlex.quote(str(agent['window']))} "
            f"--briefing {shlex.quote(system_prompt)}"
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
    interaction_model = generate_interaction_diagram(agents)

    # Replace placeholders with sanitized values
    content = team_template_content
    content = content.replace("{Project Name}", sanitize_for_template(project_name))
    content = content.replace("{Date}", datetime.now().strftime("%Y-%m-%d %H:%M"))
    content = content.replace("{PRD Location}", sanitize_for_template(str(prd) if prd else "Not specified"))
    content = content.replace("{Type}", sanitize_for_template(determine_project_type(project_name, agents)))

    # Add team members
    members_section = "\n\n".join(team_members)
    content = content.replace(
        "### 1. Project Manager\n- **Session:Window**: {project}:0\n- **Template**: project-manager.yaml\n- **Customizations**: {Any project-specific adjustments}\n- **Primary Focus**: {Specific PM focus for this project}\n\n### 2. {Agent Role 1}\n- **Session:Window**: {project}:1\n- **Template**: {template-name}.yaml\n- **Customizations**: {Project-specific adjustments}\n- **Primary Focus**: {What this agent will focus on}\n- **Key Responsibilities**:\n  - {Responsibility 1}\n  - {Responsibility 2}\n  - {Responsibility 3}\n\n### 3. {Agent Role 2}\n- **Session:Window**: {project}:2\n- **Template**: {template-name}.yaml\n- **Customizations**: {Project-specific adjustments}\n- **Primary Focus**: {What this agent will focus on}\n- **Key Responsibilities**:\n  - {Responsibility 1}\n  - {Responsibility 2}\n  - {Responsibility 3}\n\n{Continue for all team members...}",
        members_section,
    )

    # Add rationale
    rationale = f"This team composition was selected to provide comprehensive coverage for {sanitize_for_template(project_name)}. "
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
tmux-orc setup session {shlex.quote(project_name)}

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


def generate_system_prompt(agent: dict, project_name: str) -> str:
    """Generate system prompt for an agent.

    Args:
        agent: Agent configuration dictionary
        project_name: Name of the project

    Returns:
        Generated system prompt
    """
    return f"""You are a {agent['role']} working on {project_name}.
Your primary focus is: {agent['focus']}

Template: {agent['template']}
Session: {project_name}:{agent['window']}

Follow your template's guidelines while focusing specifically on {agent['focus']} for this project."""


def generate_interaction_diagram(agents: list[dict]) -> str:
    """Generate Mermaid interaction diagram for the team.

    Args:
        agents: List of agent configurations

    Returns:
        Mermaid diagram as string
    """
    # Find PM (usually window 0)
    pm_window = next((agent["window"] for agent in agents if agent["role"] == "Project Manager"), 0)

    diagram = "```mermaid\ngraph TD\n"

    # PM as central hub
    diagram += "    PM[Project Manager :0] --> |coordinates| Orchestrator[Orchestrator]\n"
    diagram += "    Orchestrator --> |strategic guidance| PM\n\n"

    # Connections from PM to other agents
    for agent in agents:
        if agent["window"] != pm_window:
            agent_id = f"Agent{agent['window']}"
            diagram += f"    PM --> |assigns tasks| {agent_id}[{agent['role']} :{agent['window']}]\n"
            diagram += f"    {agent_id} --> |status updates| PM\n"

    # Add some logical connections between agents
    backend_agents = [a for a in agents if "backend" in a["role"].lower() or "api" in a["role"].lower()]
    frontend_agents = [a for a in agents if "frontend" in a["role"].lower()]
    qa_agents = [a for a in agents if "qa" in a["role"].lower() or "test" in a["role"].lower()]

    # Backend <-> Frontend connections
    for backend in backend_agents:
        for frontend in frontend_agents:
            if backend["window"] != frontend["window"]:
                diagram += f"    Agent{backend['window']} <--> |API contracts| Agent{frontend['window']}\n"

    # QA connections to developers
    for qa in qa_agents:
        for dev in backend_agents + frontend_agents:
            if qa["window"] != dev["window"]:
                diagram += f"    Agent{dev['window']} --> |deliverables| Agent{qa['window']}\n"
                break  # Only connect to one dev to avoid clutter

    diagram += "```"
    return diagram


def determine_project_type(project_name: str, agents: list[dict]) -> str:
    """Determine project type based on name and team composition.

    Args:
        project_name: Name of the project
        agents: List of agent configurations

    Returns:
        Project type string
    """
    roles = [agent["role"].lower() for agent in agents]

    if any("api" in role for role in roles) or "api" in project_name.lower():
        return "API Development"
    elif any("cli" in role for role in roles) or "cli" in project_name.lower():
        return "CLI Tool"
    elif any("frontend" in role for role in roles) and any("backend" in role for role in roles):
        return "Full-Stack Web Application"
    elif any("data" in role for role in roles):
        return "Data Pipeline"
    else:
        return "General Software Development"

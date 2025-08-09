"""Execute PRD files by deploying and managing agent teams."""

import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm

from tmux_orchestrator.utils.tmux import TMUXManager

console = Console()


def analyze_prd_for_team_composition(prd_path: Path) -> Tuple[str, int, Dict[str, str]]:
    """Analyze PRD content to suggest optimal team type and size.

    This provides intelligent suggestions based on PRD content analysis,
    but the actual implementation plan is created by the PM agent who
    reads and interprets the full PRD document.

    Returns:
        Tuple of (team_type, team_size, tech_analysis)
    """
    try:
        prd_content = prd_path.read_text()
    except Exception:
        # Default if can't read
        return "fullstack", 5, {"error": "Could not read PRD"}

    console.print("[blue]Analyzing PRD to suggest optimal team composition...[/blue]")

    # This is just a suggestion based on keywords - the PM agent
    # will do the actual PRD interpretation and task creation

    # Analyze content for technology indicators
    content_lower = prd_content.lower()

    tech_analysis = {
        "frontend_score": 0,
        "backend_score": 0,
        "complexity": "medium",
        "requires_qa": False,
        "requires_devops": False,
    }

    # Smart content analysis
    if "user interface" in content_lower or "ui/ux" in content_lower or "frontend" in content_lower:
        tech_analysis["frontend_score"] += 3
    if any(tech in content_lower for tech in ["react", "vue", "angular", "css", "responsive"]):
        tech_analysis["frontend_score"] += 2

    if "api" in content_lower or "backend" in content_lower or "server" in content_lower:
        tech_analysis["backend_score"] += 3
    if any(tech in content_lower for tech in ["database", "microservice", "authentication", "rest", "graphql"]):
        tech_analysis["backend_score"] += 2

    # Complexity analysis
    if any(word in content_lower for word in ["enterprise", "scalable", "distributed", "microservices", "complex"]):
        tech_analysis["complexity"] = "high"
    elif any(word in content_lower for word in ["simple", "basic", "prototype", "mvp"]):
        tech_analysis["complexity"] = "low"

    # Special requirements
    if "testing" in content_lower or "qa" in content_lower or "quality" in content_lower:
        tech_analysis["requires_qa"] = True
    if any(word in content_lower for word in ["deployment", "ci/cd", "docker", "kubernetes", "infrastructure"]):
        tech_analysis["requires_devops"] = True

    # Determine team type
    if tech_analysis["frontend_score"] > tech_analysis["backend_score"] * 1.5:
        team_type = "frontend"
    elif tech_analysis["backend_score"] > tech_analysis["frontend_score"] * 1.5:
        team_type = "backend"
    else:
        team_type = "fullstack"

    # Determine team size based on complexity
    base_size = {"low": 3, "medium": 5, "high": 6}
    team_size = base_size.get(tech_analysis["complexity"], 5)

    # Adjust for special requirements
    if tech_analysis["requires_qa"]:
        team_size = min(team_size + 1, 8)
    if tech_analysis["requires_devops"] and tech_analysis["complexity"] != "low":
        team_size = min(team_size + 1, 8)

    # Ensure minimum team size
    team_size = max(team_size, 3)

    return team_type, team_size, tech_analysis


def generate_team_briefings_from_prd(prd_path: Path, project_name: str, team_type: str) -> Dict[str, str]:
    """Generate role-specific briefings based on PRD content.

    Returns:
        Dict mapping role to customized briefing
    """
    try:
        prd_content = prd_path.read_text()
    except Exception:
        prd_content = ""

    # Extract key sections from PRD
    sections = {
        "overview": _extract_section(prd_content, ["overview", "summary", "introduction"]),
        "requirements": _extract_section(prd_content, ["requirements", "features", "functionality"]),
        "technical": _extract_section(prd_content, ["technical", "architecture", "technology"]),
        "timeline": _extract_section(prd_content, ["timeline", "milestones", "schedule"]),
    }

    project_dir = Path.home() / "workspaces" / "Tmux-Orchestrator" / ".tmux_orchestrator" / "projects" / project_name

    # Base briefings with PRD context
    briefings = {
        "pm": f"""You are the Project Manager for {project_name}.

## CRITICAL: Read the Actual PRD Document
The Product Requirements Document is located at:
{project_dir}/prd.md

YOU MUST READ THIS DOCUMENT TO UNDERSTAND THE PROJECT REQUIREMENTS.
The orchestrator has NOT parsed the PRD for you. The document contains
all the project specifications, features, and technical requirements.

## Your Responsibilities
1. READ the PRD document thoroughly (./prd.md)
2. UNDERSTAND all requirements and technical specifications
3. CREATE a comprehensive task list based on YOUR understanding of the PRD
4. DISTRIBUTE tasks to team members based on their specializations
5. MONITOR progress and ensure quality gates are met
6. COORDINATE team communication and resolve blockers
7. REPORT status to orchestrator regularly

## Task Generation Process
1. Open and read ./prd.md completely
2. Analyze requirements and create implementation plan
3. Generate detailed tasks and save to: {project_dir}/tasks.md
4. Use the task generation guide if needed: /workspaces/Tmux-Orchestrator/.claude/commands/generate-tasks.md
5. Run: tmux-orc tasks distribute {project_name}

## Key Points
- The PRD is the source of truth - read it carefully
- You are responsible for interpreting requirements
- Create tasks that fully implement the PRD
- Ensure nothing is missed from the requirements

Begin by reading the PRD document and understanding the full scope.""",
        "developer": f"""You are a Developer on the {project_name} team.

## Project Context
{sections.get('overview', 'See PRD for project overview')}

## Technical Requirements
{sections.get('technical', 'See PRD for technical details')}

## Your Responsibilities
1. Implement assigned features according to PRD specifications
2. Write comprehensive tests for all code
3. Ensure code quality (linting, formatting, type checking)
4. Collaborate with team members on integration points
5. Update task status regularly

## Quality Standards
- All code must have tests
- Linting must pass before marking tasks complete
- Commit regularly (at least every 30 minutes)
- Document complex logic

Wait for the PM to assign you specific tasks from {project_dir}/agents/""",
        "qa": f"""You are a QA Engineer on the {project_name} team.

## Project Context
{sections.get('overview', 'See PRD for project overview')}

## Requirements to Validate
{sections.get('requirements', 'See PRD for full requirements')}

## Your Responsibilities
1. Create comprehensive test plans based on PRD
2. Identify edge cases and potential issues
3. Validate all features meet requirements
4. Automate testing where possible
5. Report bugs and quality issues promptly

## Testing Standards
- Test both happy paths and edge cases
- Ensure cross-browser/platform compatibility
- Performance testing for critical paths
- Security testing for sensitive features

Wait for the PM to provide specific testing tasks.""",
    }

    # Customize developer briefing based on team type
    if team_type == "frontend":
        briefings["developer"] = briefings["developer"].replace("Developer", "Frontend Developer")
        briefings["developer"] += "\n\nFocus on UI/UX implementation, responsive design, and user experience."
    elif team_type == "backend":
        briefings["developer"] = briefings["developer"].replace("Developer", "Backend Developer")
        briefings["developer"] += "\n\nFocus on API design, database architecture, and server-side logic."

    return briefings


def _extract_section(content: str, keywords: List[str]) -> str:
    """Extract a section from PRD based on keywords."""
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("#"):
            # Check if any keyword matches
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in keywords):
                # Extract until next section
                section_lines = [line]
                for j in range(i + 1, len(lines)):
                    if lines[j].startswith("#") and not lines[j].startswith("###"):
                        break
                    section_lines.append(lines[j])
                return "\n".join(section_lines).strip()
    return ""


def wait_for_task_generation(project_name: str, timeout: int = 300) -> bool:
    """Wait for PM to generate tasks with progress updates.

    Returns:
        True if tasks were generated, False if timeout
    """
    project_dir = Path.home() / "workspaces" / "Tmux-Orchestrator" / ".tmux_orchestrator" / "projects" / project_name
    tasks_file = project_dir / "tasks.md"

    start_time = time.time()
    check_interval = 5  # Check every 5 seconds

    console.print("\n[yellow]Waiting for PM to generate task list...[/yellow]")
    console.print("The PM is analyzing the PRD and creating tasks.")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Waiting for task generation...", total=None)

        while time.time() - start_time < timeout:
            # Check if tasks file exists and has content
            if tasks_file.exists():
                content = tasks_file.read_text()
                # Check if tasks have been added (look for task markers)
                if "- [ ]" in content or "- [-]" in content or "- [x]" in content:
                    progress.update(task, description="Tasks generated!")
                    return True

            # Update progress message
            elapsed = int(time.time() - start_time)
            progress.update(task, description=f"Waiting for task generation... ({elapsed}s)")

            time.sleep(check_interval)

    return False


def monitor_task_distribution(project_name: str) -> bool:
    """Monitor and execute task distribution when ready.

    Returns:
        True if distribution successful
    """
    console.print("\n[blue]Checking task distribution...[/blue]")

    # Run task distribution
    result = subprocess.run(["tmux-orc", "tasks", "distribute", project_name], capture_output=True, text=True)

    if result.returncode == 0:
        console.print("[green]✓ Tasks distributed to team members[/green]")
        return True
    else:
        console.print(f"[yellow]Task distribution issue: {result.stderr}[/yellow]")
        return False


@click.command()
@click.argument("prd_file", type=click.Path(exists=True))
@click.option("--project-name", help="Project name (defaults to PRD filename)")
@click.option("--team-size", default=5, help="Number of agents to deploy")
@click.option(
    "--team-type",
    type=click.Choice(["frontend", "backend", "fullstack", "custom"]),
    default="custom",
    help="Type of team to deploy",
)
@click.option("--no-monitor", is_flag=True, help="Skip starting the monitoring daemon")
@click.option("--skip-planning", is_flag=True, help="Skip team planning phase")
@click.option("--auto", is_flag=True, help="Automatically determine team from PRD analysis")
@click.option("--wait-for-tasks", is_flag=True, default=True, help="Wait for PM to generate tasks")
@click.pass_context
def execute(
    ctx: click.Context,
    prd_file: str,
    project_name: Optional[str],
    team_size: int,
    team_type: str,
    no_monitor: bool,
    skip_planning: bool,
    auto: bool,
    wait_for_tasks: bool,
) -> None:
    """Execute a PRD by deploying an agent team for manual orchestration.

    PRD_FILE: Path to the Product Requirements Document

    This command sets up a manual orchestration workflow where Claude (you)
    acts as the orchestrator to oversee an autonomous AI agent team.

    WORKFLOW:
    1. Creates project structure and copies PRD
    2. Analyzes PRD to suggest optimal team composition
    3. Deploys the agent team with role-specific briefings
    4. PM agent autonomously reads PRD and creates tasks
    5. PM distributes tasks to team members
    6. Team works independently with PM coordination
    7. You monitor and guide at a high level

    ORCHESTRATOR RESPONSIBILITIES:
    - Review PRD and approve team composition
    - Monitor overall project health
    - Make architectural decisions
    - Resolve cross-team blockers
    - Ensure quality standards
    - NOT micromanage individual agents

    TEAM COMPOSITION:
    - --auto: Analyzes PRD to determine optimal team
    - --team-type: Use predefined team templates
    - --team-size: Override suggested team size

    IMPORTANT: This is NOT automatic PRD parsing. The PM agent reads
    the actual PRD document and creates the implementation plan. You
    oversee the process but let agents work autonomously.

    Examples:
        tmux-orc execute ./prd.md
        tmux-orc execute ./prd.md --auto
        tmux-orc execute ./prd.md --project-name myapp
        tmux-orc execute ./prd.md --team-type backend --team-size 4
        tmux-orc execute ./prd.md --no-monitor --skip-planning

    After execution:
        - Monitor PM: tmux-orc read --session project:0
        - Check tasks: tmux-orc tasks status project
        - View team: tmux-orc team status project
        - Message PM: tmux-orc send project:0 "status?"
    """
    tmux: TMUXManager = ctx.obj["tmux"]

    # Determine project name
    prd_path = Path(prd_file).resolve()
    if not project_name:
        # Extract from filename: prd-user-auth.md -> user-auth
        name = prd_path.stem
        if name.startswith("prd-"):
            project_name = name[4:]
        else:
            project_name = name

    # Analyze PRD if auto mode
    if auto or team_type == "custom":
        console.print("[blue]Analyzing PRD to determine optimal team composition...[/blue]")
        analyzed_type, analyzed_size, tech_scores = analyze_prd_for_team_composition(prd_path)

        if auto:
            team_type = analyzed_type
            team_size = analyzed_size
            console.print("[green]✓ PRD Analysis Complete[/green]")
            if isinstance(tech_scores, dict) and "frontend_score" in tech_scores:
                # New tech_analysis format
                console.print(f"  Complexity: {tech_scores.get('complexity', 'medium')}")
                console.print(f"  Frontend work: {'High' if tech_scores.get('frontend_score', 0) > 3 else 'Low'}")
                console.print(f"  Backend work: {'High' if tech_scores.get('backend_score', 0) > 3 else 'Low'}")
                if tech_scores.get("requires_qa"):
                    console.print("  Special: QA/Testing focus detected")
                if tech_scores.get("requires_devops"):
                    console.print("  Special: DevOps requirements detected")
            console.print(f"  Recommended team: {team_type} with {team_size} agents")
        elif team_type == "custom" and not skip_planning:
            # Show analysis but let user confirm
            console.print("\n[yellow]PRD Analysis suggests:[/yellow]")
            console.print(f"  Team type: {analyzed_type}")
            console.print(f"  Team size: {analyzed_size}")
            if Confirm.ask("Use suggested configuration?"):
                team_type = analyzed_type
                team_size = analyzed_size

    console.print(f"\n[bold blue]Executing PRD: {prd_path.name}[/bold blue]")
    console.print(f"Project: {project_name}")
    console.print(f"Team: {team_type} ({team_size} agents)")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Step 1: Create project structure
        task = progress.add_task("Creating project structure...", total=8)

        # Create project structure using CLI
        import subprocess

        result = subprocess.run(
            ["tmux-orc", "tasks", "create", project_name, "--prd", str(prd_path)],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            console.print(f"[red]Failed to create project: {result.stderr}[/red]")
            return

        progress.update(task, advance=1)
        time.sleep(0.5)

        # Step 2: Team Planning Phase
        if team_type == "custom" and not skip_planning:
            progress.update(task, description="Planning team composition...")

            # Run team composition
            compose_result = subprocess.run(
                ["tmux-orc", "team", "compose", project_name, "--prd", str(prd_path)],
                capture_output=True,
                text=True,
            )

            if compose_result.returncode != 0:
                console.print("[yellow]Team composition failed, using default team[/yellow]")
                team_type = "fullstack"
            else:
                console.print("[green]✓ Team composition created[/green]")

            progress.update(task, advance=1)
            time.sleep(0.5)
        else:
            progress.update(task, advance=1)

        # Step 3: Deploy team
        progress.update(task, description="Deploying agent team...")

        # Check if session already exists
        if tmux.has_session(project_name):
            console.print(f"[yellow]Session '{project_name}' already exists[/yellow]")
            progress.update(task, advance=6)
        else:
            # Create session and deploy team
            from tmux_orchestrator.core.team_operations.deploy_team import (
                deploy_standard_team,
            )

            success, message = deploy_standard_team(tmux, team_type, team_size, project_name)

            if not success:
                console.print(f"[red]Failed to deploy team: {message}[/red]")
                return

            progress.update(task, advance=1)
            time.sleep(2)

            # Step 3: Brief the PM with enhanced PRD-based briefing
            progress.update(task, description="Briefing Project Manager...")

            pm_target = f"{project_name}:0"  # PM is always in window 0

            # Generate customized briefings based on PRD
            briefings = generate_team_briefings_from_prd(prd_path, project_name, team_type)

            if tmux.send_message(pm_target, briefings["pm"]):
                progress.update(task, advance=1)
            else:
                console.print("[yellow]⚠ PM briefing may have failed[/yellow]")
                progress.update(task, advance=1)

            time.sleep(2)

            # Step 4: Brief other team members
            progress.update(task, description="Briefing team members...")

            # Get windows in session
            windows = tmux.list_windows(project_name)
            briefed_count = 0

            for window in windows[1:]:  # Skip PM (window 0)
                window_name = window["name"].lower()
                target = f"{project_name}:{window['index']}"

                # Determine role and send appropriate briefing
                if "qa" in window_name or "test" in window_name:
                    briefing = briefings.get("qa", briefings["developer"])
                else:
                    briefing = briefings.get("developer", briefings["developer"])

                if tmux.send_message(target, briefing):
                    briefed_count += 1
                    time.sleep(1)  # Small delay between briefings

            if briefed_count > 0:
                console.print(f"[green]✓ Briefed {briefed_count} team members[/green]")

            progress.update(task, advance=1)

            time.sleep(1)

            # Step 5: Start monitoring daemon (unless disabled)
            if not no_monitor:
                progress.update(task, description="Starting monitoring daemon...")

                # Use tmux-orc monitor start instead of shell script
                monitor_result = subprocess.run(
                    ["tmux-orc", "monitor", "start", "--interval", "15"], capture_output=True, text=True
                )

                if monitor_result.returncode == 0:
                    console.print("[green]✓ Monitoring daemon started[/green]")
                else:
                    # Fallback to shell script if new command not yet implemented
                    daemon_script = Path(__file__).parent.parent.parent / "commands" / "idle-monitor-daemon.sh"
                    if daemon_script.exists():
                        try:
                            subprocess.Popen(
                                [str(daemon_script), "15"],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                            )
                            console.print("[green]✓ Monitoring daemon started (fallback)[/green]")
                        except Exception as e:
                            console.print(f"[yellow]⚠ Could not start daemon: {e}[/yellow]")

                progress.update(task, advance=1)
            else:
                progress.update(task, advance=1)

            # Step 6: Task generation and distribution workflow
            progress.update(task, description="Execution started!")
            progress.update(task, advance=1)

    # End of progress bar

    # Wait for task generation if requested
    if wait_for_tasks and tmux.has_session(project_name):
        if wait_for_task_generation(project_name, timeout=300):
            console.print("[green]✓ PM has generated the task list![/green]")

            # Automatically distribute tasks
            if monitor_task_distribution(project_name):
                console.print("[green]✓ Tasks have been distributed to the team[/green]")

                # Brief team about their tasks
                console.print("\n[blue]Notifying team members about their task assignments...[/blue]")
                project_dir = (
                    Path.home() / "workspaces" / "Tmux-Orchestrator" / ".tmux_orchestrator" / "projects" / project_name
                )

                windows = tmux.list_windows(project_name)
                for window in windows[1:]:  # Skip PM
                    window_name = window["name"].lower()
                    target = f"{project_name}:{window['index']}"

                    # Determine agent type
                    if "frontend" in window_name:
                        task_file = project_dir / "agents" / "frontend-tasks.md"
                    elif "backend" in window_name:
                        task_file = project_dir / "agents" / "backend-tasks.md"
                    elif "qa" in window_name or "test" in window_name:
                        task_file = project_dir / "agents" / "qa-tasks.md"
                    else:
                        task_file = project_dir / "agents" / "developer-tasks.md"

                    if task_file.exists():
                        notification = f"""Your tasks have been assigned!

Please review your task file at:
{task_file}

Begin working on Priority 1 tasks and update the task file as you progress.
Remember to:
- Mark tasks as in-progress: - [-]
- Mark completed tasks: - [x]
- Commit code every 30 minutes
- Run tests before marking tasks complete"""

                        tmux.send_message(target, notification)
                        time.sleep(1)

                console.print("[green]✓ Team has been notified of their task assignments[/green]")
        else:
            console.print("[yellow]⚠ Timeout waiting for task generation[/yellow]")
            console.print("You can manually check progress with: tmux-orc tasks status " + project_name)

    # Final summary
    project_dir = Path.home() / "workspaces" / "Tmux-Orchestrator" / ".tmux_orchestrator" / "projects" / project_name

    summary = f"""PRD execution initiated successfully!

[bold]Project Details:[/bold]
• Name: {project_name}
• PRD: {prd_path.name}
• Team: {team_type} ({team_size} agents)
• Session: {project_name}
• Monitoring: {'Active' if not no_monitor else 'Disabled'}

[bold]Project Location:[/bold]
{project_dir}

[bold]Workflow Status:[/bold]
• Project structure: ✓ Created
• Team deployment: ✓ {team_size} agents deployed
• PRD analysis: ✓ Team optimized for project needs
• Agent briefings: ✓ Customized based on PRD
• Task generation: {'⏳ Waiting for PM' if wait_for_tasks else '⏸ Manual mode'}
• Monitoring: {'✓ Active' if not no_monitor else '✗ Disabled'}

[bold]Next Steps:[/bold]
1. Monitor PM progress: tmux-orc agent send {project_name}:0 "status update"
2. Check task generation: tmux-orc tasks status {project_name}
3. View team activity: tmux-orc team status {project_name}
4. Watch live dashboard: tmux-orc dashboard --session {project_name}

[bold]Key Commands:[/bold]
• Attach to PM: tmux attach -t {project_name} -t 0
• View agent logs: tmux-orc monitor logs --follow
• Check idle agents: tmux-orc monitor status
• Restart failed agent: tmux-orc agent restart {project_name}:window

[bold]Communication:[/bold]
• Message PM: tmux-orc agent send {project_name}:0 "message"
• Broadcast team: tmux-orc team broadcast {project_name} "announcement"
• Schedule check-in: tmux-orc orchestrator schedule 30 {project_name}:0 "Progress check"

The end-to-end workflow is now active. The PM will analyze the PRD,
generate tasks, and coordinate the team autonomously."""

    console.print(Panel(summary, title="✨ Execution Pipeline Active", style="green"))


# Export for CLI registration
__all__ = ["execute"]

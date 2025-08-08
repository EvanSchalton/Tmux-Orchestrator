"""Execute PRD files by deploying and managing agent teams."""

import time
from pathlib import Path
from typing import Optional, Tuple

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from tmux_orchestrator.utils.tmux import TMUXManager

console = Console()


@click.command()
@click.argument('prd_file', type=click.Path(exists=True))
@click.option('--project-name', help='Project name (defaults to PRD filename)')
@click.option('--team-size', default=5, help='Number of agents to deploy')
@click.option('--team-type', 
              type=click.Choice(['frontend', 'backend', 'fullstack', 'custom']), 
              default='custom',
              help='Type of team to deploy')
@click.option('--no-monitor', is_flag=True, help='Skip starting the monitoring daemon')
@click.option('--skip-planning', is_flag=True, help='Skip team planning phase')
@click.pass_context
def execute(ctx: click.Context, prd_file: str, project_name: Optional[str], 
            team_size: int, team_type: str, no_monitor: bool, skip_planning: bool) -> None:
    """Execute a PRD by deploying an agent team and managing the workflow.
    
    PRD_FILE: Path to the Product Requirements Document
    
    This command orchestrates the complete PRD-driven development workflow:
    1. Creates project structure with task management
    2. Deploys appropriate agent team
    3. Distributes tasks to agents
    4. Starts monitoring daemon
    5. Provides real-time progress updates
    
    Examples:
        tmux-orc execute ./prd.md
        tmux-orc execute ./auth-prd.md --project-name user-auth
        tmux-orc execute ./prd.md --team-size 6 --team-type backend
        tmux-orc execute ./prd.md --no-monitor
    
    Workflow Steps:
        1. Parse PRD and create project structure
        2. Generate task list from PRD (requires user confirmation)
        3. Deploy PM and development team
        4. Distribute tasks to appropriate agents
        5. Start idle monitoring daemon
        6. Begin development execution
    
    The command will:
        • Create .tmux_orchestrator/projects/{name}/ structure
        • Copy PRD to project directory
        • Deploy team with PM, developers, and QA
        • Brief PM with PRD and workflow instructions
        • Monitor progress and provide updates
    """
    tmux: TMUXManager = ctx.obj['tmux']
    
    # Determine project name
    prd_path = Path(prd_file).resolve()
    if not project_name:
        # Extract from filename: prd-user-auth.md -> user-auth
        name = prd_path.stem
        if name.startswith('prd-'):
            project_name = name[4:]
        else:
            project_name = name
    
    console.print(f"[bold blue]Executing PRD: {prd_path.name}[/bold blue]")
    console.print(f"Project: {project_name}")
    console.print(f"Team: {team_type} ({team_size} agents)")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        # Step 1: Create project structure
        task = progress.add_task("Creating project structure...", total=8)
        
        # Create project structure using CLI
        import subprocess
        result = subprocess.run([
            'tmux-orc', 'tasks', 'create', project_name, 
            '--prd', str(prd_path)
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            console.print(f"[red]Failed to create project: {result.stderr}[/red]")
            return
        
        progress.update(task, advance=1)
        time.sleep(0.5)
        
        # Step 2: Team Planning Phase
        if team_type == 'custom' and not skip_planning:
            progress.update(task, description="Planning team composition...")
            
            # Run team composition
            compose_result = subprocess.run([
                'tmux-orc', 'team', 'compose', project_name,
                '--prd', str(prd_path)
            ], capture_output=True, text=True)
            
            if compose_result.returncode != 0:
                console.print("[yellow]Team composition failed, using default team[/yellow]")
                team_type = 'fullstack'
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
            from tmux_orchestrator.core.team_operations.deploy_team import deploy_fullstack_team
            
            if team_type == 'fullstack':
                deploy_func = deploy_fullstack_team
            else:
                # Use standard team deployment
                from tmux_orchestrator.core.team_operations.deploy_team import deploy_standard_team
                deploy_func = lambda tmux, name, size: deploy_standard_team(tmux, team_type, size, name)
            
            success, message = deploy_func(tmux, project_name, team_size)
            
            if not success:
                console.print(f"[red]Failed to deploy team: {message}[/red]")
                return
            
            progress.update(task, advance=1)
            time.sleep(2)
            
            # Step 3: Brief the PM
            progress.update(task, description="Briefing Project Manager...")
            
            pm_target = f"{project_name}:0"  # PM is always in window 0
            project_dir = Path.home() / "workspaces" / "Tmux-Orchestrator" / ".tmux_orchestrator" / "projects" / project_name
            
            briefing = f"""You are the Project Manager for {project_name}.

## Your PRD

The Product Requirements Document is located at:
{project_dir}/prd.md

Please read and understand it thoroughly.

## Workflow Instructions

1. **Generate Tasks**: 
   - Use /workspaces/Tmux-Orchestrator/.claude/commands/generate-tasks.md
   - Save to: {project_dir}/tasks.md

2. **Distribute Tasks**:
   - Run: tmux-orc tasks distribute {project_name}
   - Or manually create agent task files in {project_dir}/agents/

3. **Brief Your Team**:
   - Each agent should receive their task file location
   - Ensure they understand quality requirements
   - Set up regular check-ins

4. **Monitor Progress**:
   - Use: tmux-orc tasks status {project_name}
   - Ensure agents update their task files
   - Enforce 30-minute commit rule

5. **Quality Gates**:
   - No task proceeds with failing tests
   - All linting must pass
   - Maintain high code quality

Begin by reading the PRD and generating the task list."""
            
            if tmux.send_message(pm_target, briefing):
                progress.update(task, advance=1)
            else:
                console.print("[yellow]⚠ PM briefing may have failed[/yellow]")
                progress.update(task, advance=1)
            
            time.sleep(1)
            
            # Step 4: Start monitoring daemon (unless disabled)
            if not no_monitor:
                progress.update(task, description="Starting monitoring daemon...")
                
                import subprocess
                daemon_script = Path(__file__).parent.parent.parent / "commands" / "idle-monitor-daemon.sh"
                
                if daemon_script.exists():
                    try:
                        subprocess.Popen([str(daemon_script), "15"], 
                                       stdout=subprocess.DEVNULL, 
                                       stderr=subprocess.DEVNULL)
                        console.print("[green]✓ Monitoring daemon started[/green]")
                    except Exception as e:
                        console.print(f"[yellow]⚠ Could not start daemon: {e}[/yellow]")
                
                progress.update(task, advance=1)
            else:
                progress.update(task, advance=1)
            
            # Step 5: Provide task generation reminder
            progress.update(task, description="Waiting for task generation...")
            time.sleep(2)
            
            console.print("\n[yellow]The PM needs to generate tasks from the PRD.[/yellow]")
            console.print("Please wait for the PM to:")
            console.print("1. Read the PRD")
            console.print("2. Generate task list using /generate-tasks")
            console.print("3. Distribute tasks to the team")
            
            progress.update(task, advance=1)
            
            # Step 6: Show status
            progress.update(task, description="Execution started!")
            time.sleep(1)
            progress.update(task, advance=1)
    
    # Final summary
    summary = f"""PRD execution initiated successfully!

[bold]Project Details:[/bold]
• Name: {project_name}
• PRD: {prd_path.name}
• Team: {team_type} ({team_size} agents)
• Session: {project_name}

[bold]Project Location:[/bold]
{Path.home() / "workspaces" / "Tmux-Orchestrator" / ".tmux_orchestrator" / "projects" / project_name}

[bold]Next Steps:[/bold]
1. Monitor PM progress: tmux-orc read --session {project_name}:0
2. Check task generation: tmux-orc tasks status {project_name}
3. View team activity: tmux-orc team status {project_name}
4. Attach to session: tmux attach -t {project_name}

[bold]Available Commands:[/bold]
• Send message to PM: tmux-orc publish --session {project_name}:0 "message"
• Check agent status: tmux-orc list
• View task progress: tmux-orc tasks status {project_name}
• Export report: tmux-orc tasks export {project_name}

The PM will now read the PRD, generate tasks, and coordinate the team."""
    
    console.print(Panel(summary, title="Execution Started", style="green"))


# Export for CLI registration
__all__ = ['execute']
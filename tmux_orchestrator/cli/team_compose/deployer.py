"""Deployment logic for team composition."""

from pathlib import Path

import click
from rich.console import Console

console = Console()


def deploy_team(project_name: str, custom: bool) -> None:
    """Deploy a team based on composition document.

    Args:
        project_name: Name of the project to deploy team for
        custom: Whether to use custom team composition
    """
    # SECURITY: Validate project name to prevent path traversal
    if not project_name or ".." in project_name or "/" in project_name or "\\" in project_name:
        console.print("[red]Invalid project name. Must not contain path separators.[/red]")
        return

    project_dir = Path.home() / "workspaces" / "Tmux-Orchestrator" / ".tmux_orchestrator" / "projects" / project_name
    team_comp = project_dir / "team-composition.md"

    if custom or team_comp.exists():
        if not team_comp.exists():
            console.print(f"[red]No team composition found for '{project_name}'[/red]")
            console.print("Create one with: tmux-orc team compose " + project_name)
            return

        console.print(f"[blue]Deploying custom team for: {project_name}[/blue]")
        console.print(f"Team composition: {team_comp}")

        # Custom team composition deployment not yet implemented
        console.print("[yellow]Custom team composition files are not yet supported.[/yellow]")
        console.print("Please use manual agent spawning or tmux-orc team deploy-standard instead.")
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


def show_team_status(project_name: str) -> None:
    """Show detailed team status and health.

    Args:
        project_name: Name of the project team to check
    """
    # This would be implemented to show team-specific status
    console.print(f"[blue]Team Status: {project_name}[/blue]")

    # For now, delegate to existing functionality
    from tmux_orchestrator.cli.team import team as team_cli

    ctx = click.get_current_context()
    if "status" in team_cli.commands:
        ctx.invoke(team_cli.commands["status"], project_name=project_name)
    else:
        console.print("[yellow]Team status functionality not yet implemented.[/yellow]")
        console.print("Use: tmux-orc list agents --session " + project_name)


def generate_system_prompt(agent: dict, project_name: str) -> str:
    """Generate a system prompt for an agent based on role and project context.

    Args:
        agent: Agent configuration dictionary
        project_name: Name of the project

    Returns:
        Generated system prompt
    """
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

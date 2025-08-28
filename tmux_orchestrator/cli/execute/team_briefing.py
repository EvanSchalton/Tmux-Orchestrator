"""Team briefing generation for PRD execution."""

from pathlib import Path

from .prd_analyzer import extract_section


def generate_team_briefings_from_prd(prd_path: Path, project_name: str, team_type: str) -> dict[str, str]:
    """Generate role-specific briefings based on PRD content.

    Returns:
        dict mapping role to customized briefing
    """
    try:
        prd_content = prd_path.read_text()
    except Exception:
        prd_content = ""

    # Extract key sections from PRD
    sections = {
        "overview": extract_section(prd_content, ["overview", "summary", "introduction"]),
        "requirements": extract_section(prd_content, ["requirements", "features", "functionality"]),
        "technical": extract_section(prd_content, ["technical", "architecture", "technology"]),
        "timeline": extract_section(prd_content, ["timeline", "milestones", "schedule"]),
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
{sections.get("overview", "See PRD for project overview")}

## Technical Requirements
{sections.get("technical", "See PRD for technical details")}

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
{sections.get("overview", "See PRD for project overview")}

## Requirements to Validate
{sections.get("requirements", "See PRD for full requirements")}

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


def create_devops_briefing(project_name: str, sections: dict[str, str]) -> str:
    """Create DevOps engineer briefing.

    Args:
        project_name: Name of the project
        sections: Extracted PRD sections

    Returns:
        DevOps briefing text
    """
    project_dir = Path.home() / "workspaces" / "Tmux-Orchestrator" / ".tmux_orchestrator" / "projects" / project_name

    return f"""You are the DevOps Engineer for {project_name}.

## Technical Requirements
{sections.get("technical", "See PRD for technical details")}

## Your Responsibilities
1. Set up CI/CD pipelines
2. Configure deployment infrastructure
3. Implement monitoring and logging
4. Ensure security best practices
5. Optimize performance and scalability

## Infrastructure Standards
- Infrastructure as Code (IaC)
- Automated deployments
- Zero-downtime deployments
- Comprehensive monitoring
- Security scanning

Wait for the PM to provide specific infrastructure tasks from {project_dir}/agents/"""


def create_architect_briefing(project_name: str, sections: dict[str, str]) -> str:
    """Create Software Architect briefing.

    Args:
        project_name: Name of the project
        sections: Extracted PRD sections

    Returns:
        Architect briefing text
    """
    Path.home() / "workspaces" / "Tmux-Orchestrator" / ".tmux_orchestrator" / "projects" / project_name

    return f"""You are the Software Architect for {project_name}.

## Project Overview
{sections.get("overview", "See PRD for project overview")}

## Technical Requirements
{sections.get("technical", "See PRD for technical details")}

## Your Responsibilities
1. Design system architecture
2. Make technology choices
3. Define coding standards
4. Review critical implementations
5. Ensure scalability and maintainability

## Architecture Standards
- Follow SOLID principles
- Microservices where appropriate
- Clear separation of concerns
- Comprehensive documentation
- Performance optimization

Review the PRD and provide architectural guidance to the team."""

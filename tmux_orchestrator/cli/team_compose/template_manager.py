"""Template management for team composition."""

from pathlib import Path
from typing import Any

import yaml

# Paths - using package data directory
try:
    import pkg_resources

    TEMPLATES_DIR = Path(pkg_resources.resource_filename("tmux_orchestrator", "data/agent_examples"))
    TEAM_TEMPLATE = Path(
        pkg_resources.resource_filename("tmux_orchestrator", "data/templates/team-composition-template.md")
    )
except ImportError:
    TEMPLATES_DIR = Path(__file__).parent.parent.parent / "data" / "agent_examples"
    TEAM_TEMPLATE = Path(__file__).parent.parent.parent / "data" / "templates" / "team-composition-template.md"


def load_agent_templates() -> dict[str, Any]:
    """Load available agent templates from the data directory.

    Returns:
        Dictionary of agent templates keyed by template name
    """
    agent_templates = {}
    if TEMPLATES_DIR.exists():
        for template_file in TEMPLATES_DIR.glob("*.yaml"):
            with open(template_file) as f:
                data = yaml.safe_load(f)
                agent_templates[template_file.stem] = data
    return agent_templates


def get_default_team_template() -> str:
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


def load_team_template(template_name: str) -> list[dict]:
    """Load a predefined team template.

    Args:
        template_name: Name of the template to load

    Returns:
        List of agent configurations for the template
    """
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
                "focus": "CLI tool development coordination",
            },
            {
                "role": "Backend Developer",
                "template": "backend-developer",
                "window": 1,
                "focus": "Core CLI functionality",
            },
            {
                "role": "Backend Developer",
                "template": "backend-developer",
                "window": 2,
                "focus": "Command parsing and validation",
            },
            {
                "role": "Test Automation",
                "template": "test-automation",
                "window": 3,
                "focus": "CLI testing",
            },
        ],
        "web-app": [
            {
                "role": "Project Manager",
                "template": "project-manager",
                "window": 0,
                "focus": "Full-stack web development",
            },
            {
                "role": "Frontend Developer",
                "template": "frontend-developer",
                "window": 1,
                "focus": "UI/UX implementation",
            },
            {
                "role": "Backend Developer",
                "template": "backend-developer",
                "window": 2,
                "focus": "Server-side logic",
            },
            {
                "role": "DevOps Engineer",
                "template": "devops-engineer",
                "window": 3,
                "focus": "Deployment and infrastructure",
            },
            {
                "role": "QA Engineer",
                "template": "qa-engineer",
                "window": 4,
                "focus": "End-to-end testing",
            },
        ],
        "data-pipeline": [
            {
                "role": "Project Manager",
                "template": "project-manager",
                "window": 0,
                "focus": "Data engineering project coordination",
            },
            {
                "role": "Data Engineer",
                "template": "data-engineer",
                "window": 1,
                "focus": "Pipeline architecture",
            },
            {
                "role": "Backend Developer",
                "template": "backend-developer",
                "window": 2,
                "focus": "Data processing logic",
            },
            {
                "role": "QA Engineer",
                "template": "qa-engineer",
                "window": 3,
                "focus": "Data validation and testing",
            },
        ],
    }

    return templates.get(template_name, [])

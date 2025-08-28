"""Core task management functionality and command group."""

import os
from pathlib import Path

import click
from rich.console import Console

console = Console()


# Base directory for all task management
def get_orchestrator_home() -> Path:
    """Get the orchestrator home directory from environment or default."""
    if "TMUX_ORCHESTRATOR_HOME" in os.environ:
        return Path(os.environ["TMUX_ORCHESTRATOR_HOME"])
    return Path.home() / ".tmux_orchestrator"


# Directory getters that respect environment variable
def get_projects_dir() -> Path:
    """Get projects directory."""
    return get_orchestrator_home() / "projects"


def get_templates_dir() -> Path:
    """Get templates directory."""
    return get_orchestrator_home() / "templates"


def get_archive_dir() -> Path:
    """Get archive directory."""
    return get_orchestrator_home() / "archive"


@click.group()
def tasks() -> None:
    """Task list management for PRD-driven development workflow.

    The tasks command group provides comprehensive task management
    capabilities for organizing PRDs, master task lists, and agent-specific
    sub-tasks across development teams.

    Directory Structure:
        .tmux_orchestrator/
        ├── projects/           # Active projects
        │   └── {project}/      # Per-project organization
        │       ├── prd.md      # Product Requirements
        │       ├── tasks.md    # Master task list
        │       └── agents/     # Agent sub-tasks
        ├── templates/          # Reusable templates
        └── archive/            # Completed projects

    Workflow:
        1. Create project structure
        2. Import or create PRD
        3. Generate master task list
        4. Distribute to agent teams
        5. Track progress
        6. Archive when complete

    Examples:
        tmux-orc tasks create my-feature
        tmux-orc tasks import-prd my-feature ./prd.md
        tmux-orc tasks distribute my-feature
        tmux-orc tasks status my-feature
    """
    # Ensure directories exist
    get_projects_dir().mkdir(parents=True, exist_ok=True)
    get_templates_dir().mkdir(parents=True, exist_ok=True)
    get_archive_dir().mkdir(parents=True, exist_ok=True)

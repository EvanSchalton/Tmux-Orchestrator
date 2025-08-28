"""Generate VS Code tasks configuration."""

from typing import Any


def generate_tasks_config(project_dir: str, minimal: bool = False) -> dict[str, Any]:
    """Generate VS Code tasks configuration."""

    tasks = []

    # Core orchestrator tasks
    orchestrator_tasks = [
        {
            "label": "🎭 Start Orchestrator",
            "type": "shell",
            "command": "tmux-orc",
            "args": ["orchestrator", "start"],
            "group": "build",
            "presentation": {
                "echo": True,
                "reveal": "always",
                "focus": False,
                "panel": "shared",
            },
            "options": {"cwd": project_dir},
            "detail": "Start the main TMUX Orchestrator session",
        },
        {
            "label": "📊 System Status",
            "type": "shell",
            "command": "tmux-orc",
            "args": ["orchestrator", "status"],
            "group": "build",
            "presentation": {
                "echo": True,
                "reveal": "always",
                "focus": False,
                "panel": "shared",
            },
            "options": {"cwd": project_dir},
            "detail": "Show comprehensive system status",
        },
        {
            "label": "⏰ Schedule Reminder",
            "type": "shell",
            "command": "tmux-orc",
            "args": [
                "orchestrator",
                "schedule",
                "${input:minutes}",
                "${input:reminderNote}",
            ],
            "group": "build",
            "presentation": {
                "echo": True,
                "reveal": "always",
                "focus": False,
                "panel": "shared",
            },
            "options": {"cwd": project_dir},
            "detail": "Schedule a reminder message",
        },
    ]

    # Team management tasks
    team_tasks = [
        {
            "label": "🚀 Deploy Frontend Team",
            "type": "shell",
            "command": "tmux-orc",
            "args": ["team", "deploy", "frontend", "${input:teamSize}"],
            "group": "build",
            "presentation": {
                "echo": True,
                "reveal": "always",
                "focus": False,
                "panel": "shared",
            },
            "options": {"cwd": project_dir},
            "detail": "Deploy a frontend development team",
        },
        {
            "label": "🚀 Deploy Backend Team",
            "type": "shell",
            "command": "tmux-orc",
            "args": ["team", "deploy", "backend", "${input:teamSize}"],
            "group": "build",
            "presentation": {
                "echo": True,
                "reveal": "always",
                "focus": False,
                "panel": "shared",
            },
            "options": {"cwd": project_dir},
            "detail": "Deploy a backend development team",
        },
        {
            "label": "🔄 Recover Team",
            "type": "shell",
            "command": "tmux-orc",
            "args": ["team", "recover", "${input:sessionName}"],
            "group": "build",
            "presentation": {
                "echo": True,
                "reveal": "always",
                "focus": False,
                "panel": "shared",
            },
            "options": {"cwd": project_dir},
            "detail": "Recover failed agents in a team",
        },
    ]

    # Agent management tasks
    agent_tasks = [
        {
            "label": "🤖 Agent Status",
            "type": "shell",
            "command": "tmux-orc",
            "args": ["agent", "status"],
            "group": "build",
            "presentation": {
                "echo": True,
                "reveal": "always",
                "focus": False,
                "panel": "shared",
            },
            "options": {"cwd": project_dir},
            "detail": "Show all agent statuses",
        },
        {
            "label": "🔄 Restart Agent",
            "type": "shell",
            "command": "tmux-orc",
            "args": ["agent", "restart", "${input:agentTarget}"],
            "group": "build",
            "presentation": {
                "echo": True,
                "reveal": "always",
                "focus": False,
                "panel": "shared",
            },
            "options": {"cwd": project_dir},
            "detail": "Restart a specific agent",
        },
        {
            "label": "💬 Message Agent",
            "type": "shell",
            "command": "tmux-orc",
            "args": ["agent", "message", "${input:agentTarget}", "${input:message}"],
            "group": "build",
            "presentation": {
                "echo": True,
                "reveal": "always",
                "focus": False,
                "panel": "shared",
            },
            "options": {"cwd": project_dir},
            "detail": "Send message to specific agent",
        },
    ]

    # Monitoring tasks
    monitor_tasks = [
        {
            "label": "📈 Monitoring Dashboard",
            "type": "shell",
            "command": "tmux-orc",
            "args": ["monitor", "dashboard"],
            "group": "build",
            "presentation": {
                "echo": True,
                "reveal": "always",
                "focus": False,
                "panel": "shared",
            },
            "options": {"cwd": project_dir},
            "detail": "Open monitoring dashboard",
        },
        {
            "label": "🏁 Start Recovery Daemon",
            "type": "shell",
            "command": "tmux-orc",
            "args": ["monitor", "recovery-start"],
            "group": "build",
            "presentation": {
                "echo": True,
                "reveal": "always",
                "focus": False,
                "panel": "shared",
            },
            "options": {"cwd": project_dir},
            "detail": "Start the agent recovery daemon",
        },
    ]

    # Project Manager tasks
    pm_tasks = [
        {
            "label": "👔 Create Project Manager",
            "type": "shell",
            "command": "tmux-orc",
            "args": ["pm", "create", "${input:sessionName}"],
            "group": "build",
            "presentation": {
                "echo": True,
                "reveal": "always",
                "focus": False,
                "panel": "shared",
            },
            "options": {"cwd": project_dir},
            "detail": "Create new Project Manager",
        },
        {
            "label": "📋 PM Status Check",
            "type": "shell",
            "command": "tmux-orc",
            "args": ["pm", "status"],
            "group": "build",
            "presentation": {
                "echo": True,
                "reveal": "always",
                "focus": False,
                "panel": "shared",
            },
            "options": {"cwd": project_dir},
            "detail": "Check Project Manager status",
        },
    ]

    # Build all tasks
    tasks.extend(orchestrator_tasks)

    if not minimal:
        tasks.extend(team_tasks)
        tasks.extend(agent_tasks)
        tasks.extend(monitor_tasks)
        tasks.extend(pm_tasks)

    # Input definitions for interactive tasks
    inputs = [
        {
            "id": "teamSize",
            "description": "Team size",
            "default": "3",
            "type": "promptString",
        },
        {
            "id": "sessionName",
            "description": "Session name",
            "default": "my-project",
            "type": "promptString",
        },
        {
            "id": "agentTarget",
            "description": "Agent target (session:window)",
            "default": "my-project:0",
            "type": "promptString",
        },
        {
            "id": "message",
            "description": "Message text",
            "default": "Status update request",
            "type": "promptString",
        },
        {
            "id": "minutes",
            "description": "Minutes from now",
            "default": "15",
            "type": "promptString",
        },
        {
            "id": "reminderNote",
            "description": "Reminder note",
            "default": "Check progress",
            "type": "promptString",
        },
    ]

    return {"version": "2.0.0", "tasks": tasks, "inputs": inputs}

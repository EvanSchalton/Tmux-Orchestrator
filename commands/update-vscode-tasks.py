#!/usr/bin/env python3
"""
Update VS Code tasks.json based on currently running agents
"""

import json
import os
import subprocess
import sys
from datetime import datetime


def get_project_name() -> str:
    """Get project name from current directory."""
    return os.path.basename(os.getcwd())


def get_running_sessions() -> list[str]:
    """Get list of running tmux sessions."""
    try:
        result = subprocess.run(
            ["tmux", "list-sessions", "-F", "#{session_name}"], capture_output=True, text=True, check=True
        )
        return result.stdout.strip().split("\n") if result.stdout.strip() else []
    except subprocess.CalledProcessError:
        return []


def get_session_windows(session):
    """Get windows for a specific session."""
    try:
        result = subprocess.run(
            ["tmux", "list-windows", "-t", session, "-F", "#{window_index}:#{window_name}"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip().split("\n") if result.stdout.strip() else []
    except subprocess.CalledProcessError:
        return []


def determine_agent_type_and_group(session, window_name):
    """Determine agent type and VS Code group based on session and window name."""
    agent_type = "Agent"
    group = "workers"

    if "pm" in session.lower() or "pm" in window_name.lower():
        agent_type = "PM"
        group = "management"
    elif "frontend" in window_name.lower():
        agent_type = "Frontend"
    elif "backend" in window_name.lower():
        agent_type = "Backend"
    elif "qa" in window_name.lower() or "testing" in window_name.lower():
        agent_type = "QA"

    return agent_type, group


def create_base_tasks(project_name):
    """Create base VS Code tasks."""
    return [
        {
            "label": "🚀 Deploy Team",
            "type": "shell",
            "command": "${workspaceFolder}/scripts/deploy.sh",
            "args": ["${input:taskFile}"],
            "group": {"kind": "build", "isDefault": True},
            "presentation": {
                "echo": True,
                "reveal": "always",
                "focus": False,
                "panel": "shared",
                "showReuseMessage": True,
                "clear": False,
            },
            "problemMatcher": [],
        },
        {
            "label": "🔄 Restart Team",
            "type": "shell",
            "command": "${workspaceFolder}/scripts/restart.sh",
            "args": ["${input:taskFile}"],
            "group": "build",
            "presentation": {"reveal": "always", "panel": "shared"},
            "problemMatcher": [],
        },
        {
            "label": "📊 List All Agents",
            "type": "shell",
            "command": "${workspaceFolder}/.tmux-orchestrator/commands/list-agents.sh",
            "group": "test",
            "presentation": {"reveal": "always", "panel": "shared", "focus": True},
            "problemMatcher": [],
        },
        {
            "label": "🎯 Agent Status Dashboard",
            "type": "shell",
            "command": "${workspaceFolder}/.tmux-orchestrator/commands/agent-status.sh",
            "group": "test",
            "presentation": {"reveal": "always", "panel": "shared", "focus": True},
            "problemMatcher": [],
        },
        {
            "label": "📋 PM Check-in (Forced)",
            "type": "shell",
            "command": "${workspaceFolder}/.tmux-orchestrator/commands/force-pm-checkin.sh",
            "group": "build",
            "presentation": {"reveal": "always", "panel": "shared", "focus": True},
            "problemMatcher": [],
        },
        {
            "label": "🎭 Open All Active Agents (Dynamic)",
            "type": "shell",
            "command": "${workspaceFolder}/.tmux-orchestrator/commands/open-all-agents.sh",
            "group": "test",
            "presentation": {"reveal": "always", "panel": "shared", "focus": True},
            "problemMatcher": [],
        },
        {
            "label": "🔄 Update VS Code Tasks",
            "type": "shell",
            "command": "python3 ${workspaceFolder}/references/Tmux-Orchestrator/commands/update-vscode-tasks.py",
            "group": "build",
            "presentation": {"reveal": "always", "panel": "shared"},
            "problemMatcher": [],
        },
        {
            "label": "🚀 Start Orchestrator",
            "type": "shell",
            "command": "${workspaceFolder}/.tmux-orchestrator/commands/start-orchestrator.sh",
            "group": "build",
            "presentation": {"reveal": "always", "panel": "shared", "focus": True},
            "problemMatcher": [],
        },
        {
            "label": "🤖 Deploy Individual Agent",
            "type": "shell",
            "command": "${workspaceFolder}/.tmux-orchestrator/commands/deploy-agent.sh",
            "args": ["${input:agentComponent}", "${input:agentRole}"],
            "group": "build",
            "presentation": {"reveal": "always", "panel": "shared", "focus": True},
            "problemMatcher": [],
        },
        {
            "label": "⏰ Schedule PM Check-in",
            "type": "shell",
            "command": "${workspaceFolder}/.tmux-orchestrator/commands/schedule-checkin.sh",
            "args": ["${input:checkInMinutes}", "${input:checkInTarget}", "${input:checkInNote}"],
            "group": "build",
            "presentation": {"reveal": "always", "panel": "shared"},
            "problemMatcher": [],
        },
        {
            "label": "💬 Send Message to Agent",
            "type": "shell",
            "command": "tmux-message",
            "args": ["${input:agentTarget}", "${input:message}"],
            "group": "build",
            "presentation": {"reveal": "always", "panel": "shared"},
            "problemMatcher": [],
        },
    ]


def create_agent_tasks(sessions, project_name):
    """Create dynamic agent tasks based on running sessions."""
    tasks = []

    # Add orchestrator sessions
    orchestrator_sessions = [s for s in sessions if "orchestrator" in s]
    for session in orchestrator_sessions:
        tasks.append(
            {
                "label": f"Open Orchestrator ({session})",
                "type": "shell",
                "command": f"tmux attach -t {session}:0",
                "presentation": {"reveal": "always", "panel": "new", "group": "management"},
                "problemMatcher": [],
            }
        )

    # Add project agent sessions
    agent_sessions = [s for s in sessions if project_name in s and "orchestrator" not in s]
    for session in agent_sessions:
        windows = get_session_windows(session)
        for window in windows:
            if "Claude" in window:
                window_index, window_name = window.split(":", 1)
                agent_type, group = determine_agent_type_and_group(session, window_name)

                tasks.append(
                    {
                        "label": f"Open {agent_type} Agent ({session})",
                        "type": "shell",
                        "command": f"tmux attach -t {session}:{window_index}",
                        "presentation": {"reveal": "always", "panel": "new", "group": group},
                        "problemMatcher": [],
                    }
                )

    return tasks


def create_utility_tasks(project_name):
    """Create utility tasks."""
    return [
        {
            "label": "🛑 Kill All Sessions",
            "type": "shell",
            "command": f'tmux list-sessions | grep "{project_name}\\|orchestrator" | cut -d: -f1 | xargs -I {{}} tmux kill-session -t {{}}',
            "group": "build",
            "presentation": {"reveal": "always", "panel": "shared"},
            "options": {"shell": {"executable": "/bin/bash"}},
            "problemMatcher": [],
        },
        {
            "label": "🔧 Emergency Reset",
            "type": "shell",
            "command": "tmux kill-server && pkill -f claude",
            "group": "build",
            "presentation": {"reveal": "always", "panel": "shared"},
            "options": {"shell": {"executable": "/bin/bash"}},
            "problemMatcher": [],
        },
    ]


def create_inputs():
    """Create VS Code task inputs."""
    return [
        {"id": "taskFile", "description": "Path to task file", "default": "tasks.md", "type": "promptString"},
        {"id": "agentTarget", "description": "Agent target (session:window)", "type": "promptString"},
        {"id": "message", "description": "Message to send to agent", "type": "promptString"},
        {
            "id": "agentComponent",
            "description": "Agent component (frontend, backend, testing, etc.)",
            "type": "pickString",
            "options": ["frontend", "backend", "testing", "database", "docs", "devops"],
        },
        {
            "id": "agentRole",
            "description": "Agent role",
            "type": "pickString",
            "options": ["developer", "pm", "qa", "reviewer"],
            "default": "developer",
        },
        {
            "id": "checkInMinutes",
            "description": "Minutes until check-in",
            "type": "pickString",
            "options": ["15", "30", "60", "120"],
            "default": "30",
        },
        {
            "id": "checkInTarget",
            "description": "Check-in target (session:window)",
            "default": "orchestrator:0",
            "type": "promptString",
        },
        {"id": "checkInNote", "description": "Check-in note/reminder", "type": "promptString"},
    ]


def main():
    print("🔄 UPDATING VS CODE TASKS")
    print("=========================")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Get project name
    project_name = get_project_name()
    if project_name == "." or not project_name:
        print("❌ Error: Cannot determine project name")
        sys.exit(1)

    # Check if tasks.json exists
    if not os.path.exists(".vscode/tasks.json"):
        print("❌ Error: .vscode/tasks.json not found")
        print("   Run the setup script first or create VS Code tasks manually")
        sys.exit(1)

    # Backup existing tasks.json
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_name = f".vscode/tasks.json.backup.{timestamp}"
    subprocess.run(["cp", ".vscode/tasks.json", backup_name])
    print(f"✓ Backup created: {backup_name}")

    # Get running sessions
    print("🔍 Detecting running agents...")
    sessions = get_running_sessions()

    # Create all tasks
    tasks = []
    tasks.extend(create_base_tasks(project_name))

    agent_tasks = create_agent_tasks(sessions, project_name)
    tasks.extend(agent_tasks)

    tasks.extend(create_utility_tasks(project_name))

    # Create final configuration
    config = {"version": "2.0.0", "tasks": tasks, "inputs": create_inputs()}

    # Write to file
    with open(".vscode/tasks.json", "w") as f:
        json.dump(config, f, indent=2)

    print()
    print("✅ VS Code tasks.json updated successfully!")
    print()
    print("📊 Task Summary:")
    print(f"   Total tasks: {len(tasks)}")
    print(f"   Dynamic agent tasks: {len(agent_tasks)}")
    print()

    if agent_tasks:
        print("🎭 Dynamic agent tasks created:")
        for task in agent_tasks:
            print(f"   - {task['label']}")
    else:
        print("⚠️ No running agents detected")
        print("   Deploy a team first, then run this script again")

    print()
    print("💡 Next steps:")
    print("   1. Reload VS Code window to see updated tasks")
    print("   2. Use Ctrl+Shift+P → 'Tasks: Run Task' to access updated commands")
    print("   3. Re-run this script when agents change to update tasks")

    # Validate JSON
    try:
        with open(".vscode/tasks.json") as f:
            json.load(f)
        print("   ✓ JSON syntax validated successfully")
    except json.JSONDecodeError as e:
        print(f"   ⚠️ JSON syntax validation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

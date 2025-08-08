#!/usr/bin/env python3
"""
Example: Setting up a PRD-driven team using CLI commands
This shows the transition from shell scripts to CLI/Python
"""

import subprocess
import time
from pathlib import Path


def run_cli(command: str) -> bool:
    """Run a CLI command and return success status."""
    try:
        result = subprocess.run(
            f"tmux-orc {command}",
            shell=True,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"✓ {command}")
            return True
        else:
            print(f"✗ {command}: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ {command}: {e}")
        return False


def setup_prd_team(project_name: str, project_dir: str, prd_path: str, task_list_path: str):
    """Set up a complete PRD-driven development team using CLI commands."""
    
    print(f"🚀 Setting up PRD-driven team for: {project_name}")
    print(f"   PRD: {prd_path}")
    print(f"   Tasks: {task_list_path}")
    
    # 1. Deploy the team structure
    print("\n📦 Deploying team structure...")
    if not run_cli(f'team deploy fullstack 5 --project-name "{project_name}"'):
        return False
    
    time.sleep(5)  # Let agents initialize
    
    # 2. Send PRD to PM
    print("\n📄 Sending PRD to Project Manager...")
    with open(prd_path, 'r') as f:
        prd_content = f.read()
    
    # Escape the content for shell
    prd_message = f"""You are the Project Manager for {project_name}.

Here is the PRD for our project:

{prd_content}

Please review and prepare to execute the development workflow."""
    
    if not run_cli(f'publish --session {project_name}:0 "{prd_message}"'):
        print("Failed to send PRD to PM")
        return False
    
    time.sleep(3)
    
    # 3. Send task list to PM
    print("\n📋 Sending task list to Project Manager...")
    with open(task_list_path, 'r') as f:
        task_content = f.read()
    
    task_message = f"""Here is the complete task list generated from the PRD:

{task_content}

Please:
1. Break this into chunks for Frontend, Backend, and QA teams
2. Use /workspaces/Tmux-Orchestrator/.claude/commands/process-task-list.md when distributing
3. Enforce quality gates (all tests/linting must pass)
4. Report progress regularly using the proactive status format

Begin by analyzing the tasks and creating sub-lists for each team."""
    
    if not run_cli(f'publish --session {project_name}:0 --priority high --tag tasks "{task_message}"'):
        print("Failed to send tasks to PM")
        return False
    
    # 4. Brief the development teams
    print("\n👥 Briefing development teams...")
    
    # Frontend Developer
    fe_brief = """You are the Frontend Developer. You will receive task lists from the PM.

Requirements:
- Execute tasks using /workspaces/Tmux-Orchestrator/.claude/commands/process-task-list.md
- All tests must pass (npm test)
- No linting errors (npm run lint)
- Commit every 30 minutes
- Report status proactively after each task completion using:

**STATUS UPDATE Frontend-Dev**: 
✅ Completed: [what you finished]
🔄 Currently: [what you're working on]
🚧 Next: [what you'll do next]
⏱️ ETA: [completion time]
❌ Blockers: [any issues]"""
    
    run_cli(f'publish --session {project_name}:1 "{fe_brief}"')
    
    # Backend Developer
    be_brief = """You are the Backend Developer. You will receive task lists from the PM.

Requirements:
- Execute tasks using /workspaces/Tmux-Orchestrator/.claude/commands/process-task-list.md
- All tests must pass (pytest)
- No linting errors (ruff check)
- Type checking must pass (mypy)
- Commit every 30 minutes
- Report status proactively using the standard format"""
    
    run_cli(f'publish --session {project_name}:2 "{be_brief}"')
    
    # QA Engineer
    qa_brief = """You are the QA Engineer. You will receive test plans from the PM.

Responsibilities:
- Manual testing of all user flows
- Report bugs in batches with reproduction steps
- Include screenshots/logs for issues
- Suggest test scenarios for automation
- Use Playwright MCP if needed"""
    
    run_cli(f'publish --session {project_name}:3 "{qa_brief}"')
    
    # Test Engineer
    test_brief = """You are the Test Engineer. You will receive QA workflows to automate.

Responsibilities:
- Create Playwright tests for UI flows
- Create pytest tests for APIs
- Ensure tests are maintainable
- No flaky tests allowed
- Document all test scenarios"""
    
    run_cli(f'publish --session {project_name}:4 "{test_brief}"')
    
    # 5. Start monitoring
    print("\n📊 Starting monitoring daemon...")
    subprocess.Popen([
        "/workspaces/Tmux-Orchestrator/commands/idle-monitor-daemon.sh", "15"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # 6. Show status
    print("\n✅ Team deployed successfully!")
    run_cli("status")
    
    print(f"""
📌 Next Steps:
1. Monitor PM progress: tmux-orc read --session {project_name}:0 --tail 50
2. Check team status: tmux-orc pubsub status
3. Search for issues: tmux-orc search "error" --all-sessions
4. Attach to session: tmux attach -t {project_name}

💡 The PM will now:
- Distribute tasks to development teams
- Monitor quality gates
- Coordinate QA testing
- Report progress back to you
""")


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) != 5:
        print("Usage: python cli-setup-team.py <project_name> <project_dir> <prd_path> <task_list_path>")
        print("Example: python cli-setup-team.py my-app /workspace/my-app ./prd.md ./tasks.md")
        sys.exit(1)
    
    project_name = sys.argv[1]
    project_dir = sys.argv[2]
    prd_path = sys.argv[3]
    task_list_path = sys.argv[4]
    
    setup_prd_team(project_name, project_dir, prd_path, task_list_path)
"""Project Manager specific functionality."""

from datetime import datetime

from tmux_orchestrator.utils.tmux import TMUXManager


class PMManager:
    """Manages Project Manager operations."""

    PM_BRIEFING = """You are the Project Manager for {project}.

Task file: {task_file}

Your responsibilities:
1. Break down tasks into manageable work items
2. Create test plans BEFORE implementation
3. Ensure TDD principles are followed
4. Track progress and update documentation
5. Coordinate between all team members
6. Maintain EXCEPTIONAL quality standards

🤖 AGENT COMMUNICATION COMMANDS:
- Send message to any agent: tmux-message <session:window> 'your message'
- Available agents:
{agent_list}
- Check agent status: tmux-orc agent status
- List all agents: tmux-orc list

⚠️ IMPORTANT - MESSAGE SUBMISSION:
- After typing tmux-message command, press Enter
- VERIFY you see 'Message sent to...' confirmation
- If no confirmation appears, press Enter again
- Messages may need 2-3 Enter presses to submit properly

🔄 AGENT RESTART & RECOVERY:
When agents fail and need restart, use the team plan you created to determine their role briefing, then restart with:
claude --dangerously-skip-permissions --system-prompt "[role from team plan]"

Steps for agent recovery:
1. Navigate to failed agent's window: tmux select-window -t <session:window>
2. Reference your team plan for the correct role briefing
3. Restart with proper role: claude --dangerously-skip-permissions --system-prompt "..."
4. Verify agent is responsive before reassigning tasks

Critical: No shortcuts allowed. Quality over speed.
Please read the task file and create an implementation plan."""

    def __init__(self, tmux: TMUXManager):
        self.tmux = tmux

    def find_pm_session(self) -> str | None:
        """Find the PM session and window."""
        sessions = self.tmux.list_sessions()

        for session in sessions:
            windows = self.tmux.list_windows(session["name"])
            for window in windows:
                # Check for PM window patterns
                if any(pattern in window["name"].lower() for pattern in ["pm", "project-manager", "claude-pm"]):
                    return f"{session['name']}:{window['index']}"

        return None

    def deploy_pm(self, project_name: str, task_file: str | None = None) -> str:
        """Deploy a Project Manager."""
        session_name = f"{project_name}-{project_name}"  # Following the pattern

        # Create session if needed
        if not self.tmux.has_session(session_name):
            from pathlib import Path

            project_path = Path.cwd()
            self.tmux.create_session(session_name, "Shell", str(project_path))

        # Create PM window
        window_name = "Claude-pm"
        self.tmux.create_window(session_name, window_name, str(Path.cwd()))

        # Get window index
        windows = self.tmux.list_windows(session_name)
        window_idx = None
        for window in windows:
            if window["name"] == window_name:
                window_idx = window["index"]
                break

        if window_idx is None:
            raise RuntimeError("Failed to create PM window")

        # Start Claude
        target = f"{session_name}:{window_idx}"
        self._start_claude_pm(target)

        # Brief the PM
        import time

        time.sleep(5)
        briefing = self._get_pm_briefing(project_name, task_file)
        self.tmux.send_message(target, briefing)

        return target

    def _start_claude_pm(self, target: str) -> None:
        """Start Claude for PM."""
        # Set up environment
        self.tmux.send_keys(target, "export TERM=xterm-256color")
        self.tmux.send_keys(target, "Enter")

        # Activate venv if exists
        from pathlib import Path

        if Path(".venv").exists():
            self.tmux.send_keys(target, "source .venv/bin/activate")
            self.tmux.send_keys(target, "Enter")
            import time

            time.sleep(2)

        # Start Claude
        self.tmux.send_keys(
            target,
            "FORCE_COLOR=1 NODE_NO_WARNINGS=1 claude --dangerously-skip-permissions",
        )
        self.tmux.send_keys(target, "Enter")

    def _get_pm_briefing(self, project_name: str, task_file: str | None) -> str:
        """Get PM briefing with agent list."""
        # Get list of agents
        agents = self.tmux.list_agents()
        agent_list = []

        for agent in agents:
            if agent["type"] != "PM":  # Don't list self
                agent_list.append(f"  • {agent['type']}: tmux-message {agent['session']}:{agent['window']} 'message'")

        return self.PM_BRIEFING.format(
            project=project_name,
            task_file=task_file or "Not specified",
            agent_list="\n".join(agent_list) if agent_list else "  • No agents deployed yet",
        )

    def trigger_status_review(self) -> None:
        """Trigger PM to review status of all agents."""
        pm_target = self.find_pm_session()
        if not pm_target:
            raise RuntimeError("No PM session found")

        # Gather status from all agents
        agents = self.tmux.list_agents()
        status_report = self._build_status_report(agents)

        # Send to PM
        self.tmux.send_message(pm_target, status_report)

    def _build_status_report(self, agents: list[dict]) -> str:
        """Build a status report for PM."""
        report = f"""📊 TEAM STATUS REPORT - {datetime.now().strftime("%Y-%m-%d %H:%M")}
========================================

AGENT STATUS:"""

        for agent in agents:
            if agent["type"] == "PM":
                continue

            target = f"{agent['session']}:{agent['window']}"
            pane_content = self.tmux.capture_pane(target, lines=50)

            # Extract key info
            status = "🟢 Active" if agent["status"] == "Active" else "🔴 Idle"
            last_output = self._get_last_meaningful_output(pane_content)

            report += f"""

{agent["type"]} Agent ({target}):
- Status: {status}
- Last Activity: {last_output}"""

        report += """

📋 PM COORDINATION INSTRUCTIONS:
===============================

Based on the above status, please:

1. REVIEW each agent's current activity and progress
2. IDENTIFY any agents that appear idle or blocked
3. PROVIDE individual guidance using these commands:
   • tmux-message <session:window> 'your guidance here'
4. ENSURE all agents are working on priority tasks
5. RESOLVE any dependencies or blockers

Remember: Quality over speed. No shortcuts."""

        return report

    def _get_last_meaningful_output(self, pane_content: str) -> str:
        """Extract last meaningful output from pane."""
        lines = pane_content.strip().split("\n")

        # Skip empty lines and prompts
        for line in reversed(lines):
            line = line.strip()
            if line and not line.startswith("│") and not line.startswith(">"):
                return line[:100] + "..." if len(line) > 100 else line

        return "No recent output"

    def broadcast_to_all_agents(self, message: str) -> dict[str, bool]:
        """Broadcast a message to all agents."""
        agents = self.tmux.list_agents()
        results = {}

        for agent in agents:
            if agent["type"] == "PM":
                continue

            target = f"{agent['session']}:{agent['window']}"
            success = self.tmux.send_message(target, message)
            results[target] = success

        return results

    def custom_checkin(self, custom_message: str) -> dict[str, bool]:
        """Send custom check-in message to all agents."""
        full_message = f"""🔔 PM CHECK-IN REQUEST:

{custom_message}

Please respond with:
1. Current status
2. Any blockers
3. Expected completion time for current task"""

        return self.broadcast_to_all_agents(full_message)

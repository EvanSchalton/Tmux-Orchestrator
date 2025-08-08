"""Agent management functionality."""

from pathlib import Path
from typing import Any, Dict, List, Optional

from tmux_orchestrator.utils.tmux import TMUXManager


class AgentManager:
    """Manages individual agents."""

    AGENT_BRIEFINGS = {
        'frontend': {
            'developer': """You are the Frontend Developer for {project}.

Task file: {task_file}

Focus on:
- UI/UX implementation tasks
- React/TypeScript components
- User interactions and flows
- Responsive design
- Accessibility

Requirements:
- Follow existing code patterns
- Run 'npm run build' after every change
- Write tests for all components
- Use feature branches
- Commit every 30 minutes

Read the task file and identify all frontend-related tasks.""",
            'qa': """You are the Frontend QA Engineer for {project}.

Focus on:
- UI testing with Playwright
- Visual regression testing
- Cross-browser compatibility
- Accessibility testing
- Performance testing"""
        },
        'backend': {
            'developer': """You are the Backend Developer for {project}.

Task file: {task_file}

Focus on:
- API endpoints and services
- Business logic implementation
- Data processing pipelines
- Database operations
- Error handling

Requirements:
- Follow Python/FastAPI patterns
- Use poetry for dependencies
- Write pytest tests
- Proper error handling
- Feature branches
- Commit every 30 minutes

Read the task file and identify all backend tasks.""",
            'qa': """You are the Backend QA Engineer for {project}.

Focus on:
- API testing
- Integration testing
- Load testing
- Security testing
- Data validation"""
        },
        'testing': {
            'qa': """You are the QA Engineer for {project}.

Task file: {task_file}

Your responsibilities:
1. Create comprehensive test plans
2. Write E2E tests with Playwright MCP
3. Test all user workflows
4. Performance testing
5. Regression testing
6. Security testing

Tools available:
- Playwright MCP for browser automation
- pytest for unit/integration tests
- Load testing tools

Work closely with developers to understand features before testing.
Read the task file and plan your testing strategy."""
        }
    }

    def __init__(self, tmux: TMUXManager):
        self.tmux = tmux

    def deploy_agent(self, agent_type: str, role: str, project_name: Optional[str] = None,
                    task_file: Optional[str] = None) -> str:
        """Deploy a new agent."""
        if not project_name:
            project_name = Path.cwd().name

        # Create session name
        session_name = f"{project_name}-{agent_type}"

        # Check if session exists
        if not self.tmux.has_session(session_name):
            # Create new session
            project_path = Path.cwd()
            self.tmux.create_session(session_name, "Shell", str(project_path))

        # Create Claude window
        window_name = f"Claude-{role}"
        self.tmux.create_window(session_name, window_name, str(Path.cwd()))

        # Get window index
        windows = self.tmux.list_windows(session_name)
        window_idx = None
        for window in windows:
            if window['name'] == window_name:
                window_idx = window['index']
                break

        if window_idx is None:
            raise RuntimeError(f"Failed to create window for {agent_type} {role}")

        # Start Claude
        target = f"{session_name}:{window_idx}"
        self._start_claude(target)

        # Brief the agent
        briefing = self._get_briefing(agent_type, role, project_name, task_file)
        if briefing:
            import time
            time.sleep(5)  # Wait for Claude to start
            self.tmux.send_message(target, briefing)

        return session_name

    def _start_claude(self, target: str) -> None:
        """Start Claude in a window."""
        # Set up environment
        self.tmux.send_keys(target, 'export TERM=xterm-256color')
        self.tmux.send_keys(target, 'Enter')

        # Activate venv if exists
        if Path('.venv').exists():
            self.tmux.send_keys(target, 'source .venv/bin/activate')
            self.tmux.send_keys(target, 'Enter')
            import time
            time.sleep(2)

        # Start Claude
        self.tmux.send_keys(target, 'FORCE_COLOR=1 NODE_NO_WARNINGS=1 claude --dangerously-skip-permissions')
        self.tmux.send_keys(target, 'Enter')

    def _get_briefing(self, agent_type: str, role: str, project_name: str, task_file: Optional[str]) -> Optional[str]:
        """Get briefing for an agent."""
        if agent_type in self.AGENT_BRIEFINGS and role in self.AGENT_BRIEFINGS[agent_type]:
            briefing = self.AGENT_BRIEFINGS[agent_type][role]
            return briefing.format(
                project=project_name,
                task_file=task_file or "Not specified"
            )
        return None

    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all agents."""
        agents = self.tmux.list_agents()
        statuses = {}

        for agent in agents:
            agent_id = f"{agent['session']}:{agent['window']}"
            pane_content = self.tmux.capture_pane(agent_id, lines=100)

            # Analyze content for status
            status = {
                'state': agent['status'],
                'type': agent['type'],
                'last_activity': self._get_last_activity(pane_content),
                'current_task': self._extract_current_task(pane_content)
            }

            statuses[agent_id] = status

        return statuses

    def _get_last_activity(self, pane_content: str) -> str:
        """Extract last activity timestamp from pane content."""
        # Look for timestamp patterns
        import re
        timestamp_pattern = r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]'
        matches: List[str] = re.findall(timestamp_pattern, pane_content)

        if matches:
            return str(matches[-1])

        # Look for relative timestamps
        relative_patterns = [
            r'(\d+ minutes? ago)',
            r'(\d+ hours? ago)',
            r'(just now)'
        ]

        for pattern in relative_patterns:
            match = re.search(pattern, pane_content, re.IGNORECASE)
            if match:
                return match.group(1)

        return "Unknown"

    def _extract_current_task(self, pane_content: str) -> Optional[str]:
        """Extract current task from pane content."""
        # Look for task indicators
        import re
        task_patterns = [
            r'(?:working on|implementing|creating|fixing|updating)\s+(.+?)(?:\.|$)',
            r'current task:\s*(.+?)(?:\.|$)',
            r'task:\s*(.+?)(?:\.|$)'
        ]

        for pattern in task_patterns:
            match = re.search(pattern, pane_content, re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1).strip()

        return None

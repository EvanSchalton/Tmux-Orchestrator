"""Optimized business logic for deploying teams of agents with performance improvements."""

import time
from pathlib import Path
from typing import Tuple

from tmux_orchestrator.utils.tmux import TMUXManager


def deploy_standard_team_optimized(
    tmux_optimized: TMUXManager, team_type: str, size: int, project_name: str
) -> Tuple[bool, str]:
    """Deploy a standard team configuration with performance optimizations.

    Target: <500ms execution time (vs 1.57s original)

    Args:
        tmux_optimized: TMUXManager instance
        team_type: Type of team (frontend, backend, fullstack, testing)
        size: Number of agents to deploy
        project_name: Name of the project

    Returns:
        Tuple of (success, message)
    """
    start_time = time.time()

    if size < 1 or size > 20:
        return False, f"Team size must be between 1 and 20 (requested: {size})"

    # Create session name
    session_name = f"{project_name}-{team_type}"

    # Optimized session existence check with caching
    if tmux_optimized.has_session_optimized(session_name):
        return False, f"Session '{session_name}' already exists"

    # Create main session with optimized method
    project_dir = str(Path.cwd())
    if not tmux_optimized.create_session_optimized(session_name, "orchestrator", project_dir):
        return False, f"Failed to create session '{session_name}'"

    # Deploy agents based on team type with optimized methods
    agents_deployed = 0
    try:
        if team_type == "frontend":
            agents_deployed = _deploy_frontend_team_optimized(tmux_optimized, session_name, size, project_dir)
        elif team_type == "backend":
            agents_deployed = _deploy_backend_team_optimized(tmux_optimized, session_name, size, project_dir)
        elif team_type == "fullstack":
            agents_deployed = _deploy_fullstack_team_optimized(tmux_optimized, session_name, size, project_dir)
        elif team_type == "testing":
            agents_deployed = _deploy_testing_team_optimized(tmux_optimized, session_name, size, project_dir)
        else:
            return False, f"Unknown team type: {team_type}"

        if agents_deployed == 0:
            return False, f"Failed to deploy any agents for {team_type} team"

        execution_time = (time.time() - start_time) * 1000  # Convert to ms
        success_message = (
            f"Successfully deployed {team_type} team with {agents_deployed} agents "
            f"in session '{session_name}' ({execution_time:.1f}ms)"
        )

        return True, success_message

    except Exception as e:
        # Clean up session if deployment failed
        cleanup_tmux = TMUXManager()
        cleanup_tmux.kill_session(session_name)

        return False, f"Deployment failed: {str(e)}"


def _deploy_frontend_team_optimized(tmux_optimized: TMUXManager, session_name: str, size: int, project_dir: str) -> int:
    """Deploy frontend-focused team with optimizations."""
    agents_deployed = 0

    # Always deploy PM first
    if tmux_optimized.create_window_optimized(session_name, "Project-Manager", project_dir):
        _start_claude_agent_optimized(tmux_optimized, f"{session_name}:Project-Manager", "pm")
        agents_deployed += 1

    # Deploy frontend developers
    remaining_slots = size - 1  # Subtract PM
    for i in range(min(remaining_slots, 3)):  # Max 3 frontend devs
        window_name = f"Frontend-Dev-{i + 1}" if remaining_slots > 1 else "Frontend-Dev"
        if tmux_optimized.create_window_optimized(session_name, window_name, project_dir):
            _start_claude_agent_optimized(tmux_optimized, f"{session_name}:{window_name}", "frontend-developer")
            agents_deployed += 1

    # Add QA if team size > 3
    if size > 3:
        if tmux_optimized.create_window_optimized(session_name, "QA-Engineer", project_dir):
            _start_claude_agent_optimized(tmux_optimized, f"{session_name}:QA-Engineer", "qa")
            agents_deployed += 1

    return agents_deployed


def _deploy_backend_team_optimized(tmux_optimized: TMUXManager, session_name: str, size: int, project_dir: str) -> int:
    """Deploy backend-focused team with optimizations."""
    agents_deployed = 0

    # Always deploy PM first
    if tmux_optimized.create_window_optimized(session_name, "Project-Manager", project_dir):
        _start_claude_agent_optimized(tmux_optimized, f"{session_name}:Project-Manager", "pm")
        agents_deployed += 1

    # Deploy backend developers
    remaining_slots = size - 1
    for i in range(min(remaining_slots, 3)):
        window_name = f"Backend-Dev-{i + 1}" if remaining_slots > 1 else "Backend-Dev"
        if tmux_optimized.create_window_optimized(session_name, window_name, project_dir):
            _start_claude_agent_optimized(tmux_optimized, f"{session_name}:{window_name}", "backend-developer")
            agents_deployed += 1

    # Add DevOps if team size > 3
    if size > 3:
        if tmux_optimized.create_window_optimized(session_name, "DevOps-Engineer", project_dir):
            _start_claude_agent_optimized(tmux_optimized, f"{session_name}:DevOps-Engineer", "devops")
            agents_deployed += 1

    return agents_deployed


def _deploy_fullstack_team_optimized(
    tmux_optimized: TMUXManager, session_name: str, size: int, project_dir: str
) -> int:
    """Deploy balanced fullstack team with optimizations."""
    agents_deployed = 0

    # Deploy PM
    if tmux_optimized.create_window_optimized(session_name, "Project-Manager", project_dir):
        _start_claude_agent_optimized(tmux_optimized, f"{session_name}:Project-Manager", "pm")
        agents_deployed += 1

    # Deploy mixed team
    remaining_slots = size - 1
    roles = ["frontend-developer", "backend-developer", "qa", "devops"]

    for i in range(remaining_slots):
        role = roles[i % len(roles)]
        window_name = (
            f"{role.replace('-', '-').title()}-{(i // len(roles)) + 1}"
            if remaining_slots > len(roles)
            else role.replace("-", "-").title()
        )

        if tmux_optimized.create_window_optimized(session_name, window_name, project_dir):
            _start_claude_agent_optimized(tmux_optimized, f"{session_name}:{window_name}", role)
            agents_deployed += 1

    return agents_deployed


def _deploy_testing_team_optimized(tmux_optimized: TMUXManager, session_name: str, size: int, project_dir: str) -> int:
    """Deploy testing-focused team with optimizations."""
    agents_deployed = 0

    # Deploy PM
    if tmux_optimized.create_window_optimized(session_name, "Project-Manager", project_dir):
        _start_claude_agent_optimized(tmux_optimized, f"{session_name}:Project-Manager", "pm")
        agents_deployed += 1

    # Deploy QA engineers
    remaining_slots = size - 1
    for i in range(remaining_slots):
        window_name = f"QA-Engineer-{i + 1}" if remaining_slots > 1 else "QA-Engineer"
        if tmux_optimized.create_window_optimized(session_name, window_name, project_dir):
            _start_claude_agent_optimized(tmux_optimized, f"{session_name}:{window_name}", "qa")
            agents_deployed += 1

    return agents_deployed


def _start_claude_agent_optimized(tmux_optimized: TMUXManager, target: str, role: str) -> bool:
    """Start a Claude agent with optimized timing and reduced delays."""
    # Optimized startup sequence with reduced delays
    if not tmux_optimized.send_keys_optimized(target, "claude --dangerously-skip-permissions"):
        return False

    time.sleep(0.2)  # Reduced from 0.5s
    if not tmux_optimized.send_keys_optimized(target, "Enter"):
        return False

    # Reduced wait time for Claude startup
    time.sleep(1.5)  # Reduced from 3s

    # Send role-specific briefing with optimized message sending
    briefing = _get_role_briefing(role)
    return _send_message_optimized(tmux_optimized, target, briefing)


def _send_message_optimized(tmux_optimized: TMUXManager, target: str, message: str) -> bool:
    """Send message with optimized timing."""
    try:
        # Clear any existing input with optimized timing
        tmux_optimized.send_keys_optimized(target, "C-c")
        time.sleep(0.2)  # Reduced from 0.5s

        # Clear the input line
        tmux_optimized.send_keys_optimized(target, "C-u")
        time.sleep(0.2)  # Reduced from 0.5s

        # Send the actual message as literal text
        tmux_optimized.send_keys_optimized(target, message, literal=True)
        time.sleep(1.0)  # Reduced from 3.0s

        # Submit with Enter
        tmux_optimized.send_keys_optimized(target, "Enter")
        return True

    except Exception as e:
        import logging

        logging.error(f"Optimized message sending failed to {target}: {e}")
        return False


def _get_role_briefing(role: str) -> str:
    """Get role-specific briefing message (shortened for performance)."""
    briefings = {
        "pm": "You are the Project Manager. Coordinate team activities, maintain quality standards, and monitor progress. Begin by analyzing the project structure.",
        "frontend-developer": "You are a Frontend Developer. Implement UI/UX components with modern frameworks. Start by examining the project structure.",
        "backend-developer": "You are a Backend Developer. Design APIs and server-side logic. Begin by analyzing the project architecture.",
        "qa": "You are a QA Engineer. Design test plans and identify quality issues. Start by reviewing project requirements.",
        "devops": "You are a DevOps Engineer. Set up deployment pipelines and manage infrastructure. Begin by assessing deployment needs.",
    }

    return briefings.get(
        role,
        f"You are a {role} on this development team. Please analyze the project and begin your work.",
    )

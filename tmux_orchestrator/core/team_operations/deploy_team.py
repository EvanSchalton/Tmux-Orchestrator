"""Business logic for deploying teams of agents."""

from typing import Tuple, List, Dict, Any
from pathlib import Path

from tmux_orchestrator.utils.tmux import TMUXManager


def deploy_standard_team(
    tmux: TMUXManager, 
    team_type: str, 
    size: int, 
    project_name: str
) -> Tuple[bool, str]:
    """Deploy a standard team configuration.
    
    Args:
        tmux: TMUXManager instance
        team_type: Type of team (frontend, backend, fullstack, testing)
        size: Number of agents to deploy
        project_name: Name of the project
        
    Returns:
        Tuple of (success, message)
    """
    if size < 1 or size > 20:
        return False, f"Team size must be between 1 and 20 (requested: {size})"
    
    # Create session name
    session_name = f"{project_name}-{team_type}"
    
    # Check if session already exists
    if tmux.has_session(session_name):
        return False, f"Session '{session_name}' already exists"
    
    # Create main session
    project_dir = str(Path.cwd())
    if not tmux.create_session(session_name, "orchestrator", project_dir):
        return False, f"Failed to create session '{session_name}'"
    
    # Deploy agents based on team type
    agents_deployed = 0
    try:
        if team_type == "frontend":
            agents_deployed = _deploy_frontend_team(tmux, session_name, size, project_dir)
        elif team_type == "backend":
            agents_deployed = _deploy_backend_team(tmux, session_name, size, project_dir)
        elif team_type == "fullstack":
            agents_deployed = _deploy_fullstack_team(tmux, session_name, size, project_dir)
        elif team_type == "testing":
            agents_deployed = _deploy_testing_team(tmux, session_name, size, project_dir)
        else:
            return False, f"Unknown team type: {team_type}"
        
        if agents_deployed == 0:
            return False, f"Failed to deploy any agents for {team_type} team"
        
        return True, f"Successfully deployed {team_type} team with {agents_deployed} agents in session '{session_name}'"
        
    except Exception as e:
        # Clean up session if deployment failed
        tmux.kill_session(session_name)
        return False, f"Deployment failed: {str(e)}"


def _deploy_frontend_team(
    tmux: TMUXManager, 
    session_name: str, 
    size: int, 
    project_dir: str
) -> int:
    """Deploy frontend-focused team."""
    agents_deployed = 0
    
    # Always deploy PM first
    if tmux.create_window(session_name, "Project-Manager", project_dir):
        _start_claude_agent(tmux, f"{session_name}:Project-Manager", "pm")
        agents_deployed += 1
    
    # Deploy frontend developers
    remaining_slots = size - 1  # Subtract PM
    for i in range(min(remaining_slots, 3)):  # Max 3 frontend devs
        window_name = f"Frontend-Dev-{i+1}" if remaining_slots > 1 else "Frontend-Dev"
        if tmux.create_window(session_name, window_name, project_dir):
            _start_claude_agent(tmux, f"{session_name}:{window_name}", "frontend-developer")
            agents_deployed += 1
    
    # Add QA if team size > 3
    if size > 3:
        if tmux.create_window(session_name, "QA-Engineer", project_dir):
            _start_claude_agent(tmux, f"{session_name}:QA-Engineer", "qa")
            agents_deployed += 1
    
    return agents_deployed


def _deploy_backend_team(
    tmux: TMUXManager,
    session_name: str,
    size: int, 
    project_dir: str
) -> int:
    """Deploy backend-focused team."""
    agents_deployed = 0
    
    # Always deploy PM first
    if tmux.create_window(session_name, "Project-Manager", project_dir):
        _start_claude_agent(tmux, f"{session_name}:Project-Manager", "pm")
        agents_deployed += 1
    
    # Deploy backend developers
    remaining_slots = size - 1
    for i in range(min(remaining_slots, 3)):
        window_name = f"Backend-Dev-{i+1}" if remaining_slots > 1 else "Backend-Dev"
        if tmux.create_window(session_name, window_name, project_dir):
            _start_claude_agent(tmux, f"{session_name}:{window_name}", "backend-developer")
            agents_deployed += 1
    
    # Add DevOps if team size > 3
    if size > 3:
        if tmux.create_window(session_name, "DevOps-Engineer", project_dir):
            _start_claude_agent(tmux, f"{session_name}:DevOps-Engineer", "devops")
            agents_deployed += 1
    
    return agents_deployed


def _deploy_fullstack_team(
    tmux: TMUXManager,
    session_name: str,
    size: int,
    project_dir: str
) -> int:
    """Deploy balanced fullstack team."""
    agents_deployed = 0
    
    # Deploy PM
    if tmux.create_window(session_name, "Project-Manager", project_dir):
        _start_claude_agent(tmux, f"{session_name}:Project-Manager", "pm")
        agents_deployed += 1
    
    # Deploy mixed team
    remaining_slots = size - 1
    roles = ["frontend-developer", "backend-developer", "qa", "devops"]
    
    for i in range(remaining_slots):
        role = roles[i % len(roles)]
        window_name = f"{role.replace('-', '-').title()}-{(i//len(roles))+1}" if remaining_slots > len(roles) else role.replace('-', '-').title()
        
        if tmux.create_window(session_name, window_name, project_dir):
            _start_claude_agent(tmux, f"{session_name}:{window_name}", role)
            agents_deployed += 1
    
    return agents_deployed


def _deploy_testing_team(
    tmux: TMUXManager,
    session_name: str,
    size: int,
    project_dir: str
) -> int:
    """Deploy testing-focused team."""
    agents_deployed = 0
    
    # Deploy PM
    if tmux.create_window(session_name, "Project-Manager", project_dir):
        _start_claude_agent(tmux, f"{session_name}:Project-Manager", "pm")
        agents_deployed += 1
    
    # Deploy QA engineers
    remaining_slots = size - 1
    for i in range(remaining_slots):
        window_name = f"QA-Engineer-{i+1}" if remaining_slots > 1 else "QA-Engineer"
        if tmux.create_window(session_name, window_name, project_dir):
            _start_claude_agent(tmux, f"{session_name}:{window_name}", "qa")
            agents_deployed += 1
    
    return agents_deployed


def _start_claude_agent(tmux: TMUXManager, target: str, role: str) -> bool:
    """Start a Claude agent in the specified target with role briefing."""
    import time
    
    # Start Claude
    if not tmux.send_keys(target, 'claude --dangerously-skip-permissions'):
        return False
    
    time.sleep(0.5)
    if not tmux.send_keys(target, 'Enter'):
        return False
    
    # Wait for Claude to start
    time.sleep(3)
    
    # Send role-specific briefing
    briefing = _get_role_briefing(role)
    return tmux.send_message(target, briefing)


def _get_role_briefing(role: str) -> str:
    """Get role-specific briefing message."""
    briefings = {
        "pm": """You are the Project Manager for this development team. Your responsibilities:
1. Coordinate team activities and maintain project timeline
2. Ensure quality standards are met across all deliverables  
3. Monitor progress and identify blockers quickly
4. Facilitate communication between team members
5. Report status updates to the orchestrator

Begin by analyzing the project structure and creating an initial project plan.""",
        
        "frontend-developer": """You are a Frontend Developer on this team. Your responsibilities:
1. Implement user interfaces and user experience components
2. Work with modern frontend frameworks and tools
3. Ensure responsive design and accessibility standards
4. Collaborate with backend developers on API integration
5. Write and maintain frontend tests

Start by examining the project structure and identifying frontend requirements.""",
        
        "backend-developer": """You are a Backend Developer on this team. Your responsibilities:
1. Design and implement server-side logic and APIs
2. Work with databases and data modeling
3. Ensure security, performance, and scalability
4. Collaborate with frontend developers on API contracts
5. Write and maintain backend tests

Begin by analyzing the project architecture and backend requirements.""",
        
        "qa": """You are a QA Engineer on this team. Your responsibilities:
1. Design and execute comprehensive test plans
2. Identify bugs and quality issues early in development
3. Automate testing processes where possible
4. Ensure testing coverage across all features
5. Validate that requirements are properly implemented

Start by reviewing the project requirements and creating a testing strategy.""",
        
        "devops": """You are a DevOps Engineer on this team. Your responsibilities:
1. Set up and maintain development and deployment pipelines
2. Manage infrastructure and deployment processes
3. Ensure system reliability and monitoring
4. Implement security best practices
5. Optimize development workflows

Begin by assessing the current infrastructure and deployment needs."""
    }
    
    return briefings.get(role, f"You are a {role} on this development team. Please analyze the project and begin contributing to your assigned role.")


def recover_team_agents(tmux: TMUXManager, session_name: str) -> Tuple[bool, str]:
    """Recover failed agents in a team session.
    
    Args:
        tmux: TMUXManager instance
        session_name: Name of the session to recover
        
    Returns:
        Tuple of (success, message)
    """
    if not tmux.has_session(session_name):
        return False, f"Session '{session_name}' not found"
    
    # Get all windows in the session
    windows = tmux.list_windows(session_name)
    if not windows:
        return False, f"No windows found in session '{session_name}'"
    
    recovered_agents = 0
    failed_recoveries = 0
    
    for window in windows:
        target = f"{session_name}:{window['index']}"
        window_name = window['name'].lower()
        
        # Skip non-agent windows
        if not any(keyword in window_name for keyword in ['claude', 'pm', 'dev', 'qa', 'engineer']):
            continue
        
        # Check if agent needs recovery
        pane_content = tmux.capture_pane(target, lines=10)
        if _agent_needs_recovery(pane_content):
            # Attempt recovery using existing restart logic
            from tmux_orchestrator.core.agent_operations.restart_agent import restart_agent
            success, _ = restart_agent(tmux, target)
            
            if success:
                recovered_agents += 1
            else:
                failed_recoveries += 1
    
    if recovered_agents == 0 and failed_recoveries == 0:
        return True, f"All agents in session '{session_name}' are healthy"
    elif failed_recoveries == 0:
        return True, f"Successfully recovered {recovered_agents} agents in session '{session_name}'"
    else:
        return False, f"Recovered {recovered_agents} agents, but {failed_recoveries} recoveries failed"


def _agent_needs_recovery(pane_content: str) -> bool:
    """Determine if an agent needs recovery based on pane content."""
    if not pane_content:
        return True  # Empty content suggests failed agent
    
    # Look for error indicators
    error_indicators = [
        "error",
        "failed",
        "crashed",
        "terminated",
        "connection refused",
        "no such file",
        "permission denied"
    ]
    
    content_lower = pane_content.lower()
    for indicator in error_indicators:
        if indicator in content_lower:
            return True
    
    # Look for shell prompt (suggests Claude exited)
    if any(prompt in pane_content for prompt in ["$ ", "# ", "> "]):
        return True
    
    return False
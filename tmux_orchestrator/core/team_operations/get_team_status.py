"""Business logic for getting team status."""

from typing import Dict, List, Any, Optional
from tmux_orchestrator.utils.tmux import TMUXManager


def get_team_status(tmux: TMUXManager, session: str) -> Optional[Dict[str, Any]]:
    """Get detailed team status for a session.
    
    Args:
        tmux: TMUXManager instance
        session: Session name to check
        
    Returns:
        Dictionary with team status or None if session not found
    """
    # Check if session exists
    if not tmux.has_session(session):
        return None
    
    # Get session info
    sessions: List[Dict[str, str]] = tmux.list_sessions()
    session_info: Optional[Dict[str, str]] = next(
        (s for s in sessions if s['name'] == session), None
    )
    
    if not session_info:
        return None
    
    # Get windows in session
    windows: List[Dict[str, str]] = tmux.list_windows(session)
    
    if not windows:
        return {
            'session_info': session_info,
            'windows': [],
            'summary': {
                'total_windows': 0,
                'active_agents': 0
            }
        }
    
    # Process each window
    processed_windows: List[Dict[str, Any]] = []
    active_agents: int = 0
    
    for window in windows:
        target: str = f"{session}:{window['index']}"
        
        # Determine window type
        window_name: str = window['name']
        window_type: str = _determine_window_type(window_name)
        
        # Get pane content to determine status
        pane_content: str = tmux.capture_pane(target, 20)
        status, last_activity = _determine_window_status(tmux, pane_content)
        
        # Count agents
        if 'claude' in window_name.lower() or 'pm' in window_name.lower():
            active_agents += 1
        
        processed_windows.append({
            'index': window['index'],
            'name': window_name,
            'type': window_type,
            'status': status,
            'last_activity': last_activity,
            'target': target
        })
    
    return {
        'session_info': session_info,
        'windows': processed_windows,
        'summary': {
            'total_windows': len(windows),
            'active_agents': active_agents
        }
    }


def _determine_window_type(window_name: str) -> str:
    """Determine the type of a window based on its name.
    
    Args:
        window_name: Name of the window
        
    Returns:
        String description of window type
    """
    window_name_lower: str = window_name.lower()
    
    if 'claude' in window_name_lower or 'pm' in window_name_lower or 'qa' in window_name_lower:
        if 'pm' in window_name_lower:
            return "Project Manager"
        elif 'qa' in window_name_lower:
            return "QA Engineer"
        elif 'frontend' in window_name_lower:
            return "Frontend Dev"
        elif 'backend' in window_name_lower:
            return "Backend Dev"
        else:
            return "Developer"
    elif 'dev' in window_name_lower or 'server' in window_name_lower:
        return "Dev Server"
    elif 'shell' in window_name_lower:
        return "Shell"
    else:
        return "Other"


def _determine_window_status(tmux: TMUXManager, pane_content: str) -> tuple[str, str]:
    """Determine status and activity from pane content.
    
    Args:
        tmux: TMUXManager instance
        pane_content: Content from the pane
        
    Returns:
        Tuple of (status, last_activity)
    """
    status: str = "Active"
    last_activity: str = "Working..."
    
    if tmux._is_idle(pane_content):
        status = "Idle"
        last_activity = "Waiting for task"
    elif "error" in pane_content.lower():
        status = "Error"
        last_activity = "Has errors"
    elif "completed" in pane_content.lower():
        status = "Complete"
        last_activity = "Task completed"
    
    return status, last_activity
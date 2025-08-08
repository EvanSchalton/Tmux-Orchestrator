"""Discover Claude agents automatically in tmux sessions."""

from typing import Set, List, Optional
import logging

from tmux_orchestrator.utils.tmux import TMUXManager


def discover_agents(
    tmux: TMUXManager, 
    logger: logging.Logger,
    exclude_sessions: Optional[Set[str]] = None
) -> Set[str]:
    """
    Discover Claude agents automatically across tmux sessions.
    
    Uses enhanced detection patterns to identify Claude agents that
    should be monitored for recovery purposes.
    
    Args:
        tmux: TMUXManager instance for tmux operations
        logger: Logger instance for recording discovery events
        exclude_sessions: Set of session names to exclude from discovery
        
    Returns:
        Set of discovered agent targets in 'session:window' format
        
    Raises:
        RuntimeError: If discovery operations fail
    """
    if exclude_sessions is None:
        exclude_sessions = {'orchestrator', 'tmux-orc', 'recovery'}
    
    discovered: Set[str] = set()
    
    try:
        # Get all tmux sessions
        sessions: List[dict] = tmux.list_sessions()
        logger.debug(f"Found {len(sessions)} tmux sessions")
        
        for session in sessions:
            session_name: str = session['name']
            
            # Skip excluded sessions
            if any(exclude in session_name.lower() for exclude in exclude_sessions):
                logger.debug(f"Skipping excluded session: {session_name}")
                continue
            
            # Get windows in session
            windows: List[dict] = tmux.list_windows(session_name)
            logger.debug(f"Found {len(windows)} windows in session {session_name}")
            
            for window in windows:
                window_index: str = window.get('index', '0')
                target: str = f"{session_name}:{window_index}"
                
                # Check if window contains a Claude agent
                if _is_claude_agent(tmux, target, logger):
                    discovered.add(target)
                    logger.info(f"Discovered Claude agent: {target}")
        
        logger.info(f"Agent discovery complete: found {len(discovered)} agents")
        return discovered
        
    except Exception as e:
        error_message: str = f"Agent discovery failed: {str(e)}"
        logger.error(error_message)
        raise RuntimeError(error_message)


def _is_claude_agent(tmux: TMUXManager, target: str, logger: logging.Logger) -> bool:
    """
    Determine if a tmux pane contains a Claude agent.
    
    Uses multiple indicators to detect Claude agents with high accuracy.
    
    Args:
        tmux: TMUXManager instance
        target: Target to check in 'session:window' format
        logger: Logger instance
        
    Returns:
        True if target appears to contain a Claude agent
    """
    try:
        # Get pane content for analysis
        content: str = tmux.capture_pane(target, lines=30)
        if not content:
            return False
        
        content_lower: str = content.lower()
        
        # Strong indicators of Claude agents (any one is sufficient)
        strong_indicators: List[str] = [
            "│ >",                    # Claude prompt box
            "assistant:",             # Claude response marker
            "claude:",               # Claude name
            "anthropic",             # Company name
            "i'll help",             # Common Claude response
            "let me",                # Common Claude start
            "human:",                # Human input marker
        ]
        
        # Medium indicators (need multiple)
        medium_indicators: List[str] = [
            "i can",
            "certainly", 
            "would you like",
            "happy to help",
            "analyze",
            "implement",
            "understand"
        ]
        
        # Count indicator matches
        strong_matches: int = sum(1 for indicator in strong_indicators 
                                 if indicator in content_lower)
        medium_matches: int = sum(1 for indicator in medium_indicators
                                 if indicator in content_lower)
        
        # Agent detection logic
        if strong_matches >= 1:  # Any strong indicator
            logger.debug(f"Strong Claude indicators found in {target}: {strong_matches}")
            return True
        elif medium_matches >= 3:  # Multiple medium indicators
            logger.debug(f"Multiple medium Claude indicators found in {target}: {medium_matches}")
            return True
        elif "claude" in content_lower and medium_matches >= 1:
            logger.debug(f"Claude name + medium indicators found in {target}")
            return True
        
        return False
        
    except Exception as e:
        logger.debug(f"Error checking if {target} is Claude agent: {str(e)}")
        return False
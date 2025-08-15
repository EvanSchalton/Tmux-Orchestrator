"""
Agent state tracking system.

This module handles agent state tracking, session monitoring, and submission tracking.
Extracted from the monolithic monitor.py to improve maintainability and testability.
"""

import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Optional, Set

from tmux_orchestrator.core.config import Config
from tmux_orchestrator.utils.tmux import TMUXManager

from .types import AgentInfo, AgentState, StateTrackerInterface


class StateTracker(StateTrackerInterface):
    """Agent state tracking and session monitoring system."""

    def __init__(self, tmux: TMUXManager, config: Config, logger: logging.Logger):
        """Initialize the state tracker."""
        super().__init__(tmux, config, logger)

        # Agent state tracking
        self._agent_states: Dict[str, AgentState] = {}

        # Session tracking
        self._session_agents: Dict[str, Dict[str, Dict[str, str]]] = {}

        # Idle tracking
        self._idle_agents: Dict[str, datetime] = {}

        # Submission tracking
        self._submission_attempts: Dict[str, int] = {}
        self._last_submission_time: Dict[str, datetime] = {}

        # Team idle tracking
        self._team_idle_at: Dict[str, Optional[datetime]] = {}

        # Missing agent tracking
        self._missing_agent_grace: Dict[str, datetime] = {}
        self._missing_agent_notifications: Dict[str, datetime] = {}

        # Content caching for change detection
        self._content_cache: Dict[str, str] = {}
        self._content_hashes: Dict[str, str] = {}

    def initialize(self) -> bool:
        """Initialize the state tracker."""
        try:
            self.logger.info("Initializing StateTracker")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize StateTracker: {e}")
            return False

    def cleanup(self) -> None:
        """Clean up state tracker resources."""
        self.logger.info("Cleaning up StateTracker")
        self._agent_states.clear()
        self._session_agents.clear()
        self._idle_agents.clear()
        self._submission_attempts.clear()
        self._last_submission_time.clear()
        self._team_idle_at.clear()
        self._missing_agent_grace.clear()
        self._missing_agent_notifications.clear()
        self._content_cache.clear()
        self._content_hashes.clear()

    def update_agent_state(self, target: str, content: str) -> AgentState:
        """
        Update agent state with new content.

        Args:
            target: Agent target identifier
            content: Current agent content

        Returns:
            Updated AgentState
        """
        session, window = target.split(":", 1)
        content_hash = hashlib.md5(content.encode()).hexdigest()

        # Get or create agent state
        if target not in self._agent_states:
            self._agent_states[target] = AgentState(target=target, session=session, window=window, is_fresh=True)
            self.logger.debug(f"Created new state tracking for {target}")

        state = self._agent_states[target]

        # Update content tracking
        previous_content = state.last_content
        previous_hash = state.last_content_hash

        state.last_content = content
        state.last_content_hash = content_hash

        # Detect if content changed
        content_changed = (previous_hash != content_hash) if previous_hash else True

        if content_changed:
            state.last_activity = datetime.now()
            state.consecutive_idle_count = 0
            # Only mark as not fresh if this is not the first content update
            if previous_content is not None:
                state.is_fresh = False

            # Remove from idle tracking if was idle
            if target in self._idle_agents:
                del self._idle_agents[target]
                self.logger.debug(f"Agent {target} became active - removed from idle tracking")
        else:
            # Content hasn't changed - increment idle count
            state.consecutive_idle_count += 1

            # Track when agent first became idle
            if target not in self._idle_agents:
                self._idle_agents[target] = datetime.now()
                self.logger.debug(f"Agent {target} became idle - started tracking")

        # Cache content for future comparisons
        self._content_cache[target] = content
        self._content_hashes[target] = content_hash

        return state

    def get_agent_state(self, target: str) -> Optional[AgentState]:
        """
        Get current agent state.

        Args:
            target: Agent target identifier

        Returns:
            AgentState if exists, None otherwise
        """
        return self._agent_states.get(target)

    def reset_agent_state(self, target: str) -> None:
        """
        Reset agent tracking state.

        Args:
            target: Agent target identifier
        """
        # Reset all tracking for this agent
        if target in self._agent_states:
            del self._agent_states[target]
        if target in self._idle_agents:
            del self._idle_agents[target]
        if target in self._submission_attempts:
            del self._submission_attempts[target]
        if target in self._last_submission_time:
            del self._last_submission_time[target]
        if target in self._content_cache:
            del self._content_cache[target]
        if target in self._content_hashes:
            del self._content_hashes[target]

        self.logger.debug(f"Reset all state tracking for {target}")

    def get_session_agents(self, session: str) -> List[AgentState]:
        """
        Get all agents in a session.

        Args:
            session: Session name

        Returns:
            List of AgentState objects for agents in the session
        """
        session_agents = []
        for target, state in self._agent_states.items():
            if state.session == session:
                session_agents.append(state)
        return session_agents

    def track_session_agent(self, agent_info: AgentInfo) -> None:
        """
        Track agent information in session registry.

        Args:
            agent_info: AgentInfo to track
        """
        session = agent_info.session
        target = agent_info.target

        # Initialize session tracking if needed
        if session not in self._session_agents:
            self._session_agents[session] = {}

        # Store agent info
        self._session_agents[session][target] = {
            "name": agent_info.name,
            "type": agent_info.type,
            "status": agent_info.status,
        }

        self.logger.debug(f"Tracking agent {target} in session {session}")

    def get_session_agent_registry(self, session: str) -> Dict[str, Dict[str, str]]:
        """
        Get agent registry for a session.

        Args:
            session: Session name

        Returns:
            Dictionary mapping targets to agent info
        """
        return self._session_agents.get(session, {})

    def is_agent_idle(self, target: str) -> bool:
        """
        Check if agent is currently idle.

        Args:
            target: Agent target identifier

        Returns:
            True if agent is idle
        """
        return target in self._idle_agents

    def get_idle_duration(self, target: str) -> Optional[float]:
        """
        Get duration agent has been idle.

        Args:
            target: Agent target identifier

        Returns:
            Idle duration in seconds, or None if not idle
        """
        if target not in self._idle_agents:
            return None

        idle_start = self._idle_agents[target]
        return (datetime.now() - idle_start).total_seconds()

    def get_all_idle_agents(self) -> Dict[str, datetime]:
        """Get all currently idle agents with their idle start times."""
        return self._idle_agents.copy()

    def track_submission_attempt(self, target: str) -> None:
        """
        Track auto-submission attempt for an agent.

        Args:
            target: Agent target identifier
        """
        self._submission_attempts[target] = self._submission_attempts.get(target, 0) + 1
        self._last_submission_time[target] = datetime.now()

        self.logger.debug(f"Tracked submission attempt for {target} " f"(attempt #{self._submission_attempts[target]})")

    def get_submission_attempts(self, target: str) -> int:
        """
        Get number of submission attempts for an agent.

        Args:
            target: Agent target identifier

        Returns:
            Number of submission attempts
        """
        return self._submission_attempts.get(target, 0)

    def get_last_submission_time(self, target: str) -> Optional[datetime]:
        """
        Get last submission time for an agent.

        Args:
            target: Agent target identifier

        Returns:
            Last submission time or None
        """
        return self._last_submission_time.get(target)

    def reset_submission_tracking(self, target: str) -> None:
        """
        Reset submission tracking for an agent.

        Args:
            target: Agent target identifier
        """
        if target in self._submission_attempts:
            del self._submission_attempts[target]
        if target in self._last_submission_time:
            del self._last_submission_time[target]

        self.logger.debug(f"Reset submission tracking for {target}")

    def set_team_idle(self, session: str) -> None:
        """
        Mark entire team as idle for a session.

        Args:
            session: Session name
        """
        if session not in self._team_idle_at or self._team_idle_at[session] is None:
            self._team_idle_at[session] = datetime.now()
            self.logger.info(f"Team in session {session} marked as idle")

    def clear_team_idle(self, session: str) -> None:
        """
        Clear team idle status for a session.

        Args:
            session: Session name
        """
        if session in self._team_idle_at:
            self._team_idle_at[session] = None
            self.logger.info(f"Team in session {session} no longer idle")

    def is_team_idle(self, session: str) -> bool:
        """
        Check if team is idle for a session.

        Args:
            session: Session name

        Returns:
            True if team is idle
        """
        return session in self._team_idle_at and self._team_idle_at[session] is not None

    def get_team_idle_duration(self, session: str) -> Optional[float]:
        """
        Get duration team has been idle.

        Args:
            session: Session name

        Returns:
            Team idle duration in seconds, or None if not idle
        """
        if not self.is_team_idle(session):
            return None

        idle_start = self._team_idle_at[session]
        return (datetime.now() - idle_start).total_seconds()

    def track_missing_agent(self, target: str) -> None:
        """
        Start tracking a missing agent.

        Args:
            target: Agent target identifier
        """
        if target not in self._missing_agent_grace:
            self._missing_agent_grace[target] = datetime.now()
            self.logger.warning(f"Started tracking missing agent {target}")

    def clear_missing_agent(self, target: str) -> None:
        """
        Clear missing agent tracking.

        Args:
            target: Agent target identifier
        """
        if target in self._missing_agent_grace:
            del self._missing_agent_grace[target]
        if target in self._missing_agent_notifications:
            del self._missing_agent_notifications[target]
        self.logger.debug(f"Cleared missing agent tracking for {target}")

    def is_agent_missing(self, target: str) -> bool:
        """
        Check if agent is tracked as missing.

        Args:
            target: Agent target identifier

        Returns:
            True if agent is missing
        """
        return target in self._missing_agent_grace

    def get_missing_duration(self, target: str) -> Optional[float]:
        """
        Get duration agent has been missing.

        Args:
            target: Agent target identifier

        Returns:
            Missing duration in seconds, or None if not missing
        """
        if target not in self._missing_agent_grace:
            return None

        missing_start = self._missing_agent_grace[target]
        return (datetime.now() - missing_start).total_seconds()

    def get_all_sessions(self) -> Set[str]:
        """Get all tracked sessions."""
        sessions = set()
        for state in self._agent_states.values():
            sessions.add(state.session)
        return sessions

    def get_state_summary(self) -> Dict[str, int]:
        """Get summary of current state tracking."""
        return {
            "total_agents": len(self._agent_states),
            "idle_agents": len(self._idle_agents),
            "sessions": len(self._session_agents),
            "missing_agents": len(self._missing_agent_grace),
            "agents_with_submissions": len(self._submission_attempts),
        }

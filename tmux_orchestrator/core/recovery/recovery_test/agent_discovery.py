"""Agent discovery functionality for recovery testing."""

import logging

from tmux_orchestrator.utils.tmux import TMUXManager


class AgentDiscoveryTest:
    """Handles discovery of available agents for recovery testing."""

    def __init__(self, tmux_manager: TMUXManager, logger: logging.Logger):
        """Initialize agent discovery test."""
        self.tmux = tmux_manager
        self.logger = logger

    async def discover_test_agents(self) -> list[str]:
        """Discover available agents for testing."""
        test_agents: list[str] = []

        # Check tmux-orc-dev session first
        if self.tmux.has_session("tmux-orc-dev"):
            # Use non-critical windows for testing (avoid window 1 - orchestrator)
            test_candidates = ["tmux-orc-dev:2", "tmux-orc-dev:3", "tmux-orc-dev:4"]

            for candidate in test_candidates:
                try:
                    # Verify window exists
                    content = self.tmux.capture_pane(candidate, lines=1)
                    if content is not None:  # Window exists and is accessible
                        test_agents.append(candidate)
                except Exception:
                    continue

        # Fallback to other sessions if needed
        if not test_agents:
            try:
                sessions = self.tmux.list_sessions()
                for session in sessions:
                    session_name = session.get("name", "")
                    if session_name in ["tmux-orc-dev"]:
                        continue

                    # Check for Claude windows
                    windows = self.tmux.list_windows(session_name)
                    for window in windows:
                        window_name = window.get("name", "")
                        window_id = window.get("index", "")

                        if "claude" in window_name.lower():
                            test_agents.append(f"{session_name}:{window_id}")
                            break  # One per session is enough
            except Exception as e:
                self.logger.warning(f"Error discovering test agents: {str(e)}")

        self.logger.info(f"Discovered {len(test_agents)} test agents: {test_agents}")
        return test_agents

    def validate_test_agent(self, target: str) -> bool:
        """Validate that an agent target is suitable for testing.

        Args:
            target: Agent target to validate

        Returns:
            True if agent is valid for testing
        """
        try:
            # Check if window exists and is accessible
            content = self.tmux.capture_pane(target, lines=1)
            return content is not None
        except Exception as e:
            self.logger.debug(f"Agent {target} validation failed: {e}")
            return False

    def filter_test_agents(self, candidates: list[str]) -> list[str]:
        """Filter agent candidates to only include valid test targets.

        Args:
            candidates: List of potential test agents

        Returns:
            List of validated test agents
        """
        validated_agents = []
        for candidate in candidates:
            if self.validate_test_agent(candidate):
                validated_agents.append(candidate)
            else:
                self.logger.debug(f"Excluding invalid test agent: {candidate}")

        return validated_agents

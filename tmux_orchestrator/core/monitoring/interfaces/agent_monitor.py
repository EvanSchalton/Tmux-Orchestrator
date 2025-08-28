"""Interface for agent monitoring operations."""

from abc import ABC, abstractmethod
from typing import Any

from ..types import AgentInfo


class AgentMonitorInterface(ABC):
    """Interface for agent monitoring operations."""

    @abstractmethod
    def check_agent(self, agent_info: AgentInfo) -> tuple[bool, str | None]:
        """Check an agent's health status.

        Args:
            agent_info: Information about the agent to check

        Returns:
            Tuple of (is_healthy, issue_description)
        """
        pass

    @abstractmethod
    def get_agent_status(self, target: str) -> dict[str, Any]:
        """Get detailed status for a specific agent.

        Args:
            target: Agent target identifier

        Returns:
            Dictionary with agent status details
        """
        pass

    @abstractmethod
    def discover_agents(self) -> list[AgentInfo]:
        """Discover all active agents.

        Returns:
            List of active agent information
        """
        pass

    @abstractmethod
    def analyze_agent_content(self, content: str, agent_info: AgentInfo) -> dict[str, Any]:
        """Analyze agent terminal content.

        Args:
            content: Terminal content to analyze
            agent_info: Agent information

        Returns:
            Analysis results dictionary
        """
        pass

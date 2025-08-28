"""Interface for state tracking operations."""

from abc import ABC, abstractmethod
from typing import Any


class StateTrackerInterface(ABC):
    """Interface for state tracking operations."""

    @abstractmethod
    def update_state(self, key: str, value: Any) -> None:
        """Update tracked state.

        Args:
            key: State key
            value: State value
        """
        pass

    @abstractmethod
    def update_agent_discovered(self, agent_target: str) -> None:
        """Update agent discovery state.

        Args:
            agent_target: Target of discovered agent
        """
        pass

    @abstractmethod
    def get_state(self, key: str) -> Any | None:
        """Get tracked state.

        Args:
            key: State key

        Returns:
            State value or None if not found
        """
        pass

    @abstractmethod
    def clear_state(self, key: str | None = None) -> None:
        """Clear tracked state.

        Args:
            key: Optional specific key to clear, or None to clear all
        """
        pass

    @abstractmethod
    def get_agent_state(self, agent_id: str) -> dict[str, Any] | None:
        """Get state for a specific agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Agent state dictionary or None if not found
        """
        pass

    @abstractmethod
    def get_idle_duration(self, agent_id: str) -> float | None:
        """Get idle duration for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Idle duration in seconds or None if unknown
        """
        pass

    @abstractmethod
    def update_agent_state(self, agent_id: str, state: dict[str, Any]) -> None:
        """Update agent state.

        Args:
            agent_id: Agent identifier
            state: State dictionary to update
        """
        pass

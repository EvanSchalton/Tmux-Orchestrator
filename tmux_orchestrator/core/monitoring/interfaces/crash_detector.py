"""Interface for crash detection services."""

from abc import ABC, abstractmethod

from ..types import AgentInfo


class CrashDetectorInterface(ABC):
    """Interface for crash detection services."""

    @abstractmethod
    def detect_crash(
        self, agent_info: AgentInfo, window_content: list[str], idle_duration: float | None = None
    ) -> tuple[bool, str | None]:
        """Detect if an agent has crashed based on window content analysis.

        Args:
            agent_info: Information about the agent
            window_content: Recent lines from the agent's window
            idle_duration: How long the agent has been idle

        Returns:
            Tuple of (is_crashed, crash_reason)
        """
        pass

    @abstractmethod
    def detect_pm_crash(self, session_name: str) -> tuple[bool, str | None]:
        """Detect if a PM has crashed in a session.

        Args:
            session_name: Session to check

        Returns:
            Tuple of (is_crashed, pm_target)
        """
        pass

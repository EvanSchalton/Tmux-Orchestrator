"""Interface for agent health checking."""

from abc import ABC, abstractmethod
from typing import Any


class HealthCheckerInterface(ABC):
    """Interface for agent health checking."""

    @abstractmethod
    async def check_agent_health(self, target: str) -> tuple[bool, str | None]:
        """Check health of a specific agent.

        Args:
            target: Agent target (session:window)

        Returns:
            Tuple of (is_healthy, issue_description)
        """
        pass

    @abstractmethod
    async def get_health_metrics(self) -> dict[str, Any]:
        """Get overall health metrics.

        Returns:
            Dictionary with health metrics
        """
        pass

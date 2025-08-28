"""Interface for PM recovery management."""

from abc import ABC, abstractmethod
from typing import Any


class PMRecoveryManagerInterface(ABC):
    """Interface for PM recovery management."""

    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the recovery manager.

        Returns:
            True if initialization successful
        """
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources."""
        pass

    @abstractmethod
    def check_pm_health(self, session_name: str) -> tuple[bool, str | None, str | None]:
        """Check PM health in a session.

        Args:
            session_name: Session to check

        Returns:
            Tuple of (is_healthy, pm_target, issue_description)
        """
        pass

    @abstractmethod
    def should_attempt_recovery(self, session_name: str) -> bool:
        """Determine if recovery should be attempted.

        Args:
            session_name: Session to check

        Returns:
            True if recovery should be attempted
        """
        pass

    @abstractmethod
    def recover_pm(self, session_name: str, crashed_target: str | None = None) -> bool:
        """Recover a crashed or missing PM.

        Args:
            session_name: Session needing PM recovery
            crashed_target: Target of crashed PM

        Returns:
            True if recovery successful
        """
        pass

    @abstractmethod
    def get_recovery_status(self) -> dict[str, Any]:
        """Get current recovery status.

        Returns:
            Dictionary with recovery status details
        """
        pass

    @abstractmethod
    def handle_recovery(self, session_name: str, issue_type: str) -> bool:
        """Handle PM recovery for a specific issue.

        Args:
            session_name: Session needing recovery
            issue_type: Type of issue detected

        Returns:
            True if recovery handled successfully
        """
        pass

    @abstractmethod
    def check_and_recover_if_needed(self, session_name: str) -> bool:
        """Check PM health and recover if needed.

        Args:
            session_name: Session to check and recover

        Returns:
            True if check completed (recovery may or may not have been needed)
        """
        pass

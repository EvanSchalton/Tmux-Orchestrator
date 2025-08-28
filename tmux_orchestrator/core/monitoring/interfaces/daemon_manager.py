"""Interface for daemon lifecycle management."""

from abc import ABC, abstractmethod
from typing import Any


class DaemonManagerInterface(ABC):
    """Interface for daemon lifecycle management."""

    @abstractmethod
    def is_running(self) -> bool:
        """Check if daemon is running.

        Returns:
            True if daemon is running
        """
        pass

    @abstractmethod
    def get_pid(self) -> int | None:
        """Get daemon PID.

        Returns:
            PID if running, None otherwise
        """
        pass

    @abstractmethod
    def start_daemon(self, target_func: Any, args: tuple = ()) -> int:
        """Start the daemon process.

        Args:
            target_func: Function to run as daemon
            args: Arguments for target function

        Returns:
            PID of started daemon
        """
        pass

    @abstractmethod
    def stop_daemon(self, timeout: int = 10) -> bool:
        """Stop the daemon gracefully.

        Args:
            timeout: Maximum seconds to wait

        Returns:
            True if stopped successfully
        """
        pass

    @abstractmethod
    def restart_daemon(self, target_func: Any, args: tuple = ()) -> int:
        """Restart the daemon.

        Args:
            target_func: Function to run as daemon
            args: Arguments for target function

        Returns:
            PID of restarted daemon
        """
        pass

    @abstractmethod
    def cleanup_stale_files(self) -> None:
        """Clean up stale PID and lock files."""
        pass

    @abstractmethod
    def should_shutdown(self) -> bool:
        """Check if daemon should shutdown.

        Returns:
            True if shutdown requested
        """
        pass

    @abstractmethod
    def get_daemon_info(self) -> dict:
        """Get daemon information.

        Returns:
            Dictionary with daemon details
        """
        pass

    @abstractmethod
    def start(self) -> bool:
        """Start the daemon.

        Returns:
            True if started successfully
        """
        pass

    @abstractmethod
    def stop(self) -> bool:
        """Stop the daemon.

        Returns:
            True if stopped successfully
        """
        pass

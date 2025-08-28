"""Supervisor functionality for daemon management and self-healing."""

import sys
from typing import TYPE_CHECKING, Any

from tmux_orchestrator.core.daemon_supervisor import DaemonSupervisor

if TYPE_CHECKING:
    from tmux_orchestrator.core.config import Config
else:
    from tmux_orchestrator.core.config import Config


class SupervisorManager:
    """Manages supervised daemon operations for self-healing functionality."""

    def __init__(self, config: "Config") -> None:
        """Initialize the supervisor manager.

        Args:
            config: Configuration instance
        """
        self.config = config
        self.supervisor = DaemonSupervisor(str(config.orchestrator_base_dir))

    def start_supervised_daemon(self, interval: int = 10) -> bool:
        """Start the daemon with supervision for proper self-healing.

        This method starts the daemon under supervision which provides:
        - Automatic restart on unexpected failure
        - Exponential backoff to prevent restart storms
        - Heartbeat-based health monitoring
        - Proper cleanup on graceful shutdown

        Args:
            interval: Monitoring interval in seconds

        Returns:
            bool: True if supervision started successfully

        Raises:
            RuntimeError: If daemon startup fails
        """
        # Prepare daemon command that supervisor will manage
        daemon_command = [
            sys.executable,
            "-c",
            f"""import sys
import os; sys.path.insert(0, os.getcwd())
from tmux_orchestrator.core.monitor import IdleMonitor
from tmux_orchestrator.utils.tmux import TMUXManager

tmux = TMUXManager()
monitor = IdleMonitor(tmux)
monitor._run_monitoring_daemon({interval})
""",
        ]

        # Let supervisor handle all the locking and checking
        success = self.supervisor.start_daemon(daemon_command)
        if not success:
            raise RuntimeError("Failed to start daemon under supervision")

        return success

    def stop_supervised_daemon(self) -> bool:
        """Stop the supervised daemon.

        Returns:
            bool: True if daemon was stopped successfully
        """
        return self.supervisor.stop_daemon()

    def get_supervisor_status(self) -> dict[str, Any]:
        """Get the status of the supervised daemon.

        Returns:
            dict: Status information about the supervised daemon
        """
        return self.supervisor.get_status()

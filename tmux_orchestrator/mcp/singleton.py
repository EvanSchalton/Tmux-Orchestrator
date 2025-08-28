"""MCP Server singleton enforcement.

Ensures only one MCP server instance runs at a time to prevent
conflicts between multiple servers attempting to manage agents.
"""

import fcntl
import logging
import os
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class MCPSingleton:
    """Enforces singleton pattern for MCP server instances."""

    def __init__(self, base_dir: Optional[Path] = None):
        """Initialize MCP singleton manager.

        Args:
            base_dir: Base directory for lock/pid files (defaults to .tmux_orchestrator)
        """
        if base_dir is None:
            base_dir = Path.cwd() / ".tmux_orchestrator"

        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.pid_file = self.base_dir / "mcp-server.pid"
        self.lock_file = self.base_dir / "mcp-server.lock"
        self._lock_fd: Optional[int] = None

    def acquire_or_exit(self) -> bool:
        """Try to acquire singleton lock, exit if another instance is running.

        Returns:
            True if lock acquired, exits process if not
        """
        # First check if another instance is already running
        existing_pid = self._get_existing_pid()
        if existing_pid and self._is_process_alive(existing_pid):
            logger.warning(f"MCP server already running with PID {existing_pid}")
            logger.warning("Shutting down to prevent conflicts...")

            # Send message to stderr (visible in Claude Code)
            sys.stderr.write(f"MCP server already running (PID {existing_pid}). Shutting down.\n")
            sys.stderr.flush()

            # Exit gracefully
            sys.exit(0)

        # Try to acquire lock
        if not self._acquire_lock():
            logger.error("Failed to acquire MCP server lock")
            sys.stderr.write("Failed to acquire MCP server lock. Another instance may be starting.\n")
            sys.stderr.flush()
            sys.exit(1)

        # Write our PID
        try:
            with open(self.pid_file, "w") as f:
                f.write(str(os.getpid()))
            logger.info(f"MCP server acquired lock (PID {os.getpid()})")
            return True
        except Exception as e:
            logger.error(f"Failed to write PID file: {e}")
            self.release()
            sys.exit(1)

    def _get_existing_pid(self) -> Optional[int]:
        """Get PID from existing PID file.

        Returns:
            PID if found, None otherwise
        """
        if not self.pid_file.exists():
            return None

        try:
            with open(self.pid_file) as f:
                return int(f.read().strip())
        except (OSError, ValueError) as e:
            logger.debug(f"Could not read PID file: {e}")
            return None

    def _is_process_alive(self, pid: int) -> bool:
        """Check if process with given PID is alive.

        Args:
            pid: Process ID to check

        Returns:
            True if process exists and is alive
        """
        try:
            # Send signal 0 to check if process exists
            os.kill(pid, 0)

            # Check if it's actually an MCP server process
            # Read /proc/{pid}/cmdline to verify it's our process
            try:
                with open(f"/proc/{pid}/cmdline") as f:
                    cmdline = f.read()
                    # Check if it's running our MCP server
                    if "tmux-orc" in cmdline and "server" in cmdline:
                        return True
                    else:
                        logger.debug(f"PID {pid} exists but is not an MCP server")
                        return False
            except Exception:
                # If we can't read cmdline, assume it's valid
                return True

        except ProcessLookupError:
            # Process doesn't exist
            return False
        except PermissionError:
            # Process exists but we can't signal it (different user?)
            return True

    def _acquire_lock(self) -> bool:
        """Acquire exclusive lock for MCP server.

        Returns:
            True if lock acquired successfully
        """
        try:
            self._lock_fd = os.open(str(self.lock_file), os.O_CREAT | os.O_WRONLY, 0o600)
            # Try non-blocking exclusive lock
            fcntl.flock(self._lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except OSError as e:
            logger.debug(f"Failed to acquire lock: {e}")
            if self._lock_fd:
                os.close(self._lock_fd)
                self._lock_fd = None
            return False

    def release(self) -> None:
        """Release singleton lock and clean up."""
        # Release lock
        if self._lock_fd:
            try:
                fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
                os.close(self._lock_fd)
                self._lock_fd = None
            except Exception as e:
                logger.error(f"Error releasing lock: {e}")

        # Remove PID file
        if self.pid_file.exists():
            try:
                self.pid_file.unlink()
            except Exception as e:
                logger.error(f"Error removing PID file: {e}")

        # Remove lock file
        if self.lock_file.exists():
            try:
                self.lock_file.unlink()
            except Exception as e:
                logger.error(f"Error removing lock file: {e}")

    def __enter__(self):
        """Context manager entry."""
        self.acquire_or_exit()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.release()


def check_and_cleanup_stale() -> None:
    """Check for stale MCP server files and clean them up."""
    base_dir = Path.cwd() / ".tmux_orchestrator"
    if not base_dir.exists():
        return

    pid_file = base_dir / "mcp-server.pid"
    lock_file = base_dir / "mcp-server.lock"

    # Check if PID file exists
    if pid_file.exists():
        try:
            with open(pid_file) as f:
                pid = int(f.read().strip())

            # Check if process is alive
            try:
                os.kill(pid, 0)
                # Process exists, don't clean up
                logger.debug(f"MCP server PID {pid} is still alive")
                return
            except ProcessLookupError:
                # Process doesn't exist, clean up
                logger.info(f"Cleaning up stale MCP server files (PID {pid} not found)")
                pid_file.unlink()
        except Exception as e:
            logger.debug(f"Error checking PID file: {e}")
            # Remove potentially corrupted file
            pid_file.unlink()

    # Clean up lock file if no PID file
    if lock_file.exists() and not pid_file.exists():
        try:
            lock_file.unlink()
            logger.debug("Removed stale lock file")
        except Exception as e:
            logger.debug(f"Error removing lock file: {e}")

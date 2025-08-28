"""TMUX utility functions with backwards compatibility.

This module provides a backwards-compatible interface to the decomposed TMUX operations.
The original TMUXManager class is maintained for existing code compatibility.
"""

import logging

from .basic_operations import BasicTmuxOperations
from .list_operations import TmuxListOperations
from .messaging import TmuxMessaging
from .performance import TmuxPerformanceOperations
from .validation import TmuxValidation


class TMUXManager:
    """High-performance TMUX manager - backwards compatible interface to decomposed operations."""

    def __init__(self, cache_ttl: float = 5.0):
        """Initialize with caching configuration.

        Args:
            cache_ttl: Cache time-to-live in seconds (default 5s for CLI responsiveness)
        """
        # Initialize component modules following SRP
        self.basic_ops = BasicTmuxOperations()
        self.performance_ops = TmuxPerformanceOperations(cache_ttl=cache_ttl)
        self.messaging = TmuxMessaging(self.basic_ops)
        self.list_ops = TmuxListOperations()
        self.validation = TmuxValidation()

        # Maintain backwards compatibility
        self.tmux_cmd = "tmux"
        self._cache_ttl = cache_ttl
        self._logger = logging.getLogger(__name__)

    # Delegate to appropriate component modules for backwards compatibility

    # Basic operations delegation
    def has_session(self, session_name: str) -> bool:
        """Check if a tmux session exists."""
        return self.basic_ops.has_session(session_name)

    def create_session(self, session_name: str, window_name=None, start_directory=None) -> bool:
        """Create a new tmux session."""
        self._logger.debug(f"TMUXManager.create_session: '{session_name}' (delegating to BasicTmuxOperations)")
        result = self.basic_ops.create_session(session_name, window_name, start_directory)
        self._logger.debug(f"TMUXManager.create_session result: {result}")
        return result

    def create_window(self, session_name: str, window_name: str, start_directory=None) -> bool:
        """Create a new window in a session."""
        self._logger.debug(
            f"TMUXManager.create_window: '{window_name}' in '{session_name}' (delegating to BasicTmuxOperations)"
        )
        result = self.basic_ops.create_window(session_name, window_name, start_directory)
        self._logger.debug(f"TMUXManager.create_window result: {result}")
        return result

    def send_keys(self, target: str, keys: str, literal: bool = False) -> bool:
        """Send keys to a tmux target."""
        return self.basic_ops.send_keys(target, keys, literal)

    def press_enter(self, target: str) -> bool:
        """Press Enter key in the target pane."""
        return self.basic_ops.press_enter(target)

    def press_ctrl_u(self, target: str) -> bool:
        """Press Ctrl+U (clear line) in the target pane."""
        return self.basic_ops.press_ctrl_u(target)

    def press_escape(self, target: str) -> bool:
        """Press Escape key in the target pane."""
        return self.basic_ops.press_escape(target)

    def press_ctrl_e(self, target: str) -> bool:
        """Press Ctrl+E (end of line) in the target pane."""
        return self.basic_ops.press_ctrl_e(target)

    def capture_pane(self, target: str, lines: int = 50) -> str:
        """Capture pane output."""
        return self.basic_ops.capture_pane(target, lines)

    def kill_window(self, target: str) -> bool:
        """Kill a specific tmux window."""
        return self.basic_ops.kill_window(target)

    def kill_session(self, session_name: str) -> bool:
        """Kill a specific tmux session."""
        return self.basic_ops.kill_session(session_name)

    def run(self, command: str) -> bool:
        """Execute a raw tmux command."""
        return self.basic_ops.run(command)

    # Performance operations delegation
    def list_agents_optimized(self) -> list[dict[str, str]]:
        """Optimized agent listing with aggressive caching and batch operations."""
        return self.performance_ops.list_agents_optimized()

    def list_agents_ultra_optimized(self) -> list[dict[str, str]]:
        """Ultra-optimized agent listing with minimal subprocess calls."""
        return self.performance_ops.list_agents_ultra_optimized()

    def list_sessions_cached(self) -> list[dict[str, str]]:
        """Cached session listing for status command optimization."""
        return self.performance_ops.list_sessions_cached()

    def invalidate_cache(self) -> None:
        """Force cache invalidation for fresh data."""
        self.performance_ops.invalidate_cache()

    def quick_deploy_dry_run_optimized(self, team_type: str, size: int, project_name: str) -> tuple[bool, str, float]:
        """Ultra-fast dry run of team deployment to validate parameters and estimate timing."""
        return self.performance_ops.quick_deploy_dry_run_optimized(team_type, size, project_name)

    # Optimized versions with backwards compatibility
    def has_session_optimized(self, session_name: str) -> bool:
        """Optimized session existence check with caching."""
        return self.performance_ops._has_session_optimized(session_name)

    def create_session_optimized(self, session_name: str, window_name=None, start_directory=None) -> bool:
        """Optimized session creation with immediate cache invalidation."""
        success = self.basic_ops.create_session(session_name, window_name, start_directory)
        if success:
            self.performance_ops.invalidate_cache()
        return success

    def create_window_optimized(self, session_name: str, window_name: str, start_directory=None) -> bool:
        """Optimized window creation."""
        return self.basic_ops.create_window(session_name, window_name, start_directory)

    def send_keys_optimized(self, target: str, keys: str, literal: bool = False) -> bool:
        """Optimized key sending."""
        return self.basic_ops.send_keys(target, keys, literal)

    # Messaging operations delegation
    def send_text(self, target: str, text: str, **kwargs) -> bool:
        """Send literal text to the target pane directly. Ignores legacy chunking params."""
        return self.messaging.send_text(target, text, **kwargs)

    def send_message(self, target: str, message: str, delay: float = 0.5) -> bool:
        """Send a message to a Claude agent directly without chunking."""
        self._logger.debug(
            f"TMUXManager.send_message: to '{target}' ({len(message)} chars, delegating to TmuxMessaging)"
        )
        result = self.messaging.send_message(target, message, delay)
        self._logger.debug(f"TMUXManager.send_message result: {result}")
        return result

    def _is_idle(self, pane_content: str) -> bool:
        """Check if pane content indicates idle state."""
        return self.messaging._is_idle(pane_content)

    # List operations delegation
    def list_windows(self, session: str) -> list[dict]:
        """List windows in a session."""
        return self.list_ops.list_windows(session)

    def list_sessions(self) -> list[dict[str, str]]:
        """List all TMUX sessions."""
        return self.list_ops.list_sessions()

    def list_agents(self) -> list[dict[str, str]]:
        """Standard interface for listing agents - delegates to optimized version."""
        return self.performance_ops.list_agents_optimized()

    # Validation delegation
    def _validate_input(self, value: str, field_name: str = "input") -> str:
        """Validate input to prevent command injection vulnerabilities."""
        return self.validation.validate_input(value, field_name)


# Export the main class for backwards compatibility
__all__ = ["TMUXManager"]

"""Business logic handlers for communication MCP tools.

This module provides communication-specific handlers that can be used
by multiple tools or for future communication enhancements.
"""

import logging
from typing import Any, Dict, List

from tmux_orchestrator.server.tools.send_message import (
    SendMessageRequest,
)
from tmux_orchestrator.server.tools.send_message import (
    send_message as core_send_message,
)
from tmux_orchestrator.utils.tmux import TMUXManager

logger = logging.getLogger(__name__)


class CommunicationHandlers:
    """Handlers for communication operations."""

    def __init__(self):
        self.tmux = TMUXManager()

    def send_message(
        self,
        target: str,
        message: str,
        urgent: bool = False,
        timeout: float | None = None,
    ) -> Dict[str, Any]:
        """Handle message sending with enhanced options."""
        try:
            request = SendMessageRequest(
                target=target,
                message=message,
            )

            # Apply timeout based on urgency
            if urgent and timeout is None:
                timeout = 15.0  # Shorter timeout for urgent messages

            result = core_send_message(self.tmux, request)

            return {
                "success": result.success,
                "target": result.target,
                "message": "Message sent successfully" if result.success else result.error_message,
                "urgent": urgent,
                "timeout": timeout,
                "delivery_time": result.delivery_time if hasattr(result, "delivery_time") else None,
            }

        except Exception as e:
            logger.error(f"Enhanced message send failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "context": {"target": target, "urgent": urgent},
            }

    def broadcast_message(
        self,
        session: str,
        message: str,
        exclude_windows: List[str] | None = None,
        urgent: bool = False,
    ) -> Dict[str, Any]:
        """Handle broadcasting messages to multiple agents."""
        try:
            windows = self.tmux.list_windows(session)
            if not windows:
                return {
                    "success": False,
                    "error": f"No windows found in session {session}",
                    "error_type": "SessionNotFound",
                }

            # Filter out excluded windows
            if exclude_windows:
                windows = [w for w in windows if w.get("name") not in exclude_windows]

            results = []
            successful = 0

            for window in windows:
                target = f"{session}:{window.get('index', window.get('name'))}"
                result = self.send_message(target, message, urgent)
                results.append(
                    {
                        "target": target,
                        "success": result["success"],
                        "message": result.get("message", ""),
                    }
                )
                if result["success"]:
                    successful += 1

            return {
                "success": successful > 0,
                "session": session,
                "total_sent": len(results),
                "successful": successful,
                "failed": len(results) - successful,
                "results": results,
                "excluded_windows": exclude_windows or [],
            }

        except Exception as e:
            logger.error(f"Broadcast failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "context": {"session": session},
            }

    def validate_target(self, target: str) -> Dict[str, Any]:
        """Validate that a target exists and is reachable."""
        try:
            if ":" not in target:
                return {
                    "valid": False,
                    "error": "Invalid target format. Use 'session:window'",
                }

            session, window = target.split(":", 1)

            # Check if session exists
            sessions = self.tmux.list_sessions()
            session_exists = any(s.get("name") == session for s in sessions)

            if not session_exists:
                return {
                    "valid": False,
                    "error": f"Session '{session}' does not exist",
                    "session": session,
                }

            # Check if window exists in session
            windows = self.tmux.list_windows(session)
            window_exists = any(w.get("index") == window or w.get("name") == window for w in windows)

            if not window_exists:
                return {
                    "valid": False,
                    "error": f"Window '{window}' does not exist in session '{session}'",
                    "session": session,
                    "window": window,
                }

            return {
                "valid": True,
                "target": target,
                "session": session,
                "window": window,
            }

        except Exception as e:
            logger.error(f"Target validation failed: {e}")
            return {
                "valid": False,
                "error": str(e),
                "error_type": type(e).__name__,
            }

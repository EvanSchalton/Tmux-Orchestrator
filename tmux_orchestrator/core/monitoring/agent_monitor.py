"""
Agent discovery and monitoring functionality.

This module handles agent discovery, window detection, and basic agent analysis.
Extracted from the monolithic monitor.py to improve maintainability and testability.
"""

import hashlib
import logging
import time
from datetime import datetime
from typing import Any

from tmux_orchestrator.core.config import Config
from tmux_orchestrator.utils.tmux import TMUXManager

from .crash_detector import CrashDetector
from .types import AgentInfo, AgentMonitorInterface, IdleAnalysis, IdleType


class AgentMonitor(AgentMonitorInterface):
    """Agent discovery and monitoring system."""

    def __init__(self, tmux: TMUXManager, config: Config, logger: logging.Logger):
        """Initialize the agent monitor."""
        super().__init__(tmux, config, logger)
        self._agent_cache: dict[str, AgentInfo] = {}
        self._last_discovery_time: datetime | None = None
        self._crash_detector = CrashDetector(tmux, logger)

    def initialize(self) -> bool:
        """Initialize the agent monitor."""
        try:
            self.logger.info("Initializing AgentMonitor")
            # Perform initial agent discovery to validate connectivity
            self._initializing = True
            agents = self.discover_agents()
            self._initializing = False
            self.logger.info(f"Discovered {len(agents)} agents during initialization")
            return True
        except Exception as e:
            self._initializing = False
            self.logger.error(f"Failed to initialize AgentMonitor: {e}")
            return False

    def cleanup(self) -> None:
        """Clean up agent monitor resources."""
        self.logger.info("Cleaning up AgentMonitor")
        self._agent_cache.clear()

    def discover_agents(self) -> list[AgentInfo]:
        """
        Discover active agents to monitor.

        Returns:
            List of AgentInfo objects for all discovered agents
        """
        agents = []
        try:
            self.logger.debug("Starting agent discovery")
            # Get all tmux sessions
            sessions = self.tmux.list_sessions()
            for session_info in sessions:
                session_name = session_info["name"]

                # Get windows for this session
                try:
                    windows = self.tmux.list_windows(session_name)
                    for window_info in windows:
                        # Fix: use 'index' not 'id' - window_info contains index/name/active
                        window_idx = window_info.get("index", "0")
                        target = f"{session_name}:{window_idx}"

                        # Check if window contains an active agent
                        if self.is_agent_window(target):
                            agent_info = self._create_agent_info(target, session_name, str(window_idx), window_info)
                            agents.append(agent_info)
                            self._agent_cache[target] = agent_info

                except Exception as e:
                    self.logger.warning(f"Failed to list windows for session {session_name}: {e}")
                    continue

            self._last_discovery_time = datetime.now()
            self.logger.debug(f"Agent discovery complete: found {len(agents)} agents")
            return agents

        except Exception as e:
            self.logger.error(f"Agent discovery failed: {e}")
            # Re-raise during initialization to indicate failure
            if hasattr(self, "_initializing") and self._initializing:
                raise
            return []

    def is_agent_window(self, target: str) -> bool:
        """
        Check if a window should be monitored as an agent window.

        This checks window NAME patterns, not content, so we can track
        crashed agents that need recovery.

        Args:
            target: Window target in format "session:window"

        Returns:
            True if window should be monitored as an agent
        """
        try:
            session_name, window_idx = target.split(":")
            windows = self.tmux.list_windows(session_name)

            # Find the window info for this index
            for window in windows:
                if str(window.get("index", "")) == str(window_idx):
                    window_name = window.get("name", "").lower()

                    # Check if this is an agent window by name pattern
                    # Claude agent windows are named "Claude-{role}"
                    if window_name.startswith("claude-"):
                        return True

                    # Also check for common agent indicators in window name
                    agent_indicators = [
                        "pm",
                        "developer",
                        "qa",
                        "engineer",
                        "devops",
                        "backend",
                        "frontend",
                        "researcher",
                        "writer",
                    ]
                    if any(indicator in window_name for indicator in agent_indicators):
                        return True

            return False

        except Exception as e:
            self.logger.error(f"Error checking if {target} is agent window: {e}")
            return False

    def get_agent_display_name(self, target: str) -> str:
        """
        Get a display name for an agent that includes window name and location.

        Args:
            target: Window target in format "session:window"

        Returns:
            Formatted display name like "WindowName[session:idx]"
        """
        try:
            session_name, window_idx = target.split(":")
            windows = self.tmux.list_windows(session_name)

            for window in windows:
                if str(window.get("index", "")) == str(window_idx):
                    window_name = window.get("name", "Unknown")
                    # Format: "WindowName[session:idx]"
                    return f"{window_name}[{target}]"

            return f"Unknown[{target}]"

        except Exception as e:
            self.logger.error(f"Error getting display name for {target}: {e}")
            return target

    def analyze_agent_content(self, target: str) -> IdleAnalysis:
        """
        Analyze agent content for idle state detection.

        Uses polling-based active detection to determine if agent is actively
        working or idle.

        Args:
            target: Window target in format "session:window"

        Returns:
            IdleAnalysis with detection results
        """
        try:
            self.logger.debug(f"Analyzing content for agent {target}")

            # Step 1: Use polling-based active detection with throttling
            snapshots = []
            poll_interval = 0.8  # 800ms - increased from 300ms to reduce tmux server load
            poll_count = 3  # Reduced from 4 to 3 snapshots to prevent server crashes

            # Take snapshots for change detection with throttling
            for i in range(poll_count):
                # Add inter-command delay to prevent tmux server overload
                if i > 0:
                    time.sleep(0.1)  # 100ms delay between rapid tmux commands

                content = self.tmux.capture_pane(target, lines=50)
                snapshots.append(content)
                if i < poll_count - 1:
                    time.sleep(poll_interval)

            # Use last snapshot for state detection
            content = snapshots[-1]
            content_hash = hashlib.md5(content.encode(), usedforsecurity=False).hexdigest()

            # Step 2: Detect if terminal is actively changing
            is_active = False
            for i in range(1, len(snapshots)):
                # Simple change detection - if content changed significantly, it's active
                if snapshots[i - 1] != snapshots[i]:
                    # Check if change is meaningful (not just cursor blink)
                    changes = sum(1 for a, b in zip(snapshots[i - 1], snapshots[i]) if a != b)
                    self.logger.debug(f"Agent {target} snapshot {i} has {changes} character changes")
                    if changes > 1:
                        is_active = True
                        break

            # Step 3: Check for special states even if not actively changing
            idle_type = IdleType.UNKNOWN
            error_detected = False
            error_type = None

            # Step 3.1: Check for crashes first (applies regardless of activity state)
            agent_info = AgentInfo(
                target=target,
                session=target.split(":")[0],
                window=target.split(":")[1],
                name="agent",  # Will be updated later if needed
                type="agent",
                status="unknown",
            )

            crashed, crash_reason = self._crash_detector.detect_crash(agent_info, content)
            if crashed:
                error_detected = True
                error_type = crash_reason
                idle_type = IdleType.ERROR_STATE
                self.logger.error(f"Agent {target} crash detected: {crash_reason}")

            elif not is_active:
                content_lower = content.lower()

                # Check for compaction (robust across Claude Code versions)
                if "compacting conversation" in content_lower:
                    self.logger.debug(f"Agent {target} is compacting conversation")
                    is_active = True
                    idle_type = IdleType.COMPACTION_STATE

                # Check for error patterns
                elif self._detect_api_error_patterns(content):
                    error_detected = True
                    error_type = self._identify_error_type(content)
                    idle_type = IdleType.ERROR_STATE

                # Check if agent is fresh (newly spawned)
                elif self._is_agent_fresh(content):
                    idle_type = IdleType.FRESH_AGENT

                else:
                    # Determine idle type based on previous state
                    idle_type = IdleType.NEWLY_IDLE

            return IdleAnalysis(
                target=target,
                is_idle=not is_active,
                idle_type=idle_type,
                confidence=0.9 if is_active else 0.8,  # High confidence in polling method
                last_activity=datetime.now() if is_active else None,
                content_hash=content_hash,
                error_detected=error_detected,
                error_type=error_type,
            )

        except Exception as e:
            self.logger.error(f"Error analyzing agent content for {target}: {e}")
            return IdleAnalysis(
                target=target,
                is_idle=True,
                idle_type=IdleType.UNKNOWN,
                confidence=0.0,
                last_activity=None,
                content_hash=None,
                error_detected=True,
                error_type="analysis_failed",
            )

    def get_cached_agent_info(self, target: str) -> AgentInfo | None:
        """Get cached agent info if available."""
        return self._agent_cache.get(target)

    def get_all_cached_agents(self) -> list[AgentInfo]:
        """Get all cached agent info."""
        return list(self._agent_cache.values())

    def clear_cache(self) -> None:
        """Clear the agent cache."""
        self._agent_cache.clear()

    def _create_agent_info(self, target: str, session: str, window: str, window_info: dict[str, Any]) -> AgentInfo:
        """Create AgentInfo object from window information."""
        window_name = window_info.get("name", "Unknown")

        # Determine agent type from window name
        agent_type = self._determine_agent_type(window_name)

        return AgentInfo(
            target=target,
            session=session,
            window=window,
            name=window_name,
            type=agent_type,
            status="active",
            last_seen=datetime.now(),
        )

    def _determine_agent_type(self, window_name: str) -> str:
        """Determine agent type from window name."""
        name_lower = window_name.lower()

        if "pm" in name_lower or "project-manager" in name_lower:
            return "Project Manager"
        elif "devops" in name_lower:
            return "DevOps"
        elif "dev" in name_lower or "engineer" in name_lower:
            return "Developer"
        elif "qa" in name_lower or "test" in name_lower:
            return "QA Engineer"
        elif "research" in name_lower:
            return "Researcher"
        elif "writer" in name_lower or "doc" in name_lower:
            return "Documentation Writer"
        elif "claude" in name_lower:
            return "Claude Agent"
        else:
            return "Agent"

    def _detect_api_error_patterns(self, content: str) -> bool:
        """Detect API error patterns in agent content."""
        content_lower = content.lower()

        error_patterns = [
            "rate limit",
            "api error",
            "connection error",
            "timeout",
            "overloaded",
            "503 service unavailable",
            "502 bad gateway",
            "500 internal server error",
            "too many requests",
            "quota exceeded",
        ]

        return any(pattern in content_lower for pattern in error_patterns)

    def _identify_error_type(self, content: str) -> str:
        """Identify specific error type from content."""
        content_lower = content.lower()

        if "rate limit" in content_lower or "too many requests" in content_lower:
            return "rate_limit"
        elif "overloaded" in content_lower or "503" in content_lower:
            return "service_overloaded"
        elif "timeout" in content_lower:
            return "timeout"
        elif "connection error" in content_lower:
            return "connection_error"
        elif "quota exceeded" in content_lower:
            return "quota_exceeded"
        else:
            return "unknown_error"

    def _is_agent_fresh(self, content: str) -> bool:
        """Check if agent appears to be freshly spawned."""
        content_lower = content.lower()

        # Look for fresh agent indicators
        fresh_indicators = [
            "welcome",
            "getting started",
            "how can i help",
            "how can i assist",
            "ready to assist",
            "what would you like",
            "initial prompt",
        ]

        return any(indicator in content_lower for indicator in fresh_indicators)

"""Agent discovery and status operations."""

import logging
import re
import subprocess
import time
from typing import Any


class AgentOperations:
    """Handles TMUX agent discovery and status operations."""

    def __init__(self, tmux_cmd: str = "tmux", cache_ttl: float = 5.0):
        """Initialize agent operations.

        Args:
            tmux_cmd: TMUX command to use (default: "tmux")
            cache_ttl: Cache time-to-live in seconds
        """
        self.tmux_cmd = tmux_cmd
        self._logger = logging.getLogger(__name__)
        self._cache_ttl = cache_ttl

        # Performance caches
        self._agent_cache: dict[str, Any] = {}
        self._agent_cache_time: float = 0.0
        self._batch_size = 10

    def list_agents_optimized(self) -> list[dict[str, str]]:
        """Optimized agent listing with aggressive caching and batch operations.

        Target: <100ms execution time (vs 4.13s original)

        Returns:
            List of agent dictionaries with session, window, type, status
        """
        current_time = time.time()

        # Check cache first (5-second TTL)
        if (current_time - self._agent_cache_time) < self._cache_ttl and self._agent_cache:
            self._logger.debug("Using cached agent list")
            cached_agents = self._agent_cache.get("agents", [])
            return cached_agents if isinstance(cached_agents, list) else []

        start_time = time.time()
        agents: list[dict[str, str]] = []

        try:
            # Single command to get all sessions and windows
            sessions_windows = self._get_sessions_and_windows_batch()

            # Filter for agent windows only
            agent_windows = []
            for session_name, windows in sessions_windows.items():
                for window in windows:
                    window_name = window.get("name", "")
                    if self._is_agent_window(window_name):
                        agent_windows.append(
                            {
                                "session": session_name,
                                "window": window.get("index", ""),
                                "name": window_name,
                                "type": self._determine_agent_type(window_name),
                            }
                        )

            # Batch get statuses for all agent windows
            if agent_windows:
                statuses = self._batch_get_agent_statuses(agent_windows)

                for i, agent in enumerate(agent_windows):
                    agents.append(
                        {
                            "session": agent["session"],
                            "window": agent["window"],
                            "type": agent["type"],
                            "status": statuses.get(i, "unknown"),
                        }
                    )

            # Update cache
            self._agent_cache = {"agents": agents}
            self._agent_cache_time = current_time

            elapsed = time.time() - start_time
            self._logger.info(f"Optimized agent list completed in {elapsed:.3f}s ({len(agents)} agents)")

        except Exception as e:
            self._logger.error(f"Agent listing failed: {e}")
            # Fallback to basic list if optimized version fails
            agents = self._get_basic_agent_list()

        return agents

    def list_agents_ultra_optimized(self) -> list[dict[str, str]]:
        """Ultra-optimized agent listing for extremely fast responses.

        This version uses minimal tmux calls and aggressive caching.
        Target: <50ms execution time.
        """
        current_time = time.time()

        # Check cache first with shorter TTL for ultra-fast mode
        if (current_time - self._agent_cache_time) < 2.0 and self._agent_cache:
            cached_agents = self._agent_cache.get("agents", [])
            return cached_agents if isinstance(cached_agents, list) else []

        start_time = time.time()
        agents: list[dict[str, str]] = []

        try:
            # Single ultra-fast command to get all relevant info
            result = subprocess.run(
                [
                    self.tmux_cmd,
                    "list-windows",
                    "-a",
                    "-F",
                    "#{session_name}:#{window_index}:#{window_name}:#{pane_current_command}",
                ],
                capture_output=True,
                text=True,
                timeout=2,
            )

            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if not line:
                        continue

                    parts = line.split(":", 3)
                    if len(parts) >= 3:
                        session, window, name = parts[0], parts[1], parts[2]
                        command = parts[3] if len(parts) > 3 else ""

                        if self._is_agent_window(name):
                            # Fast status determination from command
                            status = "active" if "claude" in command.lower() or "python" in command.lower() else "idle"

                            agents.append(
                                {
                                    "session": session,
                                    "window": window,
                                    "type": self._determine_agent_type(name),
                                    "status": status,
                                }
                            )

            # Update cache
            self._agent_cache = {"agents": agents}
            self._agent_cache_time = current_time

            elapsed = time.time() - start_time
            self._logger.debug(f"Ultra-optimized agent list completed in {elapsed:.3f}s")

        except Exception as e:
            self._logger.error(f"Ultra-optimized agent listing failed: {e}")
            # Fallback to standard optimized version
            return self.list_agents_optimized()

        return agents

    def list_agents(self) -> list[dict[str, str]]:
        """Legacy method for compatibility."""
        return self.list_agents_optimized()

    def _get_sessions_and_windows_batch(self) -> dict[str, list[dict[str, Any]]]:
        """Get all sessions and their windows in a single batch operation."""
        sessions_windows: dict[str, list[dict[str, Any]]] = {}

        try:
            # Get all sessions and windows in one command
            result = subprocess.run(
                [
                    self.tmux_cmd,
                    "list-windows",
                    "-a",
                    "-F",
                    "#{session_name}:#{window_index}:#{window_name}:#{window_active}",
                ],
                capture_output=True,
                text=True,
                timeout=3,
            )

            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if not line:
                        continue

                    parts = line.split(":", 3)
                    if len(parts) >= 3:
                        session_name, window_index, window_name = parts[0], parts[1], parts[2]
                        window_active = parts[3] if len(parts) > 3 else "0"

                        if session_name not in sessions_windows:
                            sessions_windows[session_name] = []

                        sessions_windows[session_name].append(
                            {"index": window_index, "name": window_name, "active": window_active == "1"}
                        )

        except Exception as e:
            self._logger.error(f"Failed to get sessions and windows: {e}")

        return sessions_windows

    def _is_agent_window(self, window_name: str) -> bool:
        """Check if a window name indicates an agent."""
        agent_patterns = [
            r"^(backend|frontend|devops|qa|architect|pm|project-manager|orchestrator)",
            r"(dev|engineer|manager|agent)$",
            r"^(claude|ai)-",
            r"-(dev|qa|ops|pm)$",
        ]

        name_lower = window_name.lower()
        return any(re.search(pattern, name_lower) for pattern in agent_patterns)

    def _batch_get_agent_statuses(self, agent_windows: list[dict[str, Any]]) -> dict[int, str]:
        """Get statuses for all agent windows in batches."""
        statuses = {}

        # Process in batches to avoid overwhelming tmux
        for i in range(0, len(agent_windows), self._batch_size):
            batch = agent_windows[i : i + self._batch_size]
            batch_statuses = self._get_batch_statuses(batch, i)
            statuses.update(batch_statuses)

        return statuses

    def _get_batch_statuses(self, batch: list[dict[str, Any]], offset: int) -> dict[int, str]:
        """Get statuses for a batch of agent windows."""
        statuses = {}

        for idx, agent in enumerate(batch):
            target = f"{agent['session']}:{agent['window']}"
            try:
                # Quick status check using capture-pane
                result = subprocess.run(
                    [self.tmux_cmd, "capture-pane", "-t", target, "-p", "-S", "-10"],
                    capture_output=True,
                    text=True,
                    timeout=1,
                )

                if result.returncode == 0:
                    content = result.stdout.strip()
                    status = "idle" if self._is_idle(content) else "active"
                else:
                    status = "unknown"

                statuses[offset + idx] = status

            except Exception:
                statuses[offset + idx] = "unknown"

        return statuses

    def _determine_agent_type(self, window_name: str) -> str:
        """Determine agent type from window name."""
        name_lower = window_name.lower()

        type_patterns = {
            "backend": r"(backend|back-end|be)",
            "frontend": r"(frontend|front-end|fe|ui|web)",
            "devops": r"(devops|dev-ops|ops|infrastructure|infra)",
            "qa": r"(qa|quality|test|testing)",
            "pm": r"(pm|project.manager|manager)",
            "architect": r"(architect|arch|design)",
            "orchestrator": r"(orchestrator|orc)",
        }

        for agent_type, pattern in type_patterns.items():
            if re.search(pattern, name_lower):
                return agent_type

        return "agent"  # Generic fallback

    def _get_basic_agent_list(self) -> list[dict[str, str]]:
        """Basic agent listing without optimization (fallback)."""
        agents: list[dict[str, str]] = []

        try:
            # Simple approach - just list windows and filter
            result = subprocess.run(
                [self.tmux_cmd, "list-windows", "-a", "-F", "#{session_name}:#{window_index}:#{window_name}"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if not line:
                        continue

                    parts = line.split(":", 2)
                    if len(parts) >= 3:
                        session, window, name = parts[0], parts[1], parts[2]

                        if self._is_agent_window(name):
                            agents.append(
                                {
                                    "session": session,
                                    "window": window,
                                    "type": self._determine_agent_type(name),
                                    "status": "unknown",  # Skip status check for basic mode
                                }
                            )

        except Exception as e:
            self._logger.error(f"Basic agent listing failed: {e}")

        return agents

    def invalidate_cache(self) -> None:
        """Clear the agent cache to force fresh data on next request."""
        self._agent_cache.clear()
        self._agent_cache_time = 0.0

    def _is_idle(self, pane_content: str) -> bool:
        """Determine if pane content indicates an idle agent."""
        if not pane_content.strip():
            return True

        idle_indicators = [
            "bash-",
            "$ ",
            "# ",
            "waiting",
            "idle",
            "ready",
            ">>>",  # Python prompt
            "claude>",
        ]

        last_lines = pane_content.split("\n")[-3:]  # Check last 3 lines
        content_check = " ".join(last_lines).lower()

        return any(indicator in content_check for indicator in idle_indicators)

    def quick_deploy_dry_run_optimized(self, team_type: str, size: int, project_name: str) -> tuple[bool, str, float]:
        """Quick validation for team deployment without actually deploying."""
        start_time = time.time()

        try:
            # Validate team type
            valid_types = ["development", "qa", "devops", "full-stack", "research"]
            if team_type not in valid_types:
                return False, f"Invalid team type. Must be one of: {', '.join(valid_types)}", 0.0

            # Validate size
            if not (1 <= size <= 20):
                return False, "Team size must be between 1 and 20", 0.0

            # Check if project name would conflict with existing sessions
            # Note: This requires session manager, so we'll import it when needed
            from .session_manager import SessionManager

            session_mgr = SessionManager(self.tmux_cmd)
            if session_mgr.has_session(project_name):
                return False, f"Session '{project_name}' already exists", 0.0

            elapsed = time.time() - start_time
            return True, f"✓ Can deploy {size}-member {team_type} team for '{project_name}'", elapsed

        except Exception as e:
            elapsed = time.time() - start_time
            return False, f"Validation error: {e}", elapsed

"""High-performance TMUX utility functions with caching and batch operations."""

import logging
import re
import subprocess
import time
from typing import Any, cast


class TMUXManager:
    """High-performance TMUX manager with caching and batch operations."""

    def __init__(self, cache_ttl: float = 5.0):
        """Initialize with caching configuration.

        Args:
            cache_ttl: Cache time-to-live in seconds (default 5s for CLI responsiveness)
        """
        self.tmux_cmd = "tmux"
        self._logger = logging.getLogger(__name__)

        # Performance caches
        self._agent_cache: dict[str, Any] = {}
        self._agent_cache_time: float = 0.0
        self._session_cache: dict[str, Any] = {}
        self._session_cache_time: float = 0.0
        self._cache_ttl = cache_ttl

        # Batch operation optimization
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
            agents = self._agent_cache.get("agents", [])
            return agents if isinstance(agents, list) else []

        start_time = time.time()
        agents = []

        try:
            # Single batch command to get all session and window info
            sessions_and_windows = self._get_sessions_and_windows_batch()

            # Process in batches to avoid subprocess overhead
            agent_windows = []
            for session_name, windows in sessions_and_windows.items():
                for window in windows:
                    if self._is_agent_window(window["name"]):
                        agent_windows.append(
                            {"session": session_name, "window": window, "target": f"{session_name}:{window['index']}"}
                        )

            # Batch status checks (only for agent windows)
            if agent_windows:
                statuses = self._batch_get_agent_statuses(agent_windows)

                # Build final agent list
                for i, agent_window in enumerate(agent_windows):
                    window_info = cast(dict[str, str], agent_window["window"])
                    status = statuses.get(i, "Unknown")

                    agents.append(
                        {
                            "session": agent_window["session"],
                            "window": window_info["index"],
                            "type": self._determine_agent_type(window_info["name"]),
                            "status": status,
                            "target": agent_window["target"],
                        }
                    )

            # Cache results
            self._agent_cache = {"agents": agents}
            self._agent_cache_time = current_time

            execution_time = (time.time() - start_time) * 1000  # Convert to ms
            self._logger.info(f"Optimized list_agents completed in {execution_time:.1f}ms")

            return agents

        except Exception as e:
            self._logger.error(f"Optimized agent listing failed: {e}")
            # Fallback to basic listing without status checks
            return self._get_basic_agent_list()

    def list_agents_ultra_optimized(self) -> list[dict[str, str]]:
        """Ultra-optimized agent listing with minimal subprocess calls.

        Target: <300ms execution time for CLI responsiveness

        Returns:
            List of agent dictionaries with session, window, type, status
        """
        current_time = time.time()

        # Extended cache check (10-second TTL for ultra mode)
        extended_ttl = 10.0
        if (current_time - self._agent_cache_time) < extended_ttl and self._agent_cache:
            self._logger.debug("Using extended cached agent list")
            agents = self._agent_cache.get("agents", [])
            return agents if isinstance(agents, list) else []

        start_time = time.time()
        agents = []

        try:
            # Ultra-fast: Single command to get all info, skip individual status checks
            result = subprocess.run(
                [
                    self.tmux_cmd,
                    "list-panes",
                    "-a",
                    "-F",
                    "#{session_name}|#{window_index}|#{window_name}|#{pane_activity}",
                ],
                capture_output=True,
                text=True,
                timeout=2,
            )

            if result.returncode == 0:
                current_timestamp = int(time.time())

                for line in result.stdout.strip().split("\n"):
                    if "|" in line and line.strip():
                        parts = line.split("|")
                        if len(parts) >= 3:
                            session_name, window_index, window_name = parts[0], parts[1], parts[2]

                            if self._is_agent_window(window_name):
                                # Ultra-fast status determination
                                activity_time = parts[3] if len(parts) > 3 else "0"
                                try:
                                    last_activity = int(activity_time) if activity_time.isdigit() else 0
                                    time_diff = current_timestamp - last_activity
                                    status = "Active" if time_diff < 300 else "Idle"  # 5 min threshold
                                except (ValueError, TypeError):
                                    status = "Unknown"

                                agents.append(
                                    {
                                        "session": session_name,
                                        "window": window_index,
                                        "type": self._determine_agent_type(window_name),
                                        "status": status,
                                        "target": f"{session_name}:{window_index}",
                                    }
                                )

            # Cache results with extended TTL
            self._agent_cache = {"agents": agents}
            self._agent_cache_time = current_time

            execution_time = (time.time() - start_time) * 1000
            self._logger.info(f"Ultra-optimized list_agents completed in {execution_time:.1f}ms")

            return agents

        except Exception as e:
            self._logger.error(f"Ultra-optimized agent listing failed: {e}")
            # Fallback to regular optimized version
            return self.list_agents_optimized()

    def _get_sessions_and_windows_batch(self) -> dict[str, list[dict[str, str]]]:
        """Get all sessions and their windows in a single optimized call.

        Returns:
            dict mapping session names to their window lists
        """
        try:
            # Single command to get all session and window info
            cmd = [self.tmux_cmd, "list-sessions", "-F", "#{session_name}|#{session_created}|#{session_attached}"]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
            if result.returncode != 0:
                return {}

            sessions_windows = {}
            session_lines = result.stdout.strip().split("\n") if result.stdout.strip() else []

            # Get windows for all sessions in batch
            for line in session_lines:
                if "|" not in line:
                    continue

                session_name = line.split("|")[0]

                # Get windows for this session
                windows_cmd = [
                    self.tmux_cmd,
                    "list-windows",
                    "-t",
                    session_name,
                    "-F",
                    "#{window_index}|#{window_name}|#{window_active}",
                ]

                windows_result = subprocess.run(windows_cmd, capture_output=True, text=True, timeout=1)
                if windows_result.returncode == 0:
                    windows = []
                    window_lines = windows_result.stdout.strip().split("\n") if windows_result.stdout.strip() else []

                    for window_line in window_lines:
                        if "|" in window_line:
                            parts = window_line.split("|")
                            windows.append(
                                {
                                    "index": parts[0],
                                    "name": parts[1] if len(parts) > 1 else "",
                                    "active": parts[2] if len(parts) > 2 else "0",
                                }
                            )

                    sessions_windows[session_name] = windows

            return sessions_windows

        except Exception as e:
            self._logger.error(f"Batch session/window retrieval failed: {e}")
            return {}

    def _is_agent_window(self, window_name: str) -> bool:
        """Fast check if window is an agent window.

        Args:
            window_name: Name of the window

        Returns:
            True if this appears to be an agent window
        """
        window_lower = window_name.lower()
        agent_keywords = ["claude", "pm", "developer", "qa", "devops", "reviewer", "backend", "frontend"]
        return any(keyword in window_lower for keyword in agent_keywords)

    def _batch_get_agent_statuses(self, agent_windows: list[dict[str, Any]]) -> dict[int, str]:
        """Get status for multiple agents in batch operation.

        Args:
            agent_windows: List of agent window info

        Returns:
            dict mapping agent index to status string
        """
        statuses = {}

        # Process in smaller batches to avoid command line length limits
        batch_size = min(self._batch_size, len(agent_windows))

        for i in range(0, len(agent_windows), batch_size):
            batch = agent_windows[i : i + batch_size]
            batch_statuses = self._get_batch_statuses(batch, i)
            statuses.update(batch_statuses)

        return statuses

    def _get_batch_statuses(self, batch: list[dict[str, Any]], offset: int) -> dict[int, str]:
        """Get statuses for a batch of agents.

        Args:
            batch: Batch of agent windows
            offset: Offset for indexing

        Returns:
            dict mapping agent index to status
        """
        statuses = {}

        # Use a simplified approach: check if pane has recent activity
        # This is much faster than content analysis
        for i, agent_window in enumerate(batch):
            try:
                target = agent_window["target"]

                # Fast check: get last activity time instead of full content
                cmd = [self.tmux_cmd, "display-message", "-t", target, "-p", "#{pane_activity}"]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=0.5)

                if result.returncode == 0:
                    # Simple heuristic: if activity timestamp is recent, agent is active
                    activity_time = result.stdout.strip()
                    current_time = int(time.time())

                    try:
                        last_activity = int(activity_time) if activity_time.isdigit() else current_time - 3600
                        if current_time - last_activity < 300:  # Active if activity within 5 minutes
                            statuses[offset + i] = "Active"
                        else:
                            statuses[offset + i] = "Idle"
                    except (ValueError, TypeError):
                        statuses[offset + i] = "Unknown"
                else:
                    statuses[offset + i] = "Unknown"

            except Exception as e:
                self._logger.debug(f"Status check failed for {agent_window.get('target', 'unknown')}: {e}")
                statuses[offset + i] = "Unknown"

        return statuses

    def _determine_agent_type(self, window_name: str) -> str:
        """Fast agent type determination from window name.

        Args:
            window_name: Window name

        Returns:
            Agent type string
        """
        window_lower = window_name.lower()

        # Fast lookup table
        type_mapping = {
            "pm": "Project Manager",
            "qa": "QA Engineer",
            "frontend": "Frontend Dev",
            "backend": "Backend Dev",
            "devops": "DevOps Engineer",
            "reviewer": "Code Reviewer",
            "docs": "Documentation",
            "developer": "Developer",
        }

        for keyword, agent_type in type_mapping.items():
            if keyword in window_lower:
                return agent_type

        return "Developer"  # Default

    def _get_basic_agent_list(self) -> list[dict[str, str]]:
        """Fallback method for basic agent listing without status checks.

        Returns:
            Basic agent list without detailed status
        """
        try:
            sessions_windows = self._get_sessions_and_windows_batch()
            agents = []

            for session_name, windows in sessions_windows.items():
                for window in windows:
                    if self._is_agent_window(window["name"]):
                        agents.append(
                            {
                                "session": session_name,
                                "window": window["index"],
                                "type": self._determine_agent_type(window["name"]),
                                "status": "Unknown",
                                "target": f"{session_name}:{window['index']}",
                            }
                        )

            return agents

        except Exception as e:
            self._logger.error(f"Basic agent listing failed: {e}")
            return []

    def invalidate_cache(self) -> None:
        """Force cache invalidation for fresh data."""
        self._agent_cache = {}
        self._agent_cache_time = 0.0
        self._session_cache = {}
        self._session_cache_time = 0.0

    def has_session_optimized(self, session_name: str) -> bool:
        """Optimized session existence check with caching."""
        current_time = time.time()

        # Check cache first
        if (current_time - self._session_cache_time) < self._cache_ttl and self._session_cache:
            sessions = self._session_cache.get("sessions", [])
            session_names = [s.get("name", "") for s in sessions]
            return session_name in session_names

        # Fallback to direct check
        try:
            result = subprocess.run([self.tmux_cmd, "has-session", "-t", session_name], capture_output=True, timeout=1)
            return result.returncode == 0
        except Exception:
            return False

    def has_session(self, session_name: str) -> bool:
        """Check if a tmux session exists (standard interface)."""
        return self.has_session_optimized(session_name)

    def create_session_optimized(
        self, session_name: str, window_name: str | None = None, start_directory: str | None = None
    ) -> bool:
        """Optimized session creation with immediate cache invalidation."""
        try:
            cmd = [self.tmux_cmd, "new-session", "-d", "-s", session_name]
            if window_name:
                cmd.extend(["-n", window_name])
            if start_directory:
                cmd.extend(["-c", start_directory])

            result = subprocess.run(cmd, capture_output=True, timeout=5)
            success = result.returncode == 0

            if success:
                # Invalidate session cache since we created a new session
                self._session_cache = {}
                self._session_cache_time = 0.0

            return success
        except Exception as e:
            self._logger.error(f"Optimized session creation failed: {e}")
            return False

    def create_window_optimized(self, session_name: str, window_name: str, start_directory: str | None = None) -> bool:
        """Optimized window creation."""
        try:
            cmd = [self.tmux_cmd, "new-window", "-t", session_name, "-n", window_name]
            if start_directory:
                cmd.extend(["-c", start_directory])

            result = subprocess.run(cmd, capture_output=True, timeout=3)
            return result.returncode == 0
        except Exception as e:
            self._logger.error(f"Optimized window creation failed: {e}")
            return False

    def send_keys_optimized(self, target: str, keys: str, literal: bool = False) -> bool:
        """Optimized key sending with reduced timeouts."""
        try:
            cmd = [self.tmux_cmd, "send-keys", "-t", target]
            if literal:
                cmd.append("-l")
            cmd.append(keys)

            result = subprocess.run(cmd, capture_output=True, timeout=2)
            return result.returncode == 0
        except Exception as e:
            self._logger.error(f"Optimized send keys failed: {e}")
            return False

    def send_keys(self, target: str, keys: str, literal: bool = False) -> bool:
        """Send keys to a tmux target (standard interface)."""
        return self.send_keys_optimized(target, keys, literal)

    def quick_deploy_dry_run_optimized(self, team_type: str, size: int, project_name: str) -> tuple[bool, str, float]:
        """Ultra-fast dry run of team deployment to validate parameters and estimate timing.

        This method performs all validation and estimation without creating actual sessions.
        Target: <50ms execution time

        Returns:
            Tuple of (success, message, estimated_deploy_time_ms)
        """
        start_time = time.time()

        # Fast parameter validation
        if size < 1 or size > 20:
            execution_time = (time.time() - start_time) * 1000
            return False, f"Team size must be between 1 and 20 (requested: {size})", execution_time

        if team_type not in ["frontend", "backend", "fullstack", "testing"]:
            execution_time = (time.time() - start_time) * 1000
            return False, f"Unknown team type: {team_type}", execution_time

        # Session name validation
        session_name = f"{project_name}-{team_type}"

        # Fast session existence check using cache
        if self.has_session_optimized(session_name):
            execution_time = (time.time() - start_time) * 1000
            return False, f"Session '{session_name}' already exists", execution_time

        # Estimate deployment time based on team size and type
        base_time = 1000  # 1 second base time
        agent_time = size * 1500  # 1.5 seconds per agent (conservative)
        estimated_total = base_time + agent_time

        execution_time = (time.time() - start_time) * 1000
        success_message = (
            f"Validated {team_type} team deployment with {size} agents. "
            f"Estimated time: {estimated_total}ms. Session: '{session_name}'"
        )

        return True, success_message, execution_time

    def list_sessions_cached(self) -> list[dict[str, str]]:
        """Cached session listing for status command optimization."""
        current_time = time.time()

        # Check cache first
        if current_time - self._session_cache_time < self._cache_ttl and "sessions" in self._session_cache:
            sessions = self._session_cache["sessions"]
            return sessions if isinstance(sessions, list) else []

        # Cache miss - get fresh data using optimized call
        try:
            result = subprocess.run(
                [self.tmux_cmd, "list-sessions", "-F", "#{session_name}:#{session_created}:#{session_attached}"],
                capture_output=True,
                text=True,
                timeout=3,
            )

            if result.returncode != 0:
                return []

            sessions = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line.split(":")
                    sessions.append(
                        {
                            "name": parts[0],
                            "created": parts[1] if len(parts) > 1 else "",
                            "attached": parts[2] if len(parts) > 2 else "0",
                        }
                    )

            # Update cache
            self._session_cache["sessions"] = sessions
            self._session_cache_time = current_time

            return sessions

        except Exception as e:
            self._logger.error(f"Cached session listing failed: {e}")
            return []

    def list_sessions(self) -> list[dict[str, str]]:
        """Standard interface for listing sessions - delegates to optimized version."""
        return self.list_sessions_cached()

    def list_agents(self) -> list[dict[str, str]]:
        """Standard interface for listing agents - delegates to optimized version."""
        return self.list_agents_optimized()

    def create_session(
        self, session_name: str, window_name: str | None = None, start_directory: str | None = None
    ) -> bool:
        """Standard interface for creating sessions - delegates to optimized version."""
        return self.create_session_optimized(session_name, window_name, start_directory)

    def capture_pane(self, target: str, lines: int = 50) -> str:
        """Capture pane output - optimized version.

        Args:
            target: Target pane (session:window or session:window.pane)
            lines: Number of lines to capture (default 50, 0 for all)

        Returns:
            Captured pane content as string
        """
        try:
            cmd = [self.tmux_cmd, "capture-pane", "-t", target, "-p"]
            if lines > 0:
                cmd.extend(["-S", f"-{lines}"])

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                return result.stdout
            else:
                self._logger.error(f"Failed to capture pane {target}: {result.stderr}")
                return ""
        except Exception as e:
            self._logger.error(f"Error capturing pane {target}: {e}")
            return ""

    def list_windows(self, session: str) -> list[dict[str, str]]:
        """List windows in a session.

        Args:
            session: Session name

        Returns:
            List of window dictionaries with index, name, and active status
        """
        try:
            cmd = [
                self.tmux_cmd,
                "list-windows",
                "-t",
                session,
                "-F",
                "#{window_index}:#{window_name}:#{window_active}",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
            if result.returncode != 0:
                return []

            windows = []
            for line in result.stdout.strip().split("\n"):
                if line and ":" in line:
                    parts = line.split(":", 2)
                    windows.append(
                        {
                            "index": parts[0],
                            "name": parts[1] if len(parts) > 1 else "",
                            "active": parts[2] if len(parts) > 2 else "0",
                        }
                    )

            return windows

        except Exception as e:
            self._logger.error(f"Error listing windows for session {session}: {e}")
            return []

    def create_window(self, session_name: str, window_name: str, start_directory: str | None = None) -> bool:
        """Standard interface for creating windows - delegates to optimized version."""
        return self.create_window_optimized(session_name, window_name, start_directory)

    def send_text(self, target: str, text: str) -> bool:
        """Send literal text to the target pane (properly escaped)."""
        return self.send_keys(target, text, literal=True)

    def press_enter(self, target: str) -> bool:
        """Press Enter key in the target pane."""
        return self.send_keys(target, "Enter", literal=False)

    def press_ctrl_u(self, target: str) -> bool:
        """Press Ctrl+U (clear line) in the target pane."""
        return self.send_keys(target, "C-u", literal=False)

    def send_message(self, target: str, message: str, delay: float = 0.5) -> bool:
        """Send a message to a Claude agent using the proven CLI method."""
        if not self.press_ctrl_u(target):
            return False
        time.sleep(0.1)
        if not self.send_text(target, message):
            return False
        time.sleep(delay)
        return self.press_enter(target)

    def _is_idle(self, pane_content: str) -> bool:
        """Check if pane content indicates idle state."""
        idle_patterns = [
            r"waiting for.*task",
            r"ready for.*assignment",
            r"awaiting.*instruction",
            r"standing by",
            r"idle",
            r"completed.*awaiting",
        ]
        for pattern in idle_patterns:
            if re.search(pattern, pane_content, re.IGNORECASE):
                return True
        # Check for Claude prompt with no recent activity
        if "│ >" in pane_content and pane_content.strip().endswith("│"):
            return True
        return False

    def kill_window(self, target: str) -> bool:
        """Kill a specific tmux window."""
        result = subprocess.run([self.tmux_cmd, "kill-window", "-t", target], capture_output=True, text=True)
        return result.returncode == 0

    def kill_session(self, session_name: str) -> bool:
        """Kill a specific tmux session."""
        result = subprocess.run([self.tmux_cmd, "kill-session", "-t", session_name], capture_output=True, text=True)
        return result.returncode == 0

    def _validate_input(self, value: str, field_name: str = "input") -> str:
        """Validate input to prevent command injection vulnerabilities."""
        if not isinstance(value, str):
            raise ValueError(f"{field_name} must be string, got {type(value)}")

        # Check for null bytes (can cause issues with subprocess)
        if "\x00" in value:
            raise ValueError(f"{field_name} contains null byte")

        return value

    def press_escape(self, target: str) -> bool:
        """Press Escape key in the target pane."""
        return self.send_keys(target, "Escape", literal=False)

    def press_ctrl_e(self, target: str) -> bool:
        """Press Ctrl+E (end of line) in the target pane."""
        return self.send_keys(target, "C-e", literal=False)

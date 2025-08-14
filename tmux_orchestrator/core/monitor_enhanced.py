"""Enhanced monitoring daemon with proper error handling and logging."""

import logging
import os
import signal
import time
from datetime import datetime
from pathlib import Path

from tmux_orchestrator.utils.tmux import TMUXManager


class EnhancedMonitor:
    """Fixed monitoring daemon that actually monitors agents."""

    def __init__(self):
        # Use secure project directory instead of /tmp
        project_dir = Path("/workspaces/Tmux-Orchestrator/.tmux_orchestrator")
        project_dir.mkdir(exist_ok=True)
        logs_dir = project_dir / "logs"
        logs_dir.mkdir(exist_ok=True)

        self.pid_file = project_dir / "enhanced-monitor.pid"
        self.log_file = logs_dir / "enhanced-monitor.log"
        self.debug_mode = os.environ.get("TMUX_ORC_DEBUG", "").lower() in ("true", "1", "yes")
        self.monitored_agents: dict[str, dict] = {}
        self.crashed_agents: set[str] = set()

    def start(self, interval: int = 30) -> int:
        """Start the monitoring daemon."""
        if self.is_running():
            with open(self.pid_file) as f:
                return int(f.read().strip())

        # Fork to create daemon
        pid = os.fork()
        if pid > 0:
            # Parent process - wait a bit then return
            time.sleep(1)
            return pid

        # Child process - become daemon
        os.setsid()

        # Fork again to prevent zombie processes
        pid = os.fork()
        if pid > 0:
            os._exit(0)

        # Grandchild - the actual daemon
        self._run_daemon(interval)
        # This line should never be reached as _run_daemon runs forever
        os._exit(0)

    def is_running(self) -> bool:
        """Check if daemon is running."""
        if not self.pid_file.exists():
            return False
        try:
            with open(self.pid_file) as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            return True
        except (ProcessLookupError, ValueError):
            return False

    def _setup_logging(self) -> logging.Logger:
        """Set up daemon logging with proper formatting."""
        logger = logging.getLogger("enhanced_monitor")
        logger.setLevel(logging.DEBUG if self.debug_mode else logging.INFO)

        # Clear any existing handlers
        logger.handlers.clear()

        # File handler
        handler = logging.FileHandler(self.log_file)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    def _run_daemon(self, interval: int):
        """Main daemon loop with comprehensive error handling."""
        # Set up signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        # Write PID file
        with open(self.pid_file, "w") as f:
            f.write(str(os.getpid()))

        # Set up logging
        logger = self._setup_logging()
        logger.info(
            f"Enhanced monitoring daemon started (PID: {os.getpid()}, interval: {interval}s, debug: {self.debug_mode})"
        )

        # Create TMUXManager
        tmux = TMUXManager()

        # Main monitoring loop
        cycle_count = 0
        while True:
            cycle_count += 1
            start_time = time.time()

            try:
                logger.info(f"Starting monitoring cycle {cycle_count}")
                self._monitor_cycle(tmux, logger)

            except Exception as e:
                logger.error(f"Error in monitoring cycle {cycle_count}: {e}", exc_info=True)

            # Calculate sleep time
            elapsed = time.time() - start_time
            sleep_time = max(0, interval - elapsed)

            logger.debug(f"Cycle {cycle_count} took {elapsed:.2f}s, sleeping for {sleep_time:.2f}s")

            if sleep_time > 0:
                time.sleep(sleep_time)

    def _monitor_cycle(self, tmux: TMUXManager, logger: logging.Logger):
        """Perform one monitoring cycle."""
        # Discover agents
        agents = self._discover_agents(tmux, logger)

        logger.info(f"Found {len(agents)} agents to monitor: {list(agents.keys())}")

        if not agents:
            logger.warning("No agents found - checking for sessions")
            sessions = tmux.list_sessions()
            logger.info(f"Available sessions: {[s['name'] for s in sessions]}")
            return

        # Check each agent
        idle_agents = []
        crashed_agents = []

        for target, info in agents.items():
            try:
                status = self._check_agent_status(tmux, target, info, logger)

                if status == "crashed":
                    crashed_agents.append((target, info))
                    logger.error(f"Agent {target} has crashed!")
                elif status == "idle":
                    idle_agents.append((target, info))
                    logger.warning(f"Agent {target} is idle")
                elif status == "active":
                    logger.debug(f"Agent {target} is active")

            except Exception as e:
                logger.error(f"Error checking agent {target}: {e}", exc_info=True)

        # Report issues
        if crashed_agents or idle_agents:
            self._report_issues(tmux, crashed_agents, idle_agents, logger)

    def _discover_agents(self, tmux: TMUXManager, logger: logging.Logger) -> dict[str, dict]:
        """Discover all active agents."""
        agents = {}

        try:
            sessions = tmux.list_sessions()
            logger.debug(f"Found {len(sessions)} sessions")

            for session in sessions:
                session_name = session["name"]

                try:
                    windows = tmux.list_windows(session_name)
                    logger.debug(f"Session {session_name} has {len(windows)} windows")

                    for window in windows:
                        # Fix: use 'index' not 'id'
                        window_idx = window.get("index", window.get("window_index", "0"))
                        window_name = window.get("name", window.get("window_name", ""))
                        target = f"{session_name}:{window_idx}"

                        # Check if this is a Claude agent
                        if self._is_agent_window(tmux, target, logger):
                            agents[target] = {
                                "session": session_name,
                                "window": window_idx,
                                "name": window_name,
                                "type": self._determine_agent_type(window_name),
                            }
                            logger.debug(f"Found agent: {target} ({window_name})")

                except Exception as e:
                    logger.error(f"Error listing windows for {session_name}: {e}")

        except Exception as e:
            logger.error(f"Error listing sessions: {e}", exc_info=True)

        return agents

    def _is_agent_window(self, tmux: TMUXManager, target: str, logger: logging.Logger) -> bool:
        """Check if window contains a Claude agent."""
        try:
            # Check if the window exists and has content
            content = tmux.capture_pane(target, lines=50)

            if not content or len(content.strip()) < 10:
                logger.debug(f"{target} appears empty")
                return False

            # Look for Claude indicators
            claude_indicators = [
                "Claude",
                "│ >",
                "assistant:",
                "Human:",
                "Anthropic",
                "╭─",
                "╰─",
                "? for shortcuts",
                "Bypassing Permissions",
                "@anthropic-ai/claude-code",
            ]

            is_claude = any(indicator in content for indicator in claude_indicators)

            # Also check window name
            if not is_claude and "claude" in target.lower():
                is_claude = True

            if is_claude:
                logger.debug(f"{target} identified as Claude agent")
            else:
                logger.debug(f"{target} not a Claude agent (no indicators found)")

            return is_claude

        except Exception as e:
            logger.debug(f"Error checking {target}: {e}")
            return False

    def _check_agent_status(self, tmux: TMUXManager, target: str, info: dict, logger: logging.Logger) -> str:
        """Check the status of an agent - active, idle, or crashed."""
        try:
            # Capture current content
            content = tmux.capture_pane(target, lines=100)

            # Check if pane is completely empty (crashed)
            if not content or len(content.strip()) == 0:
                logger.warning(f"{target} pane is empty - agent crashed")
                return "crashed"

            # Check for error indicators
            error_indicators = [
                "Error:",
                "Traceback",
                "Exception",
                "command not found",
                "No such file or directory",
                "Connection refused",
                "killed",
                "terminated",
            ]

            if any(error in content for error in error_indicators):
                logger.warning(f"{target} shows error indicators")
                # May still be recoverable, check if responsive

            # Track content changes to detect idle state
            content_hash = hash(content)

            if target not in self.monitored_agents:
                self.monitored_agents[target] = {
                    "last_hash": content_hash,
                    "last_change": datetime.now(),
                    "idle_cycles": 0,
                }
                return "active"  # First time seeing this agent

            agent_state = self.monitored_agents[target]

            if content_hash != agent_state["last_hash"]:
                # Content changed - agent is active
                agent_state["last_hash"] = content_hash
                agent_state["last_change"] = datetime.now()
                agent_state["idle_cycles"] = 0
                return "active"
            else:
                # Content unchanged
                agent_state["idle_cycles"] += 1
                idle_time = (datetime.now() - agent_state["last_change"]).total_seconds()

                if agent_state["idle_cycles"] >= 3 or idle_time > 120:  # 3 cycles or 2 minutes
                    return "idle"
                else:
                    return "active"  # Still within idle threshold

        except Exception as e:
            logger.error(f"Error checking status of {target}: {e}")
            return "unknown"

    def _determine_agent_type(self, window_name: str) -> str:
        """Determine agent type from window name."""
        name_lower = window_name.lower()

        if "pm" in name_lower or "project" in name_lower:
            return "PM"
        elif "backend" in name_lower:
            return "Backend"
        elif "frontend" in name_lower:
            return "Frontend"
        elif "qa" in name_lower or "test" in name_lower:
            return "QA"
        elif "devops" in name_lower:
            return "DevOps"
        else:
            return "Agent"

    def _report_issues(self, tmux: TMUXManager, crashed: list, idle: list, logger: logging.Logger):
        """Report crashed and idle agents to PM."""
        # Find PM agent
        pm_target = None
        for target, info in self.monitored_agents.items():
            if info.get("type") == "PM":
                pm_target = target
                break

        if not pm_target:
            logger.warning("No PM agent found to report issues to")
            return

        # Build report message
        message = "⚠️ Agent Status Alert:\\n\\n"

        if crashed:
            message += "🔴 CRASHED AGENTS:\\n"
            for target, info in crashed:
                message += f"  • {info['type']} ({target})\\n"

        if idle:
            message += "\\n🟡 IDLE AGENTS:\\n"
            for target, info in idle:
                message += f"  • {info['type']} ({target})\\n"

        message += "\\nPlease investigate and take action."

        # Try to send to PM
        try:
            tmux.send_message(pm_target, message)
            logger.info(f"Sent alert to PM at {pm_target}")
        except Exception as e:
            logger.error(f"Failed to notify PM: {e}")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger = logging.getLogger("enhanced_monitor")
        logger.info(f"Received signal {signum}, shutting down")

        if self.pid_file.exists():
            self.pid_file.unlink()

        os._exit(0)


# CLI interface
if __name__ == "__main__":
    import sys

    monitor = EnhancedMonitor()

    if len(sys.argv) > 1 and sys.argv[1] == "stop":
        if monitor.is_running():
            with open(monitor.pid_file) as f:
                pid = int(f.read().strip())
            os.kill(pid, signal.SIGTERM)
            print(f"Stopped monitor (PID: {pid})")
        else:
            print("Monitor not running")
    else:
        interval = int(sys.argv[1]) if len(sys.argv) > 1 else 30
        pid = monitor.start(interval)
        print(f"Started enhanced monitor (PID: {pid}, interval: {interval}s)")
        print(f"Log: {monitor.log_file}")
        print("Set TMUX_ORC_DEBUG=true for verbose logging")

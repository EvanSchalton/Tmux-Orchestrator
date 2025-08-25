"""Fixed monitoring daemon that properly handles agent discovery and monitoring."""

import hashlib
import logging
import os
import signal
import subprocess
import time
from datetime import datetime
from pathlib import Path


class SimpleMonitor:
    """Simplified but robust monitoring daemon."""

    def __init__(self):
        # Use secure project directory instead of /tmp
        project_dir = Path.cwd() / ".tmux_orchestrator"
        project_dir.mkdir(exist_ok=True)
        logs_dir = project_dir / "logs"
        logs_dir.mkdir(exist_ok=True)

        self.pid_file = project_dir / "simple-monitor.pid"
        self.log_file = logs_dir / "simple-monitor.log"
        self.agent_states = {}  # Track last known state of each agent

    def setup_logging(self) -> logging.Logger:
        """Configure logging."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler(self.log_file), logging.StreamHandler()],
        )
        return logging.getLogger("simple_monitor")

    def get_tmux_pane_content(self, target: str) -> str:
        """Get the current content of a tmux pane."""
        try:
            result = subprocess.run(
                ["tmux", "capture-pane", "-t", target, "-p"], capture_output=True, text=True, check=False
            )
            return result.stdout if result.returncode == 0 else ""
        except Exception:
            return ""

    def hash_content(self, content: str) -> str:
        """Get hash of content to detect changes."""
        # Remove timestamps and other variable content
        cleaned = "\n".join(
            line
            for line in content.splitlines()
            if not any(skip in line for skip in ["[20", "seconds ago", "minutes ago"])
        )
        return hashlib.md5(cleaned.encode(), usedforsecurity=False).hexdigest()

    def find_pm_session(self, sessions: list) -> str | None:
        """Find the PM agent session."""
        for session in sessions:
            if "pm" in session.lower() or "project-manager" in session.lower():
                # Check windows in this session
                try:
                    result = subprocess.run(
                        ["tmux", "list-windows", "-t", session, "-F", "#{window_index}:#{window_name}"],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    for window in result.stdout.strip().split("\n"):
                        if window and ("pm" in window.lower() or "claude" in window.lower()):
                            idx = window.split(":")[0]
                            return f"{session}:{idx}"
                except Exception:
                    pass
        return None

    def discover_agents(self) -> dict[str, str]:
        """Discover all active agents."""
        agents = {}

        try:
            # Get all sessions
            result = subprocess.run(
                ["tmux", "list-sessions", "-F", "#{session_name}"], capture_output=True, text=True, check=True
            )

            sessions = result.stdout.strip().split("\n")

            for session in sessions:
                if not session:
                    continue

                # Get windows in session
                try:
                    window_result = subprocess.run(
                        ["tmux", "list-windows", "-t", session, "-F", "#{window_index}:#{window_name}"],
                        capture_output=True,
                        text=True,
                        check=True,
                    )

                    for window in window_result.stdout.strip().split("\n"):
                        if window:
                            idx, name = window.split(":", 1)
                            target = f"{session}:{idx}"

                            # Determine agent type from window name
                            if "claude" in name.lower():
                                if "pm" in name.lower():
                                    agent_type = "PM"
                                elif "backend" in name.lower():
                                    agent_type = "Backend"
                                elif "frontend" in name.lower():
                                    agent_type = "Frontend"
                                elif "qa" in name.lower():
                                    agent_type = "QA"
                                else:
                                    agent_type = "Agent"

                                agents[target] = agent_type

                except Exception:
                    pass

        except Exception as e:
            logging.error(f"Error discovering agents: {e}")

        return agents

    def check_agent_activity(self, target: str, agent_type: str, logger) -> bool:
        """Check if an agent has been active."""
        content = self.get_tmux_pane_content(target)
        if not content:
            return True  # Can't determine, assume active

        current_hash = self.hash_content(content)

        # Initialize state if new agent
        if target not in self.agent_states:
            self.agent_states[target] = {"hash": current_hash, "last_active": datetime.now(), "idle_count": 0}
            return True

        # Check if content changed
        if current_hash != self.agent_states[target]["hash"]:
            self.agent_states[target]["hash"] = current_hash
            self.agent_states[target]["last_active"] = datetime.now()
            self.agent_states[target]["idle_count"] = 0
            return True
        else:
            # Content unchanged - agent might be idle
            self.agent_states[target]["idle_count"] += 1
            idle_time = (datetime.now() - self.agent_states[target]["last_active"]).total_seconds()

            if self.agent_states[target]["idle_count"] >= 6:  # 60 seconds idle
                logger.warning(f"{agent_type} agent {target} has been idle for {int(idle_time)} seconds")
                return False

        return True

    def notify_pm(self, pm_target: str, idle_agents: list[tuple[str, str, int]], logger: logging.Logger) -> None:
        """Notify PM about idle agents."""
        if not idle_agents:
            return

        message = "⚠️  Idle Agent Alert:\\n\\n"
        for agent_type, target, idle_time in idle_agents:
            message += f"• {agent_type} agent {target} - idle for {idle_time}s\\n"
        message += "\\nPlease check on these agents and ensure they're making progress."

        try:
            # Send message to PM
            cmd = ["tmux", "send-keys", "-t", pm_target, f"echo '{message}'", "Enter"]
            subprocess.run(cmd, check=True)
            logger.info(f"Notified PM at {pm_target} about {len(idle_agents)} idle agents")
        except Exception as e:
            logger.error(f"Failed to notify PM: {e}")

    def run_daemon(self, interval: int = 10) -> None:
        """Main daemon loop."""
        logger = self.setup_logging()

        # Write PID
        with open(self.pid_file, "w") as f:
            f.write(str(os.getpid()))

        logger.info(f"Simple monitoring daemon started (PID: {os.getpid()}, interval: {interval}s)")

        # Set up signal handlers
        def cleanup(signum, frame):
            logger.info("Shutting down monitoring daemon")
            if self.pid_file.exists():
                self.pid_file.unlink()
            exit(0)

        signal.signal(signal.SIGTERM, cleanup)
        signal.signal(signal.SIGINT, cleanup)

        # Main loop
        while True:
            try:
                agents = self.discover_agents()

                if not agents:
                    logger.debug("No agents found")
                else:
                    logger.info(f"Monitoring {len(agents)} agents")

                    # Find PM
                    pm_target = None
                    for target, agent_type in agents.items():
                        if agent_type == "PM":
                            pm_target = target
                            break

                    # Check each agent
                    idle_agents = []
                    for target, agent_type in agents.items():
                        if not self.check_agent_activity(target, agent_type, logger):
                            idle_time = int((datetime.now() - self.agent_states[target]["last_active"]).total_seconds())
                            idle_agents.append((agent_type, target, idle_time))

                    # Notify PM if agents are idle
                    if idle_agents and pm_target:
                        self.notify_pm(pm_target, idle_agents, logger)

            except Exception as e:
                logger.error(f"Error in monitoring cycle: {e}", exc_info=True)

            time.sleep(interval)


if __name__ == "__main__":
    monitor = SimpleMonitor()
    monitor.run_daemon()

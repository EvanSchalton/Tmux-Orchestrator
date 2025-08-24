#!/usr/bin/env python3
"""
MCP Server Supervisor - Auto-restart and monitoring for Phase 2/3
Bulletproof MCP server management with health checks and recovery
"""

import asyncio
import json
import logging
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional

import psutil


@dataclass
class MCPServerStatus:
    """MCP server status snapshot"""

    timestamp: float
    pid: Optional[int]
    status: str  # running, stopped, failed, starting, recovering
    uptime_seconds: float
    memory_mb: float
    cpu_percent: float
    restart_count: int
    last_restart: Optional[float]
    health_check_status: str
    tools_count: int


class MCPServerSupervisor:
    """Production-grade MCP server supervision and auto-restart"""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path(".tmux_orchestrator/config/mcp_supervisor.json")
        self.pid_file = Path("/tmp/tmux-orc-mcp-server.pid")
        self.log_file = Path(".tmux_orchestrator/logs/mcp_supervisor.log")
        self.status_file = Path(".tmux_orchestrator/status/mcp_server.json")

        # Supervisor configuration
        self.config = {
            "health_check_interval": 30,  # seconds
            "restart_delay": 5,  # seconds between restart attempts
            "max_restart_attempts": 5,  # max restarts in window
            "restart_window": 300,  # 5 minute window for restart counting
            "memory_limit_mb": 1000,  # restart if memory exceeds this
            "cpu_limit_percent": 90,  # restart if CPU exceeds this
            "response_timeout": 10,  # health check timeout
            "startup_timeout": 60,  # max time to wait for startup
            "graceful_shutdown_timeout": 30,  # max time for graceful shutdown
        }

        self.restart_history: List[float] = []
        self.server_start_time: Optional[float] = None
        self.monitoring_active = False

        self.setup_logging()
        self.load_config()

    def setup_logging(self):
        """Setup supervisor logging"""
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.status_file.parent.mkdir(parents=True, exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler(self.log_file), logging.StreamHandler()],
        )
        self.logger = logging.getLogger("mcp_supervisor")

    def load_config(self):
        """Load supervisor configuration"""
        if self.config_path.exists():
            try:
                with open(self.config_path) as f:
                    user_config = json.load(f)
                    self.config.update(user_config)
                self.logger.info(f"Loaded config from {self.config_path}")
            except Exception as e:
                self.logger.warning(f"Failed to load config: {e}, using defaults")

    async def find_mcp_server_process(self) -> Optional[psutil.Process]:
        """Find the MCP server process"""
        try:
            # First check PID file
            if self.pid_file.exists():
                with open(self.pid_file) as f:
                    pid = int(f.read().strip())
                try:
                    proc = psutil.Process(pid)
                    if "tmux-orc server start" in " ".join(proc.cmdline()):
                        return proc
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    self.pid_file.unlink(missing_ok=True)

            # Search all processes
            for proc in psutil.process_iter(["pid", "cmdline"]):
                try:
                    if proc.info["cmdline"] and "tmux-orc server start" in " ".join(proc.info["cmdline"]):
                        # Update PID file
                        with open(self.pid_file, "w") as f:
                            f.write(str(proc.pid))
                        return proc
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            return None

        except Exception as e:
            self.logger.error(f"Error finding MCP server process: {e}")
            return None

    async def health_check(self) -> Dict[str, any]:
        """Comprehensive MCP server health check"""
        try:
            proc = await self.find_mcp_server_process()
            if not proc:
                return {"status": "not_running", "healthy": False, "details": "No MCP server process found"}

            # Process health checks
            memory_info = proc.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            cpu_percent = proc.cpu_percent()

            # Check resource limits
            memory_ok = memory_mb < self.config["memory_limit_mb"]
            cpu_ok = cpu_percent < self.config["cpu_limit_percent"]

            # Test MCP tools availability
            try:
                result = subprocess.run(
                    ["tmux-orc", "server", "tools"],
                    capture_output=True,
                    text=True,
                    timeout=self.config["response_timeout"],
                )
                tools_ok = result.returncode == 0
                tools_count = len([line for line in result.stdout.split("\n") if "→" in line])
            except subprocess.TimeoutExpired:
                tools_ok = False
                tools_count = 0
            except Exception as e:
                self.logger.warning(f"Tools check failed: {e}")
                tools_ok = False
                tools_count = 0

            healthy = memory_ok and cpu_ok and tools_ok

            return {
                "status": "running" if healthy else "unhealthy",
                "healthy": healthy,
                "pid": proc.pid,
                "memory_mb": memory_mb,
                "cpu_percent": cpu_percent,
                "memory_ok": memory_ok,
                "cpu_ok": cpu_ok,
                "tools_ok": tools_ok,
                "tools_count": tools_count,
                "uptime": time.time() - self.server_start_time if self.server_start_time else 0,
                "details": f"Memory: {memory_mb:.1f}MB, CPU: {cpu_percent:.1f}%, Tools: {tools_count}",
            }

        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {"status": "error", "healthy": False, "details": f"Health check error: {e}"}

    async def start_mcp_server(self) -> bool:
        """Start MCP server with monitoring"""
        try:
            self.logger.info("Starting MCP server...")

            # Start server process
            proc = subprocess.Popen(
                ["tmux-orc", "server", "start"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )

            # Wait for startup with timeout
            start_time = time.time()
            while time.time() - start_time < self.config["startup_timeout"]:
                if proc.poll() is not None:
                    # Process exited
                    stdout, stderr = proc.communicate()
                    self.logger.error(f"MCP server startup failed: {stderr}")
                    return False

                # Check if server is responsive
                health = await self.health_check()
                if health["healthy"]:
                    self.server_start_time = time.time()
                    self.logger.info(f"MCP server started successfully (PID: {health['pid']})")
                    return True

                await asyncio.sleep(2)

            # Startup timeout
            proc.terminate()
            self.logger.error("MCP server startup timeout")
            return False

        except Exception as e:
            self.logger.error(f"Failed to start MCP server: {e}")
            return False

    async def stop_mcp_server(self, graceful: bool = True) -> bool:
        """Stop MCP server gracefully or forcefully"""
        try:
            proc = await self.find_mcp_server_process()
            if not proc:
                self.logger.info("MCP server not running")
                return True

            self.logger.info(f"Stopping MCP server (PID: {proc.pid}, graceful: {graceful})")

            if graceful:
                # Graceful shutdown
                proc.terminate()
                try:
                    proc.wait(timeout=self.config["graceful_shutdown_timeout"])
                    self.logger.info("MCP server stopped gracefully")
                except psutil.TimeoutExpired:
                    self.logger.warning("Graceful shutdown timeout, forcing kill")
                    proc.kill()
                    proc.wait(timeout=10)
            else:
                # Force kill
                proc.kill()
                proc.wait(timeout=10)

            # Clean up PID file
            self.pid_file.unlink(missing_ok=True)
            self.server_start_time = None

            return True

        except Exception as e:
            self.logger.error(f"Failed to stop MCP server: {e}")
            return False

    async def restart_mcp_server(self, reason: str = "manual") -> bool:
        """Restart MCP server with backoff logic"""
        now = time.time()

        # Clean old restart attempts from history
        self.restart_history = [t for t in self.restart_history if now - t < self.config["restart_window"]]

        # Check restart limits
        if len(self.restart_history) >= self.config["max_restart_attempts"]:
            self.logger.error(
                f"Max restart attempts ({self.config['max_restart_attempts']}) "
                f"reached in {self.config['restart_window']}s window. Backing off."
            )
            return False

        self.logger.info(f"Restarting MCP server: {reason}")
        self.restart_history.append(now)

        # Stop current server
        await self.stop_mcp_server(graceful=True)

        # Wait before restart
        await asyncio.sleep(self.config["restart_delay"])

        # Start new server
        success = await self.start_mcp_server()
        if success:
            self.logger.info("MCP server restart successful")
        else:
            self.logger.error("MCP server restart failed")

        return success

    async def get_status(self) -> MCPServerStatus:
        """Get comprehensive server status"""
        health = await self.health_check()

        status = MCPServerStatus(
            timestamp=time.time(),
            pid=health.get("pid"),
            status=health["status"],
            uptime_seconds=health.get("uptime", 0),
            memory_mb=health.get("memory_mb", 0),
            cpu_percent=health.get("cpu_percent", 0),
            restart_count=len(self.restart_history),
            last_restart=self.restart_history[-1] if self.restart_history else None,
            health_check_status="pass" if health["healthy"] else "fail",
            tools_count=health.get("tools_count", 0),
        )

        # Save status to file
        with open(self.status_file, "w") as f:
            json.dump(asdict(status), f, indent=2)

        return status

    async def monitor_loop(self):
        """Main monitoring loop with auto-restart"""
        self.monitoring_active = True
        self.logger.info("Starting MCP server monitoring loop")

        while self.monitoring_active:
            try:
                health = await self.health_check()
                await self.get_status()

                # Log status
                if health["healthy"]:
                    self.logger.debug(f"MCP server healthy: {health['details']}")
                else:
                    self.logger.warning(f"MCP server unhealthy: {health['details']}")

                    # Auto-restart if unhealthy
                    if health["status"] == "not_running":
                        await self.restart_mcp_server("process_not_found")
                    elif health["status"] == "unhealthy":
                        restart_reason = []
                        if not health.get("memory_ok"):
                            restart_reason.append(f"memory_limit({health['memory_mb']:.1f}MB)")
                        if not health.get("cpu_ok"):
                            restart_reason.append(f"cpu_limit({health['cpu_percent']:.1f}%)")
                        if not health.get("tools_ok"):
                            restart_reason.append("tools_unresponsive")

                        await self.restart_mcp_server(" | ".join(restart_reason))

                await asyncio.sleep(self.config["health_check_interval"])

            except KeyboardInterrupt:
                self.logger.info("Monitoring interrupted by user")
                break
            except Exception as e:
                self.logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(self.config["health_check_interval"])

        self.monitoring_active = False
        self.logger.info("MCP server monitoring stopped")

    async def stop_monitoring(self):
        """Stop the monitoring loop"""
        self.monitoring_active = False
        self.logger.info("Stopping MCP server monitoring...")


# CLI interface
async def main():
    """CLI entry point for MCP supervisor"""
    import sys

    supervisor = MCPServerSupervisor()

    if len(sys.argv) < 2:
        print("Usage: python supervisor.py [start|stop|restart|status|monitor]")
        return

    command = sys.argv[1]

    if command == "start":
        success = await supervisor.start_mcp_server()
        print(f"MCP server start: {'SUCCESS' if success else 'FAILED'}")

    elif command == "stop":
        success = await supervisor.stop_mcp_server()
        print(f"MCP server stop: {'SUCCESS' if success else 'FAILED'}")

    elif command == "restart":
        reason = sys.argv[2] if len(sys.argv) > 2 else "manual"
        success = await supervisor.restart_mcp_server(reason)
        print(f"MCP server restart: {'SUCCESS' if success else 'FAILED'}")

    elif command == "status":
        status = await supervisor.get_status()
        print("MCP Server Status:")
        print(f"  Status: {status.status}")
        print(f"  PID: {status.pid}")
        print(f"  Uptime: {status.uptime_seconds:.0f}s")
        print(f"  Memory: {status.memory_mb:.1f}MB")
        print(f"  CPU: {status.cpu_percent:.1f}%")
        print(f"  Tools: {status.tools_count}")
        print(f"  Restarts: {status.restart_count}")

    elif command == "monitor":
        try:
            await supervisor.monitor_loop()
        except KeyboardInterrupt:
            await supervisor.stop_monitoring()

    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    asyncio.run(main())

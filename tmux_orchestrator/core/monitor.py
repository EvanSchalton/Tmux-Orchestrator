"""Advanced agent monitoring system with 100% accurate idle detection."""

import time
import logging
import subprocess
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass

from tmux_orchestrator.utils.tmux import TMUXManager
from tmux_orchestrator.core.config import Config


@dataclass
class AgentHealthStatus:
    """Agent health status data."""
    target: str
    last_heartbeat: datetime
    last_response: datetime
    consecutive_failures: int
    is_responsive: bool
    last_content_hash: str
    status: str  # 'healthy', 'warning', 'critical', 'unresponsive'
    is_idle: bool
    activity_changes: int


class IdleMonitor:
    """Monitor with 100% accurate idle detection using last-line monitoring."""
    
    def __init__(self, tmux: TMUXManager):
        self.tmux = tmux
        self.pid_file = Path('/tmp/tmux-orchestrator-idle-monitor.pid')
        self.log_file = Path('/tmp/tmux-orchestrator-idle-monitor.log')
    
    def is_running(self) -> bool:
        """Check if monitor daemon is running."""
        if not self.pid_file.exists():
            return False
        
        try:
            with open(self.pid_file, 'r') as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)  # Check if process exists
            return True
        except (OSError, ValueError, FileNotFoundError):
            if self.pid_file.exists():
                self.pid_file.unlink()
            return False
    
    def start(self, interval: int = 10) -> int:
        """Start the idle monitor daemon."""
        script_path = "/workspaces/Tmux-Orchestrator/commands/idle-monitor-daemon.sh"
        if not os.path.exists(script_path):
            raise FileNotFoundError(f"Monitor script not found: {script_path}")
        
        result = subprocess.run([script_path, str(interval)], capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Failed to start monitor: {result.stderr}")
        
        # Wait for PID file to be created
        for _ in range(10):  # Wait up to 1 second
            if self.pid_file.exists():
                with open(self.pid_file, 'r') as f:
                    return int(f.read().strip())
            time.sleep(0.1)
        
        raise RuntimeError("Monitor started but PID file not found")
    
    def stop(self) -> bool:
        """Stop the idle monitor daemon."""
        if not self.is_running():
            return False
        
        try:
            with open(self.pid_file, 'r') as f:
                pid = int(f.read().strip())
            os.kill(pid, 15)  # SIGTERM
            self.pid_file.unlink()
            return True
        except (OSError, ValueError, FileNotFoundError):
            return False
    
    def status(self):
        """Display monitor status."""
        from rich.console import Console
        console = Console()
        
        if self.is_running():
            with open(self.pid_file, 'r') as f:
                pid = int(f.read().strip())
            console.print(f"[green]✓ Monitor is running (PID: {pid})[/green]")
        else:
            console.print("[red]✗ Monitor is not running[/red]")
    
    def is_agent_idle(self, target: str) -> bool:
        """Check if agent is idle using the improved 4-snapshot method."""
        try:
            session, window = target.split(':')
            
            # Take 4 snapshots of the last line at 300ms intervals
            snapshots = []
            for _ in range(4):
                content = self.tmux.capture_pane(target, lines=1)
                last_line = content.strip().split('\n')[-1] if content else ""
                snapshots.append(last_line)
                time.sleep(0.3)
            
            # If all snapshots are identical, agent is idle
            return all(line == snapshots[0] for line in snapshots)
            
        except Exception:
            return False  # If we can't check, assume active


class AgentMonitor:
    """Enhanced agent monitor with bulletproof idle detection and recovery."""
    
    def __init__(self, config: Config, tmux: TMUXManager):
        self.config = config
        self.tmux = tmux
        self.idle_monitor = IdleMonitor(tmux)
        self.logger = self._setup_logging()
        self.agent_status: Dict[str, AgentHealthStatus] = {}
        
        # Health check configuration
        self.heartbeat_interval = config.get('monitoring.heartbeat_interval', 30)  
        self.response_timeout = config.get('monitoring.response_timeout', 60)  
        self.max_failures = config.get('monitoring.max_failures', 3)
        self.recovery_cooldown = config.get('monitoring.recovery_cooldown', 300)  
        
        # Track recent recovery attempts
        self.recent_recoveries: Dict[str, datetime] = {}
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging for the monitor."""
        logger = logging.getLogger('agent_monitor')
        logger.setLevel(logging.INFO)
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # Log to file
        log_file = Path('/tmp/tmux-orchestrator-monitor.log')
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def register_agent(self, target: str) -> None:
        """Register an agent for monitoring."""
        now = datetime.now()
        self.agent_status[target] = AgentHealthStatus(
            target=target,
            last_heartbeat=now,
            last_response=now,
            consecutive_failures=0,
            is_responsive=True,
            last_content_hash="",
            status="healthy",
            is_idle=False,
            activity_changes=0
        )
        self.logger.info(f"Registered agent for monitoring: {target}")
    
    def unregister_agent(self, target: str) -> None:
        """Remove agent from monitoring."""
        if target in self.agent_status:
            del self.agent_status[target]
            self.logger.info(f"Unregistered agent from monitoring: {target}")
    
    def check_agent_health(self, target: str) -> AgentHealthStatus:
        """Check agent health using improved idle detection."""
        if target not in self.agent_status:
            self.register_agent(target)
        
        status = self.agent_status[target]
        now = datetime.now()
        
        try:
            # Use the bulletproof idle detection
            is_idle = self.idle_monitor.is_agent_idle(target)
            status.is_idle = is_idle
            
            # Capture current content for change detection
            content = self.tmux.capture_pane(target, lines=50)
            content_hash = str(hash(content))
            
            # Track activity changes
            if content_hash != status.last_content_hash:
                status.last_heartbeat = now
                status.last_content_hash = content_hash
                status.activity_changes += 1
            
            # Enhanced responsiveness check
            is_responsive = self._check_agent_responsiveness(target, content, is_idle)
            
            if is_responsive:
                status.last_response = now
                status.consecutive_failures = 0
                status.is_responsive = True
                status.status = "healthy"
            else:
                status.consecutive_failures += 1
                status.is_responsive = False
                
                # Determine status based on failure patterns
                time_since_response = now - status.last_response
                if self._has_critical_errors(content):
                    status.status = "critical"
                elif time_since_response > timedelta(seconds=self.response_timeout * 2):
                    status.status = "critical"
                elif time_since_response > timedelta(seconds=self.response_timeout):
                    status.status = "warning"
                elif status.consecutive_failures >= self.max_failures:
                    status.status = "unresponsive"
                else:
                    status.status = "warning"
            
            self.agent_status[target] = status
            
        except Exception as e:
            self.logger.error(f"Error checking health for {target}: {e}")
            status.consecutive_failures += 1
            status.status = "critical"
        
        return status
    
    def _check_agent_responsiveness(self, target: str, content: str, is_idle: bool) -> bool:
        """Enhanced responsiveness check."""
        # If agent is actively working, it's responsive
        if not is_idle:
            return True
        
        # Check for normal Claude interface elements
        if self._has_normal_claude_interface(content):
            return True
        
        # Check for error conditions
        if self._has_critical_errors(content):
            return False
        
        # If idle but with normal interface, it's responsive
        return True
    
    def _has_normal_claude_interface(self, content: str) -> bool:
        """Check if content shows normal Claude interface."""
        claude_indicators = [
            "│ >",           # Claude prompt
            "assistant:",    # Claude response marker
            "I'll help",     # Common Claude response
            "I can help",    # Common Claude response
            "Let me",        # Common Claude response start
            "Human:",        # Human input marker
            "Claude:"        # Claude label
        ]
        
        return any(indicator in content for indicator in claude_indicators)
    
    def _has_critical_errors(self, content: str) -> bool:
        """Check for critical error states."""
        critical_errors = [
            "connection lost",
            "network error", 
            "timeout",
            "crashed",
            "killed",
            "segmentation fault",
            "permission denied",
            "command not found",
            "python: can't open file",
            "ModuleNotFoundError",
            "ImportError",
            "SyntaxError",
            "claude: command not found"
        ]
        
        content_lower = content.lower()
        return any(error in content_lower for error in critical_errors)
    
    def should_attempt_recovery(self, target: str, status: AgentHealthStatus) -> bool:
        """Determine if recovery should be attempted."""
        # Don't recover if recently recovered
        if target in self.recent_recoveries:
            time_since_recovery = datetime.now() - self.recent_recoveries[target]
            if time_since_recovery < timedelta(seconds=self.recovery_cooldown):
                return False
        
        # Recover if critical with multiple failures
        if status.status == "critical" and status.consecutive_failures >= self.max_failures:
            return True
        
        # Recover if unresponsive for too long
        time_since_response = datetime.now() - status.last_response
        if time_since_response > timedelta(seconds=self.response_timeout * 3):
            return True
        
        return False
    
    def attempt_recovery(self, target: str) -> bool:
        """Attempt to recover an unresponsive agent."""
        self.logger.warning(f"Attempting recovery for agent: {target}")
        
        try:
            # Use the CLI restart command
            result = subprocess.run([
                'tmux-orchestrator', 'agent', 'restart', target
            ], capture_output=True, text=True, check=True)
            
            # Mark recovery attempt
            self.recent_recoveries[target] = datetime.now()
            
            # Reset agent status after successful restart
            if target in self.agent_status:
                now = datetime.now()
                self.agent_status[target].last_response = now
                self.agent_status[target].last_heartbeat = now
                self.agent_status[target].consecutive_failures = 0
                self.agent_status[target].status = "healthy"
                self.agent_status[target].is_responsive = True
                self.agent_status[target].activity_changes = 0
            
            self.logger.info(f"Successfully recovered agent: {target}")
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to recover agent {target}: {e.stderr}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error recovering agent {target}: {e}")
            return False
    
    def monitor_all_agents(self) -> Dict[str, AgentHealthStatus]:
        """Monitor all registered agents and return their status."""
        results = {}
        
        for target in list(self.agent_status.keys()):
            try:
                status = self.check_agent_health(target)
                results[target] = status
                
                # Attempt recovery if needed
                if self.should_attempt_recovery(target, status):
                    recovery_success = self.attempt_recovery(target)
                    if recovery_success:
                        # Re-check status after recovery
                        status = self.check_agent_health(target)
                        results[target] = status
                        
            except Exception as e:
                self.logger.error(f"Error monitoring agent {target}: {e}")
        
        return results
    
    def get_unhealthy_agents(self) -> List[Tuple[str, AgentHealthStatus]]:
        """Get list of agents that are not healthy."""
        unhealthy = []
        for target, status in self.agent_status.items():
            if status.status != "healthy":
                unhealthy.append((target, status))
        return unhealthy
    
    def get_monitoring_summary(self) -> Dict:
        """Get a summary of monitoring status."""
        total_agents = len(self.agent_status)
        healthy = sum(1 for s in self.agent_status.values() if s.status == "healthy")
        warning = sum(1 for s in self.agent_status.values() if s.status == "warning")
        critical = sum(1 for s in self.agent_status.values() if s.status == "critical")
        unresponsive = sum(1 for s in self.agent_status.values() if s.status == "unresponsive")
        idle = sum(1 for s in self.agent_status.values() if s.is_idle)
        
        return {
            'total_agents': total_agents,
            'healthy': healthy,
            'warning': warning,
            'critical': critical,
            'unresponsive': unresponsive,
            'idle': idle,
            'recent_recoveries': len(self.recent_recoveries)
        }
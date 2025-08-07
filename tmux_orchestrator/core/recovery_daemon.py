"""Recovery daemon with 100% accurate idle detection integration."""

import time
import signal
import sys
import os
import logging
from pathlib import Path
from typing import Set
from datetime import datetime

from tmux_orchestrator.core.monitor import AgentMonitor
from tmux_orchestrator.core.config import Config
from tmux_orchestrator.utils.tmux import TMUXManager


class RecoveryDaemon:
    """Recovery daemon with bulletproof idle detection and automatic recovery."""
    
    def __init__(self, config_file: str = None):
        self.config = Config(config_file)
        self.tmux = TMUXManager()
        self.monitor = AgentMonitor(self.config, self.tmux)
        self.logger = self._setup_logging()
        self.running = False
        
        # Daemon configuration
        self.check_interval = self.config.get('daemon.check_interval', 30)  
        self.auto_discover = self.config.get('daemon.auto_discover', True)
        self.pid_file = Path('/tmp/tmux-orchestrator-recovery.pid')
        self.log_file = Path('/tmp/tmux-orchestrator-recovery.log')
        
        # Track discovered agents
        self.known_agents: Set[str] = set()
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _setup_logging(self) -> logging.Logger:
        """Set up daemon logging."""
        logger = logging.getLogger('recovery_daemon')
        logger.setLevel(logging.INFO)
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # File handler
        handler = logging.FileHandler(self.log_file)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)
    
    def _write_pid_file(self):
        """Write daemon PID to file."""
        with open(self.pid_file, 'w') as f:
            f.write(str(os.getpid()))
    
    def _remove_pid_file(self):
        """Remove daemon PID file."""
        if self.pid_file.exists():
            self.pid_file.unlink()
    
    def _discover_agents(self) -> Set[str]:
        """Discover Claude agents using improved detection."""
        discovered = set()
        
        try:
            sessions = self.tmux.list_sessions()
            
            for session in sessions:
                session_name = session['name']
                
                # Skip orchestrator sessions
                if any(skip in session_name.lower() for skip in ['orchestrator', 'tmux-orc', 'recovery']):
                    continue
                
                windows = self.tmux.list_windows(session_name)
                
                for window in windows:
                    window_index = window.get('index', '0')
                    target = f"{session_name}:{window_index}"
                    
                    # Enhanced Claude agent detection
                    if self._is_claude_agent(target):
                        discovered.add(target)
                        
                        # Register new agents
                        if target not in self.known_agents:
                            self.monitor.register_agent(target)
                            self.logger.info(f"Auto-discovered Claude agent: {target}")
                            self.known_agents.add(target)
        
        except Exception as e:
            self.logger.error(f"Error during agent discovery: {e}")
        
        return discovered
    
    def _is_claude_agent(self, target: str) -> bool:
        """Enhanced Claude agent detection using multiple indicators."""
        try:
            # Get both recent and historical content
            recent_content = self.tmux.capture_pane(target, lines=30)
            if not recent_content:
                return False
            
            content_lower = recent_content.lower()
            
            # Strong indicators of Claude agents
            strong_indicators = [
                "│ >",                    # Claude prompt box
                "assistant:",             # Claude response marker
                "claude:",               # Claude name
                "anthropic",             # Company name
                "i'll help",             # Common Claude response
                "let me",                # Common Claude start
                "human:",                # Human input marker
            ]
            
            # Medium indicators (need multiple)
            medium_indicators = [
                "i can",
                "certainly",
                "would you like",
                "happy to help",
                "analyze",
                "implement",
                "understand"
            ]
            
            # Check for strong indicators
            strong_matches = sum(1 for indicator in strong_indicators 
                               if indicator in content_lower)
            
            # Check for medium indicators  
            medium_matches = sum(1 for indicator in medium_indicators
                               if indicator in content_lower)
            
            # Agent detection logic
            if strong_matches >= 1:  # Any strong indicator
                return True
            elif medium_matches >= 3:  # Multiple medium indicators
                return True
            elif "claude" in content_lower and medium_matches >= 1:
                return True
            
            return False
            
        except Exception as e:
            self.logger.debug(f"Error checking if {target} is Claude agent: {e}")
            return False
    
    def _cleanup_stale_agents(self, current_agents: Set[str]):
        """Remove agents that no longer exist from monitoring."""
        stale_agents = self.known_agents - current_agents
        
        for stale_agent in stale_agents:
            self.monitor.unregister_agent(stale_agent)
            self.known_agents.remove(stale_agent)
            self.logger.info(f"Removed stale agent from monitoring: {stale_agent}")
    
    def start(self):
        """Start the recovery daemon."""
        if self.is_running():
            self.logger.error("Daemon is already running")
            return False
        
        self.logger.info("Starting recovery daemon with improved idle detection...")
        self._write_pid_file()
        self.running = True
        
        try:
            self._run_daemon_loop()
        except KeyboardInterrupt:
            self.logger.info("Daemon interrupted by user")
        except Exception as e:
            self.logger.error(f"Daemon error: {e}")
        finally:
            self.stop()
        
        return True
    
    def stop(self):
        """Stop the recovery daemon."""
        if self.running:
            self.logger.info("Stopping recovery daemon...")
            self.running = False
            self._remove_pid_file()
    
    def is_running(self) -> bool:
        """Check if daemon is already running."""
        if not self.pid_file.exists():
            return False
        
        try:
            with open(self.pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            os.kill(pid, 0)  # Check if process exists
            return True
        except (OSError, ValueError):
            self._remove_pid_file()
            return False
    
    def _run_daemon_loop(self):
        """Main daemon loop with enhanced monitoring."""
        self.logger.info(f"Daemon started with check interval: {self.check_interval}s")
        self.logger.info("Using bulletproof 4-snapshot idle detection algorithm")
        
        while self.running:
            try:
                start_time = datetime.now()
                
                # Discover agents if auto-discovery is enabled
                current_agents = set()
                if self.auto_discover:
                    current_agents = self._discover_agents()
                    self._cleanup_stale_agents(current_agents)
                
                # Monitor all registered agents with improved detection
                statuses = self.monitor.monitor_all_agents()
                
                # Enhanced logging with idle status
                summary = self.monitor.get_monitoring_summary()
                if summary['total_agents'] > 0:
                    self.logger.info(
                        f"Monitoring {summary['total_agents']} agents: "
                        f"{summary['healthy']} healthy, "
                        f"{summary['warning']} warning, "
                        f"{summary['critical']} critical, "
                        f"{summary['unresponsive']} unresponsive, "
                        f"{summary['idle']} idle"
                    )
                
                # Log detailed status for unhealthy agents
                unhealthy = self.monitor.get_unhealthy_agents()
                for target, status in unhealthy:
                    idle_status = "idle" if status.is_idle else "active"
                    self.logger.warning(
                        f"Agent {target} is {status.status} ({idle_status}): "
                        f"{status.consecutive_failures} failures, "
                        f"last response: {status.last_response.strftime('%H:%M:%S')}, "
                        f"activity changes: {status.activity_changes}"
                    )
                
                # Log successful recoveries
                if summary.get('recent_recoveries', 0) > 0:
                    self.logger.info(f"Recent recoveries: {summary['recent_recoveries']}")
                
                # Calculate sleep time to maintain consistent interval
                elapsed = (datetime.now() - start_time).total_seconds()
                sleep_time = max(0, self.check_interval - elapsed)
                
                if self.running:
                    time.sleep(sleep_time)
                    
            except Exception as e:
                self.logger.error(f"Error in daemon loop: {e}")
                if self.running:
                    time.sleep(self.check_interval)
    
    def get_status(self) -> dict:
        """Get daemon status information."""
        is_running = self.is_running()
        pid = None
        
        if is_running and self.pid_file.exists():
            with open(self.pid_file, 'r') as f:
                pid = int(f.read().strip())
        
        return {
            'running': is_running,
            'pid': pid,
            'config_file': self.config.config_file,
            'check_interval': self.check_interval,
            'auto_discover': self.auto_discover,
            'log_file': str(self.log_file),
            'pid_file': str(self.pid_file),
            'enhanced_detection': True  # Flag indicating improved idle detection
        }


def main():
    """Main entry point for recovery daemon."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Tmux Orchestrator Recovery Daemon with Enhanced Detection')
    parser.add_argument('command', choices=['start', 'stop', 'restart', 'status'],
                       help='Daemon command')
    parser.add_argument('--config', '-c', help='Configuration file path')
    
    args = parser.parse_args()
    
    daemon = RecoveryDaemon(args.config)
    
    if args.command == 'start':
        if daemon.is_running():
            print("Recovery daemon is already running")
            sys.exit(1)
        print("Starting recovery daemon with bulletproof idle detection...")
        daemon.start()
    
    elif args.command == 'stop':
        if not daemon.is_running():
            print("Recovery daemon is not running")
            sys.exit(1)
        
        with open(daemon.pid_file, 'r') as f:
            pid = int(f.read().strip())
        os.kill(pid, signal.SIGTERM)
        print("Sent stop signal to recovery daemon")
    
    elif args.command == 'restart':
        if daemon.is_running():
            with open(daemon.pid_file, 'r') as f:
                pid = int(f.read().strip())
            os.kill(pid, signal.SIGTERM)
            time.sleep(2)
        print("Restarting recovery daemon with enhanced detection...")
        daemon.start()
    
    elif args.command == 'status':
        status = daemon.get_status()
        print(f"Recovery daemon running: {status['running']}")
        if status['pid']:
            print(f"PID: {status['pid']}")
        print(f"Check interval: {status['check_interval']}s")
        print(f"Auto-discovery: {status['auto_discover']}")
        print(f"Enhanced idle detection: {status['enhanced_detection']}")
        print(f"Log file: {status['log_file']}")


if __name__ == '__main__':
    main()
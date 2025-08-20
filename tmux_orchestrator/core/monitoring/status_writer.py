"""Status file writer for daemon-based agent status tracking."""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

from tmux_orchestrator.core.config import Config


class StatusWriter:
    """Writes agent and daemon status to a JSON file for external consumption."""
    
    def __init__(self, status_file: Optional[Path] = None):
        """Initialize the status writer.
        
        Args:
            status_file: Path to status file. Defaults to .tmux_orchestrator/status.json
        """
        if status_file is None:
            config = Config.load()
            status_dir = config.orchestrator_base_dir
            status_dir.mkdir(exist_ok=True)
            self.status_file = status_dir / 'status.json'
        else:
            self.status_file = status_file
            
    def write_status(self, 
                    agents: Dict[str, Dict[str, Any]], 
                    daemon_info: Dict[str, Any]) -> None:
        """Write status data to file atomically.
        
        Args:
            agents: Dictionary of agent states keyed by agent ID
            daemon_info: Information about daemon status
        """
        # Build status document
        status_doc = {
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "daemon_status": daemon_info,
            "agents": {},
            "summary": {
                "total_agents": 0,
                "active": 0,
                "idle": 0,
                "error": 0,
                "busy": 0,
                "unknown": 0
            }
        }
        
        # Process agents
        for agent_id, agent_data in agents.items():
            # Convert agent state to serializable format
            agent_status = {
                "name": agent_data.get("name", "unknown"),
                "type": agent_data.get("type", "unknown"),
                "status": agent_data.get("status", "unknown"),
                "last_activity": agent_data.get("last_activity"),
                "pane_id": agent_data.get("pane_id"),
                "session": agent_data.get("session"),
                "window": agent_data.get("window"),
                "state_details": {
                    "idle_count": agent_data.get("idle_count", 0),
                    "content_based_state": agent_data.get("content_state"),
                    "last_content_check": agent_data.get("last_content_check")
                }
            }
            
            # Update summary counts
            status = agent_status["status"]
            status_doc["summary"]["total_agents"] += 1
            if status in status_doc["summary"]:
                status_doc["summary"][status] += 1
            else:
                status_doc["summary"]["unknown"] += 1
                
            status_doc["agents"][agent_id] = agent_status
        
        # Write atomically using temp file
        self._write_atomic(status_doc)
        
    def _write_atomic(self, data: Dict[str, Any]) -> None:
        """Write data to file atomically to prevent corruption.
        
        Args:
            data: Data to write to status file
        """
        # Create temp file in same directory for atomic rename
        temp_fd, temp_path = tempfile.mkstemp(
            dir=self.status_file.parent,
            prefix='.status_',
            suffix='.tmp'
        )
        
        try:
            # Write to temp file
            with os.fdopen(temp_fd, 'w') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            # Atomic rename
            os.replace(temp_path, self.status_file)
            
        except Exception:
            # Clean up temp file on error
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise
            
    def read_status(self) -> Optional[Dict[str, Any]]:
        """Read current status from file.
        
        Returns:
            Status dictionary or None if file doesn't exist
        """
        if not self.status_file.exists():
            return None
            
        try:
            with open(self.status_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None
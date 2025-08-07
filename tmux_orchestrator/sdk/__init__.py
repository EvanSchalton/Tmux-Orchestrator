"""TMUX Orchestrator SDK for AI agents."""

import os
import httpx
from typing import Optional, List, Dict, Any
from datetime import datetime


class Message:
    """Represents a message between agents."""
    
    def __init__(self, from_agent: str, to_agent: str, content: str, timestamp: Optional[datetime] = None):
        self.from_agent = from_agent
        self.to_agent = to_agent
        self.content = content
        self.timestamp = timestamp or datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return {
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "content": self.content,
            "timestamp": self.timestamp.isoformat()
        }


class Agent:
    """SDK for AI agents to interact with the orchestrator."""
    
    def __init__(self, agent_type: str, role: str, session: Optional[str] = None):
        self.agent_type = agent_type
        self.role = role
        self.session = session or os.environ.get('TMUX', '').split(',')[0]
        self.agent_id = f"{self.session}:{agent_type}:{role}"
        
        # Get server URL from environment or use default
        self.server_url = os.environ.get('TMUX_ORCHESTRATOR_URL', 'http://localhost:8000')
        self.client = httpx.Client(base_url=self.server_url)
        
    def register(self) -> bool:
        """Register this agent with the orchestrator."""
        try:
            response = self.client.post('/agents/register', json={
                "agent_id": self.agent_id,
                "agent_type": self.agent_type,
                "role": self.role,
                "session": self.session
            })
            return response.status_code == 200
        except Exception as e:
            print(f"Failed to register: {e}")
            return False
    
    def send_message(self, to_agent: str, content: str) -> bool:
        """Send a message to another agent."""
        try:
            message = Message(self.agent_id, to_agent, content)
            response = self.client.post('/messages/send', json=message.to_dict())
            return response.status_code == 200
        except Exception as e:
            print(f"Failed to send message: {e}")
            return False
    
    def get_messages(self) -> List[Message]:
        """Get messages for this agent."""
        try:
            response = self.client.get(f'/messages/inbox/{self.agent_id}')
            if response.status_code == 200:
                return [
                    Message(
                        from_agent=msg['from_agent'],
                        to_agent=msg['to_agent'],
                        content=msg['content'],
                        timestamp=datetime.fromisoformat(msg['timestamp'])
                    )
                    for msg in response.json()
                ]
            return []
        except Exception as e:
            print(f"Failed to get messages: {e}")
            return []
    
    def report_status(self, status: str) -> bool:
        """Report current status to the orchestrator."""
        try:
            response = self.client.put(f'/agents/{self.agent_id}/status', json={
                "status": status,
                "timestamp": datetime.now().isoformat()
            })
            return response.status_code == 200
        except Exception as e:
            print(f"Failed to report status: {e}")
            return False
    
    def report_activity(self) -> bool:
        """Report activity to avoid being marked as idle."""
        try:
            response = self.client.post('/monitor/report-activity', json={
                "agent_id": self.agent_id,
                "timestamp": datetime.now().isoformat()
            })
            return response.status_code == 200
        except Exception as e:
            print(f"Failed to report activity: {e}")
            return False
    
    def get_tasks(self) -> List[Dict[str, Any]]:
        """Get assigned tasks."""
        try:
            response = self.client.get(f'/tasks/{self.agent_id}')
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            print(f"Failed to get tasks: {e}")
            return []
    
    def update_task_status(self, task_id: str, status: str) -> bool:
        """Update task status."""
        try:
            response = self.client.put(f'/tasks/{task_id}/status', json={
                "status": status,
                "agent_id": self.agent_id,
                "timestamp": datetime.now().isoformat()
            })
            return response.status_code == 200
        except Exception as e:
            print(f"Failed to update task status: {e}")
            return False
    
    def request_help(self, issue: str) -> bool:
        """Request help from other agents."""
        try:
            response = self.client.post('/coordination/request-help', json={
                "agent_id": self.agent_id,
                "issue": issue,
                "timestamp": datetime.now().isoformat()
            })
            return response.status_code == 200
        except Exception as e:
            print(f"Failed to request help: {e}")
            return False
    
    def handoff_work(self, to_agent: str, work_description: str) -> bool:
        """Hand off work to another agent."""
        try:
            response = self.client.post('/coordination/handoff', json={
                "from_agent": self.agent_id,
                "to_agent": to_agent,
                "work_description": work_description,
                "timestamp": datetime.now().isoformat()
            })
            return response.status_code == 200
        except Exception as e:
            print(f"Failed to handoff work: {e}")
            return False
    
    def unregister(self) -> bool:
        """Unregister this agent from the orchestrator."""
        try:
            response = self.client.delete(f'/agents/{self.agent_id}')
            return response.status_code == 200
        except Exception as e:
            print(f"Failed to unregister: {e}")
            return False
    
    def __enter__(self):
        """Context manager entry."""
        self.register()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.unregister()
        self.client.close()
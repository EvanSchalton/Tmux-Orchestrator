"""Comprehensive Pydantic models for TMUX Orchestrator MCP Server.

This module provides centralized, reusable Pydantic models for all MCP tools
and API endpoints. Models are organized by domain and include JSON schema
configuration for OpenAPI documentation.
"""

from .agent_models import *  # noqa: F403
from .communication_models import *  # noqa: F403
from .coordination_models import *  # noqa: F403
from .monitoring_models import *  # noqa: F403
from .task_models import *  # noqa: F403

__all__ = [  # noqa: F405
    # Agent Models
    "AgentSpawnRequest",
    "AgentSpawnResponse",
    "AgentStatusRequest",
    "AgentStatusResponse",
    "AgentRestartRequest",
    "AgentRestartResponse",
    "AgentKillRequest",
    "AgentKillResponse",
    "AgentListResponse",
    # Communication Models
    "MessageRequest",
    "MessageResponse",
    "BroadcastRequest",
    "BroadcastResponse",
    "InterruptRequest",
    "InterruptResponse",
    "ConversationHistoryRequest",
    "ConversationHistoryResponse",
    # Coordination Models
    "TeamMember",
    "TeamDeploymentRequest",
    "TeamDeploymentResponse",
    "StandupRequest",
    "StandupResponse",
    "TeamRecoveryRequest",
    "TeamRecoveryResponse",
    "TeamStatusRequest",
    "TeamStatusResponse",
    # Monitoring Models
    "SystemStatusRequest",
    "SystemStatusResponse",
    "SessionDetailRequest",
    "SessionDetailResponse",
    "HealthCheckRequest",
    "HealthCheckResponse",
    "IdleAgentsRequest",
    "IdleAgentsResponse",
    "ActiveAgentsRequest",
    "ActiveAgentsResponse",
    # Task Models
    "Task",
    "TaskQueue",
    "TaskCreateRequest",
    "TaskCreateResponse",
    "TaskListRequest",
    "TaskListResponse",
    "TaskStatusRequest",
    "TaskStatusResponse",
]

"""Pydantic models for system monitoring and health operations."""

from typing import Any, Union

from pydantic import BaseModel, ConfigDict, Field


class SystemStatusRequest(BaseModel):
    """Request model for system status checks."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "include_metrics": True,
                "include_agent_details": True,
                "metrics_window_minutes": 30,
            }
        }
    )

    include_metrics: bool = Field(True, description="Include performance metrics in response")
    include_agent_details: bool = Field(True, description="Include detailed agent information")
    metrics_window_minutes: int = Field(30, description="Time window for metrics calculation", ge=1, le=1440)


class SystemStatusResponse(BaseModel):
    """Response model for system status operations."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "system_health": "healthy",
                "timestamp": "2025-01-08T15:30:00Z",
                "sessions": {"total": 3, "active": 3, "attached": 1},
                "agents": {"total": 8, "active": 6, "idle": 2, "error": 0},
                "performance_metrics": {
                    "avg_response_time_ms": 245,
                    "success_rate": 98.5,
                    "uptime_hours": 72.5,
                },
                "resource_usage": {
                    "cpu_percent": 15.2,
                    "memory_mb": 512,
                    "disk_usage_percent": 25.8,
                },
            }
        }
    )

    system_health: str = Field(
        ...,
        description="Overall system health status",
        pattern="^(healthy|warning|critical|unknown)$",
    )
    timestamp: str = Field(..., description="Status query timestamp")
    sessions: dict[str, int] = Field(..., description="Session statistics")
    agents: dict[str, int] = Field(..., description="Agent statistics")
    performance_metrics: dict[str, Union[float, int]] = Field(..., description="System performance metrics")
    resource_usage: dict[str, Union[float, int]] = Field(..., description="Resource utilization metrics")
    alerts: list[dict[str, str]] = Field(default_factory=list, description="Active system alerts")


class SessionDetailRequest(BaseModel):
    """Request model for detailed session information."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_name": "frontend-team",
                "include_agent_activity": True,
                "include_performance_data": True,
                "activity_lines": 50,
            }
        }
    )

    session_name: str = Field(..., description="Session name to get details for", min_length=1)
    include_agent_activity: bool = Field(True, description="Include recent agent activity")
    include_performance_data: bool = Field(True, description="Include performance metrics")
    activity_lines: int = Field(50, description="Number of activity lines per agent", ge=1, le=200)


class SessionDetailResponse(BaseModel):
    """Response model for session detail operations."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_name": "frontend-team",
                "session_metadata": {
                    "created": "2025-01-08T14:00:00Z",
                    "attached": True,
                    "last_activity": "2025-01-08T15:29:00Z",
                    "total_windows": 4,
                },
                "agents": [
                    {
                        "window": "Claude-developer",
                        "type": "developer",
                        "status": "active",
                        "uptime_minutes": 90,
                        "recent_activity": [
                            "Working on login component",
                            "Running tests",
                        ],
                        "performance": {
                            "response_time_ms": 180,
                            "task_completion_rate": 94.2,
                        },
                    }
                ],
                "session_performance": {
                    "total_tasks_completed": 23,
                    "avg_task_time_minutes": 15.5,
                    "collaboration_score": 87,
                },
            }
        }
    )

    session_name: str = Field(..., description="Session name")
    session_metadata: dict[str, Any] = Field(..., description="Session metadata and basic information")
    agents: list[dict[str, Any]] = Field(..., description="Detailed agent information")
    session_performance: dict[str, Union[float, int]] = Field(..., description="Session-level performance metrics")
    queried_at: str = Field(..., description="When details were queried")


class HealthCheckRequest(BaseModel):
    """Request model for system health checks."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "check_type": "comprehensive",
                "timeout_seconds": 10,
                "include_diagnostics": True,
            }
        }
    )

    check_type: str = Field(
        "basic",
        description="Type of health check to perform",
        pattern="^(basic|comprehensive|minimal)$",
    )
    timeout_seconds: int = Field(10, description="Timeout for health check operations", ge=1, le=60)
    include_diagnostics: bool = Field(False, description="Include diagnostic information in response")


class HealthCheckResponse(BaseModel):
    """Response model for health check operations."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "tmux_responsive": True,
                "active_sessions": 3,
                "responsive_agents": 7,
                "timestamp": "2025-01-08T15:30:00Z",
                "checks_performed": [
                    "tmux_connectivity",
                    "agent_responsiveness",
                    "resource_availability",
                ],
                "response_time_ms": 145,
                "details": {
                    "tmux_version": "3.3a",
                    "system_load": 0.85,
                    "available_memory_gb": 12.4,
                },
            }
        }
    )

    status: str = Field(
        ...,
        description="Overall health status",
        pattern="^(healthy|warning|critical|unknown)$",
    )
    tmux_responsive: bool = Field(..., description="Whether tmux is responding")
    active_sessions: int = Field(..., description="Number of active sessions")
    responsive_agents: int = Field(..., description="Number of responsive agents")
    timestamp: str = Field(..., description="Health check timestamp")
    checks_performed: list[str] = Field(..., description="List of health checks that were performed")
    response_time_ms: int = Field(..., description="Health check response time")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional diagnostic details")


class IdleAgentsRequest(BaseModel):
    """Request model for querying idle agents."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "min_idle_minutes": 5,
                "include_activity_context": True,
                "group_by_session": True,
            }
        }
    )

    min_idle_minutes: int = Field(5, description="Minimum minutes an agent must be idle", ge=0, le=1440)
    include_activity_context: bool = Field(True, description="Include last activity information")
    group_by_session: bool = Field(False, description="Group results by session")


class IdleAgentsResponse(BaseModel):
    """Response model for idle agents queries."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "idle_agents": [
                    {
                        "target": "frontend:Claude-developer",
                        "type": "developer",
                        "idle_duration_minutes": 15,
                        "last_activity": "2025-01-08T15:15:00Z",
                        "last_activity_summary": "Completed component testing",
                    }
                ],
                "total_idle": 2,
                "by_session": {"frontend": 1, "backend": 1},
                "queried_at": "2025-01-08T15:30:00Z",
            }
        }
    )

    idle_agents: list[dict[str, Any]] = Field(..., description="List of idle agents with details")
    total_idle: int = Field(..., description="Total number of idle agents")
    by_session: dict[str, int] = Field(..., description="Idle agents grouped by session")
    queried_at: str = Field(..., description="When idle agents were queried")


class ActiveAgentsRequest(BaseModel):
    """Request model for querying active agents."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "include_current_task": True,
                "include_performance_metrics": True,
                "activity_threshold_minutes": 2,
            }
        }
    )

    include_current_task: bool = Field(True, description="Include current task information")
    include_performance_metrics: bool = Field(False, description="Include performance data")
    activity_threshold_minutes: int = Field(2, description="Minutes of activity to consider 'active'", ge=0, le=60)


class ActiveAgentsResponse(BaseModel):
    """Response model for active agents queries."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "active_agents": [
                    {
                        "target": "frontend:Claude-pm",
                        "type": "pm",
                        "activity_level": "high",
                        "current_task": "Reviewing pull requests",
                        "active_duration_minutes": 45,
                        "performance": {
                            "tasks_completed_today": 8,
                            "avg_response_time_ms": 220,
                        },
                    }
                ],
                "total_active": 5,
                "by_activity_level": {"high": 2, "medium": 2, "low": 1},
                "queried_at": "2025-01-08T15:30:00Z",
            }
        }
    )

    active_agents: list[dict[str, Any]] = Field(..., description="List of active agents with details")
    total_active: int = Field(..., description="Total number of active agents")
    by_activity_level: dict[str, int] = Field(..., description="Active agents grouped by activity level")
    queried_at: str = Field(..., description="When active agents were queried")

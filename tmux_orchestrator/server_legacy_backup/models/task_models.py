"""Pydantic models for task management operations."""

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class Task(BaseModel):
    """Core task model with comprehensive task information."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "task_001_153045",
                "title": "Implement user authentication system",
                "description": "Create JWT-based authentication with login/logout functionality",
                "assigned_to": "frontend:Claude-developer",
                "status": "in_progress",
                "priority": "high",
                "created_at": "2025-01-08T15:30:00Z",
                "updated_at": "2025-01-08T15:35:00Z",
                "completion_criteria": [
                    "Login form component completed",
                    "JWT token handling implemented",
                    "User session management working",
                ],
                "dependencies": ["task_002", "task_005"],
                "estimated_hours": 4,
                "tags": ["authentication", "security", "frontend"],
            }
        }
    )

    id: str = Field(..., description="Unique task identifier")
    title: str = Field(..., description="Task title/summary", min_length=1, max_length=200)
    description: str = Field(..., description="Detailed task description", max_length=2000)
    assigned_to: Optional[str] = Field(None, description="Agent target assigned to this task", pattern=r"^[^:]+:[^:]+$")
    status: str = Field(
        "pending",
        description="Current task status",
        pattern="^(pending|assigned|in_progress|blocked|completed|cancelled)$",
    )
    priority: str = Field(
        "medium",
        description="Task priority level",
        pattern="^(low|medium|high|urgent|critical)$",
    )
    created_at: str = Field(..., description="ISO timestamp of task creation")
    updated_at: Optional[str] = Field(None, description="ISO timestamp of last update")
    completion_criteria: list[str] = Field(default_factory=list, description="List of completion requirements")
    dependencies: list[str] = Field(default_factory=list, description="List of prerequisite task IDs")
    estimated_hours: Optional[float] = Field(None, description="Estimated hours to complete", ge=0.1, le=100.0)
    tags: list[str] = Field(default_factory=list, description="Task categorization tags")


class TaskQueue(BaseModel):
    """Model for agent task queues."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "agent_target": "frontend:Claude-developer",
                "agent_type": "developer",
                "pending_tasks": [
                    {
                        "id": "task_001",
                        "title": "Fix authentication bug",
                        "priority": "high",
                    }
                ],
                "current_task": {
                    "id": "task_002",
                    "title": "Implement user profile page",
                    "started_at": "2025-01-08T15:30:00Z",
                },
                "completed_tasks": [
                    {
                        "id": "task_003",
                        "title": "Setup project structure",
                        "completed_at": "2025-01-08T14:45:00Z",
                    }
                ],
                "queue_metrics": {
                    "total_assigned": 5,
                    "pending_count": 2,
                    "in_progress_count": 1,
                    "completed_count": 2,
                },
            }
        }
    )

    agent_target: str = Field(..., description="Agent target (session:window)", pattern=r"^[^:]+:[^:]+$")
    agent_type: str = Field(..., description="Type/specialization of agent")
    pending_tasks: list[dict[str, Any]] = Field(default_factory=list, description="Tasks waiting to be started")
    current_task: Optional[dict[str, Any]] = Field(None, description="Currently active task")
    completed_tasks: list[dict[str, Any]] = Field(default_factory=list, description="Recently completed tasks")
    queue_metrics: dict[str, int] = Field(..., description="Queue statistics and metrics")


class TaskCreateRequest(BaseModel):
    """Request model for creating new tasks."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Implement user authentication",
                "description": "Create JWT-based auth system with secure token handling",
                "priority": "high",
                "assigned_to": "frontend:Claude-developer",
                "completion_criteria": [
                    "Login form completed",
                    "Token storage implemented",
                    "Session management working",
                ],
                "dependencies": ["task_002"],
                "estimated_hours": 4.5,
                "tags": ["authentication", "security"],
            }
        }
    )

    title: str = Field(..., description="Task title", min_length=1, max_length=200)
    description: str = Field(..., description="Detailed task description", min_length=10, max_length=2000)
    priority: str = Field(
        "medium",
        description="Task priority",
        pattern="^(low|medium|high|urgent|critical)$",
    )
    assigned_to: Optional[str] = Field(None, description="Agent to assign task to", pattern=r"^[^:]+:[^:]+$")
    completion_criteria: list[str] = Field(default_factory=list, description="Success criteria for task completion")
    dependencies: list[str] = Field(default_factory=list, description="Prerequisite task IDs")
    estimated_hours: Optional[float] = Field(None, description="Time estimate in hours", ge=0.1, le=100.0)
    tags: list[str] = Field(default_factory=list, description="Task tags for organization")


class TaskCreateResponse(BaseModel):
    """Response model for task creation operations."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "task": {
                    "id": "task_001_153045",
                    "title": "Implement user authentication",
                    "status": "pending",
                    "created_at": "2025-01-08T15:30:45Z",
                },
                "assigned_to_agent": True,
                "queue_position": 3,
            }
        }
    )

    success: bool = Field(..., description="Task creation success")
    task: Task = Field(..., description="Created task details")
    assigned_to_agent: bool = Field(..., description="Whether task was assigned to an agent")
    queue_position: Optional[int] = Field(None, description="Position in agent's task queue")
    error_message: Optional[str] = Field(None, description="Error details if failed")


class TaskListRequest(BaseModel):
    """Request model for listing tasks."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "in_progress",
                "assigned_to": "frontend:Claude-developer",
                "priority": "high",
                "tags": ["authentication", "frontend"],
                "limit": 50,
                "offset": 0,
                "sort_by": "priority",
                "sort_order": "desc",
            }
        }
    )

    status: Optional[str] = Field(
        None,
        description="Filter by task status",
        pattern="^(pending|assigned|in_progress|blocked|completed|cancelled)$",
    )
    assigned_to: Optional[str] = Field(None, description="Filter by assigned agent", pattern=r"^[^:]+:[^:]+$")
    priority: Optional[str] = Field(
        None,
        description="Filter by priority level",
        pattern="^(low|medium|high|urgent|critical)$",
    )
    tags: list[str] = Field(default_factory=list, description="Filter by tags (any match)")
    limit: int = Field(50, description="Maximum number of tasks to return", ge=1, le=500)
    offset: int = Field(0, description="Number of tasks to skip", ge=0)
    sort_by: str = Field(
        "created_at",
        description="Field to sort by",
        pattern="^(created_at|updated_at|priority|status|title)$",
    )
    sort_order: str = Field("desc", description="Sort order", pattern="^(asc|desc)$")


class TaskListResponse(BaseModel):
    """Response model for task listing operations."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tasks": [
                    {
                        "id": "task_001",
                        "title": "Implement authentication",
                        "status": "in_progress",
                        "priority": "high",
                        "assigned_to": "frontend:Claude-developer",
                    }
                ],
                "total_count": 1,
                "returned_count": 1,
                "has_more": False,
                "filters_applied": {"status": "in_progress", "priority": "high"},
                "queried_at": "2025-01-08T15:30:00Z",
            }
        }
    )

    tasks: list[Task] = Field(..., description="List of tasks matching criteria")
    total_count: int = Field(..., description="Total tasks matching filters")
    returned_count: int = Field(..., description="Number of tasks in this response")
    has_more: bool = Field(..., description="Whether more tasks are available")
    filters_applied: dict[str, Any] = Field(..., description="Summary of applied filters")
    queried_at: str = Field(..., description="When the query was executed")


class TaskStatusRequest(BaseModel):
    """Request model for task status queries."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "task_id": "task_001_153045",
                "include_history": True,
                "include_dependencies": True,
            }
        }
    )

    task_id: str = Field(..., description="Task ID to get status for", min_length=1)
    include_history: bool = Field(False, description="Include task history/changelog")
    include_dependencies: bool = Field(True, description="Include dependency information")


class TaskStatusResponse(BaseModel):
    """Response model for task status operations."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "task": {
                    "id": "task_001_153045",
                    "title": "Implement authentication",
                    "status": "in_progress",
                    "progress_percentage": 75,
                    "assigned_to": "frontend:Claude-developer",
                },
                "progress_details": {
                    "completed_criteria": 2,
                    "total_criteria": 3,
                    "time_spent_hours": 2.5,
                    "estimated_completion": "2025-01-08T17:00:00Z",
                },
                "dependencies": {
                    "blocked_by": [],
                    "blocking": ["task_003", "task_007"],
                    "dependency_status": "resolved",
                },
                "history": [
                    {
                        "timestamp": "2025-01-08T15:30:00Z",
                        "action": "created",
                        "details": "Task created and assigned",
                    }
                ],
                "queried_at": "2025-01-08T15:35:00Z",
            }
        }
    )

    task: Task = Field(..., description="Complete task information")
    progress_details: dict[str, Any] = Field(..., description="Detailed progress information")
    dependencies: dict[str, Any] = Field(..., description="Task dependency information")
    history: list[dict[str, Any]] = Field(default_factory=list, description="Task history/changelog")
    queried_at: str = Field(..., description="When status was queried")

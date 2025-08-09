"""Task management routes for MCP server."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from tmux_orchestrator.utils.tmux import TMUXManager

router = APIRouter()
tmux = TMUXManager()


class Task(BaseModel):
    """API model for task definition."""

    id: str
    title: str
    description: str
    assigned_to: Optional[str] = None  # session:window
    status: str = "pending"  # pending, in_progress, completed, blocked
    priority: str = "medium"  # high, medium, low
    created_at: str
    updated_at: Optional[str] = None
    completion_criteria: list[str] = []
    dependencies: list[str] = []


class TaskQueue(BaseModel):
    """API model for task queue."""

    agent_target: str  # session:window
    pending_tasks: list[Task]
    current_task: Optional[Task] = None
    completed_tasks: list[Task] = []


# In-memory task storage (would be database in production)
task_registry: dict[str, Task] = {}
agent_queues: dict[str, TaskQueue] = {}


@router.post("/create", response_model=Task)
async def create_task(
    title: str,
    description: str,
    priority: str = "medium",
    completion_criteria: Optional[list[str]] = None,
    dependencies: Optional[list[str]] = None,
) -> Task:
    """Create a new task in the registry.

    MCP tool for task creation.
    """
    try:
        task_id = f"task_{len(task_registry) + 1}_{datetime.now().strftime('%H%M%S')}"

        task = Task(
            id=task_id,
            title=title,
            description=description,
            priority=priority,
            created_at=datetime.now().isoformat(),
            completion_criteria=completion_criteria or [],
            dependencies=dependencies or [],
        )

        task_registry[task_id] = task

        return task

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list", response_model=list[Task])
async def list_all_tasks(status: Optional[str] = None) -> list[Task]:
    """List all tasks in the registry.

    MCP tool for task overview.
    """
    try:
        tasks = list(task_registry.values())

        if status:
            tasks = [task for task in tasks if task.status == status]

        # Sort by priority and creation time
        priority_order = {"high": 0, "medium": 1, "low": 2}
        tasks.sort(key=lambda t: (priority_order.get(t.priority, 99), t.created_at))

        return tasks

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{task_id}", response_model=Task)
async def get_task_status(task_id: str) -> Task:
    """Get status of a specific task.

    MCP tool for task tracking.
    """
    try:
        if task_id not in task_registry:
            raise HTTPException(status_code=404, detail="Task not found")

        return task_registry[task_id]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

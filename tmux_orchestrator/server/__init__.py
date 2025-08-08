"""TMUX Orchestrator MCP Server."""

from typing import Dict, List, Union

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from tmux_orchestrator.core.config import Config
from tmux_orchestrator.server.middleware import TimingMiddleware
from tmux_orchestrator.server.routes import (
    agent_management,
    communication,
    coordination,
    monitoring,
    tasks,
)

app = FastAPI(
    title="TMUX Orchestrator MCP Server",
    description="Model Context Protocol server for AI agent coordination and orchestration",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configure CORS for MCP protocol compatibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for MCP tools
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Add custom timing middleware
app.add_middleware(TimingMiddleware)

# Include MCP tool routers with proper prefixes and tags
app.include_router(
    agent_management.router,
    prefix="/agents",
    tags=["Agent Management"],
    responses={
        404: {"description": "Agent or session not found"},
        500: {"description": "Internal server error"}
    }
)
app.include_router(
    communication.router,
    prefix="/messages",
    tags=["Communication"],
    responses={
        404: {"description": "Target not found"},
        500: {"description": "Message delivery failed"}
    }
)
app.include_router(
    monitoring.router,
    prefix="/monitor",
    tags=["Monitoring"],
    responses={
        500: {"description": "Monitoring system error"}
    }
)
app.include_router(
    coordination.router,
    prefix="/coordination",
    tags=["Coordination"],
    responses={
        500: {"description": "Team coordination error"}
    }
)
app.include_router(
    tasks.router,
    prefix="/tasks",
    tags=["Task Management"],
    responses={
        404: {"description": "Task not found"},
        500: {"description": "Task management error"}
    }
)


@app.get("/")
async def root() -> dict[str, Union[str, List[str]]]:
    """Root endpoint with MCP server information."""
    return {
        "name": "TMUX Orchestrator MCP Server",
        "version": "2.0.0",
        "description": "Model Context Protocol server for AI agent coordination",
        "status": "running",
        "protocol": "MCP",
        "available_tools": [
            "spawn_agent", "restart_agent", "kill_agent", "get_agent_status", "list_agents",
            "send_message", "broadcast_message", "interrupt_agent", "get_conversation_history",
            "get_system_status", "get_session_detail", "health_check", "get_idle_agents",
            "deploy_team", "coordinate_standup", "recover_team", "get_team_status", 
            "list_teams", "setup_hub_spoke_coordination", "create_task", "get_task_status"
        ],
        "documentation": "/docs",
        "openapi_spec": "/openapi.json"
    }


@app.get("/health")
async def health() -> dict[str, str]:
    """Basic health check endpoint."""
    return {"status": "healthy", "service": "tmux-orchestrator-mcp"}


def main():
    """Run the MCP server."""
    config = Config.load()
    host = config.get('server.host', '127.0.0.1')
    port = config.get('server.port', 8000)

    uvicorn.run(
        "tmux_orchestrator.server:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    main()

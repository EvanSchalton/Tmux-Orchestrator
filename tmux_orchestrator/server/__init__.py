"""TMUX Orchestrator MCP Server."""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from tmux_orchestrator.core.config import Config
from tmux_orchestrator.server.middleware import TimingMiddleware
from tmux_orchestrator.server.routes import (
    agents,
    coordination,
    messages,
    monitor,
    tasks,
)

app = FastAPI(
    title="TMUX Orchestrator MCP Server",
    description="Model Context Protocol server for AI agent coordination",
    version="2.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
app.add_middleware(TimingMiddleware)

# Include routers
app.include_router(agents.router, prefix="/agents", tags=["agents"])
app.include_router(messages.router, prefix="/messages", tags=["messages"])
app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
app.include_router(monitor.router, prefix="/monitor", tags=["monitor"])
app.include_router(coordination.router, prefix="/coordination", tags=["coordination"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "TMUX Orchestrator MCP Server",
        "version": "2.0.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


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

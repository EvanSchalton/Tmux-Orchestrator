# TMUX Orchestrator Development Guide

## Setting Up Development Environment

### Using Dev Container (Recommended)

1. Clone the repository
2. Open in VS Code with Dev Containers extension
3. Select "Reopen in Container"
4. Poetry and all dependencies will be automatically installed

### Manual Setup

```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Activate virtual environment
poetry shell
```

## Project Structure

```
tmux-orchestrator/
├── tmux_orchestrator/          # Main package
│   ├── cli/                    # CLI commands
│   │   ├── __init__.py        # Main CLI entry point
│   │   ├── agent.py           # Agent management commands
│   │   ├── monitor.py         # Monitoring commands
│   │   ├── orchestrator.py    # Orchestrator commands
│   │   └── pm.py              # PM-specific commands
│   ├── core/                   # Core functionality
│   │   ├── agent_manager.py   # Agent lifecycle management
│   │   ├── config.py          # Configuration handling
│   │   ├── deployer.py        # Team deployment logic
│   │   ├── monitor.py         # Idle monitoring
│   │   └── pm_manager.py      # PM operations
│   ├── server/                 # MCP server
│   │   ├── __init__.py        # FastAPI app
│   │   ├── routes/            # API endpoints
│   │   └── models/            # Pydantic models
│   ├── sdk/                    # Agent SDK
│   │   └── __init__.py        # Agent class
│   └── utils/                  # Utilities
│       └── tmux.py            # TMUX wrapper
├── commands/                   # Legacy bash scripts
├── bin/                        # Generic scripts
├── tests/                      # Test suite
├── docs/                       # Documentation
└── pyproject.toml             # Project configuration
```

## Development Workflow

### 1. Running the CLI in Development

```bash
# Install in editable mode
poetry install

# Run CLI directly
poetry run tmux-orc --help

# Or activate shell and run
poetry shell
tmux-orc --help
```

### 2. Running the MCP Server

```bash
# Start the server
poetry run tmux-orc-server

# Or with custom settings
poetry run uvicorn tmux_orchestrator.server:app --reload --host 0.0.0.0 --port 8000
```

### 3. Testing

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=tmux_orchestrator

# Run specific test
poetry run pytest tests/test_agent_manager.py
```

### 4. Code Quality

```bash
# Format code
poetry run black tmux_orchestrator

# Lint code
poetry run ruff check tmux_orchestrator

# Type checking
poetry run mypy tmux_orchestrator
```

## Implementation Status

### ✅ Completed
- [x] CLI framework with Click
- [x] Basic command structure
- [x] Configuration system
- [x] TMUX wrapper utilities
- [x] Agent manager core
- [x] PM manager core
- [x] SDK for agents
- [x] MCP server framework

### 🚧 In Progress
- [ ] Team deployer implementation
- [ ] Monitor daemon integration
- [ ] Recovery system
- [ ] Scheduler implementation

### 📋 TODO
- [ ] MCP server routes implementation
- [ ] Database for agent state
- [ ] WebSocket support for real-time updates
- [ ] Web dashboard
- [ ] Agent metrics and analytics
- [ ] Plugin system for custom agents
- [ ] Integration tests
- [ ] Documentation site

## Key Implementation Files

### Adding a New CLI Command

1. Create command module in `cli/`
2. Define Click group/commands
3. Import and add to main CLI in `cli/__init__.py`

Example:
```python
# cli/newfeature.py
import click

@click.group()
def newfeature():
    """New feature commands."""
    pass

@newfeature.command()
def action():
    """Perform action."""
    click.echo("Action performed!")

# In cli/__init__.py
from tmux_orchestrator.cli import newfeature
cli.add_command(newfeature.newfeature)
```

### Adding MCP Endpoints

1. Create route module in `server/routes/`
2. Define FastAPI router
3. Include in main app in `server/__init__.py`

Example:
```python
# server/routes/custom.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/custom/endpoint")
async def custom_endpoint():
    return {"status": "ok"}

# In server/__init__.py
from tmux_orchestrator.server.routes import custom
app.include_router(custom.router, prefix="/custom", tags=["custom"])
```

## Testing Guidelines

1. **Unit Tests**: Test individual components in isolation
2. **Integration Tests**: Test CLI commands with mock TMUX
3. **E2E Tests**: Test full workflows with real TMUX sessions

## Contributing

1. Create feature branch from `main`
2. Implement changes with tests
3. Ensure all checks pass (format, lint, type check, tests)
4. Submit PR with clear description

## Debugging Tips

1. **CLI Debugging**:
   ```bash
   # Enable debug output
   export TMUX_ORCHESTRATOR_DEBUG=1
   tmux-orc command
   ```

2. **Server Debugging**:
   ```bash
   # Run with debug logging
   uvicorn tmux_orchestrator.server:app --log-level debug
   ```

3. **TMUX Issues**:
   ```bash
   # Check TMUX server
   tmux list-sessions
   
   # Debug TMUX commands
   export TMUX_DEBUG=1
   ```

## Release Process

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Create git tag: `git tag v2.0.0`
4. Build: `poetry build`
5. Publish: `poetry publish`
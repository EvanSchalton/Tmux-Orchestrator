# TMUX Orchestrator Dev Container

This development container provides a complete Python development environment for TMUX Orchestrator with all necessary tools pre-installed.

## What's Included

### Core Tools
- **Python 3.11** with pip and venv
- **Poetry** for dependency management
- **tmux** with sensible configuration
- **Git** and **GitHub CLI**
- **ripgrep**, **fd**, **jq** for enhanced searching

### Python Development
- **Black** - Code formatter
- **Ruff** - Fast Python linter
- **mypy** - Type checker
- **pytest** - Testing framework
- **pytest-cov** - Coverage reporting

### VS Code Extensions
- Python language support
- Pylance for IntelliSense
- Black formatter
- Ruff linter
- TOML support
- YAML support
- GitLens
- GitHub Copilot

## Quick Start

1. **Open in Dev Container**
   - Install "Dev Containers" VS Code extension
   - Open command palette: `Ctrl/Cmd + Shift + P`
   - Select "Dev Containers: Reopen in Container"

2. **After Container Starts**
   ```bash
   # CLI is automatically available
   tmux-orc --help
   
   # Start development server
   poetry run tmux-orc-server
   
   # Run tests
   poetry run pytest
   ```

## Container Features

### Automatic Setup
- Poetry installs all dependencies
- tmux configuration with plugins
- Git safe directory configuration
- CLI installed in development mode

### Port Forwarding
- **8000** - MCP server default port
- **8080** - Alternative/development port

### Shell Aliases
- `tol` → `tmux-orc list`
- `tos` → `tmux-orc status`
- `tom` → `tmux-orc monitor`

### SSH Keys
Your local SSH keys are mounted read-only for Git operations.

## Development Workflow

### 1. Make Changes
Edit files in `tmux_orchestrator/` - changes are immediately available.

### 2. Test Your Changes
```bash
# Run specific command
poetry run tmux-orc <command>

# Run tests
poetry run pytest tests/

# Check types
poetry run mypy tmux_orchestrator
```

### 3. Format & Lint
```bash
# Format code
poetry run black tmux_orchestrator

# Run linter
poetry run ruff check tmux_orchestrator
```

### 4. Start Server
```bash
# Start with auto-reload
poetry run uvicorn tmux_orchestrator.server:app --reload
```

## Troubleshooting

### Poetry Issues
```bash
# Reinstall dependencies
poetry install --no-cache

# Update dependencies
poetry update
```

### tmux Issues
```bash
# Reload tmux config
tmux source-file ~/.tmux.conf

# Kill all sessions
tmux kill-server
```

### Permission Issues
The container runs as `vscode` user (UID 1000). All files should be owned by this user.

## Customization

### VS Code Settings
Edit `.devcontainer/devcontainer.json` to add more extensions or settings.

### Shell Configuration
Additional aliases or configurations can be added to the Dockerfile.

### tmux Configuration
The tmux config is copied from `.devcontainer/tmux.conf`. Modify and rebuild to change defaults.
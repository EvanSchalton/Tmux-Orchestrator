#!/bin/bash
set -e

echo "🚀 Setting up TMUX Orchestrator development environment..."

# Configure git
git config --global --add safe.directory /workspace

# Install Python development tools globally
pip install --upgrade pip
pip install black ruff mypy pytest pytest-cov

# Install project dependencies if pyproject.toml exists
if [ -f "pyproject.toml" ]; then
    echo "📦 Installing project dependencies with Poetry..."
    poetry install
fi

# Create necessary directories
mkdir -p logs
mkdir -p .tmux-orchestrator

# Set up tmux plugin manager (TPM)
if [ ! -d "$HOME/.tmux/plugins/tpm" ]; then
    echo "📦 Installing Tmux Plugin Manager..."
    git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm
fi

# Initialize tmux config if not exists
if [ ! -f "$HOME/.tmux.conf" ]; then
    echo "📝 Setting up tmux configuration..."
    cat > "$HOME/.tmux.conf" << 'EOF'
# Set prefix to Ctrl-a
set -g prefix C-a
unbind C-b
bind C-a send-prefix

# Enable mouse support
set -g mouse on

# Start windows and panes at 1, not 0
set -g base-index 1
setw -g pane-base-index 1

# Reload config
bind r source-file ~/.tmux.conf \; display-message "Config reloaded!"

# Better split commands
bind | split-window -h
bind - split-window -v

# Plugin manager
set -g @plugin 'tmux-plugins/tpm'
set -g @plugin 'tmux-plugins/tmux-sensible'
set -g @plugin 'tmux-plugins/tmux-resurrect'

# Initialize TPM
run '~/.tmux/plugins/tpm/tpm'
EOF
fi

# Make CLI available in development
if [ -f "pyproject.toml" ]; then
    echo "🔗 Making tmux-orc CLI available..."
    poetry run pip install -e .
fi

echo "✅ Development environment ready!"
echo ""
echo "📚 Quick Start:"
echo "  - Run CLI: poetry run tmux-orc --help"
echo "  - Start server: poetry run tmux-orc-server"
echo "  - Run tests: poetry run pytest"
echo "  - Format code: poetry run black tmux_orchestrator"
echo "  - Lint code: poetry run ruff check tmux_orchestrator"
echo ""
echo "🚀 Happy coding!"

#!/bin/bash
# TMUX Orchestrator Installation Template for Devcontainers
# Simple installation script for projects that need custom setup

set -e

echo "=== Installing Tmux Orchestrator ==="

# Install system dependencies
if ! command -v tmux &> /dev/null; then
    echo "📦 Installing tmux..."
    apt-get update
    apt-get install -y tmux
else
    echo "✅ tmux already installed: $(tmux -V)"
fi

# Install Tmux Orchestrator
echo "📦 Installing Tmux Orchestrator from GitHub..."
pip install git+https://github.com/[your-username]/Tmux-Orchestrator.git

# Run setup
echo "🔧 Running initial setup..."
tmux-orc setup

# Optional: Setup VS Code integration
if [ -d ".vscode" ] || [ "$1" == "--vscode" ]; then
    echo "🔧 Setting up VS Code integration..."
    tmux-orc setup-vscode .
fi

# Optional: Setup Claude Code integration
if [ -d "$HOME/.continue" ] || [ "$1" == "--claude" ]; then
    echo "🔧 Setting up Claude Code integration..."
    tmux-orc setup-claude-code
fi

echo "✅ Tmux Orchestrator installation complete!"
echo ""
echo "Next steps:"
echo "1. Start the orchestrator: tmux-orc orchestrator start"
echo "2. Deploy a team: tmux-orc team deploy frontend 3"
echo "3. Or execute a PRD: tmux-orc execute ./prd.md"
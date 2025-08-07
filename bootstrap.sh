#!/bin/bash
# Tmux Orchestrator Bootstrap Script for Devcontainers
# One-line installation: curl -sSL https://raw.githubusercontent.com/[your-repo]/tmux-orchestrator/main/bootstrap.sh | bash

set -e

# Configuration
REPO_URL="${TMUX_ORCHESTRATOR_REPO:-https://github.com/EvanSchalton/Tmux-Orchestrator.git}"
INSTALL_DIR="${TMUX_ORCHESTRATOR_HOME:-$HOME/.tmux-orchestrator}"
TEMP_DIR="/tmp/tmux-orchestrator-install-$$"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Functions
print_banner() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════╗"
    echo "║     Tmux Orchestrator Bootstrap      ║"
    echo "║   Autonomous AI Agent Management     ║"
    echo "╚══════════════════════════════════════╝"
    echo -e "${NC}"
}

print_status() { echo -e "${GREEN}[✓]${NC} $1"; }
print_error() { echo -e "${RED}[✗]${NC} $1"; }
print_info() { echo -e "${BLUE}[i]${NC} $1"; }

# Check if running in devcontainer
is_devcontainer() {
    [ -f /.dockerenv ] || [ -n "$CODESPACES" ] || [ -n "$REMOTE_CONTAINERS" ]
}

# Main installation
main() {
    print_banner
    
    # Check if already installed
    if [ -d "$INSTALL_DIR" ] && [ -f "$INSTALL_DIR/bin/tmux-orchestrator" ]; then
        print_info "Tmux Orchestrator already installed at $INSTALL_DIR"
        read -p "Reinstall? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 0
        fi
        rm -rf "$INSTALL_DIR"
    fi
    
    # Check if running locally or from remote
    if [ -f "./install.sh" ] && [ -f "./send-claude-message.sh" ]; then
        # Local installation
        print_info "Installing from local directory..."
        ./install.sh "$INSTALL_DIR"
    else
        # Remote installation
        print_info "Downloading Tmux Orchestrator..."
        git clone --quiet "$REPO_URL" "$TEMP_DIR"
        
        print_info "Running installation..."
        cd "$TEMP_DIR"
        ./install.sh "$INSTALL_DIR"
        cd - > /dev/null
    fi
    
    # Devcontainer-specific setup
    if is_devcontainer; then
        print_info "Detected devcontainer environment"
        setup_devcontainer
    fi
    
    # Cleanup (only if we used temp dir)
    [ -d "$TEMP_DIR" ] && rm -rf "$TEMP_DIR"
    
    print_status "Bootstrap complete!"
    
    # Show next steps
    echo -e "\n${GREEN}Next steps:${NC}"
    echo "1. Add to your devcontainer.json:"
    echo -e "${YELLOW}   \"postCreateCommand\": \"curl -sSL [bootstrap-url] | bash\"${NC}"
    echo "2. Start orchestrator:"
    echo -e "${YELLOW}   tmux-orchestrator start${NC}"
    echo "3. Configure Claude commands in .claude/commands/"
}

setup_devcontainer() {
    # Create Claude commands directory
    # Try to detect workspace folder
    if [ -n "$CODESPACES" ]; then
        WORKSPACE_BASE="/workspaces"
    elif [ -n "$REMOTE_CONTAINERS_IPC" ]; then
        WORKSPACE_BASE="/workspaces"
    else
        WORKSPACE_BASE="$(pwd)"
    fi
    
    CLAUDE_COMMANDS_DIR="${WORKSPACE_FOLDER:-$WORKSPACE_BASE}/.claude/commands"
    mkdir -p "$CLAUDE_COMMANDS_DIR"
    
    # Create orchestrator command
    cat > "$CLAUDE_COMMANDS_DIR/orchestrator.md" << 'EOF'
---
description: Send a message to the Tmux Orchestrator
output: Run the command
shortcut: orch
model: claude-3-5-sonnet-latest
temperature: 0.2
maxTokens: 1000
---

# Send message to Tmux Orchestrator

Please send this message to the orchestrator:

{{message}}

Use the command: `tmux-orchestrator send orchestrator:0 "{{message}}"`

Remember to escape any quotes in the message.
EOF
    
    # Create schedule command
    cat > "$CLAUDE_COMMANDS_DIR/schedule.md" << 'EOF'
---
description: Schedule a check-in with the orchestrator
output: Run the command
shortcut: sched
---

# Schedule Orchestrator Check-in

Schedule a check-in after {{minutes}} minutes with note: {{note}}

Use: `tmux-orchestrator schedule {{minutes}} orchestrator:0 "{{note}}"`
EOF
    
    # Add to shell configuration
    SHELL_RC="${HOME}/.bashrc"
    if [ -n "$ZSH_VERSION" ]; then
        SHELL_RC="${HOME}/.zshrc"
    fi
    
    if ! grep -q "TMUX_ORCHESTRATOR_HOME" "$SHELL_RC" 2>/dev/null; then
        echo "" >> "$SHELL_RC"
        echo "# Tmux Orchestrator" >> "$SHELL_RC"
        echo "export TMUX_ORCHESTRATOR_HOME=\"$INSTALL_DIR\"" >> "$SHELL_RC"
        echo "export PATH=\"\$TMUX_ORCHESTRATOR_HOME/bin:\$PATH\"" >> "$SHELL_RC"
    fi
    
    print_status "Devcontainer integration complete"
}

# Run main function
main "$@"
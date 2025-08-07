#!/bin/bash
# Tmux Orchestrator Installation Script
# This script installs Tmux Orchestrator in a project-agnostic way

set -e

# Default configuration
DEFAULT_INSTALL_DIR="${HOME}/.tmux-orchestrator"
DEFAULT_PROJECT_DIR="${HOME}/projects"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Parse command line arguments
INSTALL_DIR="${1:-$DEFAULT_INSTALL_DIR}"
PROJECT_DIR="${2:-$DEFAULT_PROJECT_DIR}"

echo "======================================"
echo "   Tmux Orchestrator Installation"
echo "======================================"
echo ""
echo "Installation directory: $INSTALL_DIR"
echo "Default projects directory: $PROJECT_DIR"
echo ""

# Check for required dependencies
echo "Checking dependencies..."

# Check for tmux
if ! command -v tmux &> /dev/null; then
    print_error "tmux is not installed. Please install tmux first."
    echo "  Ubuntu/Debian: sudo apt-get install tmux"
    echo "  macOS: brew install tmux"
    exit 1
else
    print_status "tmux found: $(tmux -V)"
fi

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed. Please install Python 3 first."
    exit 1
else
    print_status "Python 3 found: $(python3 --version)"
fi

# Check for bc (calculator)
if ! command -v bc &> /dev/null; then
    print_warning "bc is not installed. Installing bc for calculations..."
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt-get update -qq && sudo apt-get install -y bc
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        brew install bc
    else
        print_error "Please install bc manually for your system"
        exit 1
    fi
fi

# Create installation directory structure
echo ""
echo "Creating directory structure..."
mkdir -p "$INSTALL_DIR"/{bin,scripts,registry/{logs,notes},config}
print_status "Directory structure created"

# Copy scripts
echo ""
echo "Installing scripts..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Copy main scripts
cp "$SCRIPT_DIR/send-claude-message.sh" "$INSTALL_DIR/scripts/"
cp "$SCRIPT_DIR/schedule_with_note.sh" "$INSTALL_DIR/scripts/"
cp "$SCRIPT_DIR/tmux_utils.py" "$INSTALL_DIR/scripts/"

# Make scripts executable
chmod +x "$INSTALL_DIR/scripts"/*.sh
print_status "Scripts installed"

# Create configuration file
echo ""
echo "Creating configuration..."
cat > "$INSTALL_DIR/config/tmux-orchestrator.conf" << EOF
# Tmux Orchestrator Configuration
# Edit these values to customize your installation

# Installation directory
export TMUX_ORCHESTRATOR_HOME="$INSTALL_DIR"

# Default projects directory
export TMUX_ORCHESTRATOR_PROJECTS_DIR="$PROJECT_DIR"

# Default session name
export TMUX_ORCHESTRATOR_DEFAULT_SESSION="orchestrator:0"

# Logs directory
export TMUX_ORCHESTRATOR_LOGS_DIR="\$TMUX_ORCHESTRATOR_HOME/registry/logs"

# Notes file location
export TMUX_ORCHESTRATOR_NOTES_FILE="\$TMUX_ORCHESTRATOR_HOME/registry/notes/next_check_note.txt"

# Claude command (update if using a different command)
export TMUX_ORCHESTRATOR_CLAUDE_CMD="claude"
EOF
print_status "Configuration created"

# Create main orchestrator command
echo ""
echo "Creating orchestrator command..."
cat > "$INSTALL_DIR/bin/tmux-orchestrator" << 'EOF'
#!/bin/bash
# Tmux Orchestrator Main Command

# Source configuration
CONFIG_FILE="${TMUX_ORCHESTRATOR_HOME:-$HOME/.tmux-orchestrator}/config/tmux-orchestrator.conf"
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
else
    echo "Error: Configuration file not found at $CONFIG_FILE"
    exit 1
fi

# Command handling
case "$1" in
    start)
        SESSION_NAME="${2:-orchestrator}"
        tmux new-session -d -s "$SESSION_NAME" -n "Orchestrator"
        tmux send-keys -t "$SESSION_NAME:0" "$TMUX_ORCHESTRATOR_CLAUDE_CMD" Enter
        sleep 2
        tmux send-keys -t "$SESSION_NAME:0" "You are the Tmux Orchestrator. Your job is to coordinate multiple Claude agents working on various projects." Enter
        echo "✅ Orchestrator started in session: $SESSION_NAME"
        echo "   Attach with: tmux attach -t $SESSION_NAME"
        ;;
    send)
        if [ $# -lt 3 ]; then
            echo "Usage: tmux-orchestrator send <target> \"message\""
            exit 1
        fi
        "$TMUX_ORCHESTRATOR_HOME/scripts/send-claude-message.sh" "$2" "$3"
        ;;
    schedule)
        if [ $# -lt 4 ]; then
            echo "Usage: tmux-orchestrator schedule <minutes> <target> \"note\""
            exit 1
        fi
        "$TMUX_ORCHESTRATOR_HOME/scripts/schedule_with_note.sh" "$2" "$3" "$4"
        ;;
    status)
        echo "🤖 TMUX ORCHESTRATOR STATUS"
        echo "=========================="
        echo "Active sessions:"
        tmux list-sessions 2>/dev/null || echo "No active sessions"
        ;;
    help|*)
        echo "Tmux Orchestrator Commands:"
        echo "  start [session-name]     - Start orchestrator session"
        echo "  send <target> \"message\" - Send message to Claude agent"
        echo "  schedule <min> <target> \"note\" - Schedule check-in"
        echo "  status                   - Show active sessions"
        echo "  help                     - Show this help"
        ;;
esac
EOF

chmod +x "$INSTALL_DIR/bin/tmux-orchestrator"
print_status "Orchestrator command created"

# Create symlink in PATH
echo ""
echo "Setting up PATH..."
if [ -d "/usr/local/bin" ] && [ -w "/usr/local/bin" ]; then
    ln -sf "$INSTALL_DIR/bin/tmux-orchestrator" /usr/local/bin/tmux-orchestrator
    print_status "Created symlink in /usr/local/bin"
else
    print_warning "Cannot create symlink in /usr/local/bin"
    echo "Add this to your shell configuration (.bashrc, .zshrc, etc.):"
    echo "  export PATH=\"$INSTALL_DIR/bin:\$PATH\""
fi

# Create helper commands
echo ""
echo "Creating helper commands..."

# tmux-message shortcut
ln -sf "$INSTALL_DIR/scripts/send-claude-message.sh" "$INSTALL_DIR/bin/tmux-message"

# tmux-schedule shortcut
ln -sf "$INSTALL_DIR/scripts/schedule_with_note.sh" "$INSTALL_DIR/bin/tmux-schedule"

print_status "Helper commands created"

# Final setup
echo ""
echo "======================================"
echo "   Installation Complete! 🎉"
echo "======================================"
echo ""
echo "Quick start:"
echo "  1. Start orchestrator: tmux-orchestrator start"
echo "  2. Send a message: tmux-orchestrator send orchestrator:0 \"Hello!\""
echo "  3. Schedule check-in: tmux-orchestrator schedule 30 orchestrator:0 \"Check progress\""
echo ""
echo "Configuration file: $INSTALL_DIR/config/tmux-orchestrator.conf"
echo "Documentation: $SCRIPT_DIR/README.md"
echo ""

# Create completion file for bash
if [ -d "/etc/bash_completion.d" ] && [ -w "/etc/bash_completion.d" ]; then
    cat > /etc/bash_completion.d/tmux-orchestrator << 'EOF'
_tmux_orchestrator() {
    local cur="${COMP_WORDS[COMP_CWORD]}"
    local commands="start send schedule status help"
    
    if [ $COMP_CWORD -eq 1 ]; then
        COMPREPLY=($(compgen -W "$commands" -- "$cur"))
    fi
}
complete -F _tmux_orchestrator tmux-orchestrator
EOF
    print_status "Bash completion installed"
fi

echo "Installation complete!"
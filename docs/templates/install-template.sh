#!/bin/bash
# TMUX Orchestrator Installation Template for Devcontainers
# Copy this to your project's scripts/install-tmux-orchestrator.sh and customize

set -e

# Configuration - CUSTOMIZE THESE FOR YOUR PROJECT
PROJECT_NAME="your-project"  # Change this
PROJECT_PATH="/workspaces/$PROJECT_NAME"
TASK_FILE_DEFAULT="$PROJECT_PATH/tasks.md"  # Default task file location

echo "=== Installing Tmux Orchestrator for $PROJECT_NAME ==="

# Install dependencies
if ! command -v tmux &> /dev/null; then
    echo "📦 Installing tmux and bc..."
    sudo apt-get update
    sudo apt-get install -y tmux bc
else
    echo "✅ tmux already installed: $(tmux -V)"
fi

# Create orchestrator directory structure
ORCH_DIR="$PROJECT_PATH/.tmux-orchestrator"
echo "📁 Creating orchestrator directories..."
mkdir -p "$ORCH_DIR/registry/logs"
mkdir -p "$ORCH_DIR/registry/notes"  
mkdir -p "$ORCH_DIR/scripts"
mkdir -p "$ORCH_DIR/commands"

# Copy reference scripts if available
REFS_DIR="$PROJECT_PATH/references/Tmux-Orchestrator"
echo "📋 Copying orchestrator scripts..."
if [ -f "$REFS_DIR/schedule_with_note.sh" ]; then
    cp "$REFS_DIR/schedule_with_note.sh" "$ORCH_DIR/scripts/"
fi

if [ -f "$REFS_DIR/send-claude-message.sh" ]; then
    cp "$REFS_DIR/send-claude-message.sh" "$ORCH_DIR/scripts/"
fi

if [ -f "$REFS_DIR/tmux_utils.py" ]; then
    cp "$REFS_DIR/tmux_utils.py" "$ORCH_DIR/scripts/"
fi

# Create fallback scripts if references don't exist
if [ ! -f "$ORCH_DIR/scripts/send-claude-message.sh" ]; then
    cat > "$ORCH_DIR/scripts/send-claude-message.sh" << 'EOF'
#!/bin/bash
# Send message to Claude in tmux window/pane
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <session:window[.pane]> \"message\""
    exit 1
fi
tmux send-keys -t "$1" "$2"
sleep 0.5
tmux send-keys -t "$1" Enter
EOF
fi

if [ ! -f "$ORCH_DIR/scripts/schedule_with_note.sh" ]; then
    cat > "$ORCH_DIR/scripts/schedule_with_note.sh" << 'EOF'
#!/bin/bash
# Schedule a check-in with note
if [ "$#" -lt 2 ]; then
    echo "Usage: $0 <minutes> \"note\" [target_window]"
    exit 1
fi
MINUTES=$1
NOTE=$2
TARGET=${3:-"orchestrator:0"}
echo "tmux send-keys -t '$TARGET' 'Scheduled check-in: $NOTE' Enter" | at now + $MINUTES minutes
echo "✅ Scheduled check-in for $TARGET in $MINUTES minutes: $NOTE"
EOF
fi

# Make scripts executable
chmod +x "$ORCH_DIR/scripts/"*.sh

# Create global command symlinks
echo "🔗 Creating command symlinks..."
sudo ln -sf "$ORCH_DIR/scripts/schedule_with_note.sh" /usr/local/bin/tmux-schedule
sudo ln -sf "$ORCH_DIR/scripts/send-claude-message.sh" /usr/local/bin/tmux-message

# Initialize registry
echo '[]' > "$ORCH_DIR/registry/sessions.json"
cat > "$ORCH_DIR/registry/notes/README.md" << EOF
# Orchestrator Notes for $PROJECT_NAME
Created: $(date)
EOF

# Create tmux configuration
echo "⚙️ Setting up tmux configuration..."
cat > ~/.tmux.conf << 'EOF'
# Enable mouse support
set -g mouse on

# Better colors
set -g default-terminal "screen-256color"

# Status bar
set -g status-style bg=colour235,fg=colour136
set -g status-left '#[fg=colour235,bg=colour252,bold] #S '
set -g status-right '#[fg=colour235,bg=colour252,bold] %Y-%m-%d %H:%M '
set -g status-left-length 20
set -g status-right-length 50

# Window settings
set-option -g allow-rename off
set-option -g automatic-rename off
set -g history-limit 10000
set -g base-index 1
setw -g pane-base-index 1
set -g renumber-windows on

# Better key bindings
bind | split-window -h
bind - split-window -v
bind r source-file ~/.tmux.conf \; display "Config reloaded!"
EOF

# Create command scripts
echo "🚀 Creating orchestrator commands..."

# Start orchestrator
cat > "$ORCH_DIR/commands/start-orchestrator.sh" << EOF
#!/bin/bash
SESSION_NAME=\${1:-orchestrator}
if tmux has-session -t "\$SESSION_NAME" 2>/dev/null; then
    echo "❌ Session '\$SESSION_NAME' already exists!"
    exit 1
fi
echo "🚀 Creating orchestrator session..."
tmux new-session -d -s "\$SESSION_NAME" -c "$PROJECT_PATH"
tmux rename-window -t "\$SESSION_NAME:0" "Orchestrator"
echo "🤖 Starting Claude..."
tmux send-keys -t "\$SESSION_NAME:0" "claude --dangerously-skip-permissions" Enter
sleep 5
/usr/local/bin/tmux-message "\$SESSION_NAME:0" "You are the Tmux Orchestrator for $PROJECT_NAME. Reference: $PROJECT_PATH/references/Tmux-Orchestrator/CLAUDE.md"
echo "✅ Orchestrator started! Access with: tmux attach -t \$SESSION_NAME"
EOF

# Deploy agent
cat > "$ORCH_DIR/commands/deploy-agent.sh" << EOF
#!/bin/bash
COMPONENT=\$1
ROLE=\${2:-developer}
if [ -z "\$COMPONENT" ]; then
    echo "Usage: \$0 <component> [role]"
    exit 1
fi
SESSION_NAME="$PROJECT_NAME-\$COMPONENT"
if ! tmux has-session -t "\$SESSION_NAME" 2>/dev/null; then
    tmux new-session -d -s "\$SESSION_NAME" -c "$PROJECT_PATH"
fi
WINDOW_NAME="Claude-\$ROLE"
tmux new-window -t "\$SESSION_NAME" -n "\$WINDOW_NAME" -c "$PROJECT_PATH"
tmux send-keys -t "\$SESSION_NAME:\$WINDOW_NAME" "claude --dangerously-skip-permissions" Enter
sleep 5
case "\$ROLE" in
    "developer")
        /usr/local/bin/tmux-message "\$SESSION_NAME:\$WINDOW_NAME" "You are the \$COMPONENT developer for $PROJECT_NAME. Maintain code quality and commit every 30 minutes."
        ;;
    "pm")
        /usr/local/bin/tmux-message "\$SESSION_NAME:\$WINDOW_NAME" "You are the Project Manager for \$COMPONENT. Maintain high standards and coordinate work."
        ;;
    "qa")
        /usr/local/bin/tmux-message "\$SESSION_NAME:\$WINDOW_NAME" "You are the QA engineer for \$COMPONENT. Test thoroughly and create test plans."
        ;;
esac
echo "✅ \$ROLE agent deployed for \$COMPONENT!"
EOF

# Agent status
cat > "$ORCH_DIR/commands/agent-status.sh" << 'EOF'
#!/bin/bash
echo "🤖 AGENT STATUS REPORT"
echo "====================="
echo "Time: $(date)"
echo ""
for session in $(tmux list-sessions -F "#{session_name}" 2>/dev/null); do
  if [[ "$session" =~ (orchestrator|PROJECT_NAME_PLACEHOLDER) ]]; then
    echo "📦 Session: $session"
    for window in $(tmux list-windows -t "$session" -F "#{window_index}:#{window_name}" 2>/dev/null); do
      window_index=$(echo "$window" | cut -d: -f1)
      window_name=$(echo "$window" | cut -d: -f2-)
      echo "  🪟 Window $window_index: $window_name"
      recent=$(tmux capture-pane -t "$session:$window_index" -p 2>/dev/null | tail -3 | head -2)
      if [ -n "$recent" ]; then
        echo "$recent" | sed 's/^/       /'
      fi
      echo ""
    done
  fi
done
EOF

# Replace placeholder in agent-status script
sed -i "s/PROJECT_NAME_PLACEHOLDER/$PROJECT_NAME/g" "$ORCH_DIR/commands/agent-status.sh"

# Make command scripts executable
chmod +x "$ORCH_DIR/commands/"*.sh

# Create gitignore
cat > "$ORCH_DIR/.gitignore" << 'EOF'
# Runtime files
registry/logs/*
registry/notes/*
!registry/notes/README.md
registry/sessions.json
next_check_note.txt

# Keep structure
!registry/logs/.gitkeep
!registry/notes/.gitkeep
EOF

# Create .gitkeep files
touch "$ORCH_DIR/registry/logs/.gitkeep"
touch "$ORCH_DIR/registry/notes/.gitkeep"

# Create project-specific directories
mkdir -p "$PROJECT_PATH/.pm-schedule"
mkdir -p "$PROJECT_PATH/.orchestrator-notes"

# Copy additional command scripts from references
if [ -f "$REFS_DIR/commands/list-agents.sh" ]; then
    cp "$REFS_DIR/commands/list-agents.sh" "$ORCH_DIR/commands/"
fi

if [ -f "$REFS_DIR/commands/open-all-agents.sh" ]; then
    cp "$REFS_DIR/commands/open-all-agents.sh" "$ORCH_DIR/commands/"
fi

if [ -f "$REFS_DIR/commands/force-pm-checkin.sh" ]; then
    cp "$REFS_DIR/commands/force-pm-checkin.sh" "$ORCH_DIR/commands/"
fi

# Create schedule-checkin command
cat > "$ORCH_DIR/commands/schedule-checkin.sh" << 'EOF'
#!/bin/bash
MINUTES=$1
TARGET=$2
NOTE=$3

if [ -z "$MINUTES" ] || [ -z "$TARGET" ] || [ -z "$NOTE" ]; then
  echo "Usage: $0 <minutes> <target> <note>"
  echo "Example: $0 30 orchestrator:0 'Review agent progress'"
  exit 1
fi

# Use the tmux-schedule command
/usr/local/bin/tmux-schedule "$MINUTES" "$NOTE" "$TARGET"
EOF

# Create generic deployment and restart scripts
echo "🚀 Creating generic deployment and restart scripts..."

# Create generic deploy script that works for any project
cat > "$PROJECT_PATH/scripts/deploy.sh" << EOF
#!/bin/bash
# Generic team deployment script
# Usage: ./deploy.sh <task-file>

TASK_FILE="\$1"
PROJECT_NAME=\$(basename "\$(pwd)")

if [ -z "\$TASK_FILE" ]; then
    echo "Usage: \$0 <task-file>"
    echo "Example: \$0 planning/tasks.md"
    exit 1
fi

# Use the existing tmux-deploy-team.sh script
exec ./scripts/tmux-deploy-team.sh "\$TASK_FILE" "\$PROJECT_NAME"
EOF

# Create generic restart script that works for any project
cat > "$PROJECT_PATH/scripts/restart.sh" << EOF
#!/bin/bash
# Generic team restart script
# Usage: ./restart.sh <task-file>

set -e

TASK_FILE="\$1"
PROJECT_NAME=\$(basename "\$(pwd)")

if [ -z "\$TASK_FILE" ]; then
    echo "Usage: \$0 <task-file>"
    echo "Example: \$0 planning/tasks.md"
    exit 1
fi

echo "🔄 Restarting \$PROJECT_NAME Team..."
echo "=================================="
echo "Task File: \$TASK_FILE"
echo ""

# Kill all existing sessions for this project and orchestrator
echo "🛑 Killing existing sessions..."
for session in \$(tmux ls -F "#{session_name}" 2>/dev/null | grep -E "(\$PROJECT_NAME|orchestrator)" || true); do
    if [ -n "\$session" ]; then
        echo "  Killing \$session"
        tmux kill-session -t "\$session" 2>/dev/null || true
    fi
done

# Wait a moment for cleanup
echo "⏱️  Waiting for cleanup..."
sleep 3

# Deploy fresh team with the task file
echo "🚀 Deploying fresh team..."
./scripts/deploy.sh "\$TASK_FILE"

echo ""
echo "✅ \$PROJECT_NAME team restarted successfully!"
echo ""
echo "💡 Next Steps:"
echo "  Monitor: ./scripts/monitor-\$PROJECT_NAME-team.sh"
echo "  Status:  ./.tmux-orchestrator/commands/agent-status.sh"
echo "  VS Code: Ctrl+Shift+P → Tasks: Run Task → Open All Agents"
EOF

chmod +x "$PROJECT_PATH/scripts/deploy.sh"
chmod +x "$PROJECT_PATH/scripts/restart.sh"

# Create restart script
cat > "$ORCH_DIR/restart.sh" << EOF
#!/bin/bash
# $PROJECT_NAME TMUX Orchestrator Restart Script
set -e

echo "🔄 Restarting $PROJECT_NAME Orchestrator..."

# Kill existing sessions
for session in \$(tmux list-sessions -F "#{session_name}" 2>/dev/null | grep "$PROJECT_NAME" || true); do
    tmux kill-session -t "\$session" 2>/dev/null || true
done

# Start orchestrator
bash "$ORCH_DIR/commands/start-orchestrator.sh"

echo "✅ $PROJECT_NAME orchestrator restarted!"
echo "Access with: tmux attach -t orchestrator"
EOF
chmod +x "$ORCH_DIR/restart.sh"

echo ""
echo "✅ Tmux Orchestrator installation complete for $PROJECT_NAME!"
echo ""
echo "🚀 Quick Start:"
echo "  1. Start orchestrator: $ORCH_DIR/commands/start-orchestrator.sh"
echo "  2. Deploy agents: $ORCH_DIR/commands/deploy-agent.sh frontend"
echo "  3. Check status: $ORCH_DIR/commands/agent-status.sh"
echo "  4. Restart system: $ORCH_DIR/restart.sh"
echo ""
echo "📚 Documentation: $PROJECT_PATH/references/Tmux-Orchestrator/"
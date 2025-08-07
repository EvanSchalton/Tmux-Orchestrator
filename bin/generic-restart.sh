#!/bin/bash
# Generic team restart script
# Usage: ./restart.sh <task-file>

set -e

TASK_FILE="$1"
PROJECT_NAME=$(basename "$(pwd)")

if [ -z "$TASK_FILE" ]; then
    echo "Usage: $0 <task-file>"
    echo "Example: $0 planning/tasks.md"
    exit 1
fi

echo "🔄 Restarting $PROJECT_NAME Team..."
echo "=================================="
echo "Task File: $TASK_FILE"
echo ""

# Kill all existing sessions for this project and orchestrator
echo "🛑 Killing existing sessions..."
for session in $(tmux ls -F "#{session_name}" 2>/dev/null | grep -E "($PROJECT_NAME|orchestrator)" || true); do
    if [ -n "$session" ]; then
        echo "  Killing $session"
        tmux kill-session -t "$session" 2>/dev/null || true
    fi
done

# Wait a moment for cleanup
echo "⏱️  Waiting for cleanup..."
sleep 3

# Deploy fresh team with the task file
echo "🚀 Deploying fresh team..."
./scripts/deploy.sh "$TASK_FILE"

echo ""
echo "✅ $PROJECT_NAME team restarted successfully!"
echo ""
echo "💡 Next Steps:"
echo "  Monitor: ./scripts/monitor-$PROJECT_NAME-team.sh"
echo "  Status:  ./.tmux-orchestrator/commands/agent-status.sh"
echo "  VS Code: Ctrl+Shift+P → Tasks: Run Task → Open All Agents"

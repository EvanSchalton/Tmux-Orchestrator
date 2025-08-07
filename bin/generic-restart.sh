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

# Check and start idle monitor if not running
echo ""
echo "🤖 Checking Idle Agent Monitor..."
PID_FILE="/tmp/tmux-orchestrator-idle-monitor.pid"
IDLE_MONITOR_SCRIPT="./.tmux-orchestrator/commands/start-idle-monitor.sh"

if [ -f "$IDLE_MONITOR_SCRIPT" ]; then
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE" 2>/dev/null || echo "")
        if [ -n "$PID" ] && ps -p "$PID" > /dev/null 2>&1; then
            echo "   ✅ Idle monitor already running (PID: $PID)"
        else
            echo "   ⚠️ Stale PID file found, starting fresh monitor..."
            rm -f "$PID_FILE"
            "$IDLE_MONITOR_SCRIPT" 10 > /dev/null 2>&1
            sleep 2
            echo "   ✅ Idle monitor started (10 second interval)"
        fi
    else
        echo "   🚀 Starting idle monitor..."
        "$IDLE_MONITOR_SCRIPT" 10 > /dev/null 2>&1
        sleep 2
        echo "   ✅ Idle monitor started (10 second interval)"
    fi
else
    echo "   ⚠️ Idle monitor script not found, skipping..."
fi

echo ""
echo "✅ $PROJECT_NAME team restarted successfully!"
echo ""
echo "💡 Next Steps:"
echo "  Monitor: ./scripts/monitor-$PROJECT_NAME-team.sh"
echo "  Status:  ./.tmux-orchestrator/commands/agent-status.sh"
echo "  VS Code: Ctrl+Shift+P → Tasks: Run Task → Open All Agents"
echo "  Idle Log: tail -f /tmp/tmux-orchestrator-idle-monitor.log"

#!/bin/bash
# Start the Idle Agent Monitor Daemon

PID_FILE="/tmp/tmux-orchestrator-idle-monitor.pid"
LOG_FILE="/tmp/tmux-orchestrator-idle-monitor.log"
DAEMON_SCRIPT="$(dirname "$0")/idle-monitor-daemon.sh"

echo "🚀 STARTING IDLE AGENT MONITOR"
echo "=============================="
echo "Time: $(date)"
echo ""

# Check if already running
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "❌ Monitor is already running (PID: $PID)"
        echo ""
        echo "💡 To stop it: .tmux-orchestrator/commands/stop-idle-monitor.sh"
        echo "📋 To view logs: tail -f $LOG_FILE"
        exit 1
    else
        echo "⚠️  Removing stale PID file"
        rm -f "$PID_FILE"
    fi
fi

# Check if daemon script exists
if [ ! -f "$DAEMON_SCRIPT" ]; then
    echo "❌ Cannot find idle-monitor-daemon.sh"
    exit 1
fi

# Get monitor interval from argument or use default
INTERVAL=${1:-10}

echo "📊 Configuration:"
echo "   Check interval: ${INTERVAL} seconds"
echo "   Log file: $LOG_FILE"
echo "   PID file: $PID_FILE"
echo ""

# Start the daemon in background
echo "🔄 Starting monitor daemon..."
nohup "$DAEMON_SCRIPT" "$INTERVAL" > /dev/null 2>&1 &

# Wait a moment for it to start
sleep 2

# Verify it started
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "✅ Idle monitor started successfully!"
        echo ""
        echo "📋 Monitor Details:"
        echo "   PID: $PID"
        echo "   Status: Running"
        echo "   Checking every: ${INTERVAL} seconds"
        echo ""
        echo "🎯 The monitor will:"
        echo "   • Check all agents for idle status every ${INTERVAL} seconds"
        echo "   • Notify PM when agents need work assignments"
        echo "   • Avoid spam with 5-minute cooldown per agent"
        echo "   • Log all activities to: $LOG_FILE"
        echo ""
        echo "💡 Useful commands:"
        echo "   View logs: tail -f $LOG_FILE"
        echo "   Stop monitor: .tmux-orchestrator/commands/stop-idle-monitor.sh"
        echo "   Check status: ps -p $PID"
        echo ""
        echo "✨ Your PM will now be automatically notified of idle agents!"
    else
        echo "❌ Failed to start monitor daemon"
        exit 1
    fi
else
    echo "❌ Monitor daemon failed to create PID file"
    exit 1
fi
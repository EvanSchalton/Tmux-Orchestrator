#!/bin/bash
# Stop the Idle Agent Monitor Daemon

PID_FILE="/tmp/tmux-orchestrator-idle-monitor.pid"
LOG_FILE="/tmp/tmux-orchestrator-idle-monitor.log"

echo "🛑 STOPPING IDLE AGENT MONITOR"
echo "=============================="
echo "Time: $(date)"
echo ""

# Check if PID file exists
if [ ! -f "$PID_FILE" ]; then
    echo "❌ No monitor appears to be running (PID file not found)"
    exit 1
fi

# Get PID
PID=$(cat "$PID_FILE")

# Check if process is running
if ! ps -p "$PID" > /dev/null 2>&1; then
    echo "⚠️  Monitor process not found (PID: $PID)"
    echo "🧹 Cleaning up stale PID file..."
    rm -f "$PID_FILE"
    exit 0
fi

# Stop the process
echo "📊 Found monitor process:"
echo "   PID: $PID"
echo "   Command: $(ps -p "$PID" -o comm= 2>/dev/null || echo "Unknown")"
echo ""

echo "🔄 Sending stop signal..."
kill "$PID" 2>/dev/null

# Wait for it to stop
WAIT_TIME=0
while ps -p "$PID" > /dev/null 2>&1 && [ $WAIT_TIME -lt 10 ]; do
    sleep 1
    WAIT_TIME=$((WAIT_TIME + 1))
done

# Check if stopped
if ps -p "$PID" > /dev/null 2>&1; then
    echo "⚠️  Process didn't stop gracefully, forcing..."
    kill -9 "$PID" 2>/dev/null
    sleep 1
fi

# Final check
if ps -p "$PID" > /dev/null 2>&1; then
    echo "❌ Failed to stop monitor process"
    exit 1
else
    echo "✅ Monitor stopped successfully!"
    rm -f "$PID_FILE"
    echo ""
    echo "📋 Final log entries:"
    tail -5 "$LOG_FILE" 2>/dev/null || echo "   (No log entries found)"
    echo ""
    echo "💡 Log file preserved at: $LOG_FILE"
fi
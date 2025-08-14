#!/bin/bash
# Start the enhanced monitoring daemon with debug logging

echo "Starting Enhanced TMux Orchestrator Monitor..."

# Enable debug mode
export TMUX_ORC_DEBUG=true

# Kill any existing monitors
echo "Stopping any existing monitors..."
pkill -f "tmux-orchestrator.*monitor" 2>/dev/null
sleep 1

# Start the enhanced monitor
echo "Starting enhanced monitor with 30s interval..."
python -m tmux_orchestrator.core.monitor_enhanced 30

# Show the log
echo ""
echo "Monitor started. Tailing log file..."
echo "Press Ctrl+C to stop viewing (monitor will continue running)"
echo ""
tail -f /tmp/tmux-orchestrator-enhanced-monitor.log

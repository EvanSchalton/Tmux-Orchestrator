#!/bin/bash
# PM Custom Check-in with team members
# Allows custom message for specific situations

CUSTOM_MESSAGE="$1"

if [ -z "$CUSTOM_MESSAGE" ]; then
    echo "Usage: $0 'Your custom check-in message'"
    echo ""
    echo "Example:"
    echo "  $0 'I see some agents are idle. Please report current status and request new tasks if needed.'"
    exit 1
fi

echo "👔 PM CUSTOM TEAM CHECK-IN"
echo "=========================="
echo "Time: $(date)"
echo ""
echo "Message: \"$CUSTOM_MESSAGE\""
echo ""

# Get project name
PROJECT_NAME=$(basename "$(pwd)")

# Check if tmux server is running
if ! tmux list-sessions >/dev/null 2>&1; then
    echo "❌ No tmux server running - no agents to check in with"
    exit 1
fi

echo "🔍 Finding active agents..."

# Find orchestrator and project agents
ORCHESTRATOR_SESSIONS=$(tmux list-sessions -F "#{session_name}" 2>/dev/null | grep -E "orchestrator" || true)
AGENT_SESSIONS=$(tmux list-sessions -F "#{session_name}" 2>/dev/null | grep -E "$PROJECT_NAME" | grep -v orchestrator || true)

# Count and validate
TOTAL_COUNT=0
if [ -n "$ORCHESTRATOR_SESSIONS" ]; then TOTAL_COUNT=$((TOTAL_COUNT + 1)); fi
if [ -n "$AGENT_SESSIONS" ]; then
    AGENT_COUNT=$(echo "$AGENT_SESSIONS" | wc -l)
    TOTAL_COUNT=$((TOTAL_COUNT + AGENT_COUNT))
fi

if [ $TOTAL_COUNT -eq 0 ]; then
    echo "❌ No active agents found"
    exit 1
fi

echo "   Found $TOTAL_COUNT active agents"
echo ""

# Custom message with PM header
FULL_MESSAGE="👔 PM CUSTOM CHECK-IN:

$CUSTOM_MESSAGE

Please respond promptly with your status update."

echo "📨 Sending custom check-in to all agents..."

# Send to orchestrator
if [ -n "$ORCHESTRATOR_SESSIONS" ]; then
    echo "  → Orchestrator..."
    tmux-message "orchestrator:1" "$FULL_MESSAGE"
    sleep 1
fi

# Send to all project agents (skip PM self)
if [ -n "$AGENT_SESSIONS" ]; then
    while IFS= read -r session; do
        if [ -n "$session" ] && ! echo "$session" | grep -q "$PROJECT_NAME-$PROJECT_NAME"; then
            echo "  → $session..."
            tmux-message "$session:2" "$FULL_MESSAGE"
            sleep 1
        fi
    done <<< "$AGENT_SESSIONS"
fi

echo ""
echo "✅ Custom check-in sent to all agents!"
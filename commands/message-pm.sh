#!/bin/bash
# Send message to Project Manager from external source
# Prevents interference with PM terminal and incoming agent messages

MESSAGE="$1"

if [ -z "$MESSAGE" ]; then
    echo "Usage: $0 'Your message to the PM'"
    echo ""
    echo "Examples:"
    echo "  $0 'Please provide status update on current priorities'"
    echo "  $0 'I notice agents seem idle - please assign new tasks'"
    echo "  $0 'Focus the team on fixing the authentication issues'"
    echo ""
    echo "💡 This allows you to communicate with the PM without interfering"
    echo "   with their terminal or incoming agent messages."
    exit 1
fi

echo "💬 MESSAGING PROJECT MANAGER"
echo "============================"
echo "Time: $(date)"
echo ""

# Check if tmux server is running
if ! tmux list-sessions >/dev/null 2>&1; then
    echo "❌ No tmux server running - PM not available"
    exit 1
fi

echo "🔍 Searching for PM sessions..."

# Find PM session dynamically - look for sessions with PM windows
PM_SESSIONS=""
ALL_SESSIONS=$(tmux list-sessions -F "#{session_name}" 2>/dev/null)

while IFS= read -r session; do
    if [ -n "$session" ]; then
        # Check if this session has a PM window (Claude-pm)
        PM_WINDOW=$(tmux list-windows -t "$session" -F "#{window_name}" 2>/dev/null | grep -E "Claude-pm|pm" || true)
        if [ -n "$PM_WINDOW" ]; then
            PM_SESSIONS="$PM_SESSIONS$session "
            echo "   Found PM in session: $session"
        fi
    fi
done <<< "$ALL_SESSIONS"

# Handle multiple or no PM sessions
if [ -z "$PM_SESSIONS" ]; then
    echo "❌ Could not find any PM sessions. Is the PM agent running?"
    echo ""
    echo "💡 Try deploying the team first:"
    echo "   ./scripts/deploy.sh tasks.md"
    exit 1
fi

# If multiple PMs, use the first one found
PM_SESSION=$(echo "$PM_SESSIONS" | awk '{print $1}')

if [ $(echo "$PM_SESSIONS" | wc -w) -gt 1 ]; then
    echo "⚠️  Multiple PM sessions found: $PM_SESSIONS"
    echo "📋 Using first one: $PM_SESSION"
fi

if [ -z "$PM_SESSION" ]; then
    echo "❌ Could not find PM session. Is the PM agent running?"
    echo ""
    echo "💡 Try deploying the team first:"
    echo "   ./scripts/deploy.sh tasks.md"
    exit 1
fi

echo "🎯 Found PM session: $PM_SESSION"

# Find the specific PM window in the session
PM_WINDOW_INFO=$(tmux list-windows -t "$PM_SESSION" -F "#{window_index}:#{window_name}" 2>/dev/null | grep -E "Claude-pm|pm" || true)
PM_WINDOW_INDEX=$(echo "$PM_WINDOW_INFO" | cut -d: -f1)

if [ -z "$PM_WINDOW_INDEX" ]; then
    echo "❌ Could not find PM window in session $PM_SESSION"
    exit 1
fi

echo "📨 Sending message to PM window: $PM_SESSION:$PM_WINDOW_INDEX"
echo ""

# Format message with clear external origin
FORMATTED_MESSAGE="💬 EXTERNAL MESSAGE FROM USER:

$MESSAGE

---
This message was sent externally to avoid interfering with your terminal.
Please respond or take action as appropriate."

# Send message to PM
tmux-message "$PM_SESSION:$PM_WINDOW_INDEX" "$FORMATTED_MESSAGE"

echo "✅ Message sent to PM successfully!"
echo ""
echo "💡 PM Response Options:"
echo "   - PM can respond in their terminal"
echo "   - PM can use agent communication commands to coordinate team"
echo "   - PM can message you back using orchestrator or direct communication"
echo ""
echo "🎯 Monitor PM activity:"
echo "   tmux attach -t $PM_SESSION (observe only - don't type)"
echo "   .tmux-orchestrator/commands/agent-status.sh"
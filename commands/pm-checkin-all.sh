#!/bin/bash
# PM Check-in with all team members
# Sends status check messages to all active agents

echo "👔 PM TEAM CHECK-IN"
echo "==================="
echo "Time: $(date)"
echo ""

# Get project name
PROJECT_NAME=$(basename "$(pwd)")

# Check if tmux server is running
if ! tmux list-sessions >/dev/null 2>&1; then
    echo "❌ No tmux server running - no agents to check in with"
    echo "💡 Deploy agents first: ./scripts/deploy.sh tasks.md"
    exit 1
fi

echo "🔍 Finding active agents..."

# Find orchestrator
ORCHESTRATOR_SESSIONS=$(tmux list-sessions -F "#{session_name}" 2>/dev/null | grep -E "orchestrator" || true)

# Find project agents
AGENT_SESSIONS=$(tmux list-sessions -F "#{session_name}" 2>/dev/null | grep -E "$PROJECT_NAME" | grep -v orchestrator || true)

# Count sessions
TOTAL_COUNT=0
if [ -n "$ORCHESTRATOR_SESSIONS" ]; then
    TOTAL_COUNT=$((TOTAL_COUNT + 1))
fi
if [ -n "$AGENT_SESSIONS" ]; then
    AGENT_COUNT=$(echo "$AGENT_SESSIONS" | wc -l)
    TOTAL_COUNT=$((TOTAL_COUNT + AGENT_COUNT))
fi

if [ $TOTAL_COUNT -eq 0 ]; then
    echo "❌ No active agents found to check in with"
    exit 1
fi

echo "   Found $TOTAL_COUNT active agents"
echo ""

# PM check-in message template
CHECK_IN_MESSAGE="👔 PM STATUS CHECK-IN:

This is your Project Manager conducting an off-cycle status check.

Please respond with:
1. What you're currently working on
2. Any blockers or issues you're facing  
3. What you plan to work on next
4. Estimated completion time for current task

If you're idle or between tasks, please request new work assignments.

Respond promptly so I can coordinate team priorities effectively!"

echo "📨 Sending check-in messages to all agents..."

# Check in with orchestrator
if [ -n "$ORCHESTRATOR_SESSIONS" ]; then
    echo "  → Orchestrator..."
    tmux-message "orchestrator:1" "$CHECK_IN_MESSAGE"
    sleep 2
fi

# Check in with all project agents
if [ -n "$AGENT_SESSIONS" ]; then
    while IFS= read -r session; do
        if [ -n "$session" ]; then
            echo "  → $session..."
            # Determine agent type for personalized message
            if echo "$session" | grep -q "frontend"; then
                ROLE="Frontend Developer"
                WINDOW=":2"
            elif echo "$session" | grep -q "backend"; then
                ROLE="Backend Developer" 
                WINDOW=":2"
            elif echo "$session" | grep -q "testing"; then
                ROLE="QA Engineer"
                WINDOW=":2"
            elif echo "$session" | grep -q "$PROJECT_NAME-$PROJECT_NAME"; then
                ROLE="Project Manager"
                WINDOW=":2"
                # Skip self-checkin
                echo "    (Skipping self - I'm the PM!)"
                continue
            else
                ROLE="Team Member"
                WINDOW=":2"
            fi
            
            PERSONALIZED_MESSAGE="👔 PM STATUS CHECK-IN ($ROLE):

This is your Project Manager conducting an off-cycle status check.

Please respond with:
1. What you're currently working on
2. Any blockers or issues you're facing  
3. What you plan to work on next
4. Estimated completion time for current task

If you're idle or between tasks, please request new work assignments.

Respond promptly so I can coordinate team priorities effectively!"

            tmux-message "$session$WINDOW" "$PERSONALIZED_MESSAGE"
            sleep 2
        fi
    done <<< "$AGENT_SESSIONS"
fi

echo ""
echo "✅ Check-in messages sent to all active agents!"
echo ""
echo "💡 Next steps:"
echo "   1. Wait 2-3 minutes for responses"
echo "   2. Check agent terminals for their status updates"
echo "   3. Use individual agent tasks to view responses"
echo "   4. Coordinate priorities based on their feedback"
echo ""
echo "🎯 Quick access to agents:"
echo "   Ctrl+Shift+P → Tasks: Run Task → '🎭 Open ALL Agent Terminals'"
#!/bin/bash
# Force an immediate PM check-in (off-cycle)

echo "📋 FORCED PM CHECK-IN"
echo "===================="
echo "Time: $(date)"
echo ""

# Get project name
PROJECT_NAME=$(basename "$(pwd)")
if [ "$PROJECT_NAME" = "." ] || [ -z "$PROJECT_NAME" ]; then
    echo "❌ Error: Cannot determine project name from current directory"
    echo "   Run this script from your project root directory"
    exit 1
fi

# Find PM session
PM_SESSION="$PROJECT_NAME-$PROJECT_NAME"
PM_WINDOW="Claude-pm"

# Check if PM session exists
if ! tmux has-session -t "$PM_SESSION" 2>/dev/null; then
    echo "❌ Error: PM session not found: $PM_SESSION"
    echo ""
    echo "Available sessions:"
    tmux list-sessions 2>/dev/null | grep -E "$PROJECT_NAME" || echo "  No project sessions found"
    echo ""
    echo "💡 Try deploying the team first:"
    echo "   ./scripts/deploy-$PROJECT_NAME-team.sh tasks.md"
    exit 1
fi

# Check if PM window exists
if ! tmux list-windows -t "$PM_SESSION" -F "#{window_name}" | grep -q "$PM_WINDOW" 2>/dev/null; then
    echo "❌ Error: PM window not found: $PM_SESSION:$PM_WINDOW"
    echo ""
    echo "Available windows in $PM_SESSION:"
    tmux list-windows -t "$PM_SESSION" -F "#{window_index}:#{window_name}" 2>/dev/null
    exit 1
fi

# Construct full PM target
PM_TARGET="$PM_SESSION:$PM_WINDOW"

echo "🎯 Target: $PM_TARGET"
echo "📤 Sending forced check-in request..."

# Send comprehensive check-in message
CHECK_IN_MESSAGE="🚨 FORCED CHECK-IN REQUESTED

This is an off-cycle check-in requested by the user.

Please provide a comprehensive status update including:

1. **Current Task Status:**
   - What tasks are currently in progress?
   - What has been completed since last check-in?
   - Any blockers or issues encountered?

2. **Team Coordination:**
   - Status of each team member (Frontend, Backend, QA)
   - Any cross-team dependencies or communication needed?
   - Resource allocation and workload balance?

3. **Quality Assurance:**
   - Test coverage and quality metrics
   - Code review status
   - Technical debt or quality concerns?

4. **Timeline and Priorities:**
   - Are we on track with current sprint/milestone?
   - Any priority adjustments needed?
   - Risk assessment for upcoming deliverables?

5. **Next Actions:**
   - What are the immediate next steps?
   - Any decisions needed from stakeholders?
   - Resource or support requirements?

Please be thorough and actionable in your response. This check-in was specifically requested for immediate attention."

# Send the message using tmux-message if available, otherwise use tmux send-keys
if command -v tmux-message >/dev/null 2>&1; then
    echo "   Using tmux-message command..."
    tmux-message "$PM_TARGET" "$CHECK_IN_MESSAGE"
else
    echo "   Using direct tmux send-keys..."
    tmux send-keys -t "$PM_TARGET" "$CHECK_IN_MESSAGE"
    sleep 0.5
    tmux send-keys -t "$PM_TARGET" Enter
fi

echo "✅ Forced check-in request sent!"
echo ""

# Show PM session info
echo "📊 PM Session Info:"
echo "   Session: $PM_SESSION"
echo "   Window: $PM_WINDOW" 
echo "   Full Target: $PM_TARGET"

# Check PM response readiness
echo ""
echo "⏳ Waiting for PM response..."
sleep 3

# Capture PM response preview
echo ""
echo "📋 PM Response Preview:"
echo "========================"
recent_output=$(tmux capture-pane -t "$PM_TARGET" -p 2>/dev/null | tail -10)
if [ -n "$recent_output" ]; then
    echo "$recent_output"
else
    echo "   No response captured yet..."
fi

echo ""
echo "💡 Next Steps:"
echo "   1. Attach to PM session: tmux attach -t '$PM_TARGET'"
echo "   2. Review full PM response and take action on recommendations"
echo "   3. Communicate updates to relevant team members"
echo "   4. Schedule follow-up if needed"

# Optional: Open PM session automatically
echo ""
read -p "🔗 Open PM session now? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Opening PM session..."
    exec tmux attach -t "$PM_TARGET"
fi
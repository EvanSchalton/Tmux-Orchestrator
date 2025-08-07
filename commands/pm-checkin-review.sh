#!/bin/bash
# PM Check-in and Status Review
# Gathers status from all agents and presents to PM for individual guidance

echo "👔 PM STATUS REVIEW & TEAM COORDINATION"
echo "========================================"
echo "Time: $(date)"
echo ""

# Get project name
PROJECT_NAME=$(basename "$(pwd)")

# Check if tmux server is running
if ! tmux list-sessions >/dev/null 2>&1; then
    echo "❌ No tmux server running - no agents to review"
    exit 1
fi

echo "🔍 Gathering current status from all agents..."

# Find PM session
PM_SESSION=$(tmux list-sessions -F "#{session_name}" 2>/dev/null | grep -E "$PROJECT_NAME-$PROJECT_NAME" || true)

if [ -z "$PM_SESSION" ]; then
    echo "❌ Could not find PM session. Are you running this as the PM?"
    exit 1
fi

# Find other agent sessions
ORCHESTRATOR_SESSIONS=$(tmux list-sessions -F "#{session_name}" 2>/dev/null | grep -E "orchestrator" || true)
AGENT_SESSIONS=$(tmux list-sessions -F "#{session_name}" 2>/dev/null | grep -E "$PROJECT_NAME" | grep -v "$PROJECT_NAME-$PROJECT_NAME" || true)

# Generate comprehensive status report
STATUS_REPORT="👔 COMPREHENSIVE TEAM STATUS REPORT
==================================
Time: $(date)

📊 AGENT STATUS SUMMARY:"

# Add orchestrator status
if [ -n "$ORCHESTRATOR_SESSIONS" ]; then
    echo "  → Getting Orchestrator status..."
    ORCH_ACTIVITY=$(tmux capture-pane -t "orchestrator:1" -p 2>/dev/null | tail -3 | head -1 | cut -c1-80 || echo "No recent activity")
    STATUS_REPORT="$STATUS_REPORT

🎯 ORCHESTRATOR:
   Status: Active
   Recent: $ORCH_ACTIVITY
   Session: orchestrator:1"
fi

# Add each agent status
if [ -n "$AGENT_SESSIONS" ]; then
    while IFS= read -r session; do
        if [ -n "$session" ]; then
            echo "  → Getting $session status..."
            
            # Determine agent type
            if echo "$session" | grep -q "frontend"; then
                AGENT_TYPE="🎨 FRONTEND DEVELOPER"
                FOCUS="UI/UX, React components, styling, user interactions"
            elif echo "$session" | grep -q "backend"; then
                AGENT_TYPE="⚙️ BACKEND DEVELOPER"
                FOCUS="APIs, database, server logic, data processing"
            elif echo "$session" | grep -q "testing"; then
                AGENT_TYPE="🧪 QA ENGINEER" 
                FOCUS="Testing, verification, quality assurance, bug reports"
            else
                AGENT_TYPE="🤖 AGENT"
                FOCUS="General development tasks"
            fi
            
            # Get recent activity
            ACTIVITY=$(tmux capture-pane -t "$session:2" -p 2>/dev/null | tail -3 | head -1 | cut -c1-80 || echo "No recent activity")
            
            STATUS_REPORT="$STATUS_REPORT

$AGENT_TYPE ($session):
   Focus Area: $FOCUS
   Recent Activity: $ACTIVITY
   Session: $session:2"
        fi
    done <<< "$AGENT_SESSIONS"
fi

# Add coordination instructions
STATUS_REPORT="$STATUS_REPORT

📋 PM COORDINATION INSTRUCTIONS:
===============================

Based on the above status, please:

1. REVIEW each agent's current activity and progress
2. IDENTIFY any agents that appear idle or blocked
3. PROVIDE individual guidance using these commands:

   Send specific tasks/guidance:
   • Orchestrator: tmux-message orchestrator:1 'your message'
   • Frontend: tmux-message ${PROJECT_NAME}-frontend:2 'your message'
   • Backend: tmux-message ${PROJECT_NAME}-backend:2 'your message'  
   • QA: tmux-message ${PROJECT_NAME}-testing:2 'your message'

4. COORDINATE priorities based on project needs
5. ASSIGN new work to idle agents
6. RESOLVE any blockers or dependencies

💡 EXAMPLE COMMANDS:
tmux-message ${PROJECT_NAME}-frontend:2 'Focus on fixing the login UI issues in components/Auth.tsx. Priority: High'
tmux-message ${PROJECT_NAME}-backend:2 'Implement the user authentication API endpoints. See tasks 1.1-1.3 in the PRD'
tmux-message orchestrator:1 'Please coordinate Neo4j database setup between backend and QA teams'

🎯 After providing guidance, monitor progress using:
   .tmux-orchestrator/commands/agent-status.sh

Take action now to keep your team productive and coordinated!"

# Send the comprehensive report to PM
echo ""
echo "📨 Sending comprehensive status report to PM for review and action..."
tmux-message "$PM_SESSION:2" "$STATUS_REPORT"

echo ""
echo "✅ Status report sent to PM!"
echo ""
echo "💡 The PM now has:"
echo "   - Complete status overview of all agents"
echo "   - Specific commands to message each agent individually"
echo "   - Clear instructions on coordination and task assignment"
echo ""
echo "🎯 Next: Open PM terminal to review status and provide individual guidance"
echo "   Use: tmux attach -t $PM_SESSION"
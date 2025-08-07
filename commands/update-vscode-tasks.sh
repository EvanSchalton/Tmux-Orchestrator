#!/bin/bash
# Update VS Code tasks.json based on currently running agents

echo "🔄 UPDATING VS CODE TASKS"
echo "========================="
echo "Time: $(date)"
echo ""

# Get project name
PROJECT_NAME=$(basename "$(pwd)")
if [ "$PROJECT_NAME" = "." ] || [ -z "$PROJECT_NAME" ]; then
    echo "❌ Error: Cannot determine project name"
    exit 1
fi

# Check if .vscode/tasks.json exists
if [ ! -f ".vscode/tasks.json" ]; then
    echo "❌ Error: .vscode/tasks.json not found"
    echo "   Run the setup script first or create VS Code tasks manually"
    exit 1
fi

# Backup existing tasks.json
cp ".vscode/tasks.json" ".vscode/tasks.json.backup.$(date +%Y%m%d-%H%M%S)"
echo "✓ Backup created: .vscode/tasks.json.backup.$(date +%Y%m%d-%H%M%S)"

# Detect running agents
echo "🔍 Detecting running agents..."

# Find orchestrator sessions
ORCHESTRATOR_SESSIONS=$(tmux list-sessions -F "#{session_name}" 2>/dev/null | grep -E "orchestrator" || true)

# Find project agent sessions  
AGENT_SESSIONS=$(tmux list-sessions -F "#{session_name}" 2>/dev/null | grep -E "$PROJECT_NAME" | grep -v orchestrator || true)

# Collect agent task data
AGENT_TASK_DATA=""

# Process orchestrator sessions
if [ -n "$ORCHESTRATOR_SESSIONS" ]; then
    while IFS= read -r session; do
        if [ -n "$session" ]; then
            AGENT_TASK_DATA="$AGENT_TASK_DATA
    {
      \"label\": \"Open Orchestrator ($session)\",
      \"type\": \"shell\",
      \"command\": \"tmux attach -t '$session:0'\",
      \"presentation\": {
        \"reveal\": \"always\",
        \"panel\": \"new\",
        \"group\": \"management\"
      },
      \"problemMatcher\": []
    },"
        fi
    done <<< "$ORCHESTRATOR_SESSIONS"
fi

# Process agent sessions with dynamic window detection
if [ -n "$AGENT_SESSIONS" ]; then
    while IFS= read -r session; do
        if [ -n "$session" ]; then
            # Get all windows for this session and find Claude agents
            WINDOWS=$(tmux list-windows -t "$session" -F "#{window_index}:#{window_name}" 2>/dev/null)
            
            while IFS= read -r window; do
                if [ -n "$window" ] && echo "$window" | grep -q "Claude"; then
                    WINDOW_INDEX=$(echo "$window" | cut -d: -f1)
                    WINDOW_NAME=$(echo "$window" | cut -d: -f2-)
                    
                    # Determine agent type and group
                    AGENT_TYPE="Agent"
                    GROUP="workers"
                    
                    if echo "$session" | grep -q "pm\\|manager" || echo "$WINDOW_NAME" | grep -q "pm"; then
                        AGENT_TYPE="PM"
                        GROUP="management"
                    elif echo "$WINDOW_NAME" | grep -q "frontend"; then
                        AGENT_TYPE="Frontend"
                    elif echo "$WINDOW_NAME" | grep -q "backend"; then
                        AGENT_TYPE="Backend"
                    elif echo "$WINDOW_NAME" | grep -q "qa\\|testing"; then
                        AGENT_TYPE="QA"
                    fi
                    
                    TASK_LABEL="Open $AGENT_TYPE Agent ($session)"
                    
                    AGENT_TASK_DATA="$AGENT_TASK_DATA
    {
      \"label\": \"$TASK_LABEL\",
      \"type\": \"shell\",
      \"command\": \"tmux attach -t '$session:$WINDOW_INDEX'\",
      \"presentation\": {
        \"reveal\": \"always\",
        \"panel\": \"new\",
        \"group\": \"$GROUP\"
      },
      \"problemMatcher\": []
    },"
                fi
            done <<< "$WINDOWS"
        fi
    done <<< "$AGENT_SESSIONS"
fi

# Generate properly formatted JSON
cat > .vscode/tasks.json << EOF
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "🚀 Deploy Team",
      "type": "shell", 
      "command": "\${workspaceFolder}/scripts/deploy.sh",
      "args": ["\${input:taskFile}"],
      "group": {
        "kind": "build",
        "isDefault": true
      },
      "presentation": {
        "echo": true,
        "reveal": "always",
        "focus": false,
        "panel": "shared",
        "showReuseMessage": true,
        "clear": false
      },
      "problemMatcher": []
    },
    {
      "label": "🔄 Restart Team",
      "type": "shell",
      "command": "\${workspaceFolder}/scripts/restart.sh",
      "args": ["\${input:taskFile}"],
      "group": "build",
      "presentation": {
        "reveal": "always",
        "panel": "shared"
      },
      "problemMatcher": []
    },
    {
      "label": "📊 List All Agents",
      "type": "shell",
      "command": "\${workspaceFolder}/.tmux-orchestrator/commands/list-agents.sh",
      "group": "test",
      "presentation": {
        "reveal": "always",
        "panel": "shared",
        "focus": true
      },
      "problemMatcher": []
    },
    {
      "label": "🎯 Agent Status Dashboard",
      "type": "shell",
      "command": "\${workspaceFolder}/.tmux-orchestrator/commands/agent-status.sh",
      "group": "test",
      "presentation": {
        "reveal": "always",
        "panel": "shared",
        "focus": true
      },
      "problemMatcher": []
    },
    {
      "label": "📋 PM Check-in (Forced)",
      "type": "shell",
      "command": "\${workspaceFolder}/.tmux-orchestrator/commands/force-pm-checkin.sh",
      "group": "build",
      "presentation": {
        "reveal": "always",
        "panel": "shared",
        "focus": true
      },
      "problemMatcher": []
    },
    {
      "label": "🎭 Open All Active Agents (Dynamic)",
      "type": "shell",
      "command": "\${workspaceFolder}/.tmux-orchestrator/commands/open-all-agents.sh",
      "group": "test",
      "presentation": {
        "reveal": "always",
        "panel": "shared",
        "focus": true
      },
      "problemMatcher": []
    },
    {
      "label": "🔄 Update VS Code Tasks",
      "type": "shell",
      "command": "\${workspaceFolder}/.tmux-orchestrator/commands/update-vscode-tasks.sh",
      "group": "build",
      "presentation": {
        "reveal": "always",
        "panel": "shared"
      },
      "problemMatcher": []
    },
    {
      "label": "💬 Send Message to Agent",
      "type": "shell",
      "command": "tmux-message",
      "args": ["\${input:agentTarget}", "\${input:message}"],
      "group": "build",
      "presentation": {
        "reveal": "always",
        "panel": "shared"
      },
      "problemMatcher": []
    }EOF

# Add dynamic agent tasks if any were found
if [ -n "$AGENT_TASK_DATA" ]; then
    echo "," >> .vscode/tasks.json
    # Remove the trailing comma from agent task data and add it
    echo "$AGENT_TASK_DATA" | sed 's/,$//' >> .vscode/tasks.json
fi

# Add utility tasks
cat >> .vscode/tasks.json << 'EOF'
,
    {
      "label": "🛑 Kill All Sessions",
      "type": "shell",
      "command": "tmux list-sessions | grep 'PROJECT_NAME_PLACEHOLDER\\|orchestrator' | cut -d: -f1 | xargs -I {} tmux kill-session -t {}",
      "group": "build",
      "presentation": {
        "reveal": "always",
        "panel": "shared"
      },
      "options": {
        "shell": {
          "executable": "/bin/bash"
        }
      },
      "problemMatcher": []
    },
    {
      "label": "🔧 Emergency Reset",
      "type": "shell",
      "command": "tmux kill-server && pkill -f claude",
      "group": "build", 
      "presentation": {
        "reveal": "always",
        "panel": "shared"
      },
      "options": {
        "shell": {
          "executable": "/bin/bash"
        }
      },
      "problemMatcher": []
    }
  ],
  "inputs": [
    {
      "id": "taskFile",
      "description": "Path to task file",
      "default": "tasks.md",
      "type": "promptString"
    },
    {
      "id": "agentTarget", 
      "description": "Agent target (session:window)",
      "type": "promptString"
    },
    {
      "id": "message",
      "description": "Message to send to agent",
      "type": "promptString"
    }
  ]
}
EOF

# Replace placeholder with actual project name
sed -i "s/PROJECT_NAME_PLACEHOLDER/$PROJECT_NAME/g" .vscode/tasks.json

echo ""
echo "✅ VS Code tasks.json updated successfully!"
echo ""

# Count tasks  
TASK_COUNT=$(grep -c '"label":' .vscode/tasks.json || echo "0")
AGENT_TASK_COUNT=0
if [ -n "$AGENT_TASK_DATA" ]; then
    AGENT_TASK_COUNT=$(echo "$AGENT_TASK_DATA" | grep -c '"label":' || echo "0")
fi

echo "📊 Task Summary:"
echo "   Total tasks: $TASK_COUNT"
echo "   Dynamic agent tasks: $AGENT_TASK_COUNT"
echo ""

if [ $AGENT_TASK_COUNT -gt 0 ]; then
    echo "🎭 Dynamic agent tasks created:"
    echo "$AGENT_TASK_DATA" | grep '"label":' | sed 's/.*"label": *"\([^"]*\)".*/   - \1/'
else
    echo "⚠️ No running agents detected"
    echo "   Deploy a team first, then run this script again"
fi

echo ""
echo "💡 Next steps:"
echo "   1. Reload VS Code window to see updated tasks"
echo "   2. Use Ctrl+Shift+P → 'Tasks: Run Task' to access updated commands"
echo "   3. Re-run this script when agents change to update tasks"

# Validate JSON syntax
if command -v python3 >/dev/null 2>&1; then
    if python3 -c "import json; json.load(open('.vscode/tasks.json'))" 2>/dev/null; then
        echo "   ✓ JSON syntax validated successfully"
    else
        echo "   ⚠️ JSON syntax validation failed - please check the file"
    fi
fi
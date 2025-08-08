#!/bin/bash
# Open agent terminals in VS Code integrated terminal

# This script uses VS Code's command line interface to open terminals
# It requires the 'code' command to be available in PATH

echo "Opening VS Code terminals for each agent..."

# Check if we're in VS Code terminal
if [ -z "$TERM_PROGRAM" ] && [ -z "$VSCODE_INJECTION" ]; then
    echo "Warning: This script works best when run from VS Code's integrated terminal"
fi

# Create a temporary VS Code tasks file for opening all agents
cat > /tmp/open-agents-tasks.json << 'EOF'
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "Open All Agents",
            "dependsOn": [
                "Terminal: Project Manager",
                "Terminal: MCP Developer",
                "Terminal: CLI Developer",
                "Terminal: Agent Recovery"
            ],
            "problemMatcher": []
        },
        {
            "label": "Terminal: Project Manager",
            "type": "shell",
            "command": "tmux attach-session -t tmux-orc-dev:5",
            "isBackground": true,
            "presentation": {
                "echo": true,
                "reveal": "always",
                "focus": false,
                "panel": "dedicated",
                "showReuseMessage": false,
                "clear": true,
                "group": "agents"
            },
            "problemMatcher": []
        },
        {
            "label": "Terminal: MCP Developer",
            "type": "shell",
            "command": "tmux attach-session -t tmux-orc-dev:2",
            "isBackground": true,
            "presentation": {
                "echo": true,
                "reveal": "always",
                "focus": false,
                "panel": "dedicated",
                "showReuseMessage": false,
                "clear": true,
                "group": "agents"
            },
            "problemMatcher": []
        },
        {
            "label": "Terminal: CLI Developer",
            "type": "shell",
            "command": "tmux attach-session -t tmux-orc-dev:3",
            "isBackground": true,
            "presentation": {
                "echo": true,
                "reveal": "always",
                "focus": false,
                "panel": "dedicated",
                "showReuseMessage": false,
                "clear": true,
                "group": "agents"
            },
            "problemMatcher": []
        },
        {
            "label": "Terminal: Agent Recovery",
            "type": "shell",
            "command": "tmux attach-session -t tmux-orc-dev:4",
            "isBackground": true,
            "presentation": {
                "echo": true,
                "reveal": "always",
                "focus": false,
                "panel": "dedicated",
                "showReuseMessage": false,
                "clear": true,
                "group": "agents"
            },
            "problemMatcher": []
        }
    ]
}
EOF

echo "Created temporary tasks file. Now opening terminals..."
echo ""
echo "Since VS Code doesn't support programmatically opening multiple terminals easily,"
echo "here's what you can do:"
echo ""
echo "OPTION 1: Open terminals manually in VS Code"
echo "1. Click Terminal > New Terminal (or Ctrl+Shift+\`)"
echo "2. Run: tmux attach-session -t tmux-orc-dev:5"
echo "3. Click the '+' in terminal panel to add another terminal"
echo "4. Run: tmux attach-session -t tmux-orc-dev:2"
echo "5. Repeat for windows 3 and 4"
echo ""
echo "OPTION 2: Use the split terminal feature"
echo "1. Open a terminal and attach to first agent"
echo "2. Click the 'Split Terminal' button (or Ctrl+Shift+5)"
echo "3. Attach to next agent in the new pane"
echo "4. Repeat to create a 2x2 grid"
echo ""
echo "Commands to run in each terminal:"
echo "  Terminal 1: tmux attach-session -t tmux-orc-dev:5  # Project Manager"
echo "  Terminal 2: tmux attach-session -t tmux-orc-dev:2  # MCP Developer"
echo "  Terminal 3: tmux attach-session -t tmux-orc-dev:3  # CLI Developer"
echo "  Terminal 4: tmux attach-session -t tmux-orc-dev:4  # Agent Recovery"
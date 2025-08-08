#!/bin/bash
# TMUX Orchestrator Devcontainer Setup Script
# This script integrates the TMUX Orchestrator into any devcontainer project

set -e

# Configuration
PROJECT_NAME="${1:-my-project}"
BASE_PATH="${2:-/workspaces}"
PROJECT_PATH="$BASE_PATH/$PROJECT_NAME"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}🐳 TMUX Orchestrator Devcontainer Setup${NC}"
echo -e "${BLUE}=======================================${NC}"
echo -e "Project: ${YELLOW}$PROJECT_NAME${NC}"
echo -e "Path: ${YELLOW}$PROJECT_PATH${NC}"
echo ""

# Verify we're in a project directory
if [ ! -d ".devcontainer" ]; then
    echo -e "${RED}❌ Error: Not in a devcontainer project${NC}"
    echo "   Expected .devcontainer/ directory not found"
    echo "   Run this script from your project root"
    exit 1
fi

# Step 1: Copy Tmux Orchestrator files
echo -e "${GREEN}1. Copying TMUX Orchestrator files...${NC}"

# Create references directory if it doesn't exist
mkdir -p references/

# Copy the entire Tmux-Orchestrator directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -d "$SCRIPT_DIR" ]; then
    echo "   Copying from: $SCRIPT_DIR"
    cp -r "$SCRIPT_DIR" references/Tmux-Orchestrator
    echo "   ✓ TMUX Orchestrator files copied"
else
    echo -e "${RED}❌ Error: Cannot locate Tmux-Orchestrator source directory${NC}"
    exit 1
fi

# Step 2: Create installation script
echo -e "\n${GREEN}2. Creating installation script...${NC}"

mkdir -p scripts/
cp references/Tmux-Orchestrator/install-template.sh scripts/install-tmux-orchestrator.sh

# Customize the installation script
sed -i "s/your-project/$PROJECT_NAME/g" scripts/install-tmux-orchestrator.sh
sed -i "s|/workspaces/your-project|$PROJECT_PATH|g" scripts/install-tmux-orchestrator.sh

chmod +x scripts/install-tmux-orchestrator.sh
echo "   ✓ Installation script created: scripts/install-tmux-orchestrator.sh"

# Step 3: Update devcontainer.json
echo -e "\n${GREEN}3. Updating devcontainer.json...${NC}"

DEVCONTAINER_FILE=".devcontainer/devcontainer.json"

# Backup original devcontainer.json
cp "$DEVCONTAINER_FILE" "$DEVCONTAINER_FILE.backup"
echo "   ✓ Backup created: $DEVCONTAINER_FILE.backup"

# Check if devcontainer.json already has TMUX orchestrator configuration
if grep -q "TMUX_ORCHESTRATOR_HOME" "$DEVCONTAINER_FILE"; then
    echo -e "   ${YELLOW}⚠️ TMUX Orchestrator configuration already exists${NC}"
    echo "   Review and update manually if needed"
else
    # Parse the JSON and add TMUX orchestrator configuration
    python3 << EOF
import json
import sys

try:
    with open('$DEVCONTAINER_FILE', 'r') as f:
        config = json.load(f)
    
    # Add postCreateCommand
    if 'postCreateCommand' in config:
        # Append to existing command
        existing = config['postCreateCommand']
        if 'install-tmux-orchestrator.sh' not in existing:
            config['postCreateCommand'] = existing + ' && bash scripts/install-tmux-orchestrator.sh'
    else:
        config['postCreateCommand'] = 'bash scripts/install-tmux-orchestrator.sh'
    
    # Add environment variables
    if 'remoteEnv' not in config:
        config['remoteEnv'] = {}
    
    config['remoteEnv']['TMUX_ORCHESTRATOR_HOME'] = '$PROJECT_PATH/.tmux-orchestrator'
    config['remoteEnv']['TMUX_ORCHESTRATOR_REGISTRY'] = '$PROJECT_PATH/.tmux-orchestrator/registry'
    
    # Write updated configuration
    with open('$DEVCONTAINER_FILE', 'w') as f:
        json.dump(config, f, indent=2)
    
    print("✓ devcontainer.json updated successfully")
    
except Exception as e:
    print(f"❌ Error updating devcontainer.json: {e}")
    sys.exit(1)
EOF

    if [ $? -eq 0 ]; then
        echo "   ✓ devcontainer.json updated with TMUX Orchestrator configuration"
    else
        echo -e "   ${RED}❌ Failed to update devcontainer.json automatically${NC}"
        echo "   Please add the following configuration manually:"
        echo ""
        echo '   "postCreateCommand": "bash scripts/install-tmux-orchestrator.sh",'
        echo '   "remoteEnv": {'
        echo "     \"TMUX_ORCHESTRATOR_HOME\": \"$PROJECT_PATH/.tmux-orchestrator\","
        echo "     \"TMUX_ORCHESTRATOR_REGISTRY\": \"$PROJECT_PATH/.tmux-orchestrator/registry\""
        echo '   }'
    fi
fi

# Step 4: Create project-specific deployment script
echo -e "\n${GREEN}4. Creating project-specific scripts...${NC}"

# Create generic deployment script
cat > "scripts/deploy.sh" << EOF
#!/bin/bash
# Generic team deployment script
# Usage: ./deploy.sh <task-file>

TASK_FILE="\$1"
PROJECT_NAME=\$(basename "\$(pwd)")

if [ -z "\$TASK_FILE" ]; then
    echo "Usage: \$0 <task-file>"
    echo "Example: \$0 planning/tasks.md"
    exit 1
fi

# Use the existing tmux-deploy-team.sh script
exec ./scripts/tmux-deploy-team.sh "\$TASK_FILE" "\$PROJECT_NAME"
EOF

chmod +x "scripts/deploy.sh"
echo "   ✓ Generic deployment script created: scripts/deploy.sh"

# Create generic restart script
cat > "scripts/restart.sh" << EOF
#!/bin/bash
# Generic team restart script
# Usage: ./restart.sh <task-file>

set -e

TASK_FILE="\$1"
PROJECT_NAME=\$(basename "\$(pwd)")

if [ -z "\$TASK_FILE" ]; then
    echo "Usage: \$0 <task-file>"
    echo "Example: \$0 planning/tasks.md"
    exit 1
fi

echo "🔄 Restarting \$PROJECT_NAME Team..."
echo "=================================="
echo "Task File: \$TASK_FILE"
echo ""

# Kill all existing sessions for this project and orchestrator
echo "🛑 Killing existing sessions..."
for session in \$(tmux ls -F "#{session_name}" 2>/dev/null | grep -E "(\$PROJECT_NAME|orchestrator)" || true); do
    if [ -n "\$session" ]; then
        echo "  Killing \$session"
        tmux kill-session -t "\$session" 2>/dev/null || true
    fi
done

# Wait a moment for cleanup
echo "⏱️  Waiting for cleanup..."
sleep 3

# Deploy fresh team with the task file
echo "🚀 Deploying fresh team..."
./scripts/deploy.sh "\$TASK_FILE"

echo ""
echo "✅ \$PROJECT_NAME team restarted successfully!"
echo ""
echo "💡 Next Steps:"
echo "  Monitor: ./scripts/monitor-\$PROJECT_NAME-team.sh"
echo "  Status:  ./.tmux-orchestrator/commands/agent-status.sh"
echo "  VS Code: Ctrl+Shift+P → Tasks: Run Task → Open All Agents"
EOF

chmod +x "scripts/restart.sh"
echo "   ✓ Generic restart script created: scripts/restart.sh"

# Step 5: Configure VS Code integration
echo -e "\n${GREEN}5. Configuring VS Code integration...${NC}"

# Create .vscode directory if it doesn't exist
mkdir -p .vscode/

# Check if tasks.json already exists
if [ -f ".vscode/tasks.json" ]; then
    echo "   ⚠️ Existing .vscode/tasks.json found"
    cp ".vscode/tasks.json" ".vscode/tasks.json.backup"
    echo "   ✓ Backup created: .vscode/tasks.json.backup"
fi

# Copy and customize the tasks template
if [ -f "references/Tmux-Orchestrator/vscode/tasks-template.json" ]; then
    # Use sed to replace placeholder variables with actual project name
    sed "s/\\\${workspaceFolderBasename}/$PROJECT_NAME/g" \
        references/Tmux-Orchestrator/vscode/tasks-template.json > .vscode/tasks.json
    echo "   ✓ VS Code tasks configured for $PROJECT_NAME"
    echo "     - Deploy/restart team commands"
    echo "     - Agent listing and status"
    echo "     - PM check-in and monitoring" 
    echo "     - Quick agent access"
    echo "     - Emergency controls"
else
    echo "   ⚠️ VS Code tasks template not found, skipping"
fi

# Create VS Code settings for tmux integration
cat > .vscode/settings.json.tmux << EOF
{
  "terminal.integrated.defaultProfile.linux": "tmux",
  "terminal.integrated.profiles.linux": {
    "tmux": {
      "path": "/usr/bin/tmux",
      "args": ["new-session", "-s", "vscode-$PROJECT_NAME"]
    }
  },
  "workbench.colorCustomizations": {
    "activityBar.background": "#1e3a8a",
    "activityBar.foreground": "#ffffff",
    "statusBar.background": "#1e40af",
    "statusBar.foreground": "#ffffff"
  }
}
EOF

echo "   ✓ VS Code tmux settings created (optional): .vscode/settings.json.tmux"
echo "     Merge with existing settings.json if desired"

# Step 6: Create sample task file
echo -e "\n${GREEN}6. Creating sample task file...${NC}"

if [ ! -f "tasks.md" ]; then
    cat > "tasks.md" << EOF
# $PROJECT_NAME Development Tasks

## Objective
Describe the overall goal of this development cycle.

## Frontend Tasks
- [ ] Update UI components
- [ ] Implement responsive design
- [ ] Add accessibility features
- [ ] Write component tests

## Backend Tasks  
- [ ] Create API endpoints
- [ ] Implement business logic
- [ ] Database schema updates
- [ ] Write unit tests

## Integration Tasks
- [ ] Frontend-backend integration
- [ ] End-to-end testing
- [ ] Performance optimization
- [ ] Documentation updates

## Success Criteria
- All tests passing
- Code review completed
- Documentation updated
- Performance benchmarks met
EOF
    echo "   ✓ Sample task file created: tasks.md"
else
    echo "   ✓ Existing tasks.md found - not overwriting"
fi

# Create README section
cat > "TMUX_ORCHESTRATOR_README.md" << EOF
# TMUX Orchestrator Integration

This project is integrated with the TMUX Orchestrator for autonomous development.

## Quick Start

### Deploy Development Team
\`\`\`bash
# Deploy team based on tasks.md
./scripts/deploy.sh tasks.md

# Or with custom task file
./scripts/deploy.sh path/to/tasks.md
\`\`\`

### Restart Team
\`\`\`bash
# Quick restart
./scripts/restart.sh tasks.md

# Restart with different task file
./scripts/restart.sh new-tasks.md
\`\`\`

### Monitor Team
\`\`\`bash
# Check agent status
.tmux-orchestrator/commands/agent-status.sh

# Attach to specific agent
tmux attach -t $PROJECT_NAME-frontend
tmux attach -t $PROJECT_NAME-backend
tmux attach -t orchestrator
\`\`\`

### Send Messages
\`\`\`bash
# Send message to agent
tmux-message $PROJECT_NAME-frontend:0 "Status update please"

# Request specific action
tmux-message $PROJECT_NAME-backend:0 "Run tests and report results"
\`\`\`

## Files Created

- \`scripts/install-tmux-orchestrator.sh\` - Installation script
- \`scripts/deploy.sh\` - Generic team deployment
- \`scripts/restart.sh\` - Generic team restart
- \`references/Tmux-Orchestrator/\` - Full documentation
- \`tasks.md\` - Sample task file

## Documentation

See \`references/Tmux-Orchestrator/\` for complete documentation:
- \`SETUP.md\` - Setup and configuration
- \`RUNNING.md\` - Day-to-day operations  
- \`CLAUDE.md\` - Agent behavior guide
- \`Examples/\` - Screenshots and examples

## Next Steps

1. **Customize tasks.md** for your project needs
2. **Rebuild devcontainer** to install TMUX Orchestrator
3. **Deploy team**: \`./scripts/deploy-$PROJECT_NAME-team.sh\`
4. **Monitor progress**: \`.tmux-orchestrator/commands/agent-status.sh\`
EOF

echo "   ✓ Documentation created: TMUX_ORCHESTRATOR_README.md"

# Step 7: Summary and next steps
echo -e "\n${BLUE}✅ TMUX Orchestrator Integration Complete!${NC}"
echo -e "${GREEN}===========================================${NC}"
echo ""
echo -e "${GREEN}Files Created:${NC}"
echo -e "  📋 scripts/install-tmux-orchestrator.sh"
echo -e "  🚀 scripts/deploy.sh"
echo -e "  🔄 scripts/restart.sh"
echo -e "  📚 references/Tmux-Orchestrator/ (full documentation)"
echo -e "  📝 tasks.md (sample task file)"
echo -e "  📖 TMUX_ORCHESTRATOR_README.md"
echo -e "  🎮 .vscode/tasks.json (VS Code integration)"
echo -e "  ⚙️ .vscode/settings.json.tmux (optional tmux settings)"
echo ""
echo -e "${GREEN}Configuration Updated:${NC}"
echo -e "  🐳 .devcontainer/devcontainer.json (backup at .devcontainer/devcontainer.json.backup)"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo -e "  1. ${YELLOW}Review and customize tasks.md${NC} for your project"
echo -e "  2. ${YELLOW}Rebuild your devcontainer${NC} to install TMUX Orchestrator"
echo -e "  3. ${YELLOW}Deploy your team${NC}: ./scripts/deploy.sh tasks.md"
echo -e "  4. ${YELLOW}Read the documentation${NC}: references/Tmux-Orchestrator/SETUP.md"
echo ""
echo -e "${GREEN}Quick Commands:${NC}"
echo -e "  Deploy: ${YELLOW}./scripts/deploy.sh tasks.md${NC}"
echo -e "  Restart: ${YELLOW}./scripts/restart.sh tasks.md${NC}"
echo -e "  Monitor: ${YELLOW}.tmux-orchestrator/commands/agent-status.sh${NC}"
echo -e "  List agents: ${YELLOW}.tmux-orchestrator/commands/list-agents.sh${NC}"
echo -e "  Force PM check-in: ${YELLOW}.tmux-orchestrator/commands/force-pm-checkin.sh${NC}"
echo ""
echo -e "${GREEN}VS Code Integration:${NC}"
echo -e "  Use Ctrl+Shift+P → 'Tasks: Run Task' to access orchestrator commands"
echo -e "  Quick deploy: ${YELLOW}🚀 Deploy Team${NC}"
echo -e "  Agent status: ${YELLOW}📊 List All Agents${NC}"
echo -e "  PM check-in: ${YELLOW}📋 PM Check-in (Forced)${NC}"
echo ""
echo -e "${BLUE}🎉 Ready for autonomous development!${NC}"
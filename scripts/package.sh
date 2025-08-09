#!/bin/bash
# Package Tmux Orchestrator for distribution

set -e

# Configuration
PACKAGE_NAME="tmux-orchestrator"
VERSION=$(date +%Y%m%d)
OUTPUT_DIR="./dist"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Packaging Tmux Orchestrator v${VERSION}...${NC}"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Create tarball with all necessary files
tar -czf "$OUTPUT_DIR/${PACKAGE_NAME}-${VERSION}.tar.gz" \
    --exclude='.git' \
    --exclude='dist' \
    --exclude='*.log' \
    --exclude='registry' \
    send-claude-message.sh \
    schedule_with_note.sh \
    tmux_utils.py \
    install.sh \
    bootstrap.sh \
    README.md \
    QUICKSTART.md \
    devcontainer-template.json \
    CLAUDE.md \
    LEARNINGS.md \
    images/

# Create standalone installer
cat > "$OUTPUT_DIR/install-tmux-orchestrator.sh" << 'EOF'
#!/bin/bash
# Standalone Tmux Orchestrator Installer
# Usage: curl -sSL [url]/install-tmux-orchestrator.sh | bash

set -e

TEMP_DIR="/tmp/tmux-orchestrator-$$"
PACKAGE_URL="${1:-https://github.com/EvanSchalton/Tmux-Orchestrator/releases/latest/download/tmux-orchestrator.tar.gz}"

echo "📦 Downloading Tmux Orchestrator..."
mkdir -p "$TEMP_DIR"
cd "$TEMP_DIR"

if command -v curl &> /dev/null; then
    curl -sSL "$PACKAGE_URL" | tar -xz
elif command -v wget &> /dev/null; then
    wget -qO- "$PACKAGE_URL" | tar -xz
else
    echo "Error: curl or wget required"
    exit 1
fi

echo "🚀 Running installer..."
./install.sh

# Cleanup
cd /
rm -rf "$TEMP_DIR"

echo "✅ Installation complete!"
echo "   Run: tmux-orchestrator help"
EOF

chmod +x "$OUTPUT_DIR/install-tmux-orchestrator.sh"

# Create Claude commands bundle
mkdir -p "$OUTPUT_DIR/claude-commands"
cat > "$OUTPUT_DIR/claude-commands/orchestrator.md" << 'EOF'
---
description: Send a message to the Tmux Orchestrator
output: Run the command
shortcut: orch
---

# Orchestrator Message

Send this message to the orchestrator: {{message}}

Use: `tmux-orchestrator send orchestrator:0 "{{message}}"`
EOF

cat > "$OUTPUT_DIR/claude-commands/schedule.md" << 'EOF'
---
description: Schedule a check-in with the orchestrator
output: Run the command
shortcut: sched
---

# Schedule Check-in

Schedule a check-in in {{minutes}} minutes with note: {{note}}

Use: `tmux-orchestrator schedule {{minutes}} orchestrator:0 "{{note}}"`
EOF

tar -czf "$OUTPUT_DIR/claude-commands.tar.gz" -C "$OUTPUT_DIR" claude-commands/
rm -rf "$OUTPUT_DIR/claude-commands"

# Create release notes
cat > "$OUTPUT_DIR/RELEASE-${VERSION}.md" << EOF
# Tmux Orchestrator Release ${VERSION}

## 📦 Files

- \`tmux-orchestrator-${VERSION}.tar.gz\` - Complete package
- \`install-tmux-orchestrator.sh\` - Standalone installer
- \`claude-commands.tar.gz\` - Claude slash commands

## 🚀 Installation

### Method 1: Direct Install
\`\`\`bash
curl -sSL [url]/install-tmux-orchestrator.sh | bash
\`\`\`

### Method 2: Devcontainer
Add to \`devcontainer.json\`:
\`\`\`json
{
  "postCreateCommand": "curl -sSL [url]/bootstrap.sh | bash"
}
\`\`\`

### Method 3: Manual
\`\`\`bash
tar -xzf tmux-orchestrator-${VERSION}.tar.gz
./install.sh
\`\`\`

## 📚 Documentation

See QUICKSTART.md for usage instructions.
EOF

echo -e "${GREEN}✅ Package created successfully!${NC}"
echo ""
echo "📁 Distribution files in: $OUTPUT_DIR/"
ls -la "$OUTPUT_DIR/"

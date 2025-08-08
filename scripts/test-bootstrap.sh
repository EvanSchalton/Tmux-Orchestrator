#!/bin/bash
# Test Tmux Orchestrator Bootstrap Process

set -e

# Test configuration
TEST_DIR="/tmp/tmux-orchestrator-test-$$"
TEST_HOME="$TEST_DIR/home"
ORIGINAL_HOME="$HOME"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Functions
print_test() { echo -e "${BLUE}[TEST]${NC} $1"; }
print_pass() { echo -e "${GREEN}[PASS]${NC} $1"; }
print_fail() { echo -e "${RED}[FAIL]${NC} $1"; exit 1; }

# Setup test environment
print_test "Setting up test environment..."
mkdir -p "$TEST_HOME"
export HOME="$TEST_HOME"
export TMUX_ORCHESTRATOR_HOME="$TEST_HOME/.tmux-orchestrator"

# Test 1: Bootstrap installation
print_test "Testing bootstrap installation..."
cd "$(dirname "$0")"
./bootstrap.sh

# Verify installation
if [ ! -d "$TMUX_ORCHESTRATOR_HOME" ]; then
    print_fail "Installation directory not created"
fi

if [ ! -f "$TMUX_ORCHESTRATOR_HOME/bin/tmux-orchestrator" ]; then
    print_fail "Main command not installed"
fi

if [ ! -x "$TMUX_ORCHESTRATOR_HOME/scripts/send-claude-message.sh" ]; then
    print_fail "Scripts not installed or not executable"
fi

print_pass "Bootstrap installation successful"

# Test 2: Command availability
print_test "Testing command availability..."
export PATH="$TMUX_ORCHESTRATOR_HOME/bin:$PATH"

if ! command -v tmux-orchestrator &> /dev/null; then
    print_fail "tmux-orchestrator command not in PATH"
fi

# Test help command
if ! tmux-orchestrator help &> /dev/null; then
    print_fail "Help command failed"
fi

print_pass "Commands working correctly"

# Test 3: Configuration
print_test "Testing configuration..."
CONFIG_FILE="$TMUX_ORCHESTRATOR_HOME/config/tmux-orchestrator.conf"

if [ ! -f "$CONFIG_FILE" ]; then
    print_fail "Configuration file not created"
fi

# Source and verify config
source "$CONFIG_FILE"
if [ "$TMUX_ORCHESTRATOR_HOME" != "$TEST_HOME/.tmux-orchestrator" ]; then
    print_fail "Configuration not set correctly"
fi

print_pass "Configuration valid"

# Test 4: Devcontainer integration
print_test "Testing devcontainer integration..."
# The bootstrap script creates commands in the current working directory
CLAUDE_COMMANDS_DIR="$(pwd)/.claude/commands"

if [ ! -f "$CLAUDE_COMMANDS_DIR/orchestrator.md" ]; then
    print_fail "Claude orchestrator command not created"
fi

if [ ! -f "$CLAUDE_COMMANDS_DIR/schedule.md" ]; then
    print_fail "Claude schedule command not created"
fi

print_pass "Devcontainer integration complete"

# Test 5: Directory structure
print_test "Verifying directory structure..."
REQUIRED_DIRS=(
    "$TMUX_ORCHESTRATOR_HOME/bin"
    "$TMUX_ORCHESTRATOR_HOME/scripts"
    "$TMUX_ORCHESTRATOR_HOME/registry/logs"
    "$TMUX_ORCHESTRATOR_HOME/registry/notes"
    "$TMUX_ORCHESTRATOR_HOME/config"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        print_fail "Missing directory: $dir"
    fi
done

print_pass "Directory structure correct"

# Cleanup
export HOME="$ORIGINAL_HOME"
rm -rf "$TEST_DIR"

# Summary
echo -e "\n${GREEN}═══════════════════════════════════════${NC}"
echo -e "${GREEN}  All tests passed! ✅${NC}"
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo ""
echo "The bootstrap process is working correctly."
echo "Ready to be used in other devcontainer projects!"
#!/bin/bash
# Manual test script for PM false positive detection
# This script helps developers quickly test if PMs are being incorrectly killed

echo "🧪 PM False Positive Detection Manual Test"
echo "=========================================="
echo ""
echo "This test will:"
echo "1. Spawn a test PM that outputs 'failed' messages"
echo "2. Monitor if the PM gets killed (it should NOT be killed)"
echo "3. Report the results"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test session name
TEST_SESSION="pm-false-positive-test"
TEST_WINDOW="1"

# Function to check if PM is still alive
check_pm_alive() {
    if tmux list-windows -t "$TEST_SESSION" 2>/dev/null | grep -q "Claude-PM"; then
        return 0  # PM is alive
    else
        return 1  # PM is dead
    fi
}

# Function to capture PM content
capture_pm_content() {
    tmux capture-pane -t "$TEST_SESSION:$TEST_WINDOW" -p 2>/dev/null
}

echo "Step 1: Setting up test environment..."
echo "--------------------------------------"

# Kill existing test session if it exists
tmux kill-session -t "$TEST_SESSION" 2>/dev/null

# Create new test session
echo "Creating test session: $TEST_SESSION"
tmux new-session -d -s "$TEST_SESSION" -n "Claude-PM"

# Start the PM simulation script
echo "Starting PM simulation that outputs 'failed' messages..."
tmux send-keys -t "$TEST_SESSION:$TEST_WINDOW" "python /workspaces/Tmux-Orchestrator/qa_test_scripts/simulate_pm_failed_output.py" Enter

# Give it time to start
sleep 3

echo ""
echo "Step 2: Initial PM Status"
echo "-------------------------"
if check_pm_alive; then
    echo -e "${GREEN}✓ PM is running${NC}"
else
    echo -e "${RED}✗ PM failed to start${NC}"
    exit 1
fi

echo ""
echo "Current PM output:"
echo "=================="
capture_pm_content | tail -20
echo "=================="

echo ""
echo "Step 3: Waiting for monitor to potentially kill PM..."
echo "----------------------------------------------------"
echo "If the bug exists, the PM will be killed within 30-60 seconds"
echo "because it outputs messages containing 'failed', 'error', etc."
echo ""

# Monitor for 60 seconds
for i in {1..12}; do
    sleep 5
    echo -n "."

    if ! check_pm_alive; then
        echo ""
        echo -e "${RED}❌ CRITICAL BUG CONFIRMED!${NC}"
        echo -e "${RED}PM was killed after $((i*5)) seconds${NC}"
        echo ""
        echo "The PM was incorrectly terminated because it output legitimate"
        echo "messages containing crash indicator keywords like 'failed'."
        echo ""
        echo "This confirms the bug at monitor.py line 1724"
        echo ""

        # Cleanup
        tmux kill-session -t "$TEST_SESSION" 2>/dev/null
        exit 1
    fi
done

echo ""
echo ""
echo -e "${GREEN}✅ SUCCESS: PM survived for 60 seconds!${NC}"
echo ""
echo "The PM was NOT killed despite outputting messages with 'failed'."
echo "This indicates the false positive bug has been fixed!"
echo ""

echo "Final PM status:"
if check_pm_alive; then
    echo -e "${GREEN}✓ PM is still running${NC}"
    echo ""
    echo "Last output from PM:"
    echo "==================="
    capture_pm_content | tail -10
    echo "==================="
else
    echo -e "${YELLOW}⚠ PM stopped (but not by monitor)${NC}"
fi

echo ""
echo "Step 4: Cleanup"
echo "--------------"
tmux kill-session -t "$TEST_SESSION" 2>/dev/null
echo "Test session cleaned up"

echo ""
echo "Test complete!"
echo ""
echo "To run more comprehensive tests, use:"
echo "  python tests/test_pm_crash_detection_validation.py"
echo ""

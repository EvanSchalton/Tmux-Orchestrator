#!/bin/bash
# Quick test for 'failed' keyword false positive fix

echo "🧪 Testing 'failed' Keyword Context-Aware Detection"
echo "=================================================="
echo ""

# Create test session
TEST_SESSION="failed-keyword-test"
tmux kill-session -t "$TEST_SESSION" 2>/dev/null
tmux new-session -d -s "$TEST_SESSION" -n "Claude-PM"

echo "📋 Test 1: PM discussing test failures"
echo "-------------------------------------"
tmux send-keys -t "$TEST_SESSION:1" "echo '╭─ Assistant ─────────────────────────────────────────────────────╮'" Enter
tmux send-keys -t "$TEST_SESSION:1" "echo '│ Test results: 3 tests failed                                   │'" Enter
tmux send-keys -t "$TEST_SESSION:1" "echo '│ - auth_test.py failed with timeout                             │'" Enter
tmux send-keys -t "$TEST_SESSION:1" "echo '│ - db_test.py failed to connect                                 │'" Enter
tmux send-keys -t "$TEST_SESSION:1" "echo '│ Working on fixes...                                            │'" Enter
tmux send-keys -t "$TEST_SESSION:1" "echo '╰─────────────────────────────────────────────────────────────────╯'" Enter
sleep 2

# Capture content
echo "Current content:"
tmux capture-pane -t "$TEST_SESSION:1" -p | tail -10
echo ""

# Check if session is still alive after 5 seconds
echo "Waiting 5 seconds to see if PM gets killed..."
sleep 5

if tmux list-windows -t "$TEST_SESSION" 2>/dev/null | grep -q "Claude-PM"; then
    echo "✅ SUCCESS: PM still alive despite 'failed' in output!"
else
    echo "❌ FAILURE: PM was killed - false positive bug still present!"
fi

echo ""
echo "📋 Test 2: PM discussing deployment failures"
echo "-------------------------------------------"
tmux send-keys -t "$TEST_SESSION:1" C-l  # Clear screen
tmux send-keys -t "$TEST_SESSION:1" "echo '╭─ Assistant ─────────────────────────────────────────────────────╮'" Enter
tmux send-keys -t "$TEST_SESSION:1" "echo '│ Deployment failed due to:                                      │'" Enter
tmux send-keys -t "$TEST_SESSION:1" "echo '│ - Database migration failed                                    │'" Enter
tmux send-keys -t "$TEST_SESSION:1" "echo '│ - Health check failed after timeout                            │'" Enter
tmux send-keys -t "$TEST_SESSION:1" "echo '│ - SSL validation failed                                        │'" Enter
tmux send-keys -t "$TEST_SESSION:1" "echo '│ Implementing rollback...                                       │'" Enter
tmux send-keys -t "$TEST_SESSION:1" "echo '╰─────────────────────────────────────────────────────────────────╯'" Enter
sleep 2

echo "Waiting another 5 seconds..."
sleep 5

if tmux list-windows -t "$TEST_SESSION" 2>/dev/null | grep -q "Claude-PM"; then
    echo "✅ SUCCESS: PM survived multiple 'failed' keywords!"
    echo ""
    echo "🎉 CONTEXT-AWARE DETECTION IS WORKING!"
else
    echo "❌ FAILURE: PM was killed - fix not working properly!"
fi

# Cleanup
echo ""
echo "Cleaning up test session..."
tmux kill-session -t "$TEST_SESSION" 2>/dev/null

echo ""
echo "Test complete. For comprehensive validation, run:"
echo "  python qa_validate_context_aware_fix.py"

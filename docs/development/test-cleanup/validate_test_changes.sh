#!/bin/bash
# Validation script for test changes

echo "=== Test Validation Report ==="
echo "Date: $(date)"
echo ""

echo "1. Checking pytest discovery..."
TEST_COUNT=$(poetry run pytest --collect-only -q 2>&1 | grep -c "test session starts" || echo "0")
COLLECTED=$(poetry run pytest --collect-only 2>&1 | grep "collected" | grep -oE "[0-9]+ items" || echo "0 items")
echo "   Tests collected: $COLLECTED"

echo ""
echo "2. Checking for collection errors..."
ERRORS=$(poetry run pytest --collect-only --quiet 2>&1 | grep -E "(ERROR|FAILED|error collecting)" | wc -l)
if [ "$ERRORS" -eq 0 ]; then
    echo "   ✅ No collection errors found"
else
    echo "   ❌ Found $ERRORS collection errors:"
    poetry run pytest --collect-only --quiet 2>&1 | grep -E "(ERROR|FAILED|error collecting)" | head -5
fi

echo ""
echo "3. Checking test file naming patterns..."
WRONG_PATTERN=$(find tests -name "test_*.py" -type f | wc -l)
RIGHT_PATTERN=$(find tests -name "*_test.py" -type f | wc -l)
echo "   Files with test_*.py pattern: $WRONG_PATTERN"
echo "   Files with *_test.py pattern: $RIGHT_PATTERN"

echo ""
echo "4. Checking for __init__.py in tests..."
INIT_FILES=$(find tests -name "__init__.py" | wc -l)
if [ "$INIT_FILES" -eq 0 ]; then
    echo "   ✅ No __init__.py files found"
else
    echo "   ❌ Found $INIT_FILES __init__.py files"
fi

echo ""
echo "5. Running quick coverage check..."
poetry run pytest tests/test_cli/agent_test.py --cov=tmux_orchestrator --cov-report=term-missing --no-cov-on-fail -q | tail -5

echo ""
echo "=== Baseline Comparison ==="
echo "Expected: 765 tests"
echo "Current: $COLLECTED"
echo ""

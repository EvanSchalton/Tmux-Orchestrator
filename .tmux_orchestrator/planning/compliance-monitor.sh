#!/bin/bash
# Compliance Monitor - Runs every 30 minutes
# QA Validator automated compliance check

echo "=== Compliance Check $(date) ==="

# Check line length compliance
echo "Line length violations (E501):"
ruff check --select E501 --statistics 2>&1 | grep "E501" || echo "None found"

# Test core CLI commands
echo -e "\nCore CLI Tests:"
echo -n "tmux-orc list: "
tmux-orc list >/dev/null 2>&1 && echo "✅ PASS" || echo "❌ FAIL"

echo -n "tmux-orc context show orc: "
tmux-orc context show orc >/dev/null 2>&1 && echo "✅ PASS" || echo "❌ FAIL"

echo -n "tmux-orc reflect: "
tmux-orc reflect >/dev/null 2>&1 && echo "✅ PASS" || echo "❌ FAIL"

# Check for import errors
echo -e "\nImport chain verification:"
python -c "from tmux_orchestrator.cli import main" 2>&1 && echo "✅ CLI imports OK" || echo "❌ CLI import failed"
python -c "from tmux_orchestrator.mcp_tools import *" 2>&1 && echo "✅ MCP tools OK" || echo "❌ MCP tools failed"

# Run quick test subset
echo -e "\nQuick test check:"
pytest tests/unit/cli/context_test.py -q 2>&1 | tail -5

echo -e "\n=== Check complete at $(date) ==="
echo "Next check in 30 minutes..."

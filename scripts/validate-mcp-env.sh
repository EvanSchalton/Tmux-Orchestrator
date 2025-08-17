#!/bin/bash
# MCP Environment Validation Script

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo "🔍 MCP Development Environment Validation"
echo "========================================"

# Check Python
echo ""
echo "🐍 Python Environment:"
python3 --version
poetry --version

# Check Poetry environment
echo ""
echo "📦 Poetry Environment:"
poetry env info

# Check dependencies
echo ""
echo "📚 Dependencies:"
if poetry run python -c "import fastmcp; print(f'FastMCP: {fastmcp.__version__}')" 2>/dev/null; then
    echo "✅ FastMCP available"
else
    echo "⚠️ FastMCP not available"
fi

if poetry run python -c "import mcp; print(f'MCP: {mcp.__version__}')" 2>/dev/null; then
    echo "✅ MCP available"
else
    echo "❌ MCP not available"
fi

# Check tmux
echo ""
echo "🖥️ tmux:"
tmux -V

# Check MCP structure
echo ""
echo "🏗️ MCP Package Structure:"
poetry run python -c "
from pathlib import Path

structure = {
    'tmux_orchestrator/mcp': 'MCP package',
    'tmux_orchestrator/mcp/tools': 'Tools package',
    'tmux_orchestrator/mcp/handlers': 'Handlers package',
    'tests/mcp': 'Test package'
}

all_good = True
for path, desc in structure.items():
    if Path(path).is_dir():
        print(f'✅ {desc}: {path}')
    else:
        print(f'❌ Missing {desc}: {path}')
        all_good = False

if all_good:
    print('✅ MCP structure complete')
else:
    print('❌ MCP structure incomplete')
    exit(1)
"

# Check Docker (optional)
echo ""
echo "🐳 Docker (optional):"
if command -v docker >/dev/null 2>&1; then
    docker --version
    echo "✅ Docker available"
else
    echo "⚠️ Docker not available (optional)"
fi

echo ""
echo "✅ MCP development environment validation completed"

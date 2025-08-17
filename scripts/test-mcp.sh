#!/bin/bash
# MCP Testing Script for Phase 1 Development

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo "🧪 Running MCP Phase 1 Tests"
echo "============================="

# Run MCP-specific tests
echo "📦 Testing MCP package structure..."
poetry run pytest tests/mcp/ -v --tb=short

echo ""
echo "🔧 Testing FastMCP functionality..."
poetry run python -c "
try:
    import fastmcp
    print('✅ FastMCP available')

    # Test basic functionality
    mcp = fastmcp.FastMCP('test')

    @mcp.tool()
    async def test_tool(param: str) -> str:
        return param

    print('✅ FastMCP tool decorator works')

except ImportError:
    print('⚠️ FastMCP not available - install with: poetry add fastmcp')
except Exception as e:
    print(f'❌ FastMCP test failed: {e}')
"

echo ""
echo "🏗️ Testing MCP structure..."
python3 << 'PYEOF'
from pathlib import Path

required_files = [
    "tmux_orchestrator/mcp/__init__.py",
    "tmux_orchestrator/mcp/tools/__init__.py",
    "tmux_orchestrator/mcp/handlers/__init__.py",
    "tests/mcp/__init__.py"
]

missing = []
for file_path in required_files:
    if not Path(file_path).exists():
        missing.append(file_path)
        print(f"❌ Missing: {file_path}")
    else:
        print(f"✅ Found: {file_path}")

if missing:
    print(f"\n⚠️ {len(missing)} files need to be created")
else:
    print("\n✅ MCP structure complete")
PYEOF

echo ""
echo "✅ MCP testing completed"

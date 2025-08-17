#!/bin/bash
# MCP Development Helper Script

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

show_help() {
    echo "MCP Development Helper"
    echo "===================="
    echo ""
    echo "Usage: $0 <command>"
    echo ""
    echo "Commands:"
    echo "  test          Run MCP tests"
    echo "  install       Install/update FastMCP"
    echo "  validate      Validate MCP structure"
    echo "  docker-test   Run Docker MCP tests"
    echo "  performance   Run performance tests"
    echo "  clean         Clean MCP artifacts"
    echo "  help          Show this help"
}

cmd_test() {
    echo "🧪 Running MCP tests..."
    ./scripts/test-mcp.sh
}

cmd_install() {
    echo "📦 Installing/updating FastMCP..."
    if poetry show fastmcp >/dev/null 2>&1; then
        echo "FastMCP already installed, updating..."
        poetry update fastmcp
    else
        echo "Installing FastMCP..."
        poetry add fastmcp
    fi
    echo "✅ FastMCP installation completed"
}

cmd_validate() {
    echo "🔍 Validating MCP structure..."
    poetry run python -c "
import sys
from pathlib import Path

print('Checking MCP package structure...')

required_dirs = [
    'tmux_orchestrator/mcp',
    'tmux_orchestrator/mcp/tools',
    'tmux_orchestrator/mcp/handlers',
    'tests/mcp'
]

for dir_path in required_dirs:
    if Path(dir_path).is_dir():
        print(f'✅ Directory: {dir_path}')
    else:
        print(f'❌ Missing directory: {dir_path}')
        sys.exit(1)

required_files = [
    'tmux_orchestrator/mcp/__init__.py',
    'tmux_orchestrator/mcp/tools/__init__.py',
    'tmux_orchestrator/mcp/handlers/__init__.py',
    'tests/mcp/__init__.py'
]

for file_path in required_files:
    if Path(file_path).is_file():
        print(f'✅ File: {file_path}')
    else:
        print(f'❌ Missing file: {file_path}')
        sys.exit(1)

print('✅ MCP structure validation passed')
"
}

cmd_docker_test() {
    echo "🐳 Running Docker MCP tests..."
    if command -v docker >/dev/null 2>&1; then
        if [ -f "docker-compose.fastmcp.yml" ]; then
            docker-compose -f docker-compose.fastmcp.yml --profile validate up --abort-on-container-exit
        else
            echo "❌ docker-compose.fastmcp.yml not found"
            exit 1
        fi
    else
        echo "❌ Docker not available"
        exit 1
    fi
}

cmd_performance() {
    echo "⚡ Running MCP performance tests..."
    poetry run python -c "
import asyncio
import time

async def test_performance():
    print('Testing FastMCP performance...')

    try:
        import fastmcp

        start = time.perf_counter()
        mcp = fastmcp.FastMCP('perf-test')

        @mcp.tool()
        async def test_tool(param: str) -> str:
            return param

        duration = time.perf_counter() - start
        print(f'FastMCP setup time: {duration:.3f}s')

        if duration < 0.1:
            print('✅ Performance test PASSED (<0.1s)')
        else:
            print('⚠️ Performance test WARNING (>0.1s)')

    except ImportError:
        print('⚠️ FastMCP not available for performance testing')

asyncio.run(test_performance())
"
}

cmd_clean() {
    echo "🧹 Cleaning MCP artifacts..."
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true
    rm -rf .pytest_cache .mypy_cache 2>/dev/null || true
    echo "✅ MCP artifacts cleaned"
}

# Main command handling
case "${1:-help}" in
    test)
        cmd_test
        ;;
    install)
        cmd_install
        ;;
    validate)
        cmd_validate
        ;;
    docker-test)
        cmd_docker_test
        ;;
    performance)
        cmd_performance
        ;;
    clean)
        cmd_clean
        ;;
    help|*)
        show_help
        ;;
esac

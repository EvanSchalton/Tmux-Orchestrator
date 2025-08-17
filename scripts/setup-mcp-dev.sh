#!/bin/bash
# MCP Development Environment Setup Script
# Quick setup script for MCP Phase 1 development

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Project setup
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🚀 MCP Development Environment Quick Setup"
echo "=========================================="

cd "$PROJECT_DIR"

# Check Poetry environment
log_info "Checking Poetry environment..."
if command -v poetry >/dev/null 2>&1; then
    log_success "Poetry found: $(poetry --version)"
else
    log_error "Poetry not found. Please install Poetry first."
    exit 1
fi

# Install FastMCP dependencies
log_info "Installing FastMCP dependencies..."
poetry install --no-interaction

# Verify FastMCP installation
log_info "Verifying FastMCP installation..."
if poetry run python -c "import fastmcp; print(f'FastMCP {fastmcp.__version__} available')" 2>/dev/null; then
    log_success "FastMCP successfully installed and available"
else
    log_error "FastMCP installation failed"
    exit 1
fi

# Check MCP package structure
log_info "Checking MCP package structure..."
required_dirs=(
    "tmux_orchestrator/mcp"
    "tmux_orchestrator/mcp/tools"
    "tmux_orchestrator/mcp/handlers"
    "tests/mcp"
)

for dir in "${required_dirs[@]}"; do
    if [ -d "$dir" ]; then
        log_success "Directory exists: $dir"
    else
        log_warning "Creating directory: $dir"
        mkdir -p "$dir"
    fi
done

# Create __init__.py files if missing
init_files=(
    "tmux_orchestrator/mcp/__init__.py"
    "tmux_orchestrator/mcp/tools/__init__.py"
    "tmux_orchestrator/mcp/handlers/__init__.py"
    "tests/mcp/__init__.py"
)

for init_file in "${init_files[@]}"; do
    if [ ! -f "$init_file" ]; then
        touch "$init_file"
        log_success "Created: $init_file"
    fi
done

# Run basic MCP validation
log_info "Running MCP validation..."
poetry run python -c "
try:
    import fastmcp
    mcp = fastmcp.FastMCP('dev-test')

    @mcp.tool()
    async def test_tool(param: str) -> str:
        return param

    print('✅ FastMCP tool decorator working')

    # Test MCP package import
    import tmux_orchestrator.mcp
    print('✅ MCP package imports successfully')

except Exception as e:
    print(f'❌ MCP validation failed: {e}')
    exit(1)
"

echo ""
log_success "🎉 MCP development environment ready!"
echo ""
log_info "Available development commands:"
echo "  ./scripts/mcp-dev.sh help          - Show all available commands"
echo "  ./scripts/test-mcp.sh              - Run MCP tests"
echo "  ./scripts/validate-mcp-env.sh      - Validate environment"
echo ""
log_info "FastMCP dependencies:"
echo "  - fastmcp: $(poetry run python -c 'import fastmcp; print(fastmcp.__version__)' 2>/dev/null || echo 'Not available')"
echo "  - mcp: $(poetry run python -c 'import mcp; print(mcp.__version__)' 2>/dev/null || echo 'Not available')"
echo ""
log_success "Ready for Phase 1 FastMCP development! 🚀"

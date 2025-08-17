#!/bin/bash
# FastMCP Development Environment Setup Script
# Sets up complete development environment for FastMCP Phase 1 implementation

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$PROJECT_DIR/setup-fastmcp.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

log_header() {
    echo -e "${PURPLE}[SETUP]${NC} $1" | tee -a "$LOG_FILE"
}

# Check prerequisites
check_prerequisites() {
    log_header "Checking prerequisites for FastMCP development..."

    # Check Python version
    if command -v python3 >/dev/null 2>&1; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        log_success "Python found: $PYTHON_VERSION"

        # Check if Python 3.11+
        if python3 -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)"; then
            log_success "Python version 3.11+ confirmed"
        else
            log_error "Python 3.11+ required for FastMCP. Current: $PYTHON_VERSION"
            exit 1
        fi
    else
        log_error "Python 3 not found. Please install Python 3.11+"
        exit 1
    fi

    # Check Poetry
    if command -v poetry >/dev/null 2>&1; then
        POETRY_VERSION=$(poetry --version | cut -d' ' -f3)
        log_success "Poetry found: $POETRY_VERSION"
    else
        log_error "Poetry not found. Please install Poetry first."
        log_info "Install with: curl -sSL https://install.python-poetry.org | python3 -"
        exit 1
    fi

    # Check tmux
    if command -v tmux >/dev/null 2>&1; then
        TMUX_VERSION=$(tmux -V | cut -d' ' -f2)
        log_success "tmux found: $TMUX_VERSION"
    else
        log_warning "tmux not found. Installing tmux..."
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            sudo apt-get update && sudo apt-get install -y tmux
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            brew install tmux
        else
            log_error "Please install tmux manually for your system"
            exit 1
        fi
        log_success "tmux installed"
    fi

    # Check Docker (optional)
    if command -v docker >/dev/null 2>&1; then
        DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | sed 's/,//')
        log_success "Docker found: $DOCKER_VERSION"
        DOCKER_AVAILABLE=true
    else
        log_warning "Docker not found. Docker tests will be skipped."
        DOCKER_AVAILABLE=false
    fi
}

# Setup MCP directory structure
setup_mcp_structure() {
    log_header "Setting up MCP package structure..."

    cd "$PROJECT_DIR"

    # Create MCP package directories
    MCP_DIRS=(
        "tmux_orchestrator/mcp"
        "tmux_orchestrator/mcp/tools"
        "tmux_orchestrator/mcp/handlers"
        "tests/mcp"
    )

    for dir in "${MCP_DIRS[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            log_success "Created directory: $dir"
        else
            log_info "Directory exists: $dir"
        fi
    done

    # Create __init__.py files
    INIT_FILES=(
        "tmux_orchestrator/mcp/__init__.py"
        "tmux_orchestrator/mcp/tools/__init__.py"
        "tmux_orchestrator/mcp/handlers/__init__.py"
        "tests/mcp/__init__.py"
    )

    for init_file in "${INIT_FILES[@]}"; do
        if [ ! -f "$init_file" ]; then
            touch "$init_file"
            log_success "Created __init__.py: $init_file"
        else
            log_info "__init__.py exists: $init_file"
        fi
    done

    log_success "MCP package structure ready"
}

# Install dependencies
install_dependencies() {
    log_header "Installing dependencies with FastMCP support..."

    cd "$PROJECT_DIR"

    # Install Poetry dependencies
    log_info "Installing Poetry dependencies..."
    poetry install --no-interaction

    # Verify FastMCP installation
    log_info "Verifying FastMCP installation..."
    if poetry run python -c "import fastmcp; print(f'FastMCP {fastmcp.__version__} available')" 2>/dev/null; then
        log_success "FastMCP successfully installed and available"
    else
        log_warning "FastMCP not available - this is expected during early development"
        log_info "Add 'fastmcp = \"^0.4.0\"' to pyproject.toml dependencies when ready"
    fi

    # Install pre-commit hooks
    log_info "Setting up pre-commit hooks..."
    if poetry run pre-commit install; then
        log_success "Pre-commit hooks installed"
    else
        log_warning "Pre-commit hooks setup failed"
    fi
}

# Create development scripts
create_dev_scripts() {
    log_header "Creating FastMCP development scripts..."

    # MCP test runner script
    cat > "$PROJECT_DIR/scripts/test-mcp.sh" << 'EOF'
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
EOF

    chmod +x "$PROJECT_DIR/scripts/test-mcp.sh"
    log_success "Created MCP test script"

    # MCP development helper script
    cat > "$PROJECT_DIR/scripts/mcp-dev.sh" << 'EOF'
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
EOF

    chmod +x "$PROJECT_DIR/scripts/mcp-dev.sh"
    log_success "Created MCP development helper script"
}

# Setup VS Code configuration for MCP development
setup_vscode_config() {
    log_header "Setting up VS Code configuration for MCP development..."

    VSCODE_DIR="$PROJECT_DIR/.vscode"
    mkdir -p "$VSCODE_DIR"

    # Update settings.json for MCP development
    cat > "$VSCODE_DIR/settings.json" << 'EOF'
{
    "python.defaultInterpreterPath": "./.venv/bin/python",
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": [
        "tests/mcp/"
    ],
    "python.linting.enabled": true,
    "python.linting.ruffEnabled": true,
    "python.linting.mypyEnabled": true,
    "python.formatting.provider": "ruff",
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true,
        ".pytest_cache": true,
        ".mypy_cache": true,
        ".ruff_cache": true
    },
    "python.analysis.typeCheckingMode": "basic",
    "python.analysis.autoImportCompletions": true,
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    }
}
EOF

    # Update tasks.json for MCP development
    cat > "$VSCODE_DIR/tasks.json" << 'EOF'
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "MCP: Run Tests",
            "type": "shell",
            "command": "./scripts/test-mcp.sh",
            "group": "test",
            "presentation": {
                "echo": true,
                "reveal": "always",
                "focus": false,
                "panel": "shared"
            },
            "problemMatcher": []
        },
        {
            "label": "MCP: Validate Structure",
            "type": "shell",
            "command": "./scripts/mcp-dev.sh",
            "args": ["validate"],
            "group": "build",
            "presentation": {
                "echo": true,
                "reveal": "always",
                "focus": false,
                "panel": "shared"
            }
        },
        {
            "label": "MCP: Install FastMCP",
            "type": "shell",
            "command": "./scripts/mcp-dev.sh",
            "args": ["install"],
            "group": "build",
            "presentation": {
                "echo": true,
                "reveal": "always",
                "focus": false,
                "panel": "shared"
            }
        },
        {
            "label": "MCP: Performance Test",
            "type": "shell",
            "command": "./scripts/mcp-dev.sh",
            "args": ["performance"],
            "group": "test",
            "presentation": {
                "echo": true,
                "reveal": "always",
                "focus": false,
                "panel": "shared"
            }
        },
        {
            "label": "MCP: Docker Test",
            "type": "shell",
            "command": "./scripts/mcp-dev.sh",
            "args": ["docker-test"],
            "group": "test",
            "presentation": {
                "echo": true,
                "reveal": "always",
                "focus": false,
                "panel": "shared"
            }
        }
    ]
}
EOF

    log_success "VS Code configuration updated for MCP development"
}

# Create MCP environment validation
create_env_validation() {
    log_header "Creating environment validation script..."

    cat > "$PROJECT_DIR/scripts/validate-mcp-env.sh" << 'EOF'
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
EOF

    chmod +x "$PROJECT_DIR/scripts/validate-mcp-env.sh"
    log_success "Created environment validation script"
}

# Main setup function
main() {
    log_header "Starting FastMCP Development Environment Setup"
    echo "Setup log: $LOG_FILE" | tee -a "$LOG_FILE"

    cd "$PROJECT_DIR"

    # Run setup steps
    check_prerequisites
    setup_mcp_structure
    install_dependencies
    create_dev_scripts
    setup_vscode_config
    create_env_validation

    # Final validation
    log_header "Running final environment validation..."
    if ./scripts/validate-mcp-env.sh >> "$LOG_FILE" 2>&1; then
        log_success "Environment validation passed"
    else
        log_warning "Environment validation had issues - check log for details"
    fi

    # Summary
    log_header "FastMCP Development Environment Setup Complete!"
    echo ""
    log_success "🎉 Setup completed successfully!"
    echo ""
    log_info "Next steps for developers:"
    echo "  1. Install FastMCP: ./scripts/mcp-dev.sh install"
    echo "  2. Validate setup: ./scripts/mcp-dev.sh validate"
    echo "  3. Run tests: ./scripts/mcp-dev.sh test"
    echo "  4. Open VS Code and use the configured tasks"
    echo ""
    log_info "Available development commands:"
    echo "  ./scripts/mcp-dev.sh help          - Show all available commands"
    echo "  ./scripts/test-mcp.sh              - Run MCP tests"
    echo "  ./scripts/validate-mcp-env.sh      - Validate environment"
    echo ""
    log_info "VS Code tasks configured for:"
    echo "  - MCP: Run Tests"
    echo "  - MCP: Validate Structure"
    echo "  - MCP: Install FastMCP"
    echo "  - MCP: Performance Test"
    echo "  - MCP: Docker Test"
    echo ""
    if [ "${DOCKER_AVAILABLE:-false}" = "true" ]; then
        log_info "Docker support available:"
        echo "  docker-compose -f docker-compose.fastmcp.yml --profile validate up"
    fi
    echo ""
    log_success "Ready for Phase 1 FastMCP implementation! 🚀"
}

# Run main function
main "$@"

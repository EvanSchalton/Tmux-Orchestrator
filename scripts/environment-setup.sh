#!/bin/bash
# Environment Setup Script - Architecture Neutral
# Sets up development and testing environment regardless of architecture choices

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$PROJECT_DIR/environment-setup.log"

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

# Display usage information
show_usage() {
    cat << EOF
Environment Setup - Architecture Neutral

Usage: $0 <command> [options]

Commands:
  full           Complete environment setup
  python         Setup Python environment
  deps           Install dependencies
  git            Setup Git hooks and configuration
  vscode         Setup VS Code configuration
  docker         Setup Docker environment
  testing        Setup testing infrastructure
  validate       Validate environment setup
  clean          Clean environment artifacts
  help           Show this help message

Options:
  --force        Force reinstallation
  --minimal      Minimal setup (no optional components)
  --dev          Development environment (includes all tools)
  --ci           CI environment (minimal, non-interactive)
  --skip-checks  Skip prerequisite checks

Examples:
  $0 full --dev
  $0 python --force
  $0 testing --minimal
  $0 validate

Environment Variables:
  PYTHON_VERSION    Target Python version (default: 3.11)
  POETRY_VERSION    Target Poetry version (default: 1.6.1)
  SKIP_DOCKER       Skip Docker setup (default: false)
  SETUP_MODE        Setup mode (dev, ci, minimal)
EOF
}

# Check prerequisites
check_prerequisites() {
    log_header "Checking prerequisites..."

    local overall_status=0

    # Check OS
    case "$OSTYPE" in
        linux-gnu*)
            log_success "Operating System: Linux"
            ;;
        darwin*)
            log_success "Operating System: macOS"
            ;;
        msys* | cygwin*)
            log_success "Operating System: Windows (WSL/Git Bash)"
            ;;
        *)
            log_warning "Operating System: Unknown ($OSTYPE)"
            ;;
    esac

    # Check Python
    local python_version="${PYTHON_VERSION:-3.11}"
    if command -v python3 >/dev/null 2>&1; then
        local current_version
        current_version=$(python3 --version | cut -d' ' -f2)
        log_success "Python found: $current_version"

        # Check version compatibility
        if python3 -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)" 2>/dev/null; then
            log_success "Python version compatible (>= 3.11)"
        else
            log_error "Python version incompatible. Need >= 3.11, found: $current_version"
            overall_status=1
        fi
    else
        log_error "Python 3 not found. Please install Python $python_version or higher."
        overall_status=1
    fi

    # Check Git
    if command -v git >/dev/null 2>&1; then
        local git_version
        git_version=$(git --version | cut -d' ' -f3)
        log_success "Git found: $git_version"
    else
        log_error "Git not found. Please install Git."
        overall_status=1
    fi

    # Check curl
    if command -v curl >/dev/null 2>&1; then
        log_success "curl found"
    else
        log_warning "curl not found. Some features may not work."
    fi

    return $overall_status
}

# Setup Python environment
setup_python_environment() {
    log_header "Setting up Python environment..."

    cd "$PROJECT_DIR"

    # Check if Poetry is installed
    if command -v poetry >/dev/null 2>&1; then
        local poetry_version
        poetry_version=$(poetry --version | cut -d' ' -f3)
        log_success "Poetry found: $poetry_version"

        if [[ "${FORCE:-false}" == "true" ]]; then
            log_info "Force flag set, updating Poetry..."
            curl -sSL https://install.python-poetry.org | python3 -
        fi
    else
        log_info "Installing Poetry..."
        curl -sSL https://install.python-poetry.org | python3 -

        # Add Poetry to PATH for this session
        export PATH="$HOME/.local/bin:$PATH"

        if command -v poetry >/dev/null 2>&1; then
            log_success "Poetry installed successfully"
        else
            log_error "Poetry installation failed"
            return 1
        fi
    fi

    # Configure Poetry
    log_info "Configuring Poetry..."
    poetry config virtualenvs.in-project true
    poetry config virtualenvs.create true

    # Install dependencies
    log_info "Installing Python dependencies..."
    if poetry install --no-interaction; then
        log_success "Dependencies installed successfully"
    else
        log_error "Dependency installation failed"
        return 1
    fi

    # Verify installation
    log_info "Verifying Python environment..."
    if poetry run python --version >/dev/null 2>&1; then
        local venv_python
        venv_python=$(poetry run python --version)
        log_success "Virtual environment ready: $venv_python"
    else
        log_error "Virtual environment verification failed"
        return 1
    fi
}

# Install dependencies
install_dependencies() {
    log_header "Installing dependencies..."

    cd "$PROJECT_DIR"

    # Install Poetry dependencies
    log_info "Installing Poetry dependencies..."
    if poetry install --no-interaction; then
        log_success "Poetry dependencies installed"
    else
        log_error "Poetry dependency installation failed"
        return 1
    fi

    # Install system dependencies based on OS
    if [[ "${SKIP_SYSTEM:-false}" != "true" ]]; then
        log_info "Installing system dependencies..."

        case "$OSTYPE" in
            linux-gnu*)
                # Ubuntu/Debian
                if command -v apt-get >/dev/null 2>&1; then
                    sudo apt-get update
                    sudo apt-get install -y tmux build-essential curl git
                # CentOS/RHEL
                elif command -v yum >/dev/null 2>&1; then
                    sudo yum install -y tmux gcc gcc-c++ make curl git
                # Arch Linux
                elif command -v pacman >/dev/null 2>&1; then
                    sudo pacman -S --noconfirm tmux base-devel curl git
                fi
                ;;
            darwin*)
                # macOS with Homebrew
                if command -v brew >/dev/null 2>&1; then
                    brew install tmux
                else
                    log_warning "Homebrew not found. Please install tmux manually."
                fi
                ;;
        esac

        log_success "System dependencies processed"
    fi
}

# Setup Git hooks and configuration
setup_git() {
    log_header "Setting up Git configuration..."

    cd "$PROJECT_DIR"

    # Install pre-commit hooks
    if command -v poetry >/dev/null 2>&1; then
        log_info "Installing pre-commit hooks..."
        if poetry run pre-commit install; then
            log_success "Pre-commit hooks installed"
        else
            log_warning "Pre-commit hooks installation failed"
        fi
    fi

    # Setup Git configuration for project
    log_info "Configuring Git for project..."

    # Set up commit message template if it doesn't exist
    if [ ! -f ".gitmessage" ]; then
        cat > ".gitmessage" << 'EOF'
# Title: Summary, imperative, start upper case, don't end with a period
# No more than 50 chars. #### 50 chars is here: #

# Remember blank line between title and body.

# Body: Explain *what* and *why* (not *how*). Include task ID (Jira issue).
# Wrap at 72 chars. ################################## which is here: #


# At the end: Include Signed-off-by and GitHub/GitLab closes/fixes line
# Example:
# Signed-off-by: Your Name <your.email@example.com>
# Closes #123
EOF
        git config commit.template .gitmessage
        log_success "Git commit template configured"
    fi

    # Configure Git hooks path
    if [ -d ".githooks" ]; then
        git config core.hooksPath .githooks
        log_success "Git hooks path configured"
    fi

    log_success "Git configuration completed"
}

# Setup VS Code configuration
setup_vscode() {
    log_header "Setting up VS Code configuration..."

    cd "$PROJECT_DIR"

    local vscode_dir=".vscode"
    mkdir -p "$vscode_dir"

    # Create settings.json
    cat > "$vscode_dir/settings.json" << 'EOF'
{
    "python.defaultInterpreterPath": "./.venv/bin/python",
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": [
        "tests/"
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
        ".ruff_cache": true,
        ".venv": true
    },
    "python.analysis.typeCheckingMode": "basic",
    "python.analysis.autoImportCompletions": true,
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    },
    "files.associations": {
        "*.yml": "yaml",
        "*.yaml": "yaml",
        "Dockerfile*": "dockerfile",
        "docker-compose*.yml": "yaml"
    }
}
EOF

    # Create tasks.json
    cat > "$vscode_dir/tasks.json" << 'EOF'
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "Run Tests",
            "type": "shell",
            "command": "./scripts/test-runner.sh",
            "args": ["all", "--coverage"],
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
            "label": "Run Unit Tests",
            "type": "shell",
            "command": "./scripts/test-runner.sh",
            "args": ["unit", "--verbose"],
            "group": "test",
            "presentation": {
                "echo": true,
                "reveal": "always",
                "focus": false,
                "panel": "shared"
            }
        },
        {
            "label": "Code Quality Check",
            "type": "shell",
            "command": "./scripts/test-runner.sh",
            "args": ["quality"],
            "group": "build",
            "presentation": {
                "echo": true,
                "reveal": "always",
                "focus": false,
                "panel": "shared"
            }
        },
        {
            "label": "Docker: Build Images",
            "type": "shell",
            "command": "./scripts/container-manager.sh",
            "args": ["build"],
            "group": "build",
            "presentation": {
                "echo": true,
                "reveal": "always",
                "focus": false,
                "panel": "shared"
            }
        },
        {
            "label": "Docker: Run Tests",
            "type": "shell",
            "command": "./scripts/container-manager.sh",
            "args": ["test", "--profile=full-testing"],
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

    # Create launch.json for debugging
    cat > "$vscode_dir/launch.json" << 'EOF'
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Current File",
            "type": "python",
            "request": "launch",
            "program": "${file}",
            "console": "integratedTerminal",
            "python": "./.venv/bin/python"
        },
        {
            "name": "Python: pytest",
            "type": "python",
            "request": "launch",
            "module": "pytest",
            "args": ["${workspaceFolder}/tests/"],
            "console": "integratedTerminal",
            "python": "./.venv/bin/python"
        },
        {
            "name": "CLI: tmux-orc",
            "type": "python",
            "request": "launch",
            "module": "tmux_orchestrator.cli",
            "args": ["--help"],
            "console": "integratedTerminal",
            "python": "./.venv/bin/python"
        }
    ]
}
EOF

    log_success "VS Code configuration created"
}

# Setup Docker environment
setup_docker() {
    log_header "Setting up Docker environment..."

    if [[ "${SKIP_DOCKER:-false}" == "true" ]]; then
        log_info "Skipping Docker setup (SKIP_DOCKER=true)"
        return 0
    fi

    # Check Docker availability
    if ! command -v docker >/dev/null 2>&1; then
        log_warning "Docker not found. Skipping Docker setup."
        return 0
    fi

    cd "$PROJECT_DIR"

    # Validate Docker compose files
    local compose_files=("docker-compose.testing.yml" "docker-compose.multi-agent.yml")

    for compose_file in "${compose_files[@]}"; do
        if [ -f "$compose_file" ]; then
            log_info "Validating: $compose_file"
            if docker-compose -f "$compose_file" config >/dev/null 2>&1; then
                log_success "Valid: $compose_file"
            else
                log_error "Invalid: $compose_file"
                return 1
            fi
        fi
    done

    # Build base images if requested
    if [[ "${BUILD_IMAGES:-false}" == "true" ]]; then
        log_info "Building Docker images..."
        if [ -f "Dockerfile.testing" ]; then
            docker build -f Dockerfile.testing -t tmux-orchestrator-testing .
            log_success "Built testing image"
        fi
    fi

    log_success "Docker environment ready"
}

# Setup testing infrastructure
setup_testing() {
    log_header "Setting up testing infrastructure..."

    cd "$PROJECT_DIR"

    # Create test directories
    local test_dirs=(
        "tests/core"
        "tests/integration"
        "tests/security"
        "tests/benchmarks"
        "test-results"
        "test-logs"
    )

    for dir in "${test_dirs[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            log_success "Created: $dir"
        fi
    done

    # Create pytest configuration if it doesn't exist
    if [ ! -f "pytest.ini" ]; then
        cat > "pytest.ini" << 'EOF'
[tool:pytest]
testpaths = tests
python_files = test_*.py *_test.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --tb=short
    --strict-markers
    --strict-config
    --disable-warnings
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    security: marks tests as security tests
    performance: marks tests as performance tests
    unit: marks tests as unit tests
filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
EOF
        log_success "Created pytest.ini"
    fi

    # Make test scripts executable
    local scripts=("test-runner.sh" "container-manager.sh")
    for script in "${scripts[@]}"; do
        if [ -f "scripts/$script" ]; then
            chmod +x "scripts/$script"
            log_success "Made executable: scripts/$script"
        fi
    done

    log_success "Testing infrastructure ready"
}

# Validate environment setup
validate_environment() {
    log_header "Validating environment setup..."

    cd "$PROJECT_DIR"

    local overall_status=0

    # Check Python environment
    log_info "Checking Python environment..."
    if poetry run python --version >/dev/null 2>&1; then
        log_success "Python environment: OK"
    else
        log_error "Python environment: FAILED"
        overall_status=1
    fi

    # Check dependencies
    log_info "Checking dependencies..."
    if poetry run python -c "import tmux_orchestrator" 2>/dev/null; then
        log_success "Project imports: OK"
    else
        log_error "Project imports: FAILED"
        overall_status=1
    fi

    # Check test runner
    log_info "Checking test runner..."
    if [ -x "scripts/test-runner.sh" ]; then
        log_success "Test runner: OK"
    else
        log_error "Test runner: FAILED"
        overall_status=1
    fi

    # Check container manager
    log_info "Checking container manager..."
    if [ -x "scripts/container-manager.sh" ]; then
        log_success "Container manager: OK"
    else
        log_error "Container manager: FAILED"
        overall_status=1
    fi

    # Run quick test
    log_info "Running quick validation test..."
    if poetry run python -c "print('Environment validation: PASSED')"; then
        log_success "Quick test: PASSED"
    else
        log_error "Quick test: FAILED"
        overall_status=1
    fi

    if [ $overall_status -eq 0 ]; then
        log_success "Environment validation: ALL CHECKS PASSED"
    else
        log_error "Environment validation: SOME CHECKS FAILED"
    fi

    return $overall_status
}

# Clean environment artifacts
clean_environment() {
    log_header "Cleaning environment artifacts..."

    cd "$PROJECT_DIR"

    # Remove Python cache
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true

    # Remove test artifacts
    rm -rf .pytest_cache .mypy_cache .ruff_cache 2>/dev/null || true
    rm -rf htmlcov/ .coverage 2>/dev/null || true

    # Clean logs and results
    rm -rf test-logs/* test-results/* 2>/dev/null || true

    # Clean Poetry cache
    poetry cache clear --all pypi 2>/dev/null || true

    log_success "Environment artifacts cleaned"
}

# Parse command line options
parse_options() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --force)
                export FORCE=true
                ;;
            --minimal)
                export SETUP_MODE=minimal
                ;;
            --dev)
                export SETUP_MODE=dev
                ;;
            --ci)
                export SETUP_MODE=ci
                ;;
            --skip-checks)
                export SKIP_CHECKS=true
                ;;
            --skip-docker)
                export SKIP_DOCKER=true
                ;;
            --build-images)
                export BUILD_IMAGES=true
                ;;
            *)
                log_warning "Unknown option: $1"
                ;;
        esac
        shift
    done
}

# Main execution logic
main() {
    case "${1:-help}" in
        full)
            shift
            parse_options "$@"
            if [[ "${SKIP_CHECKS:-false}" != "true" ]]; then
                check_prerequisites || exit 1
            fi
            setup_python_environment && \
            install_dependencies && \
            setup_git && \
            setup_vscode && \
            setup_docker && \
            setup_testing && \
            validate_environment
            ;;
        python)
            shift
            parse_options "$@"
            setup_python_environment
            ;;
        deps)
            shift
            parse_options "$@"
            install_dependencies
            ;;
        git)
            shift
            parse_options "$@"
            setup_git
            ;;
        vscode)
            shift
            parse_options "$@"
            setup_vscode
            ;;
        docker)
            shift
            parse_options "$@"
            setup_docker
            ;;
        testing)
            shift
            parse_options "$@"
            setup_testing
            ;;
        validate)
            shift
            parse_options "$@"
            validate_environment
            ;;
        clean)
            shift
            parse_options "$@"
            clean_environment
            ;;
        help)
            show_usage
            ;;
        *)
            echo "Unknown command: $1"
            show_usage
            exit 1
            ;;
    esac
}

# Initialize logging
echo "$(date): Environment setup started" > "$LOG_FILE"

# Run main function with all arguments
main "$@"

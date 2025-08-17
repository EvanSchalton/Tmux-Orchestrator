#!/bin/bash
# Generic Test Runner Script - Architecture Neutral
# Provides standardized testing interface regardless of underlying architecture

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/test-logs"
RESULTS_DIR="$PROJECT_DIR/test-results"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_DIR/test-runner.log"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_DIR/test-runner.log"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_DIR/test-runner.log"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_DIR/test-runner.log"
}

log_header() {
    echo -e "${PURPLE}[TEST]${NC} $1" | tee -a "$LOG_DIR/test-runner.log"
}

# Initialize directories
init_test_environment() {
    mkdir -p "$LOG_DIR" "$RESULTS_DIR"
    log_info "Test environment initialized"
    log_info "Logs: $LOG_DIR"
    log_info "Results: $RESULTS_DIR"
}

# Display usage information
show_usage() {
    cat << EOF
Generic Test Runner - Architecture Neutral

Usage: $0 <command> [options]

Commands:
  unit           Run unit tests
  integration    Run integration tests
  security       Run security tests
  performance    Run performance tests
  quality        Run code quality checks
  all            Run all test suites
  docker         Run tests in Docker containers
  continuous     Run tests in watch mode
  clean          Clean test artifacts
  report         Generate test reports
  validate       Validate test environment
  help           Show this help message

Options:
  --verbose      Verbose output
  --quiet        Minimal output
  --parallel     Run tests in parallel
  --coverage     Generate coverage reports
  --timeout=N    Set test timeout (seconds)
  --output=DIR   Custom output directory

Examples:
  $0 unit --coverage
  $0 all --parallel --verbose
  $0 docker --profile performance-testing
  $0 performance --timeout=300

Environment Variables:
  TEST_ENV       Test environment (dev, ci, local)
  PYTEST_ARGS    Additional pytest arguments
  DOCKER_COMPOSE Docker compose file to use
EOF
}

# Validate test environment
validate_environment() {
    log_header "Validating test environment..."

    # Check Python version
    if command -v python3 >/dev/null 2>&1; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        log_success "Python found: $PYTHON_VERSION"
    else
        log_error "Python 3 not found"
        return 1
    fi

    # Check Poetry
    if command -v poetry >/dev/null 2>&1; then
        POETRY_VERSION=$(poetry --version | cut -d' ' -f3)
        log_success "Poetry found: $POETRY_VERSION"
    else
        log_error "Poetry not found"
        return 1
    fi

    # Check test directories
    test_dirs=("tests/core" "tests/integration" "tests/security" "tests/benchmarks")
    for dir in "${test_dirs[@]}"; do
        if [ -d "$PROJECT_DIR/$dir" ]; then
            log_success "Test directory exists: $dir"
        else
            log_warning "Test directory missing: $dir"
            mkdir -p "$PROJECT_DIR/$dir"
            log_info "Created: $dir"
        fi
    done

    # Check test configuration
    if [ -f "$PROJECT_DIR/pytest.ini" ]; then
        log_success "pytest.ini found"
    else
        log_warning "pytest.ini not found"
    fi

    log_success "Environment validation completed"
}

# Run unit tests
run_unit_tests() {
    log_header "Running unit tests..."

    cd "$PROJECT_DIR"

    local pytest_args="${PYTEST_ARGS:-} -v --tb=short"
    if [[ "${COVERAGE:-false}" == "true" ]]; then
        pytest_args="$pytest_args --cov=tmux_orchestrator --cov-report=html --cov-report=term"
    fi

    if [[ "${PARALLEL:-false}" == "true" ]]; then
        pytest_args="$pytest_args -n auto"
    fi

    local timeout="${TIMEOUT:-300}"
    pytest_args="$pytest_args --timeout=$timeout"

    log_info "Running: poetry run pytest tests/core/ $pytest_args"

    if poetry run pytest tests/core/ $pytest_args --junitxml="$RESULTS_DIR/unit-tests.xml"; then
        log_success "Unit tests passed"
        return 0
    else
        log_error "Unit tests failed"
        return 1
    fi
}

# Run integration tests
run_integration_tests() {
    log_header "Running integration tests..."

    cd "$PROJECT_DIR"

    # Check system dependencies
    if ! command -v tmux >/dev/null 2>&1; then
        log_error "tmux not found - required for integration tests"
        return 1
    fi

    local pytest_args="${PYTEST_ARGS:-} -v --tb=short"
    local timeout="${TIMEOUT:-600}"
    pytest_args="$pytest_args --timeout=$timeout"

    log_info "Running: poetry run pytest tests/integration/ $pytest_args"

    if poetry run pytest tests/integration/ $pytest_args --junitxml="$RESULTS_DIR/integration-tests.xml"; then
        log_success "Integration tests passed"
        return 0
    else
        log_error "Integration tests failed"
        return 1
    fi
}

# Run security tests
run_security_tests() {
    log_header "Running security tests..."

    cd "$PROJECT_DIR"

    # Run pytest security tests
    local pytest_args="${PYTEST_ARGS:-} -v --tb=short"
    log_info "Running security test suite..."

    if poetry run pytest tests/security/ $pytest_args --junitxml="$RESULTS_DIR/security-tests.xml"; then
        log_success "Security tests passed"
    else
        log_error "Security tests failed"
        return 1
    fi

    # Run bandit security analysis
    log_info "Running bandit security analysis..."
    if poetry run bandit -r tmux_orchestrator/ -f json -o "$RESULTS_DIR/bandit-report.json"; then
        log_success "Bandit analysis completed"
    else
        log_warning "Bandit analysis found issues"
    fi

    # Display summary
    poetry run bandit -r tmux_orchestrator/ -f txt

    log_success "Security testing completed"
}

# Run performance tests
run_performance_tests() {
    log_header "Running performance tests..."

    cd "$PROJECT_DIR"

    local pytest_args="${PYTEST_ARGS:-} -v --tb=short"
    local timeout="${TIMEOUT:-1200}"
    pytest_args="$pytest_args --timeout=$timeout"

    # Performance validation
    log_info "Validating performance requirements..."

    # Test CLI startup time
    log_info "Testing CLI startup performance..."
    start_time=$(date +%s.%N)
    poetry run tmux-orc --help > /dev/null 2>&1
    end_time=$(date +%s.%N)
    duration=$(echo "$end_time - $start_time" | bc)

    log_info "CLI startup time: ${duration}s"
    if (( $(echo "$duration < 1.0" | bc -l) )); then
        log_success "CLI startup performance: PASSED (<1s)"
    else
        log_warning "CLI startup performance: SLOW (${duration}s)"
    fi

    # Run performance test suite
    log_info "Running performance test suite..."
    if poetry run pytest tests/benchmarks/ $pytest_args --junitxml="$RESULTS_DIR/performance-tests.xml"; then
        log_success "Performance tests passed"
        return 0
    else
        log_error "Performance tests failed"
        return 1
    fi
}

# Run code quality checks
run_quality_checks() {
    log_header "Running code quality checks..."

    cd "$PROJECT_DIR"

    local overall_status=0

    # Black formatting check
    log_info "Checking code formatting with Black..."
    if poetry run black --check tmux_orchestrator/ tests/; then
        log_success "Black formatting: PASSED"
    else
        log_error "Black formatting: FAILED"
        overall_status=1
    fi

    # Ruff linting
    log_info "Running linting with Ruff..."
    if poetry run ruff check tmux_orchestrator/ tests/; then
        log_success "Ruff linting: PASSED"
    else
        log_error "Ruff linting: FAILED"
        overall_status=1
    fi

    # Import sorting
    log_info "Checking import sorting with isort..."
    if poetry run isort --check-only tmux_orchestrator/ tests/; then
        log_success "Import sorting: PASSED"
    else
        log_error "Import sorting: FAILED"
        overall_status=1
    fi

    # Type checking
    log_info "Running type checking with mypy..."
    if poetry run mypy tmux_orchestrator/ --ignore-missing-imports; then
        log_success "Type checking: PASSED"
    else
        log_warning "Type checking: ISSUES FOUND"
    fi

    if [ $overall_status -eq 0 ]; then
        log_success "Code quality checks passed"
    else
        log_error "Code quality checks failed"
    fi

    return $overall_status
}

# Run Docker-based tests
run_docker_tests() {
    log_header "Running Docker-based tests..."

    local profile="${1:-full-testing}"
    local compose_file="${DOCKER_COMPOSE:-docker-compose.testing.yml}"

    if [ ! -f "$PROJECT_DIR/$compose_file" ]; then
        log_error "Docker compose file not found: $compose_file"
        return 1
    fi

    log_info "Using Docker compose profile: $profile"
    log_info "Compose file: $compose_file"

    cd "$PROJECT_DIR"

    if docker-compose -f "$compose_file" --profile "$profile" up --abort-on-container-exit; then
        log_success "Docker tests completed successfully"
        return 0
    else
        log_error "Docker tests failed"
        return 1
    fi
}

# Generate test reports
generate_reports() {
    log_header "Generating test reports..."

    cd "$PROJECT_DIR"

    # Install reporting dependencies if needed
    if ! poetry run python -c "import pytest_html" 2>/dev/null; then
        log_info "Installing pytest-html for reporting..."
        poetry add --group dev pytest-html pytest-json-report
    fi

    # Generate comprehensive reports
    local pytest_args="--html=$RESULTS_DIR/report.html --json-report --json-report-file=$RESULTS_DIR/report.json"
    pytest_args="$pytest_args --cov=tmux_orchestrator --cov-report=html:$RESULTS_DIR/coverage"
    pytest_args="$pytest_args --junitxml=$RESULTS_DIR/junit.xml"

    log_info "Generating comprehensive test reports..."
    poetry run pytest tests/ $pytest_args -v

    log_success "Test reports generated in: $RESULTS_DIR"
    log_info "HTML Report: $RESULTS_DIR/report.html"
    log_info "Coverage Report: $RESULTS_DIR/coverage/index.html"
    log_info "JSON Report: $RESULTS_DIR/report.json"
}

# Clean test artifacts
clean_artifacts() {
    log_header "Cleaning test artifacts..."

    cd "$PROJECT_DIR"

    # Remove Python cache
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true

    # Remove test artifacts
    rm -rf .pytest_cache .mypy_cache .ruff_cache 2>/dev/null || true
    rm -rf htmlcov/ .coverage 2>/dev/null || true

    # Clean result directories
    if [ -d "$RESULTS_DIR" ]; then
        rm -rf "$RESULTS_DIR"/*
        log_success "Test results cleaned"
    fi

    if [ -d "$LOG_DIR" ]; then
        rm -rf "$LOG_DIR"/*
        log_success "Test logs cleaned"
    fi

    log_success "Test artifacts cleaned"
}

# Run continuous testing
run_continuous_tests() {
    log_header "Starting continuous testing (watch mode)..."

    cd "$PROJECT_DIR"

    # Install pytest-watch if needed
    if ! poetry run python -c "import pytest_watch" 2>/dev/null; then
        log_info "Installing pytest-watch for continuous testing..."
        poetry add --group dev pytest-watch
    fi

    log_info "Watching for file changes..."
    log_info "Press Ctrl+C to stop"

    poetry run ptw -- -v --tb=short
}

# Main execution logic
main() {
    init_test_environment

    case "${1:-help}" in
        unit)
            shift
            parse_options "$@"
            run_unit_tests
            ;;
        integration)
            shift
            parse_options "$@"
            run_integration_tests
            ;;
        security)
            shift
            parse_options "$@"
            run_security_tests
            ;;
        performance)
            shift
            parse_options "$@"
            run_performance_tests
            ;;
        quality)
            shift
            parse_options "$@"
            run_quality_checks
            ;;
        all)
            shift
            parse_options "$@"
            log_header "Running all test suites..."
            run_unit_tests && \
            run_integration_tests && \
            run_security_tests && \
            run_performance_tests && \
            run_quality_checks
            ;;
        docker)
            shift
            local profile="${1:-full-testing}"
            run_docker_tests "$profile"
            ;;
        continuous)
            shift
            parse_options "$@"
            run_continuous_tests
            ;;
        report)
            shift
            parse_options "$@"
            generate_reports
            ;;
        clean)
            clean_artifacts
            ;;
        validate)
            validate_environment
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

# Parse command line options
parse_options() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --verbose)
                export VERBOSE=true
                ;;
            --quiet)
                export QUIET=true
                ;;
            --parallel)
                export PARALLEL=true
                ;;
            --coverage)
                export COVERAGE=true
                ;;
            --timeout=*)
                export TIMEOUT="${1#*=}"
                ;;
            --output=*)
                RESULTS_DIR="${1#*=}"
                ;;
            *)
                # Unknown option, pass to pytest
                export PYTEST_ARGS="${PYTEST_ARGS:-} $1"
                ;;
        esac
        shift
    done
}

# Run main function with all arguments
main "$@"

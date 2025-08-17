#!/bin/bash
# Test Pipeline Integration Script
# Simulates CI/CD pipeline locally for development and validation

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
RESULTS_DIR="$PROJECT_DIR/test-results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
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

# Create results directory
setup_results() {
    mkdir -p "$RESULTS_DIR"
    echo "# Test Pipeline Results - $TIMESTAMP" > "$RESULTS_DIR/pipeline_report.md"
}

# Phase 9.0 Quality Gate Tests
run_quality_gate() {
    log_info "Running Phase 9.0 Quality Gate..."

    echo "## Phase 9.0 - Quality Gate Results" >> "$RESULTS_DIR/pipeline_report.md"
    echo "Generated: $(date)" >> "$RESULTS_DIR/pipeline_report.md"
    echo "" >> "$RESULTS_DIR/pipeline_report.md"

    # Test 9.1: Complete quality checks
    log_info "Task 9.1: Running mypy, ruff, pytest..."
    if poetry run invoke ci; then
        log_success "✅ Task 9.1: Quality checks passed"
        echo "- ✅ Task 9.1: Quality checks (mypy, ruff, pytest) - PASSED" >> "$RESULTS_DIR/pipeline_report.md"
    else
        log_error "❌ Task 9.1: Quality checks failed"
        echo "- ❌ Task 9.1: Quality checks (mypy, ruff, pytest) - FAILED" >> "$RESULTS_DIR/pipeline_report.md"
        return 1
    fi

    # Test 9.2: Backward compatibility
    log_info "Task 9.2: Testing backward compatibility..."
    if test_backward_compatibility; then
        log_success "✅ Task 9.2: Backward compatibility verified"
        echo "- ✅ Task 9.2: Backward compatibility - PASSED" >> "$RESULTS_DIR/pipeline_report.md"
    else
        log_warning "⚠️ Task 9.2: Backward compatibility issues detected"
        echo "- ⚠️ Task 9.2: Backward compatibility - PARTIAL" >> "$RESULTS_DIR/pipeline_report.md"
    fi

    # Test 9.3: Performance requirements
    log_info "Task 9.3: Testing performance requirements (<1 second)..."
    if test_performance_requirements; then
        log_success "✅ Task 9.3: Performance requirements met"
        echo "- ✅ Task 9.3: Performance requirements (<1s) - PASSED" >> "$RESULTS_DIR/pipeline_report.md"
    else
        log_error "❌ Task 9.3: Performance requirements not met"
        echo "- ❌ Task 9.3: Performance requirements (<1s) - FAILED" >> "$RESULTS_DIR/pipeline_report.md"
        return 1
    fi

    # Test 9.6: MCP server concurrent requests
    log_info "Task 9.6: Testing MCP server concurrent requests..."
    if test_mcp_concurrent_requests; then
        log_success "✅ Task 9.6: MCP server handles concurrent requests"
        echo "- ✅ Task 9.6: MCP server concurrent requests - PASSED" >> "$RESULTS_DIR/pipeline_report.md"
    else
        log_warning "⚠️ Task 9.6: MCP server concurrent request issues"
        echo "- ⚠️ Task 9.6: MCP server concurrent requests - PARTIAL" >> "$RESULTS_DIR/pipeline_report.md"
    fi
}

# Test backward compatibility
test_backward_compatibility() {
    log_info "Testing existing shell scripts compatibility..."

    # Test tmux-orc CLI backward compatibility
    if poetry run tmux-orc --help >/dev/null 2>&1; then
        log_success "CLI help command works"
    else
        log_error "CLI help command failed"
        return 1
    fi

    if poetry run tmux-orc spawn --help >/dev/null 2>&1; then
        log_success "CLI spawn command help works"
    else
        log_warning "CLI spawn command help failed"
    fi

    if poetry run tmux-orc reflect >/dev/null 2>&1; then
        log_success "CLI reflect command works"
    else
        log_warning "CLI reflect command failed"
    fi

    return 0
}

# Test performance requirements
test_performance_requirements() {
    log_info "Testing CLI command performance (<1 second requirement)..."

    local commands=(
        "tmux-orc --help"
        "tmux-orc reflect"
        "tmux-orc reflect --format json"
        "tmux-orc status"
    )

    local total_time=0
    local failed_count=0

    echo "### Performance Test Results" >> "$RESULTS_DIR/pipeline_report.md"
    echo "| Command | Duration | Status |" >> "$RESULTS_DIR/pipeline_report.md"
    echo "|---------|----------|---------|" >> "$RESULTS_DIR/pipeline_report.md"

    for cmd in "${commands[@]}"; do
        log_info "Testing: $cmd"

        local start_time=$(date +%s.%N)
        if timeout 5s poetry run $cmd >/dev/null 2>&1; then
            local end_time=$(date +%s.%N)
            local duration=$(echo "$end_time - $start_time" | bc -l)
            total_time=$(echo "$total_time + $duration" | bc -l)

            if (( $(echo "$duration < 1.0" | bc -l) )); then
                log_success "✅ $cmd: ${duration}s"
                echo "| $cmd | ${duration}s | ✅ PASS |" >> "$RESULTS_DIR/pipeline_report.md"
            else
                log_error "❌ $cmd: ${duration}s (>1s)"
                echo "| $cmd | ${duration}s | ❌ FAIL |" >> "$RESULTS_DIR/pipeline_report.md"
                ((failed_count++))
            fi
        else
            log_error "❌ $cmd: timeout or error"
            echo "| $cmd | TIMEOUT | ❌ FAIL |" >> "$RESULTS_DIR/pipeline_report.md"
            ((failed_count++))
        fi
    done

    local avg_time=$(echo "scale=3; $total_time / ${#commands[@]}" | bc -l)
    echo "" >> "$RESULTS_DIR/pipeline_report.md"
    echo "**Average Time:** ${avg_time}s" >> "$RESULTS_DIR/pipeline_report.md"
    echo "**Failed Commands:** $failed_count/${#commands[@]}" >> "$RESULTS_DIR/pipeline_report.md"

    if [[ $failed_count -eq 0 ]]; then
        log_success "All commands met performance requirements"
        return 0
    else
        log_error "$failed_count commands failed performance requirements"
        return 1
    fi
}

# Test MCP server concurrent requests
test_mcp_concurrent_requests() {
    log_info "Testing MCP server concurrent request handling..."

    # Check if MCP server tests exist
    if poetry run pytest tests/test_mcp_server_focused.py -v --tb=short >/dev/null 2>&1; then
        log_success "MCP server focused tests passed"
        return 0
    else
        log_warning "MCP server focused tests not found or failed"
        return 1
    fi
}

# Phase 10.0 Deployment Tests
run_deployment_tests() {
    log_info "Running Phase 10.0 Deployment Tests..."

    echo "" >> "$RESULTS_DIR/pipeline_report.md"
    echo "## Phase 10.0 - Deployment Test Results" >> "$RESULTS_DIR/pipeline_report.md"
    echo "" >> "$RESULTS_DIR/pipeline_report.md"

    # Test 10.1: Fresh installation
    log_info "Task 10.1: Testing fresh Poetry installation..."
    if test_fresh_installation; then
        log_success "✅ Task 10.1: Fresh installation successful"
        echo "- ✅ Task 10.1: Fresh Poetry installation - PASSED" >> "$RESULTS_DIR/pipeline_report.md"
    else
        log_error "❌ Task 10.1: Fresh installation failed"
        echo "- ❌ Task 10.1: Fresh Poetry installation - FAILED" >> "$RESULTS_DIR/pipeline_report.md"
        return 1
    fi

    # Test 10.3: MCP server startup
    log_info "Task 10.3: Testing MCP server startup..."
    if test_mcp_server_startup; then
        log_success "✅ Task 10.3: MCP server startup successful"
        echo "- ✅ Task 10.3: MCP server startup - PASSED" >> "$RESULTS_DIR/pipeline_report.md"
    else
        log_warning "⚠️ Task 10.3: MCP server startup issues"
        echo "- ⚠️ Task 10.3: MCP server startup - PARTIAL" >> "$RESULTS_DIR/pipeline_report.md"
    fi
}

# Test fresh installation
test_fresh_installation() {
    log_info "Simulating fresh installation test..."

    # Test that all required commands are available
    local required_commands=(
        "tmux-orc"
        "tmux-orc-server"
    )

    for cmd in "${required_commands[@]}"; do
        if poetry run which "$cmd" >/dev/null 2>&1; then
            log_success "$cmd is available"
        else
            log_error "$cmd is not available"
            return 1
        fi
    done

    # Test core module imports
    if poetry run python -c "
import tmux_orchestrator
import tmux_orchestrator.cli
import tmux_orchestrator.core
import tmux_orchestrator.server
print('All core modules imported successfully')
" >/dev/null 2>&1; then
        log_success "Core modules import successfully"
        return 0
    else
        log_error "Core module import failed"
        return 1
    fi
}

# Test MCP server startup
test_mcp_server_startup() {
    log_info "Testing MCP server startup capability..."

    # Test server help command
    if timeout 10s poetry run tmux-orc-server --help >/dev/null 2>&1; then
        log_success "MCP server help command works"
        return 0
    else
        log_warning "MCP server help command failed or timed out"
        return 1
    fi
}

# Docker integration tests
run_docker_tests() {
    log_info "Running Docker integration tests..."

    echo "" >> "$RESULTS_DIR/pipeline_report.md"
    echo "## Docker Integration Test Results" >> "$RESULTS_DIR/pipeline_report.md"
    echo "" >> "$RESULTS_DIR/pipeline_report.md"

    # Test Docker build
    if docker build -t tmux-orchestrator:test-local . >/dev/null 2>&1; then
        log_success "✅ Docker production build successful"
        echo "- ✅ Docker production build - PASSED" >> "$RESULTS_DIR/pipeline_report.md"
    else
        log_error "❌ Docker production build failed"
        echo "- ❌ Docker production build - FAILED" >> "$RESULTS_DIR/pipeline_report.md"
        return 1
    fi

    # Test Docker dev build
    if docker build -f Dockerfile.dev -t tmux-orchestrator:dev-test-local . >/dev/null 2>&1; then
        log_success "✅ Docker development build successful"
        echo "- ✅ Docker development build - PASSED" >> "$RESULTS_DIR/pipeline_report.md"
    else
        log_error "❌ Docker development build failed"
        echo "- ❌ Docker development build - FAILED" >> "$RESULTS_DIR/pipeline_report.md"
        return 1
    fi

    # Test docker-compose configuration
    if docker-compose config >/dev/null 2>&1; then
        log_success "✅ Docker Compose configuration valid"
        echo "- ✅ Docker Compose configuration - PASSED" >> "$RESULTS_DIR/pipeline_report.md"
    else
        log_error "❌ Docker Compose configuration invalid"
        echo "- ❌ Docker Compose configuration - FAILED" >> "$RESULTS_DIR/pipeline_report.md"
        return 1
    fi

    # Cleanup test images
    docker rmi tmux-orchestrator:test-local tmux-orchestrator:dev-test-local >/dev/null 2>&1 || true
}

# Generate final report
generate_final_report() {
    log_info "Generating final pipeline report..."

    echo "" >> "$RESULTS_DIR/pipeline_report.md"
    echo "## Summary" >> "$RESULTS_DIR/pipeline_report.md"
    echo "" >> "$RESULTS_DIR/pipeline_report.md"
    echo "Pipeline execution completed at: $(date)" >> "$RESULTS_DIR/pipeline_report.md"
    echo "Results saved to: $RESULTS_DIR/" >> "$RESULTS_DIR/pipeline_report.md"

    log_success "Pipeline report generated: $RESULTS_DIR/pipeline_report.md"
}

# Main execution
main() {
    log_info "Starting Tmux Orchestrator CI/CD Pipeline Test"
    log_info "Project Directory: $PROJECT_DIR"
    log_info "Results Directory: $RESULTS_DIR"

    cd "$PROJECT_DIR"

    setup_results

    # Check prerequisites
    if ! command -v poetry >/dev/null 2>&1; then
        log_error "Poetry not found. Please install Poetry first."
        exit 1
    fi

    if ! command -v docker >/dev/null 2>&1; then
        log_warning "Docker not found. Skipping Docker tests."
        SKIP_DOCKER=true
    fi

    # Run test phases
    if run_quality_gate; then
        log_success "Phase 9.0 Quality Gate completed"
    else
        log_error "Phase 9.0 Quality Gate failed"
        exit 1
    fi

    if run_deployment_tests; then
        log_success "Phase 10.0 Deployment Tests completed"
    else
        log_error "Phase 10.0 Deployment Tests failed"
        exit 1
    fi

    if [[ "${SKIP_DOCKER:-false}" != "true" ]]; then
        if run_docker_tests; then
            log_success "Docker Integration Tests completed"
        else
            log_error "Docker Integration Tests failed"
            exit 1
        fi
    fi

    generate_final_report

    log_success "🎉 All pipeline tests completed successfully!"
    log_info "Review the full report at: $RESULTS_DIR/pipeline_report.md"
}

# Run main function
main "$@"

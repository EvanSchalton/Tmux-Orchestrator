#!/bin/bash
# Run all tests with coverage

set -e

echo "🧪 Running Tmux Orchestrator Test Suite"
echo "======================================"

# Check if in virtual environment
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "⚠️  Warning: Not in a virtual environment"
    echo "   Consider activating a virtual environment first"
    echo ""
fi

# Install test dependencies
echo "📦 Installing test dependencies..."
pip install -r requirements-test.txt

# Run linting
echo ""
echo "🔍 Running linting checks..."
ruff check tmux_orchestrator tests || echo "⚠️  Linting issues found"
black --check tmux_orchestrator tests || echo "⚠️  Formatting issues found"

# Run type checking
echo ""
echo "🔍 Running type checking..."
mypy tmux_orchestrator --ignore-missing-imports || echo "⚠️  Type checking issues found"

# Run unit tests
echo ""
echo "🧪 Running unit tests..."
pytest tests/test_cli tests/test_core tests/test_server -v

# Run integration tests
echo ""
echo "🔗 Running integration tests..."
pytest tests/test_integration -v

# Generate coverage report
echo ""
echo "📊 Generating coverage report..."
pytest tests/ --cov=tmux_orchestrator --cov-report=html --cov-report=term

echo ""
echo "✅ Test suite complete!"
echo "📊 Coverage report available at: htmlcov/index.html"

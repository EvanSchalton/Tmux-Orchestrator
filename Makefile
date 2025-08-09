.PHONY: install test lint format type-check security-check clean pre-commit check all

# Install all dependencies including dev
install:
	poetry install
	poetry run pre-commit install

# Run all tests
test:
	poetry run pytest -v

# Run tests with coverage
test-cov:
	poetry run pytest --cov=tmux_orchestrator --cov-report=term-missing --cov-report=html

# Format code
format:
	poetry run black tmux_orchestrator tests
	poetry run isort tmux_orchestrator tests

# Check formatting without changing files
format-check:
	poetry run black --check tmux_orchestrator tests
	poetry run isort --check-only tmux_orchestrator tests

# Run linter
lint:
	poetry run ruff check tmux_orchestrator tests

# Run type checker
type-check:
	poetry run mypy tmux_orchestrator

# Run security checks
security-check:
	poetry run bandit -r tmux_orchestrator -ll

# Run all checks (what CI will run)
check: format-check lint type-check security-check test

# Run pre-commit on all files
pre-commit:
	poetry run pre-commit run --all-files

# Clean up generated files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage" -delete
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache

# Run all checks and fixes
all: clean format lint type-check security-check test

# Quick check before commit (faster than pre-commit hook)
quick-check:
	poetry run ruff check tmux_orchestrator tests
	poetry run mypy tmux_orchestrator --ignore-missing-imports
	poetry run pytest tests/test_cli/test_setup.py -v  # Run just one test file as smoke test

# Help
help:
	@echo "Available commands:"
	@echo "  make install       - Install all dependencies and pre-commit hooks"
	@echo "  make test         - Run all tests"
	@echo "  make test-cov     - Run tests with coverage report"
	@echo "  make format       - Format code with black and isort"
	@echo "  make format-check - Check code formatting"
	@echo "  make lint         - Run ruff linter"
	@echo "  make type-check   - Run mypy type checker"
	@echo "  make security-check - Run bandit security linter"
	@echo "  make check        - Run all checks (format, lint, type, security, test)"
	@echo "  make pre-commit   - Run pre-commit on all files"
	@echo "  make clean        - Clean up generated files"
	@echo "  make quick-check  - Quick check before commit"
	@echo "  make all          - Clean, format, and run all checks"

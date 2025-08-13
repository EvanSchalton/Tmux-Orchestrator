# Development Guide

This project uses `invoke` for all development tasks. This ensures consistency between local development and CI/CD.

## Quick Start

```bash
# Install dependencies and setup
poetry run invoke install

# Run all CI/CD checks locally (identical to GitHub Actions)
poetry run invoke ci

# Quick check before committing
poetry run invoke quick
# or use the alias
poetry run invoke q
```

## Available Tasks

### Core Development Tasks

| Command | Description | Alias |
|---------|-------------|-------|
| `invoke test` | Run all tests | `invoke t` |
| `invoke test --verbose --coverage` | Run tests with coverage report | |
| `invoke lint` | Run linting checks | `invoke l` |
| `invoke lint --fix` | Run linting with auto-fix | |
| `invoke format` | Format code | `invoke f` |
| `invoke format --check` | Check formatting without changes | |
| `invoke type-check` | Run MyPy type checking | |
| `invoke security` | Run Bandit security scan | |

### Workflow Commands

| Command | Description |
|---------|-------------|
| `invoke check` | Run all checks (lint, format, security, type, test) |
| `invoke ci` | Run exact CI/CD simulation locally |
| `invoke quick` | Quick checks before committing |
| `invoke full` | Clean, format, and run all checks |
| `invoke pre-commit` | Run pre-commit hooks on all files |

### Utility Commands

| Command | Description |
|---------|-------------|
| `invoke clean` | Clean up generated files |
| `invoke update-deps` | Update dependencies |
| `invoke show-errors` | Show current MyPy errors |
| `invoke serve-docs` | Serve documentation locally |
| `invoke test-component <component>` | Test specific component |

## Component Testing

Test specific components:
```bash
invoke test-component cli
invoke test-component core
invoke test-component server
invoke test-component sdk

# Test specific module
invoke test-component cli --module setup
```

## CI/CD Parity

The `invoke ci` command runs the exact same checks as GitHub Actions:
1. Ruff linting
2. Ruff formatting check
3. Bandit security scan
4. MyPy type checking
5. Pytest tests

This ensures your local environment produces identical results to CI/CD.

## Pre-commit Hooks

Pre-commit hooks are automatically installed with `invoke install`. They run:
- Ruff formatting
- Ruff linting
- MyPy type checking
- Bandit security scan
- General file checks (trailing whitespace, file size, etc.)

## Development Workflow

1. **Before starting work:**
   ```bash
   poetry run invoke install  # Ensure dependencies are up to date
   ```

2. **During development:**
   ```bash
   poetry run invoke quick   # Quick checks while coding
   poetry run invoke test-component <component>  # Test specific areas
   ```

3. **Before committing:**
   ```bash
   poetry run invoke check   # Run all checks
   # or
   poetry run invoke ci      # Match exact CI/CD behavior
   ```

4. **Formatting and fixes:**
   ```bash
   poetry run invoke format  # Auto-format code
   poetry run invoke lint --fix  # Auto-fix linting issues
   ```

## Tips

- Use short aliases (`t`, `f`, `l`, `q`) for frequently used commands
- Run `invoke --list` to see all available tasks
- Run `invoke --help <task>` for detailed help on any task
- The `invoke ci` command ensures your code will pass GitHub Actions

## MyPy Progress

Current MyPy status: ~4 errors remaining (down from 123!)
```bash
# Check current errors
poetry run invoke show-errors
```

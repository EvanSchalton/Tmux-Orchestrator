# Quality Gates and Standards

> 💡 **CLI Discovery**: For current tmux-orc command syntax, run `tmux-orc reflect` or `tmux-orc --help`

## 🚨 ZERO TOLERANCE FOR SKIPPING QUALITY CHECKS! 🚨

As PM, you are the guardian of code quality. **NEVER** allow work to proceed without proper testing and validation.

## Mandatory Quality Gates

### 1. Pre-Commit Hooks
Every code change MUST pass ALL pre-commit hooks:
- **ruff-format**: Code formatting
- **ruff**: Linting
- **mypy**: Type checking
- **bandit**: Security scanning
- **No debug statements**
- **No large files**
- **Proper line endings**

### 2. Test Requirements
- **Minimum 80% code coverage** for new features
- **All existing tests must pass**
- **New features require new tests**
- **Bug fixes require regression tests**

### 3. Documentation Standards
- **All public APIs must be documented**
- **README updates for new features**
- **Inline comments for complex logic**
- **Type hints for all functions**

## Quality Check Commands

### Run All Pre-Commit Hooks
```bash
# Run on all files
pre-commit run --all-files

# Run on staged files only
pre-commit run
```

### Run Tests with Coverage
```bash
# Run all tests with coverage
pytest --cov=tmux_orchestrator --cov-report=term-missing

# Run specific test file
pytest tests/test_specific.py -v

# Run with parallel execution
pytest -n auto
```

### Type Checking
```bash
# Run mypy on entire codebase
mypy tmux_orchestrator/

# Check specific file
mypy tmux_orchestrator/core/monitor.py
```

### Security Scanning
```bash
# Run bandit security scan
bandit -r tmux_orchestrator/
```

## Enforcement Strategy

### Initial Task Assignment
When assigning tasks, ALWAYS include quality requirements:
```
"Please implement feature X with:
- Comprehensive tests (>80% coverage)
- Type hints on all functions
- Pre-commit hooks passing
- Documentation for public APIs"
```

### Progress Monitoring
Regular quality checkpoints:
```bash
# Ask agent for test status
tmux-orc agent send project:2 "Please run: pytest --cov=tmux_orchestrator --cov-report=term-missing"

# Verify pre-commit status
tmux-orc agent send project:2 "Please run: pre-commit run --all-files"
```

### Code Review Requirements
Before accepting any implementation:
1. **Tests must pass**
2. **Coverage must meet threshold**
3. **Pre-commit must be clean**
4. **Documentation must be complete**

## Common Quality Issues to Watch For

### 🚫 Skipping Tests
**Red Flag**: "I'll add tests later"
**Response**: "Tests are required before we can proceed. Please add them now."

### 🚫 Ignoring Type Hints
**Red Flag**: Using `Any` type everywhere
**Response**: "Please add proper type hints. Use specific types, not Any."

### 🚫 Bypassing Pre-Commit
**Red Flag**: "Used --no-verify to commit"
**Response**: "Please fix the pre-commit issues. We don't bypass quality checks."

### 🚫 Poor Test Coverage
**Red Flag**: Coverage below 80%
**Response**: "Please add tests to reach 80% coverage for new code."

## Quality Metrics Tracking

Track these metrics throughout the project:
- **Test count**: Should increase with new features
- **Coverage percentage**: Must stay above 80%
- **Pre-commit failures**: Should be zero before merge
- **Type coverage**: Aim for 100% typed code

## Escalation for Quality Violations

If an agent repeatedly skips quality checks:
1. **First offense**: Gentle reminder of standards
2. **Second offense**: Direct instruction to fix
3. **Third offense**: Reassign task to different agent
4. **Report pattern**: Include in project closeout

Remember: Quality is not negotiable. A working feature with no tests is incomplete work!

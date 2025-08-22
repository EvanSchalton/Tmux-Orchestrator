# Pre-Commit Workflow - Orchestrator Action Command

## 🚨 ORCHESTRATOR INSTRUCTION
**When this slash command is invoked, the Orchestrator should:**

1. **Assess Current State**: Check git status and run `pre-commit run --all-files` to identify issues
2. **Create Planning Documents**: Generate briefing and team plan for pre-commit fixes
3. **Spawn Pre-Commit Team**: Deploy specialized team to execute systematic workflow
4. **Monitor Progress**: Oversee team through completion and version bump validation

**This is an ACTION COMMAND, not documentation to show the user.**

---

## Pre-Commit Workflow - Systematic Code Quality Enforcement

### Overview
This workflow systematically fixes pre-commit issues and pushes code to GitHub, using the automatic version bump as final validation that work is complete.

## Success Pattern Reference
Successfully executed in: `.tmux_orchestrator/planning/completed/2025-08-18T02-40-53-pre-commit-workflow/`

## Pre-Commit Workflow Steps

### Phase 1: Assessment and Analysis

#### 1.1 Initial Status Check
```bash
# Check current git status and divergence
git status
git log --oneline origin/main..HEAD

# Run pre-commit to identify all issues
pre-commit run --all-files

# Capture initial issue count for tracking
```

#### 1.2 Categorize Issues
- **Parse Errors**: Syntax errors preventing code execution (CRITICAL)
- **Linting Errors**: Code style and quality issues
- **Security Issues**: Bandit findings that need review
- **Import Errors**: Missing or incorrect imports
- **Type Errors**: MyPy type checking failures (if enabled)

### Phase 2: Systematic Resolution

#### 2.1 Fix Parse Errors First (Blocking Issues)
```bash
# Parse errors must be fixed manually before any automation
# Example: IndentationError, SyntaxError, EOF parsing errors
```

#### 2.2 Apply Automated Fixes
```bash
# Run automated fixes for linting
poetry run invoke lint --fix
# or
ruff check --fix

# Run formatter
poetry run invoke format
# or
ruff format
```

#### 2.3 Review and Fix Remaining Issues
- Issues requiring `--unsafe-fixes` need manual review
- Security findings from Bandit need case-by-case evaluation
- Import reorganization for deprecated methods

### Phase 3: Test Organization (If Applicable)

#### 3.1 Test Directory Structure
Ensure tests follow same structure as main codebase:
```
tests/
├── test_cli/
│   ├── test_spawn/
│   └── test_commands/
├── test_core/
│   ├── test_monitoring/
│   └── test_agent_operations/
└── test_integration/
```

#### 3.2 Update Deprecated Method Usage
- When refactoring consolidates similar functions, update tests to use current implementations
- Do NOT create aliases for deprecated methods
- Update imports to match new module structure

### Phase 4: Validation and Commit

#### 4.1 Final Pre-Commit Validation
```bash
# Run all pre-commit hooks
pre-commit run --all-files

# All hooks should pass:
# ✓ ruff-format
# ✓ ruff
# ✓ bandit
# ✓ file quality checks
```

#### 4.2 Stage and Commit Changes
```bash
# Review changes to be committed
git diff --cached --stat

# Commit with descriptive message
git commit -m "fix: Resolve pre-commit issues and reorganize tests

- Fix all linting and formatting issues
- Reorganize test directory structure
- Update deprecated method usage
- All pre-commit hooks passing

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### Phase 5: Push and Verify

#### 5.1 Push to GitHub
```bash
# Push all commits
git push origin main
```

#### 5.2 Monitor CI/CD Pipeline
```bash
# Wait 2-3 minutes for CI/CD to complete
# Then fetch and verify version bump
git fetch origin
git log --oneline origin/main -3

# Look for auto-commit like:
# "chore: Auto-bump version to X.X.X [skip ci]"
```

#### 5.3 Pull Version Bump
```bash
# Pull the version bump commit
git pull origin main

# Verify version updated
cat pyproject.toml | grep version
cat tmux_orchestrator/__init__.py | grep version
```

## Quality Gates Checklist

### Pre-Commit Hooks Configuration
`.pre-commit-config.yaml` should include:
- ✅ Ruff formatter (code formatting)
- ✅ Ruff linter (code quality)
- ✅ Bandit (security scanning)
- ✅ File quality checks (EOF, trailing whitespace, YAML/JSON validation)
- ✅ MyPy (type checking - may be temporarily disabled)

### Success Criteria
1. **All pre-commit hooks pass** - No failures on `pre-commit run --all-files`
2. **Clean git status** - All changes committed and pushed
3. **Version bump received** - Automatic version increment via CD pipeline
4. **CI/CD passes** - All GitHub Actions workflows succeed

## Common Issues and Solutions

### Issue: Large Number of Files Changed
**Solution**: Focus on systematic progression:
1. Fix blocking issues first (parse errors)
2. Apply automated fixes in batches
3. Test incrementally

### Issue: Import Errors After Refactoring
**Solution**:
- Check DEVELOPMENT-GUIDE.md for current module structure
- Update imports to use consolidated functions
- Remove references to deprecated modules

### Issue: Test Failures After Reorganization
**Solution**:
- Ensure test discovery still works with new structure
- Update conftest.py paths if needed
- Verify __init__.py files in test directories

## Team Coordination for Pre-Commit Workflow

When orchestrating a team for pre-commit fixes:

### Recommended Team Composition
1. **PM**: Coordinate phases and track progress
2. **Senior Developer**: Handle parse errors and complex fixes
3. **QA Engineer**: Reorganize tests and validate functionality
4. **DevOps Engineer**: Monitor CI/CD and coordinate deployment

### Task Distribution
- **Parallel Work**: Different team members can work on different file categories
- **Sequential Dependencies**: Parse errors → Automated fixes → Manual fixes → Testing
- **Validation Gates**: Each phase should be validated before proceeding

## Automation Commands Reference

```bash
# Full CI simulation locally
poetry run invoke ci

# Individual commands
poetry run invoke format        # Code formatting
poetry run invoke lint --fix    # Linting with fixes
poetry run invoke type-check    # Type checking
poetry run invoke security      # Security scanning
poetry run invoke test          # Run tests
```

## Version Bump as Completion Signal

The automatic version bump serves as the definitive signal that:
1. Code has been successfully pushed to main
2. All CI/CD checks have passed
3. Code meets quality standards
4. Deployment pipeline is functioning correctly

**Note**: Always wait for and verify the version bump before considering the pre-commit workflow complete.

---

*Last Updated: 2025-08-18*
*Reference Implementation: `.tmux_orchestrator/planning/completed/2025-08-18T02-40-53-pre-commit-workflow/`

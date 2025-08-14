# Git Discipline and Standards

## 🔐 MANDATORY Git Workflow

**ALL agents (including you) MUST follow these Git standards. NO EXCEPTIONS!**

## Commit Frequency

### 30-Minute Rule
- **Commit every 30 minutes** of work, regardless of completion status
- Use `[WIP]` prefix for work-in-progress commits
- This prevents work loss and enables progress tracking

### Commit Message Standards
```bash
# Feature commits
feat: Add user authentication with JWT tokens

# Bug fixes
fix: Resolve login issue with special characters

# Work in progress
[WIP] feat: Partial implementation of auth module

# Refactoring
refactor: Extract validation logic to separate module

# Tests
test: Add unit tests for authentication

# Documentation
docs: Update README with authentication setup
```

## Pre-Commit Discipline

### Never Bypass Pre-Commit
```bash
# ❌ FORBIDDEN
git commit --no-verify

# ✅ CORRECT - Fix issues first
pre-commit run --all-files
# Fix any issues
git add .
git commit -m "feat: Add feature with all checks passing"
```

### Handling Pre-Commit Failures
1. **Read the error message**
2. **Fix the specific issue**
3. **Re-run pre-commit**
4. **Only commit when clean**

## Branch Management

### Feature Branch Workflow
```bash
# Create feature branch
git checkout -b feature/auth-implementation

# Work and commit
git add .
git commit -m "feat: Implement JWT authentication"

# Keep branch updated
git checkout main
git pull origin main
git checkout feature/auth-implementation
git rebase main
```

### Branch Naming Convention
- `feature/` - New features
- `fix/` - Bug fixes
- `refactor/` - Code refactoring
- `test/` - Test additions/improvements
- `docs/` - Documentation updates

## Collaborative Git Workflow

### Before Starting Work
```bash
# Always start with latest code
git checkout main
git pull origin main
git checkout -b feature/your-feature
```

### During Development
```bash
# Regular commits (every 30 min)
git add -A
git commit -m "feat: Description of progress"

# Check status frequently
git status
git diff
```

### Before Submitting PR
```bash
# Update from main
git checkout main
git pull origin main
git checkout feature/your-feature
git rebase main

# Run all quality checks
pre-commit run --all-files
pytest
```

## Merge Conflict Resolution

### Prevention
- Communicate about file changes
- Work on separate modules
- Pull latest changes frequently
- Small, focused commits

### Resolution Process
```bash
# If conflicts occur
git status  # See conflicted files
# Edit files to resolve conflicts
git add resolved_file.py
git rebase --continue
```

## Git Commit Checklist

Before EVERY commit:
- [ ] Tests pass locally
- [ ] Pre-commit hooks pass
- [ ] Commit message follows convention
- [ ] Changes are focused and related
- [ ] No debug code or print statements
- [ ] No sensitive information

## Common Git Mistakes to Avoid

### ❌ Giant Commits
```bash
# WRONG - Everything in one commit
git add .
git commit -m "Did lots of stuff"
```

### ❌ Meaningless Messages
```bash
# WRONG - Unclear commit message
git commit -m "fix"
git commit -m "updates"
git commit -m "changes"
```

### ❌ Committing Generated Files
```bash
# WRONG - Check .gitignore
git add node_modules/
git add __pycache__/
git add .env
```

### ✅ Good Practices
```bash
# RIGHT - Clear, focused commits
git add src/auth/
git commit -m "feat: Add JWT token generation for user auth"

git add tests/test_auth.py
git commit -m "test: Add unit tests for JWT token generation"
```

## Emergency Procedures

### Accidentally Committed Secrets
```bash
# IMMEDIATE ACTION REQUIRED
# 1. Remove from history
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch path/to/secret/file" \
  --prune-empty --tag-name-filter cat -- --all

# 2. Force push (coordinate with team)
git push origin --force --all

# 3. Rotate the exposed secrets immediately
```

### Need to Undo Last Commit
```bash
# Soft reset (keeps changes)
git reset --soft HEAD~1

# Hard reset (discards changes) - USE CAREFULLY
git reset --hard HEAD~1
```

## PM Git Responsibilities

As PM, enforce Git discipline by:
1. **Checking commit history** regularly
2. **Reminding agents** of 30-minute rule
3. **Reviewing commit messages** for clarity
4. **Ensuring pre-commit** compliance
5. **Coordinating** conflict resolution

Remember: Good Git habits prevent disasters!

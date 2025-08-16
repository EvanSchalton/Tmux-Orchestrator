# Critical Fixes Priority List

## 🔴 IMMEDIATE FIXES (Production Blockers)

### 1. Shell Injection in spawn_orc.py (CRITICAL - CVSS 9.8)
**Assigned to**: Senior Engineer (review:3)
**Status**: IN PROGRESS
**File**: `tmux_orchestrator/cli/spawn_orc.py:46-77`
**Fix**: Properly escape shell commands, use subprocess with arrays instead of shell=True

### 2. Command Injection in team_compose.py (CRITICAL - CVSS 9.1)
**Status**: PENDING
**File**: `tmux_orchestrator/cli/team_compose.py:178-181`
**Fix**: Use shlex.quote() for all user inputs passed to shell

### 3. Path Traversal in server.py (HIGH - CVSS 7.5)
**Status**: PENDING
**File**: `tmux_orchestrator/server/main.py:45`
**Fix**: Validate and sanitize file paths, use os.path.normpath()

## 🟡 HIGH PRIORITY FIXES

### 4. Hardcoded Paths
**Status**: PENDING
**Files**: Multiple locations
**Fix**: Use environment variables or configuration files

### 5. God Class Refactoring (Monitor class)
**Status**: PENDING
**File**: `tmux_orchestrator/core/monitor.py`
**Fix**: Split into focused service classes

## Progress Tracking

- [ ] Fix 1: Shell Injection in spawn_orc.py
- [ ] Fix 2: Command Injection in team_compose.py
- [ ] Fix 3: Path Traversal in server.py
- [ ] Fix 4: Hardcoded Paths
- [ ] Fix 5: God Class Refactoring

## Quality Gates
Each fix must:
1. Include comprehensive tests
2. Pass all existing tests
3. Pass linting (ruff)
4. Pass type checking (mypy)
5. Include security test cases
6. Maintain backwards compatibility

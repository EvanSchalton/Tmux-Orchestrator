# Test Directory Reorganization Plan

## Current State Analysis

### Statistics
- **Total test files:** 56
- **Root level files:** 19 (too many!)
- **Subdirectories:** 4 (test_cli, test_core, test_integration, test_server)
- **Naming violations:** 34 files violate the `*_test.py` pattern

### Critical Issues Found

#### 1. Naming Convention Violations
Per development-patterns.md, test files in subdirectories must end with `_test.py`, not start with `test_`.

**Examples of violations:**
- `test_cli/test_monitor.py` → Should be `test_cli/monitor_test.py`
- `test_server/test_mcp_server.py` → Should be `test_server/mcp_server_test.py`

#### 2. Root Level Clutter
18 test files sit at the root level, making navigation difficult:
- 9 monitor-related files
- 4 compaction detection files
- 3 rate limit files
- Multiple integration tests

#### 3. Inconsistent Organization
- Integration tests split between root and `test_integration/`
- Monitor tests scattered across root and `test_cli/`
- No clear separation between unit and integration tests

#### 4. Potential Duplicates
Multiple files testing similar functionality:
- `test_compaction_detection.py`, `test_compaction_detection_realistic.py`, `test_compaction_detection_simple.py`
- `test_rate_limit.py`, `test_rate_limit_handling.py`

## Proposed New Structure

```
tests/
├── conftest.py
├── test_core/
│   ├── agent_operations_test.py
│   ├── error_handler_test.py
│   ├── event_bus_test.py
│   ├── test_recovery/
│   │   ├── agent_recovery_test.py
│   │   ├── common_errors_test.py
│   │   ├── recovery_test.py
│   │   └── spawner_test.py
│   └── test_team_operations/
│       ├── team_context_test.py
│       ├── team_creation_test.py
│       └── team_operations_test.py
├── test_monitor/
│   ├── monitor_test.py
│   ├── monitor_callbacks_test.py
│   ├── monitor_daemon_test.py
│   ├── monitor_daemon_resume_test.py
│   ├── monitor_error_handling_test.py
│   ├── monitor_helpers_test.py
│   ├── monitor_integration_test.py
│   ├── monitor_models_test.py
│   ├── monitor_resilience_test.py
│   ├── test_compaction/
│   │   ├── compaction_detection_test.py
│   │   ├── compaction_realistic_test.py
│   │   └── compaction_simple_test.py
│   └── test_rate_limit/
│       ├── rate_limit_test.py
│       └── rate_limit_handling_test.py
├── test_cli/
│   ├── agent_test.py
│   ├── cli_utils_test.py
│   ├── client_test.py
│   ├── config_test.py
│   ├── context_test.py
│   ├── claude_test.py
│   ├── server_test.py
│   ├── session_test.py
│   └── validator_test.py
├── test_server/
│   ├── mcp_server_test.py
│   ├── server_test.py
│   └── test_tools/
│       └── [15 tool test files with *_test.py names]
├── test_integration/
│   ├── end_to_end_test.py
│   ├── combined_features_test.py
│   ├── compaction_integration_test.py
│   └── rate_limit_integration_test.py
├── test_data/
│   └── contexts_test.py
└── test_prompts/
    └── project_manager_test.py
```

## Key Changes

### 1. Fix All Naming Violations
- Rename 34 files from `test_*.py` to `*_test.py` pattern
- Maintain consistency with development-patterns.md

### 2. Create Logical Groupings
- **test_monitor/**: Consolidate all 9 monitor-related tests
  - **test_compaction/**: Group compaction detection tests
  - **test_rate_limit/**: Group rate limit tests
- **test_integration/**: Move all integration tests together
- **test_data/**: New directory for data model tests
- **test_prompts/**: New directory for prompt-related tests

### 3. Reduce Root Clutter
- Move 18 files from root to appropriate subdirectories
- Keep only conftest.py at root level

### 4. Mirror Source Structure
- Tests now better reflect the source code organization
- Easier to find corresponding tests for source files

## Implementation Plan

### Phase 1: Create New Directories
```bash
mkdir -p tests/test_monitor/test_compaction
mkdir -p tests/test_monitor/test_rate_limit
mkdir -p tests/test_data
mkdir -p tests/test_prompts
```

### Phase 2: Move and Rename Files (Incremental)
1. Start with monitor tests (lowest risk)
2. Move integration tests
3. Fix naming in existing subdirectories
4. Move remaining root files

### Phase 3: Update Imports
- Use automated search/replace for import updates
- Run tests after each batch of moves

### Phase 4: Consolidate Duplicates
- Review similar test files for redundancy
- Merge where appropriate
- Ensure no loss of test coverage

## Benefits

1. **Improved Navigation**: Clear structure makes finding tests easier
2. **Follows Standards**: Complies with development-patterns.md
3. **Scalability**: New tests have obvious homes
4. **Reduced Confusion**: No more duplicate-looking files
5. **Better Organization**: Unit vs integration tests clearly separated

## Risk Mitigation

- Working on branch `test-cleanup-reorganization`
- Moving files incrementally
- Running tests after each phase
- Maintaining git history with proper moves

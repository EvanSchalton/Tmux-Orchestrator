# Phase 1 Validation Process - Test File Renaming

## Overview
This document outlines the validation process for Phase 1 of the test cleanup: renaming test files from `test_*.py` to `*_test.py` pattern.

## Pre-Renaming Setup (COMPLETED)
1. ✅ Baseline test count: 765 tests
2. ✅ Test inventory saved: 756 tests in 54 files
3. ✅ No collection errors in baseline

## Validation Scripts Created

### 1. `validate_renamed_files.py`
- **Purpose**: Ensures all renamed files are discovered by pytest
- **Checks**:
  - All test files in filesystem are discovered
  - Naming pattern progress tracking
  - Total test count comparison
- **Usage**: `python validate_renamed_files.py`

### 2. `compare_test_inventory.py`
- **Purpose**: Deep comparison of test functions before/after
- **Features**:
  - Tracks individual test functions, not just files
  - Identifies missing or new tests
  - Creates detailed comparison report
- **Usage**:
  ```bash
  # Before renaming (already done)
  python compare_test_inventory.py save

  # After each batch of renames
  python compare_test_inventory.py check
  ```

### 3. `validate_test_changes.sh`
- **Purpose**: Quick validation checks
- **Checks**: Discovery, errors, naming patterns, coverage

## Validation Process for Backend Dev

### During Renaming (Per Batch)
1. **Before renaming a batch** (5-10 files):
   ```bash
   # Note current test count
   poetry run pytest --collect-only -q | grep collected
   ```

2. **Rename the batch**:
   ```bash
   # Example for a single file
   git mv tests/test_example.py tests/example_test.py

   # Update any imports in the file itself
   # No need to update imports in other files (pytest discovers by pattern)
   ```

3. **After renaming the batch**:
   ```bash
   # Quick validation
   python validate_renamed_files.py

   # If any issues, check specific file
   poetry run pytest tests/renamed_file_test.py -v
   ```

### After All Renames Complete
1. **Run full validation**:
   ```bash
   # Check all files discovered
   python validate_renamed_files.py

   # Deep test comparison
   python compare_test_inventory.py check

   # Quick checks
   ./validate_test_changes.sh
   ```

2. **Verify git status**:
   ```bash
   # Should only show renames, no deletions
   git status --porcelain | grep -E "^D|^A"
   # Should be empty (no adds/deletes, only renames)
   ```

3. **Run sample tests**:
   ```bash
   # Run a few renamed test files
   poetry run pytest tests/cli/agent_test.py -v
   poetry run pytest tests/monitor_helpers_test.py -v
   ```

## Success Criteria
- [ ] All 765 tests still discovered
- [ ] No pytest collection errors
- [ ] All files follow `*_test.py` pattern
- [ ] Git shows only renames (no adds/deletes)
- [ ] Sample tests pass

## Troubleshooting

### If tests are missing:
1. Check the comparison report: `test_inventory_comparison.json`
2. Look for typos in renamed files
3. Ensure no files were accidentally deleted
4. Check for import errors in renamed files

### If collection errors occur:
1. Check for circular imports
2. Verify file has no syntax errors
3. Ensure conftest.py wasn't modified
4. Run pytest on specific file with `-v` flag

### Recovery:
```bash
# If something goes wrong, revert the batch
git checkout -- tests/
```

## Progress Tracking
- Started with: 0/54 files renamed
- Current: 5/54 files renamed (Backend Dev update)
- Target: 54/54 files following new pattern

## Notes
- Pytest discovers tests by pattern, so imports in other files don't need updating
- Focus on one directory at a time for easier tracking
- Commit after each successful batch validation

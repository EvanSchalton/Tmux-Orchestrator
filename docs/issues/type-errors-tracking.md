# Type Errors Tracking Issue

## Overview
As of 2025-08-09, there are 123 mypy type errors in the codebase that need to be addressed. MyPy has been temporarily disabled in both pre-commit hooks and CI/CD until these are resolved.

## Summary of Type Errors by Category

### 1. Optional/None Type Issues (45 errors)
- Incompatible None assignments to typed variables
- Missing None checks for Optional types
- Union type attribute access without narrowing

### 2. Missing Type Annotations (15 errors)
- Variables that need explicit type hints
- Empty collections without type parameters

### 3. Dict/List Type Mismatches (20 errors)
- Dict entries with incorrect value types
- Expected int but got other types in dict values
- Collection type assumptions

### 4. Attribute Access Errors (15 errors)
- Accessing attributes that don't exist on types
- Wrong attribute names or missing attributes

### 5. Return Type Issues (10 errors)
- Functions returning Any when specific type expected
- Incorrect return type annotations

### 6. Operator Type Errors (10 errors)
- Unsupported operations between types
- Comparison/arithmetic with wrong types

### 7. Function Argument Type Errors (8 errors)
- Passing wrong types to function parameters
- Missing or extra keyword arguments

## Files with Most Errors
1. `tmux_orchestrator/core/recovery/recovery_test.py` - 28 errors
2. `tmux_orchestrator/cli/execute.py` - 10 errors
3. `tmux_orchestrator/server/tools/report_activity.py` - 12 errors
4. `tmux_orchestrator/server/routes/agent_management.py` - 10 errors

## Resolution Strategy
1. Start with the simplest fixes (missing annotations)
2. Address Optional/None handling systematically
3. Fix return types and function signatures
4. Resolve dict/list type issues
5. Handle complex type narrowing cases

## Re-enabling MyPy
Once all errors are fixed:
1. Remove the skip from `.pre-commit-config.yaml`
2. Uncomment the mypy step in `.github/workflows/tests.yml`
3. Ensure all new code passes type checking

# 📋 QA Test Cases for Context-Aware Crash Detection

**Date:** 2025-08-16
**QA Engineer:** Claude QA
**Feature:** Context-aware pattern matching for false positive prevention
**Status Report:** `.tmux_orchestrator/planning/2025-08-15T22-30-00-daemon-recovery-improvements/status-report.md`

## 🎯 OBJECTIVE

Validate that the context-aware crash detection implementation:
1. Prevents false positives when PMs output legitimate error messages
2. Still detects real crashes when Claude process exits
3. Uses regex patterns to identify safe contexts

## 📁 TEST ARTIFACTS CREATED

### 1. **Comprehensive Validation Script**
**File:** `qa_validate_context_aware_fix.py`
- Tests 30+ safe context scenarios
- Tests 9 unsafe context scenarios
- Validates regex patterns from status report
- Provides detailed pass/fail report
- **Run:** `python qa_validate_context_aware_fix.py`

### 2. **Quick Manual Test Script**
**File:** `qa_test_failed_keyword.sh`
- Quick visual test for 'failed' keyword
- Shows if PM gets killed for legitimate output
- Takes ~15 seconds to run
- **Run:** `./qa_test_failed_keyword.sh`

### 3. **Existing Test Suites**
- `tests/test_context_aware_crash_detection.py` - Unit tests
- `tests/test_pm_crash_detection_validation.py` - Integration tests
- `tests/test_false_positive_fix_verification.py` - Comprehensive verification

## 🧪 KEY TEST SCENARIOS

### ✅ SAFE CONTEXTS (Should NOT kill PM)

#### Test Results
- "3 tests failed in authentication module"
- "Unit test suite failed: 5 errors"
- "Test runner failed to complete"

#### Build Outputs
- "Build failed: TypeScript compilation error"
- "Docker build failed at step 5"
- "npm build failed with exit code 1"

#### CI/CD
- "GitHub Actions job 'test' failed"
- "Jenkins pipeline failed at deploy stage"
- "GitLab CI workflow failed"

#### Deployment
- "Deployment to production failed - rolling back"
- "Staging deployment failed: timeout"
- "Canary deployment failed health checks"

#### Status Reports
- "Previous attempt failed, retrying..."
- "The last sync failed at 14:30"
- "Backup job failed but will retry"

#### Tool Output
- "⎿ Security scan: 3 checks failed"
- "│ FAILED: SQL injection test"
- "└ Total failed: 5"

### ❌ UNSAFE CONTEXTS (Should kill PM)

- `"failed"` (isolated keyword)
- `"Killed"` (direct termination)
- `"$ failed"` (shell prompt with error)
- `"Segmentation fault"`
- `"user@host:~$ "` (bare shell prompt)

## 📊 RECOMMENDED IMPLEMENTATION

Based on the status report, the developer should implement:

```python
def _should_ignore_crash_indicator(self, line: str, indicator: str) -> bool:
    """Check if crash indicator should be ignored based on context"""
    ignore_contexts = [
        r"test.*failed",
        r"check.*failed",
        r"Tests failed:",
        r"Build failed:",
        r"[Jj]ob.*failed",
        r"[Pp]ipeline.*failed",
        r"[Dd]eployment.*failed",
        r"\d+.*failed",  # "3 tests failed"
        r"failed.*retry",
        r"previous.*failed",
        r"⎿.*failed",  # Tool output
        r"│.*failed",  # Tool output lines
    ]
    for context in ignore_contexts:
        if re.search(context, line, re.IGNORECASE):
            return True
    return False
```

## 🚀 VALIDATION PROCESS

1. **Run Quick Test** (30 seconds)
   ```bash
   ./qa_test_failed_keyword.sh
   ```

2. **Run Comprehensive Validation** (2 minutes)
   ```bash
   python qa_validate_context_aware_fix.py
   ```

3. **Run Full Test Suite** (5 minutes)
   ```bash
   python tests/test_pm_crash_detection_validation.py
   pytest tests/test_context_aware_crash_detection.py -v
   ```

## 🎯 SUCCESS CRITERIA

- **Zero false positives** for legitimate PM output
- **100% detection rate** for actual crashes
- **All regex patterns** properly matching safe contexts
- **No PM death loops** from recovery messages

## 📈 CURRENT STATUS

Based on previous testing:
- Current implementation: 80% accuracy
- Main issue: Some complex scenarios still trigger false positives
- Recommendation: Implement full context-aware pattern matching

---

**QA READY TO VALIDATE IMPLEMENTATION** 🛡️

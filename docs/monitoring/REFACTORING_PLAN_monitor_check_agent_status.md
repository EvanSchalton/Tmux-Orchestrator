# Refactoring Plan: `_check_agent_status` Method

## Overview
This document outlines the refactoring plan for the `_check_agent_status` method in `/workspaces/Tmux-Orchestrator/tmux_orchestrator/core/monitor.py`. The goal is to break down this complex method into smaller, testable helper functions.

## Current Issues
- The method is 74 lines long (lines 360-433)
- It handles multiple responsibilities: crash detection, idle detection, Claude interface checking, auto-submission, and notifications
- Difficult to unit test due to tight coupling with TMUXManager
- Complex conditional logic that's hard to follow

## Proposed Helper Functions

### 1. `is_claude_interface_present(content: str) -> bool`
**Responsibility**: Detect if Claude Code interface is actively present in terminal content

**Implementation**:
```python
def is_claude_interface_present(content: str) -> bool:
    """Check if Claude Code interface is ACTIVELY present (not just history)."""
    # Check for bash prompt indicators (Claude crashed)
    lines = content.strip().split('\n')
    last_few_lines = [line for line in lines[-5:] if line.strip()]

    # Bash prompt patterns indicate Claude is NOT running
    bash_indicators = ["vscode ➜", "$ ", "# ", "bash-", "@", "]"]
    for line in last_few_lines:
        if line.strip().endswith(('$', '#', '>', '%')):
            return False
        if any(indicator in line for indicator in bash_indicators):
            return False

    # Claude UI indicators mean Claude IS running
    claude_indicators = [
        "? for shortcuts",
        "Welcome to Claude Code",
        "╭─", "╰─", "│ >",
        "assistant:", "Human:",
        "Bypassing Permissions",
        "@anthropic-ai/claude-code"
    ]
    return any(indicator in content for indicator in claude_indicators)
```

### 2. `detect_agent_state(content: str) -> AgentState`
**Responsibility**: Determine the current state of an agent from terminal content

**Implementation**:
```python
from enum import Enum

class AgentState(Enum):
    HEALTHY = "healthy"
    CRASHED = "crashed"
    STARTING = "starting"
    ERROR = "error"
    IDLE = "idle"
    ACTIVE = "active"
    MESSAGE_QUEUED = "message_queued"

def detect_agent_state(content: str) -> AgentState:
    """Detect agent state from terminal content."""
    # Check for crashes first
    if not is_claude_interface_present(content):
        if _has_crash_indicators(content):
            return AgentState.CRASHED
        return AgentState.ERROR

    # Check for errors
    if _has_error_indicators(content):
        return AgentState.ERROR

    # Check for starting state
    if _is_starting(content):
        return AgentState.STARTING

    # Check for queued messages
    if has_unsubmitted_message(content):
        return AgentState.MESSAGE_QUEUED

    # Will need idle detection from snapshots
    return AgentState.HEALTHY
```

### 3. `has_unsubmitted_message(content: str) -> bool`
**Responsibility**: Check if there's an unsubmitted message in Claude's input prompt

**Implementation**:
```python
def has_unsubmitted_message(content: str) -> bool:
    """Check if agent has unsubmitted message in Claude prompt."""
    lines = content.strip().split('\n')

    # Single line check
    for line in lines:
        if "│ >" in line:
            prompt_content = line.split("│ >", 1)[1] if "│ >" in line else ""
            if prompt_content.strip():
                return True

    # Multi-line check
    in_prompt = False
    for line in lines:
        if "│ >" in line:
            in_prompt = True
            prompt_content = line.split("│ >", 1)[1] if "│ >" in line else ""
            if prompt_content.strip():
                return True
        elif in_prompt and "│" in line:
            content_match = line.strip()
            if content_match.startswith("│") and content_match.endswith("│"):
                inner_content = content_match[1:-1].strip()
                if inner_content and inner_content != ">":
                    return True
        elif "╰─" in line:
            in_prompt = False

    return False
```

### 4. `is_terminal_idle(snapshots: List[str]) -> bool`
**Responsibility**: Determine if terminal is idle based on content snapshots

**Implementation**:
```python
def is_terminal_idle(snapshots: List[str]) -> bool:
    """Check if terminal is idle based on multiple snapshots."""
    if len(snapshots) < 2:
        return False

    # Compare each snapshot to the first one
    for i in range(1, len(snapshots)):
        distance = _calculate_change_distance(snapshots[0], snapshots[i])
        if distance > 1:  # Meaningful change detected
            return False

    return True

def _calculate_change_distance(text1: str, text2: str) -> int:
    """Calculate simple change distance between two texts."""
    if abs(len(text1) - len(text2)) > 1:
        return 999

    differences = 0
    for i, (c1, c2) in enumerate(zip(text1, text2)):
        if c1 != c2:
            differences += 1
            if differences > 1:
                return differences

    differences += abs(len(text1) - len(text2))
    return differences
```

### 5. `needs_recovery(state: AgentState) -> bool`
**Responsibility**: Determine if an agent needs recovery based on its state

**Implementation**:
```python
def needs_recovery(state: AgentState) -> bool:
    """Determine if agent needs recovery based on state."""
    return state in [AgentState.CRASHED, AgentState.ERROR]
```

### 6. `should_notify_pm(state: AgentState, target: str, notification_history: dict) -> bool`
**Responsibility**: Determine if PM should be notified about agent state

**Implementation**:
```python
from datetime import datetime, timedelta

def should_notify_pm(state: AgentState, target: str, notification_history: dict) -> bool:
    """Determine if PM should be notified about agent state."""
    # Always notify for crashes and errors
    if state in [AgentState.CRASHED, AgentState.ERROR]:
        return True

    # Notify for idle agents without cooldown
    if state == AgentState.IDLE:
        return True

    # Don't notify for healthy/active agents
    return False
```

### 7. Additional Helper Functions

```python
def _has_crash_indicators(content: str) -> bool:
    """Check for crash indicators in content."""
    crash_indicators = [
        "claude: command not found",
        "segmentation fault",
        "core dumped",
        "killed",
        "Traceback (most recent call last)",
        "ModuleNotFoundError",
        "Process finished with exit code",
        "[Process completed]",
        "Terminated"
    ]
    content_lower = content.lower()
    return any(indicator.lower() in content_lower for indicator in crash_indicators)

def _has_error_indicators(content: str) -> bool:
    """Check for error indicators in content."""
    error_indicators = [
        "network error occurred",
        "timeout error occurred",
        "permission denied",
        "Error:",
        "connection lost"
    ]
    content_lower = content.lower()
    return any(indicator.lower() in content_lower for indicator in error_indicators)

def _is_starting(content: str) -> bool:
    """Check if Claude is still starting up."""
    starting_indicators = [
        "Initializing Claude Code",
        "Loading configuration",
        "Setting up environment",
        "Connecting to Claude API"
    ]
    return any(indicator in content for indicator in starting_indicators)
```

## Refactored `_check_agent_status` Method

```python
def _check_agent_status(self, tmux: TMUXManager, target: str, logger: logging.Logger) -> None:
    """Check agent status using modular helper functions."""
    try:
        # Step 1: Capture current content
        content = tmux.capture_pane(target, lines=50)

        # Step 2: Detect agent state
        state = detect_agent_state(content)

        # Step 3: Handle crashed agents
        if state == AgentState.CRASHED:
            logger.error(f"Agent {target} has crashed - attempting auto-restart")
            success = self._attempt_agent_restart(tmux, target, logger)
            if not success:
                logger.error(f"Auto-restart failed for {target} - notifying PM")
                self._notify_crash(tmux, target, logger)
            return

        # Step 4: Check idle status with snapshots
        snapshots = self._capture_snapshots(tmux, target, count=4, interval=0.3)
        is_idle = is_terminal_idle(snapshots)

        # Step 5: Update state based on idle detection
        if is_idle and state == AgentState.HEALTHY:
            state = AgentState.IDLE
        elif not is_idle:
            state = AgentState.ACTIVE
            # Reset tracking for active agents
            self._reset_agent_tracking(target)
            return

        # Step 6: Handle idle agents with Claude interface
        if state == AgentState.IDLE and is_claude_interface_present(content):
            logger.info(f"Agent {target} is idle with Claude interface")

            # Notify PM
            if should_notify_pm(state, target, self._idle_notifications):
                self._check_idle_notification(tmux, target, logger)

            # Try auto-submit for stuck messages
            if state == AgentState.MESSAGE_QUEUED:
                self._try_auto_submit(tmux, target, logger)

        # Step 7: Handle agents needing recovery
        elif needs_recovery(state):
            logger.error(f"Agent {target} needs recovery - state: {state}")
            self._notify_recovery_needed(tmux, target, logger)

    except Exception as e:
        logger.error(f"Failed to check agent {target}: {e}")

def _capture_snapshots(self, tmux: TMUXManager, target: str, count: int, interval: float) -> List[str]:
    """Capture multiple snapshots of terminal content."""
    snapshots = []
    for i in range(count):
        content = tmux.capture_pane(target, lines=50)
        snapshots.append(content)
        if i < count - 1:
            time.sleep(interval)
    return snapshots

def _reset_agent_tracking(self, target: str) -> None:
    """Reset tracking for active agents."""
    if target in self._idle_agents:
        del self._idle_agents[target]
    if target in self._submission_attempts:
        self._submission_attempts[target] = 0
    if target in self._last_submission_time:
        del self._last_submission_time[target]

def _try_auto_submit(self, tmux: TMUXManager, target: str, logger: logging.Logger) -> None:
    """Try auto-submitting stuck messages with cooldown."""
    current_time = time.time()
    last_attempt = self._last_submission_time.get(target, 0)

    if current_time - last_attempt >= 10:  # 10 second cooldown
        logger.info(f"Auto-submitting stuck message for {target}")
        tmux.send_keys(target, "Enter")
        self._submission_attempts[target] = self._submission_attempts.get(target, 0) + 1
        self._last_submission_time[target] = current_time
```

## Test Structure

### Directory Layout
```
tests/
├── fixtures/
│   └── monitor_states/
│       ├── healthy/
│       │   ├── agent_active_typing.txt
│       │   ├── agent_waiting_response.txt
│       │   └── agent_claude_welcome.txt
│       ├── crashed/
│       │   ├── agent_bash_prompt.txt
│       │   ├── agent_command_not_found.txt
│       │   └── agent_python_traceback.txt
│       ├── message_queued/
│       │   ├── agent_unsubmitted_single_line.txt
│       │   └── agent_unsubmitted_multiline.txt
│       ├── idle/
│       │   ├── agent_empty_prompt.txt
│       │   └── agent_thinking_stuck.txt
│       ├── starting/
│       │   ├── agent_initializing.txt
│       │   └── agent_welcome_appearing.txt
│       └── error/
│           ├── agent_network_error.txt
│           └── agent_permission_denied.txt
└── test_monitor_helpers.py
```

### Test File Structure

```python
# tests/test_monitor_helpers.py
import pytest
from pathlib import Path
from tmux_orchestrator.core.monitor_helpers import (
    is_claude_interface_present,
    detect_agent_state,
    has_unsubmitted_message,
    is_terminal_idle,
    needs_recovery,
    should_notify_pm,
    AgentState
)

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "monitor_states"

def load_fixture(category: str, filename: str) -> str:
    """Load a test fixture file."""
    path = FIXTURES_DIR / category / filename
    return path.read_text()

class TestClaudeInterfaceDetection:
    """Test is_claude_interface_present function."""

    def test_healthy_agent_has_interface(self):
        content = load_fixture("healthy", "agent_active_typing.txt")
        assert is_claude_interface_present(content) is True

    def test_crashed_agent_no_interface(self):
        content = load_fixture("crashed", "agent_bash_prompt.txt")
        assert is_claude_interface_present(content) is False

    def test_command_not_found_no_interface(self):
        content = load_fixture("crashed", "agent_command_not_found.txt")
        assert is_claude_interface_present(content) is False

class TestAgentStateDetection:
    """Test detect_agent_state function."""

    def test_detect_healthy_state(self):
        content = load_fixture("healthy", "agent_waiting_response.txt")
        assert detect_agent_state(content) == AgentState.HEALTHY

    def test_detect_crashed_state(self):
        content = load_fixture("crashed", "agent_python_traceback.txt")
        assert detect_agent_state(content) == AgentState.CRASHED

    def test_detect_message_queued_state(self):
        content = load_fixture("message_queued", "agent_unsubmitted_single_line.txt")
        assert detect_agent_state(content) == AgentState.MESSAGE_QUEUED

    def test_detect_error_state(self):
        content = load_fixture("error", "agent_network_error.txt")
        assert detect_agent_state(content) == AgentState.ERROR

    def test_detect_starting_state(self):
        content = load_fixture("starting", "agent_initializing.txt")
        assert detect_agent_state(content) == AgentState.STARTING

class TestUnsubmittedMessageDetection:
    """Test has_unsubmitted_message function."""

    def test_single_line_message(self):
        content = load_fixture("message_queued", "agent_unsubmitted_single_line.txt")
        assert has_unsubmitted_message(content) is True

    def test_multiline_message(self):
        content = load_fixture("message_queued", "agent_unsubmitted_multiline.txt")
        assert has_unsubmitted_message(content) is True

    def test_empty_prompt(self):
        content = load_fixture("idle", "agent_empty_prompt.txt")
        assert has_unsubmitted_message(content) is False

    def test_no_prompt(self):
        content = load_fixture("crashed", "agent_bash_prompt.txt")
        assert has_unsubmitted_message(content) is False

class TestIdleDetection:
    """Test is_terminal_idle function."""

    def test_identical_snapshots_are_idle(self):
        snapshot = load_fixture("idle", "agent_empty_prompt.txt")
        snapshots = [snapshot] * 4  # 4 identical snapshots
        assert is_terminal_idle(snapshots) is True

    def test_changing_snapshots_not_idle(self):
        snapshots = [
            load_fixture("healthy", "agent_active_typing.txt"),
            load_fixture("healthy", "agent_waiting_response.txt"),
            load_fixture("healthy", "agent_active_typing.txt"),
            load_fixture("healthy", "agent_waiting_response.txt")
        ]
        assert is_terminal_idle(snapshots) is False

    def test_minor_changes_are_idle(self):
        # Simulate cursor blink (1 character difference)
        base = load_fixture("idle", "agent_empty_prompt.txt")
        snapshots = [base, base[:-1] + "_", base, base[:-1] + "_"]
        assert is_terminal_idle(snapshots) is True

class TestRecoveryLogic:
    """Test needs_recovery function."""

    def test_crashed_needs_recovery(self):
        assert needs_recovery(AgentState.CRASHED) is True

    def test_error_needs_recovery(self):
        assert needs_recovery(AgentState.ERROR) is True

    def test_healthy_no_recovery(self):
        assert needs_recovery(AgentState.HEALTHY) is False

    def test_idle_no_recovery(self):
        assert needs_recovery(AgentState.IDLE) is False

class TestNotificationLogic:
    """Test should_notify_pm function."""

    def test_notify_on_crash(self):
        assert should_notify_pm(AgentState.CRASHED, "session:0", {}) is True

    def test_notify_on_error(self):
        assert should_notify_pm(AgentState.ERROR, "session:0", {}) is True

    def test_notify_on_idle(self):
        assert should_notify_pm(AgentState.IDLE, "session:0", {}) is True

    def test_no_notify_on_healthy(self):
        assert should_notify_pm(AgentState.HEALTHY, "session:0", {}) is False

    def test_no_notify_on_active(self):
        assert should_notify_pm(AgentState.ACTIVE, "session:0", {}) is False
```

## Implementation Steps

1. **Create helper module**: `tmux_orchestrator/core/monitor_helpers.py`
2. **Move helper functions**: Extract all helper functions to the new module
3. **Add AgentState enum**: Define the state enumeration
4. **Update imports**: Import helpers in `monitor.py`
5. **Refactor _check_agent_status**: Replace inline logic with helper calls
6. **Add comprehensive tests**: Implement the test suite
7. **Run tests**: Ensure all tests pass
8. **Integration test**: Test the refactored monitor in a live environment

## Benefits

1. **Testability**: Each helper function can be unit tested independently
2. **Readability**: Clear function names describe what each part does
3. **Maintainability**: Changes to detection logic are isolated
4. **Reusability**: Helper functions can be used elsewhere
5. **Debugging**: Easier to debug specific detection issues
6. **Documentation**: Each function has a clear, single responsibility

## Migration Notes

- The refactored code maintains backward compatibility
- No changes to the public API
- Internal behavior remains identical
- Performance should be similar or better due to clearer logic flow

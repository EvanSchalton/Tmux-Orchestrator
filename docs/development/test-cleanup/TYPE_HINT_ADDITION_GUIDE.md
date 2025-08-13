# Type Hint Addition Guide for Test Files

## Overview

Following the successful completion of Phase 3 file splitting, the next enhancement is adding type hints to all test functions and fixtures. This guide provides patterns and examples for consistent type hint implementation.

## Current State

From the pattern compliance audit:
- **~90% of test functions lack type hints**
- **Most fixtures lack return type annotations**
- **Some imports for typing are missing**

## Type Hint Patterns for Tests

### 1. Test Functions

All test functions should have `-> None` return type:

```python
# ❌ Current (missing type hint)
def test_agent_spawn():
    """Test agent spawning."""
    pass

# ✅ With type hint
def test_agent_spawn() -> None:
    """Test agent spawning."""
    pass
```

### 2. Fixtures

All fixtures should have typed returns:

```python
# ❌ Current
@pytest.fixture
def mock_tmux():
    return Mock(spec=TMUXManager)

# ✅ With type hints
from unittest.mock import Mock
from typing import Generator

@pytest.fixture
def mock_tmux() -> Mock:
    """Create a mock TMUXManager."""
    return Mock(spec=TMUXManager)

# For fixtures with cleanup
@pytest.fixture
def temp_file() -> Generator[Path, None, None]:
    """Create a temporary file."""
    file = Path("temp.txt")
    file.touch()
    yield file
    file.unlink()
```

### 3. Common Fixture Types

```python
from typing import Any, Dict, List, Generator
from pathlib import Path
from unittest.mock import Mock, MagicMock
from click.testing import CliRunner
import pytest

# Simple fixtures
@pytest.fixture
def cli_runner() -> CliRunner:
    return CliRunner()

@pytest.fixture
def sample_data() -> Dict[str, Any]:
    return {"key": "value"}

@pytest.fixture
def agent_list() -> List[Dict[str, str]]:
    return [{"id": "1", "type": "developer"}]

# Mock fixtures
@pytest.fixture
def mock_function() -> Mock:
    return Mock(return_value="success")

# Generator fixtures (with cleanup)
@pytest.fixture
def temp_directory() -> Generator[Path, None, None]:
    dir_path = Path("temp_dir")
    dir_path.mkdir()
    yield dir_path
    shutil.rmtree(dir_path)
```

### 4. Parametrized Tests

```python
from typing import Optional

@pytest.mark.parametrize(
    "input_value,expected",
    [
        ("valid", True),
        ("", False),
        (None, False),
    ],
)
def test_validation(input_value: Optional[str], expected: bool) -> None:
    """Test input validation."""
    assert validate(input_value) == expected
```

### 5. Test Function Parameters

```python
# With fixtures
def test_agent_operations(
    mock_tmux: Mock,
    cli_runner: CliRunner,
    sample_data: Dict[str, Any]
) -> None:
    """Test agent operations."""
    pass

# With monkeypatch
def test_with_patch(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test with monkeypatch."""
    monkeypatch.setenv("TEST_VAR", "value")
```

## Implementation Strategy

### Phase 1: Add Missing Imports (Batch Operation)
Add these imports to test files as needed:
```python
from typing import Any, Dict, List, Optional, Generator, Union
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path
```

### Phase 2: Update Test Functions (File by File)
1. Start with recently split files (already clean and organized)
2. Add `-> None` to all test functions
3. Add parameter types where fixtures are used

### Phase 3: Update Fixtures (Global then Local)
1. Update global fixtures in `conftest.py`
2. Update local fixtures in individual test files
3. Ensure consistency across related fixtures

## Quick Reference Cheat Sheet

```python
# Test function
def test_something() -> None:

# Fixture returning simple type
@pytest.fixture
def my_string() -> str:

# Fixture returning mock
@pytest.fixture
def mock_obj() -> Mock:

# Fixture with cleanup
@pytest.fixture
def resource() -> Generator[Resource, None, None]:

# Common parameter types
mock_tmux: Mock
cli_runner: CliRunner
monkeypatch: pytest.MonkeyPatch
tmp_path: Path
capsys: pytest.CaptureFixture[str]
caplog: pytest.LogCaptureFixture
```

## Validation Checklist

After adding type hints:
- [ ] All test functions have `-> None`
- [ ] All fixtures have return type annotations
- [ ] Required typing imports are present
- [ ] No mypy errors in test files
- [ ] Tests still pass

## Common Pitfalls to Avoid

1. **Don't over-type**: Keep it simple for test code
2. **Avoid complex generics**: Tests should be readable
3. **Don't type pytest built-ins**: Like `request` fixture
4. **Be consistent**: Use same types for similar fixtures

## Example File Transformation

### Before
```python
import pytest
from unittest.mock import Mock

@pytest.fixture
def mock_client():
    return Mock()

def test_client_connect(mock_client):
    mock_client.connect.return_value = True
    assert mock_client.connect("localhost") is True
```

### After
```python
import pytest
from unittest.mock import Mock

@pytest.fixture
def mock_client() -> Mock:
    """Create a mock client."""
    return Mock()

def test_client_connect(mock_client: Mock) -> None:
    """Test client connection."""
    mock_client.connect.return_value = True
    assert mock_client.connect("localhost") is True
```

## Estimated Effort

- **Total test files**: 58
- **Average time per file**: 3-5 minutes
- **Total estimated time**: 3-5 hours
- **Recommendation**: Process in batches of 10-15 files

---
*Type hints improve code clarity and catch potential issues early. This guide ensures consistent implementation across the test suite.*

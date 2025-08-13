# Type Hint Patterns for Test Files

## Quick Reference Guide

### 1. Test Functions - Always `-> None`
```python
def test_something() -> None:
    """All test functions return None."""
    assert True

def test_with_fixtures(mock_tmux: Mock, cli_runner: CliRunner) -> None:
    """Test functions with fixtures also return None."""
    result = cli_runner.invoke(some_command)
    assert result.exit_code == 0
```

### 2. Mock Fixtures - Use `Mock` Type
```python
from unittest.mock import Mock

@pytest.fixture
def mock_tmux() -> Mock:
    """Mock fixtures return Mock type."""
    mock = Mock(spec=TMUXManager)
    mock.list_sessions.return_value = []
    return mock

@pytest.fixture
def mock_client() -> Mock:
    """Another mock example."""
    return Mock()
```

### 3. Response/Data Fixtures - Use Specific Types
```python
from typing import Dict, List, Any
from pathlib import Path

@pytest.fixture
def sample_agent_data() -> Dict[str, Any]:
    """Data fixtures use specific types."""
    return {
        "agent_id": "test-agent",
        "status": "active",
        "metadata": {"key": "value"}
    }

@pytest.fixture
def agent_list() -> List[Dict[str, str]]:
    """List fixtures specify full type."""
    return [
        {"id": "agent-1", "type": "developer"},
        {"id": "agent-2", "type": "pm"}
    ]
```

### 4. File/Path Fixtures - Use Generator Pattern
```python
from typing import Generator
from pathlib import Path
import tempfile

@pytest.fixture
def temp_activity_file() -> Generator[Path, None, None]:
    """File fixtures that clean up use Generator."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        temp_path = Path(f.name)
        json.dump([], f)
    yield temp_path
    # Cleanup
    if temp_path.exists():
        temp_path.unlink()
```

### 5. Common Test Fixture Types
```python
# Click CLI testing
from click.testing import CliRunner

@pytest.fixture
def cli_runner() -> CliRunner:
    return CliRunner()

# String fixtures
@pytest.fixture
def api_key() -> str:
    return "test-api-key-123"

# Boolean fixtures
@pytest.fixture
def debug_mode() -> bool:
    return True

# Datetime fixtures
from datetime import datetime

@pytest.fixture
def test_timestamp() -> datetime:
    return datetime(2024, 1, 15, 10, 0, 0)
```

### 6. Parametrized Test Type Hints
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
    """Parameters get typed based on test data."""
    assert validate(input_value) == expected
```

### 7. Common Imports Needed
```python
# Add these imports as needed
from typing import Any, Dict, List, Optional, Generator, Union
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path
from datetime import datetime
from click.testing import CliRunner
```

## Conversion Checklist
When adding type hints to a test file:

- [ ] Add `-> None` to all `def test_*()` functions
- [ ] Add return types to all fixtures
- [ ] Import necessary types from `typing` module
- [ ] Import `Mock` from `unittest.mock` if using mocks
- [ ] Run tests to ensure no breakage
- [ ] Optional: Run mypy to check for type errors

## Common Patterns by Test Type

### CLI Tests
```python
def test_cli_command(cli_runner: CliRunner, mock_tmux: Mock) -> None:
    """CLI tests often use CliRunner and mocks."""
    result = cli_runner.invoke(agent, ["list"])
    assert result.exit_code == 0
```

### API/Tool Tests
```python
def test_api_tool(mock_tmux: Mock, sample_request: Dict[str, Any]) -> None:
    """API tests use mocks and data fixtures."""
    response = some_api_function(mock_tmux, sample_request)
    assert response["status"] == "success"
```

### Integration Tests
```python
def test_integration(
    mock_tmux: Mock,
    temp_file: Path,
    sample_data: List[Dict[str, str]]
) -> None:
    """Integration tests often combine multiple fixtures."""
    # Test implementation
    pass
```

---
*Use this guide to ensure consistent type hints across all test files.*

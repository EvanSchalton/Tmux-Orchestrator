# Common Conversion Errors Checklist

## 🔴 Critical Errors to Watch For

### 1. Missing Imports
```python
# ❌ Forgot to import pytest
@pytest.fixture  # NameError!
def my_fixture():
    pass

# ✅ Correct
import pytest

@pytest.fixture
def my_fixture():
    pass
```

### 2. Incorrect Fixture Scope
```python
# ❌ Module scope for mutable objects
@pytest.fixture(scope="module")
def mock_manager():
    return Mock()  # Shared mock = test interference!

# ✅ Function scope for mocks
@pytest.fixture
def mock_manager():
    return Mock()  # Fresh mock per test
```

### 3. Lost Test Functionality
```python
# ❌ Lost assertion during conversion
# Before:
def test_something(self):
    result = self.helper.process()
    self.assertEqual(result.status, "ok")
    self.assertIn("data", result)  # This line missing!

# After (incorrect):
def test_something(helper):
    result = helper.process()
    assert result.status == "ok"
    # Missing: assert "data" in result
```

### 4. Self Reference Not Removed
```python
# ❌ Forgot to remove self
def test_something(mock_tmux):
    self.mock_tmux.read_pane.return_value = "test"  # Error!

# ✅ Correct
def test_something(mock_tmux):
    mock_tmux.read_pane.return_value = "test"
```

### 5. Setup Method Not Fully Converted
```python
# ❌ Partial conversion
def test_something():
    # setup_method code copied here
    self.data = {"key": "value"}  # Still has self!
    assert self.data["key"] == "value"

# ✅ Proper fixture
@pytest.fixture
def test_data():
    return {"key": "value"}

def test_something(test_data):
    assert test_data["key"] == "value"
```

### 6. Wrong Assertion Conversion
```python
# ❌ Incorrect conversions
assert a.assertEqual(b)  # Wrong!
assert not x.assertTrue()  # Wrong!

# ✅ Correct pytest assertions
assert a == b
assert x
assert a != b
assert not x
assert a in b
```

### 7. Lost Setup/Teardown Logic
```python
# ❌ Only converted setup, forgot teardown
@pytest.fixture
def temp_file():
    file = create_temp_file()
    return file  # No cleanup!

# ✅ Complete conversion with cleanup
@pytest.fixture
def temp_file():
    file = create_temp_file()
    yield file
    file.unlink()  # Cleanup preserved
```

### 8. Fixture Dependency Issues
```python
# ❌ Fixture tries to use instance variable
@pytest.fixture
def helper(self):  # Can't have self!
    return Helper(self.config)

# ✅ Proper fixture composition
@pytest.fixture
def config():
    return {"timeout": 30}

@pytest.fixture
def helper(config):
    return Helper(config)
```

### 9. Test Discovery Issues
```python
# ❌ Test not discoverable
def something_test():  # Wrong pattern!
    pass

class TestHelpers:  # Still a class!
    def test_something(self):
        pass

# ✅ Discoverable tests
def test_something():  # Correct pattern
    pass
```

### 10. Parameterization Lost
```python
# ❌ Lost test variations
# Before (multiple test methods):
def test_with_empty(self):
    self._test_helper("")

def test_with_data(self):
    self._test_helper("data")

# After (lost variation):
def test_helper():
    # Only tests one case!

# ✅ Proper parameterization
@pytest.mark.parametrize("input_data", ["", "data", None])
def test_helper(input_data):
    # Tests all cases
```

## 🟡 Common Fixture Issues

### 1. Fixture Not Found
```python
# ❌ Fixture in wrong location
# test_file.py uses fixture but it's not in same file or conftest.py

# ✅ Place shared fixtures in conftest.py
# tests/conftest.py or tests/test_server/conftest.py
```

### 2. Circular Fixture Dependencies
```python
# ❌ Circular dependency
@pytest.fixture
def fixture_a(fixture_b):
    return fixture_b + 1

@pytest.fixture
def fixture_b(fixture_a):
    return fixture_a + 1
```

### 3. Fixture Scope Mismatch
```python
# ❌ Function-scoped fixture using module-scoped
@pytest.fixture(scope="module")
def database():
    return setup_db()

@pytest.fixture  # function scope
def user(database):  # Error: scope mismatch
    return database.create_user()
```

## 🟢 Validation Steps After Conversion

### 1. Syntax Check
```bash
# Check for basic Python errors
python -m py_compile tests/converted_file_test.py
```

### 2. Import Check
```bash
# Verify all imports work
python -c "import tests.converted_file_test"
```

### 3. Test Discovery
```bash
# Ensure pytest finds all tests
poetry run pytest tests/converted_file_test.py --collect-only
```

### 4. Fixture Resolution
```bash
# Check fixtures are found
poetry run pytest tests/converted_file_test.py --fixtures
```

### 5. Run Tests
```bash
# Run with verbose output
poetry run pytest tests/converted_file_test.py -v
```

### 6. Coverage Check
```bash
# Ensure same coverage
poetry run pytest tests/converted_file_test.py --cov=tmux_orchestrator --cov-report=term-missing
```

## Quick Validation Script

```bash
#!/bin/bash
FILE=$1

echo "=== Validating $FILE ==="

# 1. Check for common errors
echo "Checking for common issues..."
grep -n "self\." "$FILE" && echo "⚠️  Found self references!"
grep -n "class Test" "$FILE" && echo "⚠️  Found test classes!"
grep -n "setUp\|tearDown" "$FILE" && echo "⚠️  Found setup/teardown methods!"
grep -n "unittest" "$FILE" && echo "⚠️  Found unittest imports!"

# 2. Test discovery
echo -e "\nChecking test discovery..."
poetry run pytest "$FILE" --collect-only -q

# 3. Run tests
echo -e "\nRunning tests..."
poetry run pytest "$FILE" -v

# 4. Final check
echo -e "\nFinal validation..."
python docs/development/test-cleanup/phase2_conversion_monitor.py validate "$FILE"
```

## Red Flags in Git Diff

When reviewing `git diff`:

1. **Large deletions with small additions** - Possible test loss
2. **No pytest import added** - Tests won't run
3. **setUp but no @pytest.fixture** - Setup not converted
4. **Many `assert True`** - Assertions might be broken
5. **Commented out code** - Functionality might be lost

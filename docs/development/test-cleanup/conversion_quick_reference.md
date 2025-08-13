# Test Class Conversion Quick Reference

## Common Conversions

### 1. Basic Test Class
```python
# ❌ Before
class TestMyFeature:
    def test_basic_case(self):
        assert True

# ✅ After
def test_my_feature_basic_case():
    assert True
```

### 2. Setup Method → Fixture
```python
# ❌ Before
class TestWithSetup:
    def setup_method(self):
        self.client = create_client()
        self.data = {"key": "value"}

    def test_client_call(self):
        result = self.client.call(self.data)
        assert result.status == "ok"

# ✅ After
@pytest.fixture
def client():
    return create_client()

@pytest.fixture
def test_data():
    return {"key": "value"}

def test_with_setup_client_call(client, test_data):
    result = client.call(test_data)
    assert result.status == "ok"
```

### 3. SetUpClass → Module Fixture
```python
# ❌ Before
class TestExpensive:
    @classmethod
    def setUpClass(cls):
        cls.db = setup_database()

    def test_query(self):
        result = self.db.query("SELECT 1")
        assert result == 1

# ✅ After
@pytest.fixture(scope="module")
def database():
    db = setup_database()
    yield db
    db.close()  # cleanup

def test_expensive_query(database):
    result = database.query("SELECT 1")
    assert result == 1
```

### 4. unittest.TestCase Assertions
```python
# ❌ Before (unittest)
self.assertEqual(a, b)
self.assertNotEqual(a, b)
self.assertTrue(x)
self.assertFalse(x)
self.assertIn(a, b)
self.assertIsNone(x)
self.assertRaises(Error, func)

# ✅ After (pytest)
assert a == b
assert a != b
assert x
assert not x
assert a in b
assert x is None
with pytest.raises(Error):
    func()
```

### 5. Grouping Related Tests
```python
# ❌ Before - Large class
class TestUserAPI:
    def test_create_user(self): ...
    def test_update_user(self): ...
    def test_delete_user(self): ...
    # ... 20 more methods

# ✅ After - Split by operation
# In test_user_api_create.py
def test_user_api_create_valid(): ...
def test_user_api_create_invalid(): ...

# In test_user_api_update.py
def test_user_api_update_valid(): ...
def test_user_api_update_partial(): ...

# In test_user_api_delete.py
def test_user_api_delete_existing(): ...
def test_user_api_delete_missing(): ...
```

### 6. Shared Fixtures in conftest.py
```python
# In tests/conftest.py or tests/test_server/conftest.py
@pytest.fixture
def mock_tmux():
    """Shared tmux mock for all tests in this directory."""
    return Mock(spec=TMUXManager)

@pytest.fixture
def test_session_id():
    """Consistent test session ID."""
    return "test-session:0"
```

## Validation After Each Conversion

```bash
# 1. Check the specific file
python docs/development/test-cleanup/phase2_conversion_monitor.py validate tests/your_file_test.py

# 2. Run the tests
poetry run pytest tests/your_file_test.py -v

# 3. Check for remaining classes
grep "class Test" tests/your_file_test.py

# 4. Verify test count preserved
poetry run pytest tests/your_file_test.py --collect-only -q
```

## Red Flags to Avoid

❌ Don't lose test coverage during conversion
❌ Don't change test behavior (only structure)
❌ Don't create test dependencies
❌ Don't forget to convert ALL setup/teardown methods
❌ Don't mix unittest and pytest patterns in same file

## Tips

✅ Convert one class at a time
✅ Run tests after each class conversion
✅ Use descriptive fixture names
✅ Keep fixtures close to usage (unless shared)
✅ Commit after each successful file conversion

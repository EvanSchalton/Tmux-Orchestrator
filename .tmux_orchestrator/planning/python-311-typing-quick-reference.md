# Python 3.11+ Typing Modernization - Quick Reference Guide

## Common Transformations

### 1. Optional Types
```python
# ❌ Old
from typing import Optional
value: Optional[str] = None
def get_name() -> Optional[str]:

# ✅ New
value: str | None = None
def get_name() -> str | None:
```

### 2. Basic Collections
```python
# ❌ Old
from typing import List, Dict, Set, Tuple
items: List[str] = []
mapping: Dict[str, int] = {}
unique: Set[int] = set()
pair: Tuple[str, int] = ("a", 1)

# ✅ New
items: list[str] = []
mapping: dict[str, int] = {}
unique: set[int] = set()
pair: tuple[str, int] = ("a", 1)
```

### 3. Union Types
```python
# ❌ Old
from typing import Union
result: Union[str, int] = "hello"
value: Union[Dict[str, Any], List[str]] = {}

# ✅ New
result: str | int = "hello"
value: dict[str, Any] | list[str] = {}
```

### 4. Complex Nested Types
```python
# ❌ Old
from typing import List, Dict, Optional, Tuple
data: List[Dict[str, Optional[int]]] = []
result: Tuple[bool, Optional[str], List[str]] = (True, None, [])

# ✅ New
data: list[dict[str, int | None]] = []
result: tuple[bool, str | None, list[str]] = (True, None, [])
```

## Import Cleanup Rules

### Remove These Imports
```python
# Remove completely - use built-in types
from typing import List, Dict, Set, Tuple, Optional, Union

# Keep these (still needed from typing)
from typing import Any, Callable, TypeVar, Protocol, Literal, Final
```

### Example Import Transformation
```python
# ❌ Old
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime

# ✅ New
from typing import Any, Callable  # Only keep what's still needed
from datetime import datetime
```

## Special Cases

### 1. Default None Parameters
```python
# Both work, but be consistent
def process(data: str | None = None):  # Preferred
def process(data: Optional[str] = None):  # Still valid but old style
```

### 2. Multiple Union Types
```python
# ❌ Old
Union[str, int, float, None]

# ✅ New
str | int | float | None
```

### 3. Callable Types (Keep from typing)
```python
from typing import Callable
handler: Callable[[str], None] = lambda x: print(x)
```

## DO NOT Transform These

1. **Type aliases** - May need `from typing import TypeAlias`
2. **Generic types** - Still need `TypeVar`, `Generic`
3. **Protocols** - Still need `from typing import Protocol`
4. **Special forms** - `Literal`, `Final`, `ClassVar`, etc.

## Testing Checklist

- [ ] All imports updated
- [ ] All type hints modernized
- [ ] Tests pass: `pytest <test_file>`
- [ ] Mypy passes: `mypy <module>`
- [ ] No circular imports
- [ ] Code still readable

## Common Mistakes to Avoid

1. **Don't forget nested types**
   ```python
   # Easy to miss the inner List
   Dict[str, List[int]] → dict[str, list[int]]
   ```

2. **Don't remove all typing imports**
   ```python
   # Still need Any, Callable, etc.
   from typing import Any  # Keep this!
   ```

3. **Watch for string annotations**
   ```python
   # Forward references still need quotes
   def process(self) -> 'MyClass':  # Keep quotes
   ```

## Regex Patterns for Search/Replace

```regex
# Find Optional patterns
Optional\[([^\]]+)\]  → $1 | None

# Find List patterns
List\[([^\]]+)\]  → list[$1]

# Find Dict patterns
Dict\[([^,]+),\s*([^\]]+)\]  → dict[$1, $2]

# Find simple Union (2 types)
Union\[([^,]+),\s*([^\]]+)\]  → $1 | $2
```

---
*Use this guide for consistent transformations across all modules*

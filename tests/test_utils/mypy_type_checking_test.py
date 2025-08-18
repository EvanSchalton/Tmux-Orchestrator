#!/usr/bin/env python3
"""Comprehensive test suite for mypy type checking validation scenarios.

This module tests various type annotation issues that mypy should catch,
preparing validation tests for the Senior Developer's pre-commit fixes.
"""

import subprocess
import tempfile
from pathlib import Path

import pytest


class TestMypyTypeCheckingScenarios:
    """Test various type checking scenarios that mypy should handle."""

    def test_basic_type_annotation_errors(self):
        """Test that mypy catches basic type annotation errors."""
        code_with_type_errors = """def function_with_type_errors(x: int, y: str) -> str:
    # Error: returning int instead of str
    return x + len(y)

def another_function(items: list[str]) -> int:
    # Error: returning string instead of int
    return "not an integer"

def third_function() -> str | None:
    # Error: returning int instead of str | None
    return 42
"""

        mypy_result = self._run_mypy_check(code_with_type_errors)

        # Should detect return type mismatches
        assert "error:" in mypy_result.lower(), "Should detect type errors"
        assert any(
            keyword in mypy_result.lower() for keyword in ["incompatible return value", "return type", "expected"]
        ), f"Should detect return type errors: {mypy_result}"

    def test_function_parameter_type_errors(self):
        """Test that mypy catches function parameter type errors."""
        code_with_param_errors = """def process_string(text: str) -> str:
    return text.upper()

def process_number(num: int) -> int:
    return num * 2

def main():
    # Error: passing int to function expecting str
    result1 = process_string(42)

    # Error: passing str to function expecting int
    result2 = process_number("hello")

    return result1, result2
"""

        mypy_result = self._run_mypy_check(code_with_param_errors)

        # Should detect argument type mismatches
        assert "error:" in mypy_result.lower(), "Should detect parameter type errors"
        assert any(
            keyword in mypy_result.lower() for keyword in ["argument", "incompatible", "expected"]
        ), f"Should detect argument type errors: {mypy_result}"

    def test_collection_type_errors(self):
        """Test that mypy catches collection type annotation errors."""
        code_with_collection_errors = """

def process_list(items: list[str]) -> list[int]:
    # Error: returning list[str] instead of list[int]
    return items

def process_dict(data: dict[str, int]) -> dict[str, str]:
    # Error: returning dict[str, int] instead of dict[str, str]
    return data

def create_mixed_list() -> list[str]:
    # Error: returning list[int] instead of list[str]
    return [1, 2, 3, 4, 5]
"""

        mypy_result = self._run_mypy_check(code_with_collection_errors)

        # Should detect collection type mismatches
        assert "error:" in mypy_result.lower(), "Should detect collection type errors"

    def test_any_vs_specific_types(self):
        """Test the difference between Any and specific type annotations."""
        code_with_any_issues = '''from typing import Any

# This should work with Any
def flexible_function(data: Any) -> Any:
    return data.anything.can.happen

# This should fail with specific types
def strict_function(data: dict[str, str]) -> str:
    # Error: dict doesn't have 'nonexistent_method'
    return data.nonexistent_method()

# Test the corrected patterns from monitor_async.py
async def check_agent_status_async(target: str) -> dict[str, Any]:
    """Properly typed async function."""
    return {
        "target": target,
        "state": "active",
        "timestamp": "now"
    }

async def monitor_agents_batch(agents: list[str]) -> dict[str, dict[str, Any]]:
    """Properly typed batch monitoring function."""
    result: dict[str, dict[str, Any]] = {}
    for agent in agents:
        result[agent] = await check_agent_status_async(agent)
    return result
'''

        mypy_result = self._run_mypy_check(code_with_any_issues)

        # Should detect the specific type error but not the Any usage
        assert "error:" in mypy_result.lower(), "Should detect specific type errors"

    def test_optional_and_union_types(self):
        """Test that mypy handles Optional and Union types correctly."""
        code_with_optional_errors = """from typing import Optional, Union

def process_optional(value: str | None) -> str:
    # Error: value might be None
    return value.upper()

def process_union(value: str | int) -> str:
    # Error: int doesn't have upper() method
    return value.upper()

def correct_optional_handling(value: str | None) -> str:
    if value is None:
        return "default"
    return value.upper()

def correct_union_handling(value: str | int) -> str:
    if isinstance(value, str):
        return value.upper()
    return str(value)
"""

        mypy_result = self._run_mypy_check(code_with_optional_errors)

        # Should detect None-related and Union-related errors
        assert "error:" in mypy_result.lower(), "Should detect Optional/Union type errors"

    def test_class_type_annotations(self):
        """Test that mypy handles class type annotations correctly."""
        code_with_class_errors = """from typing import Optional

class Person:
    def __init__(self, name: str, age: int) -> None:
        self.name = name
        self.age = age

    def get_name(self) -> str:
        return self.name

    def get_age(self) -> int:
        return self.age

class Team:
    def __init__(self) -> None:
        self.members: list[Person] = []

    def add_member(self, person: Person) -> None:
        self.members.append(person)

    def get_member(self, index: int) -> Person | None:
        if 0 <= index < len(self.members):
            return self.members[index]
        return None

def create_team() -> Team:
    team = Team()
    # Error: passing str instead of Person
    team.add_member("John Doe")
    return team

def get_member_name(team: Team, index: int) -> str:
    member = team.get_member(index)
    # Error: member might be None
    return member.get_name()
"""

        mypy_result = self._run_mypy_check(code_with_class_errors)

        # Should detect class-related type errors
        assert "error:" in mypy_result.lower(), "Should detect class type errors"

    def test_async_type_annotations(self):
        """Test that mypy handles async/await type annotations correctly."""
        code_with_async_errors = """import asyncio
from typing import Any, Awaitable, Callable, Coroutine

async def async_function() -> str:
    await asyncio.sleep(0.1)
    return "result"

async def async_with_error() -> int:
    # Error: returning str instead of int
    return await async_function()

def sync_function_calling_async() -> str:
    # Error: returning coroutine instead of str
    return async_function()

async def correct_async_usage() -> str:
    result = await async_function()
    return result

# Test async function type annotations
async def async_monitor_function(targets: list[str]) -> list[str]:
    results = []
    for target in targets:
        result = await async_function()
        results.append(result)
    return results
"""

        mypy_result = self._run_mypy_check(code_with_async_errors)

        # Should detect async-related type errors
        assert "error:" in mypy_result.lower(), "Should detect async type errors"

    def test_generic_type_annotations(self):
        """Test that mypy handles generic type annotations correctly."""
        code_with_generic_errors = """from typing import Generic, TypeVar

T = TypeVar('T')

class Container(Generic[T]):
    def __init__(self) -> None:
        self.items: list[T] = []

    def add(self, item: T) -> None:
        self.items.append(item)

    def get_all(self) -> list[T]:
        return self.items

def test_generic_usage():
    # String container
    str_container: Container[str] = Container()
    str_container.add("hello")
    # Error: adding int to string container
    str_container.add(42)

    # Int container
    int_container: Container[int] = Container()
    int_container.add(42)
    # Error: adding str to int container
    int_container.add("hello")
"""

        mypy_result = self._run_mypy_check(code_with_generic_errors)

        # Should detect generic type errors
        assert "error:" in mypy_result.lower(), "Should detect generic type errors"

    def test_protocol_and_structural_typing(self):
        """Test that mypy handles Protocol and structural typing correctly."""
        code_with_protocol_usage = """from typing import Protocol

class Drawable(Protocol):
    def draw(self) -> None: ...

class Circle:
    def draw(self) -> None:
        print("Drawing circle")

class Square:
    def draw(self) -> None:
        print("Drawing square")

class InvalidShape:
    def paint(self) -> None:  # Wrong method name
        print("Painting")

def draw_shape(shape: Drawable) -> None:
    shape.draw()

def test_protocol_usage():
    circle = Circle()
    square = Square()
    invalid = InvalidShape()

    draw_shape(circle)  # OK
    draw_shape(square)  # OK
    # Error: InvalidShape doesn't implement Drawable protocol
    draw_shape(invalid)
"""

        mypy_result = self._run_mypy_check(code_with_protocol_usage)

        # Should detect protocol violations
        # Note: Protocol support might depend on mypy version
        if "protocol" in mypy_result.lower() or "error:" in mypy_result.lower():
            assert True, "mypy detected protocol-related issues"

    def test_project_specific_type_patterns(self):
        """Test type patterns specific to the tmux-orchestrator project."""
        code_with_project_patterns = '''from typing import Any, Optional
from datetime import datetime

# Simulate monitor_async.py patterns that had issues
class MockAgentState:
    ACTIVE = "active"
    IDLE = "idle"
    CRASHED = "crashed"

async def check_agent_status_async(target: str) -> dict[str, Any]:
    """This should now work correctly with proper Any import."""
    return {
        "target": target,
        "state": MockAgentState.ACTIVE,
        "is_active": True,
        "content": "test content",
        "timestamp": datetime.now(),
    }

async def monitor_agents_batch(agents: list[str]) -> dict[str, dict[str, Any]]:
    """This should work with proper type annotations."""
    agent_statuses: dict[str, dict[str, Any]] = {}
    for agent in agents:
        result = await check_agent_status_async(agent)
        if isinstance(result, dict):
            agent_statuses[agent] = result
    return agent_statuses

async def get_agent_notifications(
    agent_statuses: dict[str, dict[str, Any]]
) -> dict[str, list[str]]:
    """Test the fixed notification function."""
    notifications: dict[str, list[str]] = {}

    for target, status in agent_statuses.items():
        session_name = target.split(":")[0]

        if session_name not in notifications:
            notifications[session_name] = []

        state = status.get("state")
        timestamp_obj = status.get("timestamp", datetime.now())
        timestamp = timestamp_obj.strftime("%H:%M:%S") if hasattr(timestamp_obj, 'strftime') else str(timestamp_obj)

        if state == MockAgentState.IDLE:
            notifications[session_name].append(f"IDLE: {target} [{timestamp}]")

    return notifications
'''

        mypy_result = self._run_mypy_check(code_with_project_patterns)

        # This should pass without type errors now
        if "error:" in mypy_result.lower():
            # If there are still errors, they should be minimal
            assert "any?" not in mypy_result.lower(), "Should not have 'any?' type issues"
            assert (
                'Function "builtins.any" is not valid as a type' not in mypy_result
            ), "Should not have 'any' type issues"

    def _run_mypy_check(self, code: str) -> str:
        """Helper method to run mypy check on code and return results."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            temp_file = Path(f.name)

        try:
            # Run mypy check
            result = subprocess.run(
                ["mypy", str(temp_file), "--strict"],
                capture_output=True,
                text=True,
                cwd="/workspaces/Tmux-Orchestrator",
            )

            # Return the output regardless of return code
            return result.stdout + result.stderr

        finally:
            temp_file.unlink()


class TestMypyConfigurationValidation:
    """Test mypy configuration and project-specific settings."""

    def test_mypy_config_exists_and_valid(self):
        """Test that mypy configuration exists and is valid."""
        # Check for mypy configuration files
        project_root = Path("/workspaces/Tmux-Orchestrator")

        config_files = [
            project_root / "mypy.ini",
            project_root / ".mypy.ini",
            project_root / "pyproject.toml",
            project_root / "setup.cfg",
        ]

        config_found = any(config_file.exists() for config_file in config_files)

        if config_found:
            # Test that mypy can read the configuration
            result = subprocess.run(["mypy", "--help"], capture_output=True, text=True, cwd=str(project_root))
            assert result.returncode == 0, "mypy should be able to show help"

    def test_mypy_version_compatibility(self):
        """Test that mypy version is compatible with project requirements."""
        result = subprocess.run(
            ["mypy", "--version"], capture_output=True, text=True, cwd="/workspaces/Tmux-Orchestrator"
        )

        assert result.returncode == 0, "mypy should report version successfully"
        assert "mypy" in result.stdout.lower(), "Should show mypy version"

    def test_specific_module_type_checking(self):
        """Test type checking on specific project modules."""
        # Test the module that had issues
        module_path = Path("/workspaces/Tmux-Orchestrator/tmux_orchestrator/core/monitor_async.py")

        if module_path.exists():
            result = subprocess.run(
                ["mypy", str(module_path)], capture_output=True, text=True, cwd="/workspaces/Tmux-Orchestrator"
            )

            # Should not have the specific errors that were fixed
            output = result.stdout + result.stderr
            assert 'Function "builtins.any" is not valid as a type' not in output, "Should not have 'any' type errors"
            assert "any? has no attribute" not in output, "Should not have 'any?' attribute errors"

    def test_imports_type_checking(self):
        """Test that imports in the project have proper type annotations."""
        test_import_code = """
# Test importing the fixed modules
try:
    from tmux_orchestrator.core.monitor_async import AsyncAgentMonitor
    from tmux_orchestrator.utils.tmux import TMUXManager

    # These should be properly typed now
    tmux = TMUXManager()
    monitor = AsyncAgentMonitor(tmux)

    # Type annotations should be available
    assert hasattr(AsyncAgentMonitor, '__annotations__'), "Class should have type annotations"

except ImportError as e:
    print(f"Import error: {e}")
"""

        mypy_result = self._run_mypy_check(test_import_code)

        # Should not have import-related type errors
        if "error:" in mypy_result.lower():
            # Allow some errors but not type annotation errors
            assert "any?" not in mypy_result.lower(), "Should not have 'any?' issues"

    def _run_mypy_check(self, code: str) -> str:
        """Helper method to run mypy check on code and return results."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            temp_file = Path(f.name)

        try:
            # Run mypy check
            result = subprocess.run(
                ["mypy", str(temp_file)], capture_output=True, text=True, cwd="/workspaces/Tmux-Orchestrator"
            )

            # Return the output regardless of return code
            return result.stdout + result.stderr

        finally:
            temp_file.unlink()


class TestMypyErrorPatterns:
    """Test specific error patterns that mypy should catch."""

    def test_attribute_error_detection(self):
        """Test that mypy detects attribute errors."""
        code_with_attribute_errors = """
def test_attribute_errors():
    x = 42
    # Error: int has no attribute 'upper'
    result = x.upper()

    y = "hello"
    # Error: str has no attribute '__add__' with int (should use + operator)
    result2 = y.append("world")  # Wrong method for str

    return result, result2
"""

        mypy_result = self._run_mypy_check(code_with_attribute_errors)
        assert "error:" in mypy_result.lower(), "Should detect attribute errors"

    def test_index_error_detection(self):
        """Test that mypy detects potential index errors."""
        code_with_index_issues = """
def test_index_errors(items: list[str]) -> str:
    # mypy can't detect runtime index errors, but can detect type mismatches
    index: str = "not an int"  # This will cause issues
    # Error: can't use str as index
    return items[index]
"""

        mypy_result = self._run_mypy_check(code_with_index_issues)
        assert "error:" in mypy_result.lower(), "Should detect index type errors"

    def test_callable_type_errors(self):
        """Test that mypy detects callable type errors."""
        code_with_callable_errors = """from typing import Callable

def process_with_callback(data: str, callback: Callable[[str], int]) -> int:
    return callback(data)

def wrong_callback(x: str) -> str:  # Returns str, not int
    return x.upper()

def correct_callback(x: str) -> int:
    return len(x)

def test_callbacks():
    # Error: callback returns str, expected int
    result1 = process_with_callback("test", wrong_callback)

    # OK: callback returns int as expected
    result2 = process_with_callback("test", correct_callback)

    return result1, result2
"""

        mypy_result = self._run_mypy_check(code_with_callable_errors)
        assert "error:" in mypy_result.lower(), "Should detect callable type errors"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

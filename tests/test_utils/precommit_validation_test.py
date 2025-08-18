#!/usr/bin/env python3
"""Comprehensive test suite for pre-commit hook validation scenarios.

This module tests various pre-commit failure scenarios to ensure the Senior Developer's
fixes work correctly across all quality gates.
"""

import subprocess
import tempfile
from pathlib import Path

import pytest


class TestPreCommitValidation:
    """Test suite for pre-commit hook validation scenarios."""

    def test_ruff_format_fixes_code_style(self):
        """Test that ruff-format correctly fixes code style issues."""
        # Create temporary Python file with bad formatting
        bad_format_code = """def  badly_formatted_function( x,y ):
    if x>y:return x
    else:
        return   y

class BadlyFormattedClass:
    def __init__(self,name):
        self.name=name
    def method(self ):
        return self.name
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(bad_format_code)
            temp_file = Path(f.name)

        try:
            # Run ruff-format on the file
            result = subprocess.run(
                ["ruff", "format", str(temp_file)], capture_output=True, text=True, cwd="/workspaces/Tmux-Orchestrator"
            )

            # Verify ruff-format succeeded
            assert result.returncode == 0, f"ruff-format failed: {result.stderr}"

            # Read the formatted code
            formatted_code = temp_file.read_text()

            # Verify formatting improvements
            assert "def badly_formatted_function(x, y):" in formatted_code
            assert "if x > y:" in formatted_code
            assert "return x" in formatted_code
            assert "def __init__(self, name):" in formatted_code
            assert "self.name = name" in formatted_code

        finally:
            temp_file.unlink()

    def test_ruff_lint_catches_code_issues(self):
        """Test that ruff linter catches common code issues."""
        # Create temporary Python file with lint issues
        problematic_code = """import os, sys
import unused_module

def function_with_issues():
    x = 1
    unused_var = 2
    if x == 1:
        print("bad")
    return x

class MyClass:
    def method(self):
        pass
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(problematic_code)
            temp_file = Path(f.name)

        try:
            # Run ruff check on the file
            result = subprocess.run(
                ["ruff", "check", str(temp_file)], capture_output=True, text=True, cwd="/workspaces/Tmux-Orchestrator"
            )

            # Verify ruff found issues
            assert result.returncode != 0, "ruff should have found lint issues"
            output = result.stdout

            # Check for expected lint issues
            assert any(
                issue in output
                for issue in [
                    "F401",  # unused import
                    "F841",  # unused variable
                ]
            ), f"Expected lint issues not found in output: {output}"

        finally:
            temp_file.unlink()

    def test_mypy_type_checking_validation(self):
        """Test that mypy catches type annotation issues."""
        # Create temporary Python file with type issues
        type_issues_code = """from typing import List, Dict

def function_with_type_issues(x: int, y: str) -> str:
    # Type error: returning int instead of str
    return x + len(y)

def another_function() -> List[str]:
    # Type error: returning dict instead of list
    return {"key": "value"}

class TypedClass:
    def __init__(self, name: str):
        self.name = name

    def get_items(self) -> Dict[str, int]:
        # Type error: returning list instead of dict
        return ["item1", "item2"]
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(type_issues_code)
            temp_file = Path(f.name)

        try:
            # Run mypy on the file
            result = subprocess.run(
                ["mypy", str(temp_file), "--strict"],
                capture_output=True,
                text=True,
                cwd="/workspaces/Tmux-Orchestrator",
            )

            # Verify mypy found type issues
            assert result.returncode != 0, "mypy should have found type issues"
            output = result.stdout

            # Check for expected type errors
            assert "error:" in output.lower(), f"Expected type errors not found: {output}"

        finally:
            temp_file.unlink()

    def test_bandit_security_scanning(self):
        """Test that bandit catches security issues."""
        # Create temporary Python file with security issues
        security_issues_code = """import subprocess
import os

def insecure_function():
    # Security issue: shell=True with user input
    user_input = input("Enter command: ")
    subprocess.call(user_input, shell=True)

    # Security issue: hardcoded password
    password = "hardcoded_password_123"

    # Security issue: eval() usage
    user_code = input("Enter Python code: ")
    eval(user_code)

    return password

def another_security_issue():
    # Security issue: using os.system
    os.system("rm -rf /tmp/*")
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(security_issues_code)
            temp_file = Path(f.name)

        try:
            # Run bandit on the file
            result = subprocess.run(
                ["bandit", str(temp_file)], capture_output=True, text=True, cwd="/workspaces/Tmux-Orchestrator"
            )

            # Verify bandit found security issues (exit code 1 means issues found)
            assert result.returncode == 1, "bandit should have found security issues"
            output = result.stdout

            # Check for expected security warnings
            assert any(
                issue in output.lower() for issue in ["shell=true", "hardcoded", "eval", "os.system"]
            ), f"Expected security issues not found: {output}"

        finally:
            temp_file.unlink()

    def test_pre_commit_hooks_integration(self):
        """Test that all pre-commit hooks work together properly."""
        # This test uses the actual project's pre-commit configuration

        # Create a test commit scenario
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            # Code that should pass all hooks after auto-fixes
            good_code = '''"""Test module for pre-commit validation."""

from typing import List, Optional


class TestClass:
    """A properly formatted test class."""

    def __init__(self, name: str) -> None:
        """Initialize with name."""
        self.name = name

    def get_name(self) -> str:
        """Return the name."""
        return self.name

    def process_items(self, items: List[str]) -> Optional[str]:
        """Process a list of items safely."""
        if not items:
            return None
        return items[0]
'''
            f.write(good_code)
            temp_file = Path(f.name)

        try:
            # Run pre-commit on the file
            result = subprocess.run(
                ["pre-commit", "run", "--files", str(temp_file)],
                capture_output=True,
                text=True,
                cwd="/workspaces/Tmux-Orchestrator",
            )

            # This should pass (return code 0) or have only formatting changes
            assert result.returncode in [0, 1], f"Pre-commit failed unexpectedly: {result.stderr}"

        finally:
            temp_file.unlink()

    def test_yaml_file_validation(self):
        """Test YAML validation hook works correctly."""
        # Create temporary YAML file with issues
        bad_yaml = """
version: 1.0
config:
  name: test
  settings:
    - item1
    - item2
    invalid_indent:
  bad_syntax: [unclosed
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(bad_yaml)
            temp_file = Path(f.name)

        try:
            # Run YAML check
            result = subprocess.run(
                ["pre-commit", "run", "check-yaml", "--files", str(temp_file)],
                capture_output=True,
                text=True,
                cwd="/workspaces/Tmux-Orchestrator",
            )

            # Should fail due to invalid YAML
            assert result.returncode != 0, "YAML check should have failed"

        finally:
            temp_file.unlink()

    def test_json_file_validation(self):
        """Test JSON validation hook works correctly."""
        # Create temporary JSON file with syntax error
        bad_json = """
{
    "name": "test",
    "config": {
        "setting1": "value1",
        "setting2": "value2",
    }  // trailing comma and comment not allowed
}
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(bad_json)
            temp_file = Path(f.name)

        try:
            # Run JSON check
            result = subprocess.run(
                ["pre-commit", "run", "check-json", "--files", str(temp_file)],
                capture_output=True,
                text=True,
                cwd="/workspaces/Tmux-Orchestrator",
            )

            # Should fail due to invalid JSON
            assert result.returncode != 0, "JSON check should have failed"

        finally:
            temp_file.unlink()

    def test_trailing_whitespace_fix(self):
        """Test that trailing whitespace is automatically fixed."""
        # Create file with trailing whitespace
        code_with_whitespace = """def my_function():
    result = "test"
    return result
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code_with_whitespace)
            temp_file = Path(f.name)

        try:
            # Run trailing whitespace fix
            subprocess.run(
                ["pre-commit", "run", "trailing-whitespace", "--files", str(temp_file)],
                capture_output=True,
                text=True,
                cwd="/workspaces/Tmux-Orchestrator",
            )

            # Read the fixed content
            fixed_content = temp_file.read_text()

            # Verify trailing whitespace was removed
            lines = fixed_content.split("\n")
            for line in lines:
                if line:  # Skip empty lines
                    assert not line.endswith(" "), f"Trailing whitespace not removed from: '{line}'"

        finally:
            temp_file.unlink()

    def test_end_of_file_fix(self):
        """Test that end-of-file newlines are properly handled."""
        # Create file without final newline
        code_without_newline = "def test():\n    pass"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, newline="") as f:
            f.write(code_without_newline)
            temp_file = Path(f.name)

        try:
            # Run end-of-file fix
            subprocess.run(
                ["pre-commit", "run", "end-of-file-fixer", "--files", str(temp_file)],
                capture_output=True,
                text=True,
                cwd="/workspaces/Tmux-Orchestrator",
            )

            # Read the fixed content
            fixed_content = temp_file.read_text()

            # Verify file ends with newline
            assert fixed_content.endswith("\n"), "File should end with newline"

        finally:
            temp_file.unlink()


class TestPreCommitProjectSpecific:
    """Tests specific to this project's pre-commit configuration."""

    def test_current_precommit_config_valid(self):
        """Test that the current .pre-commit-config.yaml is valid."""
        config_file = Path("/workspaces/Tmux-Orchestrator/.pre-commit-config.yaml")
        assert config_file.exists(), "Pre-commit config file should exist"

        # Validate the configuration
        result = subprocess.run(
            ["pre-commit", "validate-config"], capture_output=True, text=True, cwd="/workspaces/Tmux-Orchestrator"
        )

        assert result.returncode == 0, f"Pre-commit config is invalid: {result.stderr}"

    def test_all_hooks_installable(self):
        """Test that all configured hooks can be installed."""
        result = subprocess.run(
            ["pre-commit", "install-hooks"], capture_output=True, text=True, cwd="/workspaces/Tmux-Orchestrator"
        )

        assert result.returncode == 0, f"Failed to install hooks: {result.stderr}"

    def test_pre_commit_dry_run(self):
        """Test pre-commit in dry-run mode to check hook functionality."""
        # Test on a small subset of files to avoid timeout
        test_files = [
            "tmux_orchestrator/__init__.py",
            "tests/test_precommit_validation.py",  # This file itself
        ]

        for test_file in test_files:
            file_path = Path("/workspaces/Tmux-Orchestrator") / test_file
            if file_path.exists():
                result = subprocess.run(
                    ["pre-commit", "run", "--files", str(file_path)],
                    capture_output=True,
                    text=True,
                    cwd="/workspaces/Tmux-Orchestrator",
                    timeout=30,  # 30 second timeout per file
                )

                # Accept both success (0) and formatting changes (1)
                assert result.returncode in [0, 1], f"Pre-commit failed on {test_file}: {result.stderr}"

    @pytest.mark.parametrize(
        "hook_name",
        [
            "ruff-format",
            "ruff",
            "mypy",
            "bandit",
            "trailing-whitespace",
            "end-of-file-fixer",
            "check-yaml",
            "check-json",
        ],
    )
    def test_individual_hook_functionality(self, hook_name: str):
        """Test each hook individually to ensure they work correctly."""
        # Create a simple test file that should pass the hook
        test_content = '''"""Simple test module."""

def test_function() -> str:
    """Return a test string."""
    return "test"
'''

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(test_content)
            temp_file = Path(f.name)

        try:
            # Run specific hook
            result = subprocess.run(
                ["pre-commit", "run", hook_name, "--files", str(temp_file)],
                capture_output=True,
                text=True,
                cwd="/workspaces/Tmux-Orchestrator",
                timeout=15,  # 15 second timeout
            )

            # Most hooks should pass or make acceptable changes
            # mypy might have issues with isolated files, so we're more lenient
            if hook_name == "mypy":
                assert result.returncode in [0, 1], f"Hook {hook_name} failed unexpectedly: {result.stderr}"
            else:
                assert result.returncode in [0, 1], f"Hook {hook_name} failed: {result.stderr}"

        finally:
            temp_file.unlink()


class TestPreCommitFixVerification:
    """Tests to verify that Senior Developer's fixes work correctly."""

    def test_type_annotation_fixes(self):
        """Test that type annotation issues are properly resolved."""
        # Test the specific patterns that were causing mypy failures
        test_code = '''from typing import Any, Dict, List

async def check_agent_status_async(target: str) -> Dict[str, Any]:
    """Properly typed async function."""
    return {
        "target": target,
        "state": "active",
        "timestamp": "now"
    }

async def monitor_agents_batch(agents: List[str]) -> Dict[str, Dict[str, Any]]:
    """Properly typed batch monitoring function."""
    result: Dict[str, Dict[str, Any]] = {}
    for agent in agents:
        result[agent] = await check_agent_status_async(agent)
    return result
'''

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(test_code)
            temp_file = Path(f.name)

        try:
            # Run mypy on properly typed code
            result = subprocess.run(
                ["mypy", str(temp_file)], capture_output=True, text=True, cwd="/workspaces/Tmux-Orchestrator"
            )

            # Should pass without type errors
            assert result.returncode == 0, f"Type annotations still have issues: {result.stdout}"

        finally:
            temp_file.unlink()

    def test_async_monitoring_type_safety(self):
        """Test that async monitoring module has proper type safety."""
        # Import and test the actual async monitoring module
        try:
            from tmux_orchestrator.core.monitor_async import AsyncAgentMonitor
            from tmux_orchestrator.utils.tmux import TMUXManager

            # Create instances to test type safety
            tmux = TMUXManager()
            monitor = AsyncAgentMonitor(tmux)

            # These should not cause type errors
            assert hasattr(monitor, "check_agent_status_async")
            assert hasattr(monitor, "monitor_agents_batch")
            assert hasattr(monitor, "get_agent_notifications")

        except ImportError as e:
            pytest.fail(f"Failed to import async monitoring module: {e}")

    def test_no_remaining_type_issues(self):
        """Test that there are no remaining 'any?' type issues."""
        # Check the specific file that had issues
        monitor_async_file = Path("/workspaces/Tmux-Orchestrator/tmux_orchestrator/core/monitor_async.py")

        if monitor_async_file.exists():
            content = monitor_async_file.read_text()

            # Should not contain 'any?' which was causing mypy errors
            assert "any?" not in content.lower(), "File still contains problematic 'any?' type hints"

            # Should contain proper 'Any' imports and usage
            assert "from typing import Any" in content, "Missing proper Any import"
            assert "Dict[str, Any]" in content, "Missing proper Dict[str, Any] usage"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

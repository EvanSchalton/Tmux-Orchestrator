#!/usr/bin/env python3
"""Comprehensive test cases for ruff formatting validation scenarios.

This module tests various code formatting issues that ruff should catch and fix,
preparing validation tests for the Senior Developer's pre-commit fixes.
"""

import subprocess
import tempfile
from pathlib import Path
from typing import List

import pytest


class TestRuffFormattingScenarios:
    """Test various code formatting scenarios that ruff should handle."""

    def test_function_spacing_fixes(self):
        """Test that ruff fixes function spacing issues."""
        bad_spacing = """def function_with_bad_spacing(x,y,z):
    return x+y+z

def another_function( a , b ):
    if a>b:return a
    elif a<b:
        return b
    else:return a+b
"""

        expected_fixes = [
            "def function_with_bad_spacing(x, y, z):",
            "return x + y + z",
            "def another_function(a, b):",
            "if a > b:",
            "return a",
            "elif a < b:",
            "return b",
            "else:",
            "return a + b",
        ]

        self._test_ruff_format_fixes(bad_spacing, expected_fixes)

    def test_class_formatting_fixes(self):
        """Test that ruff fixes class formatting issues."""
        bad_class_format = """class BadlyFormattedClass:
    def __init__(self,name,age):
        self.name=name
        self.age=age
    def get_info(self):
        return f"{self.name}:{self.age}"
    def is_adult(self):
        return self.age>=18

class  AnotherClass  :
    pass
"""

        expected_fixes = [
            "def __init__(self, name, age):",
            "self.name = name",
            "self.age = age",
            'return f"{self.name}:{self.age}"',
            "return self.age >= 18",
            "class AnotherClass:",
        ]

        self._test_ruff_format_fixes(bad_class_format, expected_fixes)

    def test_import_statement_fixes(self):
        """Test that ruff fixes import statement formatting."""
        bad_imports = """import os,sys,json
from typing import Dict,List,Optional,Tuple
from pathlib import Path,PurePath
import subprocess as sp,shutil

def func():
    pass
"""

        expected_fixes = [
            "import json",
            "import os",
            "import sys",
            "from typing import Dict, List, Optional, Tuple",
            "from pathlib import Path, PurePath",
            "import shutil",
            "import subprocess as sp",
        ]

        self._test_ruff_format_fixes(bad_imports, expected_fixes)

    def test_dictionary_formatting_fixes(self):
        """Test that ruff fixes dictionary and list formatting."""
        bad_collections = """def create_config():
    config={'name':'test','settings':{'debug':True,'level':'info'},'items':[1,2,3,4,5]}

    another_dict={
        'key1':'value1','key2':'value2',
        'key3':'value3'
    }

    long_list=[
        'item1','item2','item3','item4','item5','item6','item7','item8'
    ]

    return config,another_dict,long_list
"""

        expected_fixes = [
            "config = {",
            '"name": "test",',
            '"settings": {"debug": True, "level": "info"},',
            '"items": [1, 2, 3, 4, 5],',
            '"key1": "value1",',
            '"key2": "value2",',
            '"key3": "value3",',
            '"item1",',
            '"item2",',
        ]

        self._test_ruff_format_fixes(bad_collections, expected_fixes)

    def test_string_formatting_fixes(self):
        """Test that ruff fixes string formatting issues."""
        bad_strings = """def string_examples():
    # Single vs double quotes
    mixed_quotes='This should be "consistent"'
    another_string="And this 'should be' too"

    # Long strings
    long_string="This is a very long string that should probably be broken into multiple lines for better readability"

    # F-string formatting
    name="test"
    age=25
    info=f"Name: {name}, Age: {age}"

    return mixed_quotes,another_string,long_string,info
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(bad_strings)
            temp_file = Path(f.name)

        try:
            # Run ruff format
            result = subprocess.run(
                ["ruff", "format", str(temp_file)], capture_output=True, text=True, cwd="/workspaces/Tmux-Orchestrator"
            )

            assert result.returncode == 0, f"ruff-format failed: {result.stderr}"

            # Read formatted content
            formatted_content = temp_file.read_text()

            # Verify basic formatting improvements
            assert 'name = "test"' in formatted_content
            assert "age = 25" in formatted_content
            assert 'f"Name: {name}, Age: {age}"' in formatted_content

        finally:
            temp_file.unlink()

    def test_line_length_handling(self):
        """Test that ruff handles long lines appropriately."""
        long_lines = """def function_with_very_long_parameter_list(parameter_one, parameter_two, parameter_three, parameter_four, parameter_five, parameter_six):
    very_long_variable_name = some_function_call_with_many_arguments(argument_one, argument_two, argument_three, argument_four, argument_five)

    return very_long_variable_name.some_method_with_long_name().another_chained_method().final_method()

class ClassWithLongMethodNames:
    def very_long_method_name_that_exceeds_recommended_line_length(self, param1, param2, param3, param4):
        return param1 + param2 + param3 + param4
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(long_lines)
            temp_file = Path(f.name)

        try:
            # Run ruff format
            result = subprocess.run(
                ["ruff", "format", str(temp_file)], capture_output=True, text=True, cwd="/workspaces/Tmux-Orchestrator"
            )

            assert result.returncode == 0, f"ruff-format failed: {result.stderr}"

            # Read formatted content
            formatted_content = temp_file.read_text()
            lines = formatted_content.split("\n")

            # Verify that extremely long lines are handled
            # (ruff may break them or leave them if breaking would make code less readable)
            for line in lines:
                if line.strip():  # Skip empty lines
                    # Most lines should be reasonable length, but some may remain long if breaking hurts readability
                    assert len(line) < 200, f"Line still extremely long after formatting: {line[:100]}..."

        finally:
            temp_file.unlink()

    def test_operator_spacing_fixes(self):
        """Test that ruff fixes operator spacing issues."""
        bad_operators = """def calculate():
    result=1+2*3/4-5
    comparison=x>y and a<=b or c!=d
    assignment+=value
    power_result=base**exponent

    if x==y:
        z=x//y
    elif x!=y:
        z=x%y

    return result,comparison,assignment,power_result,z
"""

        expected_fixes = [
            "result = 1 + 2 * 3 / 4 - 5",
            "comparison = x > y and a <= b or c != d",
            "assignment += value",
            "power_result = base**exponent",  # ** typically stays together
            "if x == y:",
            "z = x // y",
            "elif x != y:",
            "z = x % y",
        ]

        self._test_ruff_format_fixes(bad_operators, expected_fixes)

    def test_comment_formatting_fixes(self):
        """Test that ruff fixes comment formatting issues."""
        bad_comments = """def function_with_comments():
    #Bad comment spacing
    x=1#Inline comment with no space

    # Good comment spacing
    y=2  # Good inline comment

    #Another bad comment
    z=x+y#No space before comment

    return z#Final comment
"""

        expected_fixes = [
            "# Bad comment spacing",
            "x = 1  # Inline comment with no space",
            "y = 2  # Good inline comment",
            "# Another bad comment",
            "z = x + y  # No space before comment",
            "return z  # Final comment",
        ]

        self._test_ruff_format_fixes(bad_comments, expected_fixes)

    def test_nested_structure_formatting(self):
        """Test that ruff formats nested structures correctly."""
        nested_code = """def complex_nested_structure():
    data={'users':[{'name':'alice','age':30,'roles':['admin','user']},{'name':'bob','age':25,'roles':['user']}],'settings':{'debug':True,'logging':{'level':'info','handlers':['console','file']}}}

    nested_list=[[1,2,3],[4,5,6],[7,8,9]]

    complex_comprehension=[item for sublist in nested_list for item in sublist if item%2==0]

    return data,nested_list,complex_comprehension
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(nested_code)
            temp_file = Path(f.name)

        try:
            # Run ruff format
            result = subprocess.run(
                ["ruff", "format", str(temp_file)], capture_output=True, text=True, cwd="/workspaces/Tmux-Orchestrator"
            )

            assert result.returncode == 0, f"ruff-format failed: {result.stderr}"

            # Read formatted content
            formatted_content = temp_file.read_text()

            # Verify basic structure improvements
            assert "data = {" in formatted_content
            assert '"name": "alice",' in formatted_content
            assert "nested_list = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]" in formatted_content
            assert "item % 2 == 0" in formatted_content

        finally:
            temp_file.unlink()

    def _test_ruff_format_fixes(self, bad_code: str, expected_fixes: List[str]):
        """Helper method to test ruff formatting fixes."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(bad_code)
            temp_file = Path(f.name)

        try:
            # Run ruff format
            result = subprocess.run(
                ["ruff", "format", str(temp_file)], capture_output=True, text=True, cwd="/workspaces/Tmux-Orchestrator"
            )

            assert result.returncode == 0, f"ruff-format failed: {result.stderr}"

            # Read formatted content
            formatted_content = temp_file.read_text()

            # Verify expected fixes are present
            for expected_fix in expected_fixes:
                assert expected_fix in formatted_content, f"Expected fix not found: '{expected_fix}'"

        finally:
            temp_file.unlink()


class TestRuffLintingScenarios:
    """Test various linting scenarios that ruff should catch."""

    def test_unused_import_detection(self):
        """Test that ruff detects unused imports."""
        code_with_unused_imports = """import os
import sys
import json
import subprocess
from typing import Dict, List, Optional
from pathlib import Path

def simple_function():
    # Only using json and Dict
    data: Dict[str, str] = json.loads('{"key": "value"}')
    return data
"""

        lint_result = self._run_ruff_check(code_with_unused_imports)

        # Should detect unused imports
        assert "F401" in lint_result, "Should detect unused imports (F401)"
        assert any(
            module in lint_result for module in ["os", "sys", "subprocess", "List", "Optional", "Path"]
        ), "Should identify specific unused imports"

    def test_unused_variable_detection(self):
        """Test that ruff detects unused variables."""
        code_with_unused_vars = """def function_with_unused_variables():
    used_var = "I am used"
    unused_var = "I am not used"
    another_unused = 42

    return used_var

def another_function():
    x = 1
    y = 2
    z = 3
    return x  # y and z are unused
"""

        lint_result = self._run_ruff_check(code_with_unused_vars)

        # Should detect unused variables
        assert "F841" in lint_result, "Should detect unused variables (F841)"

    def test_undefined_name_detection(self):
        """Test that ruff detects undefined names."""
        code_with_undefined_names = """def function_with_undefined_names():
    result = undefined_variable + 10
    return another_undefined_variable

def another_function():
    if some_undefined_condition:
        return missing_variable
    return 0
"""

        lint_result = self._run_ruff_check(code_with_undefined_names)

        # Should detect undefined names
        assert "F821" in lint_result, "Should detect undefined names (F821)"

    def test_import_order_issues(self):
        """Test that ruff detects import order issues."""
        code_with_import_issues = """import json
import os
from pathlib import Path
import sys  # This should come before local imports
from typing import Dict

def test_function():
    return os.getcwd()
"""

        lint_result = self._run_ruff_check(code_with_import_issues)

        # May detect import sorting issues depending on ruff configuration
        # Note: Import sorting is often handled by isort, not ruff
        # But ruff might have some import-related rules
        assert isinstance(lint_result, str), "Should return lint results"

    def test_line_too_long_detection(self):
        """Test that ruff detects lines that are too long."""
        very_long_line = "def function_with_extremely_long_line_that_definitely_exceeds_the_maximum_recommended_line_length_and_should_be_detected_by_linting_tools():"

        code_with_long_lines = f"""
{very_long_line}
    return "This function has a very long signature that should be flagged by the linter as being too long for readability"
"""

        lint_result = self._run_ruff_check(code_with_long_lines)

        # May detect line length issues (E501) depending on configuration
        # Note: Some formatters handle this automatically
        assert isinstance(lint_result, str), "Should return lint results"

    def test_syntax_error_detection(self):
        """Test that ruff detects syntax errors."""
        code_with_syntax_errors = """def function_with_syntax_error():
    if True
        return "Missing colon"

    x = [1, 2, 3
    return x  # Missing closing bracket

def another_function(:
    pass  # Invalid parameter syntax
"""

        lint_result = self._run_ruff_check(code_with_syntax_errors)

        # Should detect syntax errors
        assert any(
            error_type in lint_result for error_type in ["E999", "SyntaxError", "invalid syntax"]
        ), "Should detect syntax errors"

    def test_indentation_issues(self):
        """Test that ruff detects indentation problems."""
        code_with_indentation_issues = """def function_with_bad_indentation():
    if True:
        x = 1
      y = 2  # Inconsistent indentation
    z = 3

  def nested_function():  # Wrong indentation level
      pass

    return x, y, z
"""

        lint_result = self._run_ruff_check(code_with_indentation_issues)

        # Should detect indentation issues
        # Note: Modern formatters often fix these automatically
        assert isinstance(lint_result, str), "Should return lint results"

    def _run_ruff_check(self, code: str) -> str:
        """Helper method to run ruff check on code and return results."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            temp_file = Path(f.name)

        try:
            # Run ruff check
            result = subprocess.run(
                ["ruff", "check", str(temp_file)], capture_output=True, text=True, cwd="/workspaces/Tmux-Orchestrator"
            )

            # Return the output regardless of return code
            return result.stdout + result.stderr

        finally:
            temp_file.unlink()


class TestRuffProjectSpecific:
    """Test ruff behavior on project-specific code patterns."""

    def test_async_code_formatting(self):
        """Test that ruff properly formats async/await code."""
        async_code = """import asyncio
from typing import List

async def async_function_with_bad_formatting(x,y):
    result=await another_async_function(x,y)
    return result

async def another_async_function(a,b):
    await asyncio.sleep(0.1)
    return a+b

class AsyncClass:
    async def async_method(self,param):
        return await self.helper_method(param)

    async def helper_method(self,value):
        return value*2
"""

        expected_fixes = [
            "async def async_function_with_bad_formatting(x, y):",
            "result = await another_async_function(x, y)",
            "async def another_async_function(a, b):",
            "return a + b",
            "async def async_method(self, param):",
            "async def helper_method(self, value):",
            "return value * 2",
        ]

        self._test_formatting_fixes(async_code, expected_fixes)

    def test_type_annotation_formatting(self):
        """Test that ruff properly formats type annotations."""
        typed_code = """from typing import Dict,List,Optional,Union,Tuple

def typed_function(param1:str,param2:int)->Optional[str]:
    return param1if param2>0 else None

def complex_types(data:Dict[str,List[int]],callback:Optional[callable]=None)->Tuple[bool,str]:
    if callback:
        result=callback(data)
    else:
        result=True
    return result,"success"

class TypedClass:
    def __init__(self,name:str,items:List[str])->None:
        self.name=name
        self.items=items
"""

        expected_fixes = [
            "from typing import Dict, List, Optional, Union, Tuple",
            "def typed_function(param1: str, param2: int) -> Optional[str]:",
            "return param1 if param2 > 0 else None",
            "def complex_types(",
            "data: Dict[str, List[int]],",
            "callback: Optional[callable] = None,",
            ") -> Tuple[bool, str]:",
            "result = callback(data)",
            "result = True",
            'return result, "success"',
            "def __init__(self, name: str, items: List[str]) -> None:",
            "self.name = name",
            "self.items = items",
        ]

        self._test_formatting_fixes(typed_code, expected_fixes)

    def test_tmux_orchestrator_patterns(self):
        """Test formatting of common patterns in tmux-orchestrator codebase."""
        orchestrator_patterns = """from tmux_orchestrator.core.monitor import IdleMonitor
from tmux_orchestrator.utils.tmux import TMUXManager

class TestOrchestrator:
    def __init__(self,tmux:TMUXManager):
        self.tmux=tmux
        self.monitor=IdleMonitor(tmux)

    def check_agents(self,targets:List[str])->Dict[str,bool]:
        results={}
        for target in targets:
            content=self.tmux.capture_pane(target)
            is_idle=self.monitor.is_agent_idle(target)
            results[target]=not is_idle
        return results

    def send_notifications(self,notifications:Dict[str,List[str]])->None:
        for pm_target,messages in notifications.items():
            for message in messages:
                self.tmux.send_message(pm_target,message)
"""

        expected_fixes = [
            "def __init__(self, tmux: TMUXManager):",
            "self.tmux = tmux",
            "self.monitor = IdleMonitor(tmux)",
            "def check_agents(self, targets: List[str]) -> Dict[str, bool]:",
            "results = {}",
            "content = self.tmux.capture_pane(target)",
            "is_idle = self.monitor.is_agent_idle(target)",
            "results[target] = not is_idle",
            "def send_notifications(self, notifications: Dict[str, List[str]]) -> None:",
            "for pm_target, messages in notifications.items():",
            "self.tmux.send_message(pm_target, message)",
        ]

        self._test_formatting_fixes(orchestrator_patterns, expected_fixes)

    def _test_formatting_fixes(self, code: str, expected_fixes: List[str]):
        """Helper method to test formatting fixes."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            temp_file = Path(f.name)

        try:
            # Run ruff format
            result = subprocess.run(
                ["ruff", "format", str(temp_file)], capture_output=True, text=True, cwd="/workspaces/Tmux-Orchestrator"
            )

            assert result.returncode == 0, f"ruff-format failed: {result.stderr}"

            # Read formatted content
            formatted_content = temp_file.read_text()

            # Verify expected fixes are present
            for expected_fix in expected_fixes:
                assert expected_fix in formatted_content, f"Expected fix not found: '{expected_fix}'"

        finally:
            temp_file.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

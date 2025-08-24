#!/usr/bin/env python3
"""Test all 12 examples from MCP_EXAMPLES_AND_ERROR_HANDLING.md"""

import json
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Dict


class MCPDocumentationTester:
    """Test MCP documentation examples for accuracy."""

    def __init__(self):
        self.results = []
        self.doc_path = Path("/workspaces/Tmux-Orchestrator/docs/MCP_EXAMPLES_AND_ERROR_HANDLING.md")

    def test_mcp_tool_format(self) -> Dict[str, Any]:
        """Test that MCP tool naming follows correct format."""
        test_name = "mcp_tool_format"

        # Read documentation
        doc_content = self.doc_path.read_text()

        # Extract all MCP tool calls from examples
        import re

        tool_pattern = r"tmux-orc_[a-z_]+\("
        tools_found = re.findall(tool_pattern, doc_content)

        # Verify tool format
        valid_tools = []
        invalid_tools = []

        for tool in tools_found:
            tool_name = tool.rstrip("(")
            # Check format: tmux-orc_category_action or tmux-orc_action
            parts = tool_name.split("_")
            if len(parts) >= 2 and parts[0] == "tmux-orc":
                valid_tools.append(tool_name)
            else:
                invalid_tools.append(tool_name)

        return {
            "test": test_name,
            "passed": len(invalid_tools) == 0,
            "total_tools": len(tools_found),
            "valid_tools": len(valid_tools),
            "invalid_tools": invalid_tools[:5] if invalid_tools else [],
        }

    def test_cli_commands_exist(self) -> Dict[str, Any]:
        """Test that documented CLI commands actually exist."""
        test_name = "cli_commands_exist"

        # Get all available commands
        result = subprocess.run(["tmux-orc", "reflect", "--format", "json"], capture_output=True, text=True)

        if result.returncode != 0:
            return {"test": test_name, "passed": False, "error": "Failed to get CLI commands"}

        try:
            cli_data = json.loads(result.stdout)
            available_commands = set()

            # Extract command names from reflection
            for cmd, info in cli_data.items():
                available_commands.add(cmd)
                if isinstance(info, dict) and "commands" in info:
                    for subcmd in info["commands"]:
                        available_commands.add(f"{cmd}_{subcmd}")

        except json.JSONDecodeError:
            return {"test": test_name, "passed": False, "error": "Failed to parse reflection output"}

        # Check documented commands exist
        doc_content = self.doc_path.read_text()
        documented_commands = re.findall(r"tmux-orc_([a-z_]+)\(", doc_content)

        missing_commands = []
        for cmd in documented_commands:
            # Convert MCP format to CLI format (replace _ with space)
            cli_cmd = cmd.replace("_", " ")
            if cli_cmd not in available_commands and cmd not in available_commands:
                missing_commands.append(cmd)

        return {
            "test": test_name,
            "passed": len(missing_commands) == 0,
            "documented_commands": len(documented_commands),
            "available_commands": len(available_commands),
            "missing_commands": list(set(missing_commands))[:5],
        }

    def test_json_examples_syntax(self) -> Dict[str, Any]:
        """Test that JSON examples in documentation are valid."""
        test_name = "json_examples_syntax"

        doc_content = self.doc_path.read_text()

        # Extract JSON blocks
        json_blocks = re.findall(r"```json\n(.*?)\n```", doc_content, re.DOTALL)

        invalid_blocks = []
        for i, block in enumerate(json_blocks):
            try:
                json.loads(block)
            except json.JSONDecodeError as e:
                invalid_blocks.append(
                    {"block_index": i, "error": str(e), "preview": block[:100] + "..." if len(block) > 100 else block}
                )

        return {
            "test": test_name,
            "passed": len(invalid_blocks) == 0,
            "total_json_blocks": len(json_blocks),
            "invalid_blocks": invalid_blocks[:3],
        }

    def test_error_handling_patterns(self) -> Dict[str, Any]:
        """Test that error handling patterns are consistent."""
        test_name = "error_handling_patterns"

        doc_content = self.doc_path.read_text()

        # Check for consistent error handling patterns
        patterns_found = {
            "success_check": len(re.findall(r'if\s+.*\["success"\]', doc_content)),
            "error_key": len(re.findall(r'\["error"\]', doc_content)),
            "not_success": len(re.findall(r'if\s+not\s+.*\["success"\]', doc_content)),
            "try_except": len(re.findall(r"try:", doc_content)),
        }

        # All examples should check success
        examples_count = 12
        has_error_handling = patterns_found["success_check"] + patterns_found["not_success"] >= examples_count

        return {
            "test": test_name,
            "passed": has_error_handling,
            "patterns_found": patterns_found,
            "error_handling_coverage": f"{patterns_found['success_check'] + patterns_found['not_success']}/{examples_count}",
        }

    def test_context_command_integration(self) -> Dict[str, Any]:
        """Test that context show mcp command works."""
        test_name = "context_command_integration"

        result = subprocess.run(["tmux-orc", "context", "show", "mcp"], capture_output=True, text=True)

        success = result.returncode == 0
        has_content = len(result.stdout) > 100
        has_mcp_section = "MCP" in result.stdout or "Model Context Protocol" in result.stdout

        return {
            "test": test_name,
            "passed": success and has_content and has_mcp_section,
            "command_success": success,
            "output_length": len(result.stdout),
            "has_mcp_content": has_mcp_section,
        }

    def test_tool_categories(self) -> Dict[str, Any]:
        """Test that all documented tool categories are accurate."""
        test_name = "tool_categories"

        # Expected categories from documentation
        expected_categories = {
            "agent": "Agent lifecycle management",
            "monitor": "Daemon monitoring and health checks",
            "team": "Team coordination",
            "spawn": "Create new agents",
            "context": "Access role contexts",
        }

        # Get actual categories from CLI
        result = subprocess.run(["tmux-orc", "reflect", "--format", "json"], capture_output=True, text=True)

        if result.returncode != 0:
            return {"test": test_name, "passed": False, "error": "Failed to get CLI structure"}

        try:
            cli_data = json.loads(result.stdout)
            actual_categories = [cmd for cmd in cli_data.keys() if cmd in expected_categories]

            missing = set(expected_categories.keys()) - set(actual_categories)

            return {
                "test": test_name,
                "passed": len(missing) == 0,
                "expected_categories": list(expected_categories.keys()),
                "found_categories": actual_categories,
                "missing_categories": list(missing),
            }
        except Exception as e:
            return {"test": test_name, "passed": False, "error": f"Failed to parse CLI data: {e}"}

    def test_mcp_for_agents_tutorial(self) -> Dict[str, Any]:
        """Test that MCP_FOR_AGENTS.md tutorial is accessible."""
        test_name = "mcp_for_agents_tutorial"

        tutorial_path = Path("/workspaces/Tmux-Orchestrator/docs/MCP_FOR_AGENTS.md")

        exists = tutorial_path.exists()
        if exists:
            content = tutorial_path.read_text()
            has_quickstart = "quick start" in content.lower()
            has_examples = "example" in content.lower()
            has_tool_reference = "tool" in content.lower()

            return {
                "test": test_name,
                "passed": exists and all([has_quickstart, has_examples, has_tool_reference]),
                "file_exists": exists,
                "has_quickstart": has_quickstart,
                "has_examples": has_examples,
                "has_tool_reference": has_tool_reference,
                "file_size": len(content) if exists else 0,
            }
        else:
            return {"test": test_name, "passed": False, "file_exists": False, "error": "MCP_FOR_AGENTS.md not found"}

    def run_all_tests(self):
        """Run all documentation tests."""
        print("📚 MCP Documentation Validation Suite")
        print("=" * 50)

        tests = [
            self.test_context_command_integration,
            self.test_mcp_tool_format,
            self.test_cli_commands_exist,
            self.test_json_examples_syntax,
            self.test_error_handling_patterns,
            self.test_tool_categories,
            self.test_mcp_for_agents_tutorial,
        ]

        for test_func in tests:
            print(f"\nTesting: {test_func.__name__}")
            try:
                result = test_func()
                self.results.append(result)
                status = "✅ PASSED" if result["passed"] else "❌ FAILED"
                print(f"  {status}")
                if not result["passed"]:
                    print(f"  Details: {json.dumps(result, indent=2)}")
            except Exception as e:
                print(f"  ❌ ERROR: {str(e)}")
                self.results.append({"test": test_func.__name__, "passed": False, "error": str(e)})

        # Summary
        passed = sum(1 for r in self.results if r["passed"])
        total = len(self.results)

        print("\n" + "=" * 50)
        print(f"Documentation Test Summary: {passed}/{total} passed")

        # Save results
        report_path = Path("/workspaces/Tmux-Orchestrator/mcp_documentation_test_report.json")
        with open(report_path, "w") as f:
            json.dump(
                {
                    "test_run": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "summary": f"{passed}/{total} passed",
                    "results": self.results,
                },
                f,
                indent=2,
            )

        print(f"\nDetailed report: {report_path}")

        return passed == total


if __name__ == "__main__":
    tester = MCPDocumentationTester()
    success = tester.run_all_tests()
    exit(0 if success else 1)

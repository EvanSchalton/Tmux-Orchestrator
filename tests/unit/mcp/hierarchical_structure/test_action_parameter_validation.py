#!/usr/bin/env python3
"""
Test validation for the 'action' parameter approach in hierarchical MCP tools.

This module specifically tests:
1. Action parameter functionality
2. EnumDescriptions clarity
3. Error message formatting
4. LLM-friendly schema structure
"""

import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))

from mcp_operations_inventory import MCPOperationsInventory  # noqa: E402


@dataclass
class ActionParameterTest:
    """Test case for action parameter validation."""

    test_id: str
    tool: str
    action: str
    parameters: dict[str, Any]
    expected_success: bool
    description: str
    error_type: str | None = None


@dataclass
class SchemaValidation:
    """Schema validation results."""

    has_enum_descriptions: bool
    has_examples: bool
    has_pattern_validation: bool
    has_conditional_requirements: bool
    llm_friendliness_score: float


class ActionParameterValidator:
    """Validate the action parameter approach for hierarchical MCP tools."""

    def __init__(self):
        self.inventory = MCPOperationsInventory()
        self.test_cases = self._create_test_cases()
        self.schema_template = self._create_schema_template()

    def _create_schema_template(self) -> dict[str, Any]:
        """Create the ideal schema template based on MCP Arch specifications."""
        return {
            "agent": {
                "description": "[Agent] Manage Claude agents in tmux sessions",
                "schema": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": [
                                "status",
                                "restart",
                                "message",
                                "kill",
                                "info",
                                "attach",
                                "list",
                                "deploy",
                                "send",
                                "kill-all",
                            ],
                            "description": "The agent operation to perform",
                            "enumDescriptions": {
                                "status": "Show all agents status",
                                "restart": "Restart specific agent (requires: target)",
                                "message": "Send message to agent (requires: target, args[0]=message)",
                                "kill": "Terminate agent (requires: target)",
                                "info": "Get agent information (requires: target)",
                                "attach": "Attach to agent session (requires: target)",
                                "list": "List all agents",
                                "deploy": "Deploy new agent (requires: role, session)",
                                "send": "Send keys to agent (requires: target, args[0]=keys)",
                                "kill-all": "Kill all agents",
                            },
                        },
                        "target": {
                            "type": "string",
                            "pattern": "^[a-zA-Z0-9_-]+:[0-9]+$",
                            "description": "Target in session:window format (e.g., 'myapp:0')",
                            "examples": ["frontend:1", "backend:2", "myproject:0"],
                        },
                        "args": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Additional arguments for the action",
                        },
                        "options": {"type": "object", "description": "Command flags and options"},
                    },
                    "required": ["action"],
                    "allOf": [
                        {
                            "if": {
                                "properties": {
                                    "action": {"enum": ["restart", "message", "kill", "info", "attach", "send"]}
                                }
                            },
                            "then": {"required": ["target"]},
                        },
                        {
                            "if": {"properties": {"action": {"const": "message"}}},
                            "then": {"properties": {"args": {"minItems": 1}}},
                        },
                        {
                            "if": {"properties": {"action": {"const": "deploy"}}},
                            "then": {"properties": {"args": {"minItems": 2}}},
                        },
                    ],
                },
                "examples": [
                    {
                        "description": "Check all agents status",
                        "call": "agent(action='status')",
                        "result": "Lists all active agents",
                    },
                    {
                        "description": "Send message to frontend agent",
                        "call": "agent(action='message', target='frontend:1', args=['Update the header'])",
                        "result": "Message sent to agent",
                    },
                ],
            }
        }

    def _create_test_cases(self) -> list[ActionParameterTest]:
        """Create comprehensive test cases for action parameter validation."""
        tests = []

        # Valid action tests
        tests.extend(
            [
                ActionParameterTest(
                    test_id="valid_simple_action",
                    tool="agent",
                    action="status",
                    parameters={},
                    expected_success=True,
                    description="Simple action without parameters",
                ),
                ActionParameterTest(
                    test_id="valid_targeted_action",
                    tool="agent",
                    action="restart",
                    parameters={"target": "frontend:1"},
                    expected_success=True,
                    description="Action with required target",
                ),
                ActionParameterTest(
                    test_id="valid_message_action",
                    tool="agent",
                    action="message",
                    parameters={"target": "backend:2", "args": ["Task completed"]},
                    expected_success=True,
                    description="Message action with target and content",
                ),
                ActionParameterTest(
                    test_id="valid_deploy_action",
                    tool="spawn",
                    action="agent",
                    parameters={"args": ["backend-dev", "work:3"], "options": {"briefing": "API development"}},
                    expected_success=True,
                    description="Deploy action with role and session",
                ),
            ]
        )

        # Invalid action tests
        tests.extend(
            [
                ActionParameterTest(
                    test_id="invalid_action_name",
                    tool="agent",
                    action="stat",  # Typo
                    parameters={},
                    expected_success=False,
                    description="Invalid action name",
                    error_type="invalid_action",
                ),
                ActionParameterTest(
                    test_id="missing_required_target",
                    tool="agent",
                    action="restart",
                    parameters={},  # Missing target
                    expected_success=False,
                    description="Missing required target parameter",
                    error_type="missing_parameter",
                ),
                ActionParameterTest(
                    test_id="invalid_target_format",
                    tool="agent",
                    action="kill",
                    parameters={"target": "frontend"},  # Missing :window
                    expected_success=False,
                    description="Invalid target format",
                    error_type="invalid_target",
                ),
                ActionParameterTest(
                    test_id="missing_message_content",
                    tool="agent",
                    action="message",
                    parameters={"target": "frontend:1"},  # Missing message
                    expected_success=False,
                    description="Missing message content",
                    error_type="missing_parameter",
                ),
            ]
        )

        # Edge cases
        tests.extend(
            [
                ActionParameterTest(
                    test_id="extra_parameters",
                    tool="agent",
                    action="status",
                    parameters={"unnecessary": "param"},
                    expected_success=True,
                    description="Extra parameters should be ignored",
                ),
                ActionParameterTest(
                    test_id="complex_options",
                    tool="monitor",
                    action="start",
                    parameters={"options": {"interval": 30, "verbose": True}},
                    expected_success=True,
                    description="Complex options parameter",
                ),
            ]
        )

        return tests

    def validate_schema_structure(self, tool: str) -> SchemaValidation:
        """Validate schema structure for LLM-friendliness."""
        schema = self.schema_template.get(tool, {}).get("schema", {})

        # Check for enum descriptions
        action_prop = schema.get("properties", {}).get("action", {})
        has_enum_descriptions = "enumDescriptions" in action_prop

        # Check for examples
        target_prop = schema.get("properties", {}).get("target", {})
        has_examples = "examples" in target_prop

        # Check for pattern validation
        has_pattern_validation = "pattern" in target_prop

        # Check for conditional requirements
        has_conditional_requirements = "allOf" in schema or "if" in str(schema)

        # Calculate LLM friendliness score
        score = 0.0
        if has_enum_descriptions:
            score += 0.4  # Most important for LLMs
        if has_examples:
            score += 0.3
        if has_pattern_validation:
            score += 0.2
        if has_conditional_requirements:
            score += 0.1

        return SchemaValidation(
            has_enum_descriptions=has_enum_descriptions,
            has_examples=has_examples,
            has_pattern_validation=has_pattern_validation,
            has_conditional_requirements=has_conditional_requirements,
            llm_friendliness_score=score,
        )

    def format_llm_error(self, error_type: str, details: dict) -> dict:
        """Format errors for optimal LLM understanding."""
        templates = {
            "invalid_action": {
                "error": "Invalid action '{action}' for {tool}",
                "suggestion": "Valid actions: {valid_actions}",
                "example": "Try: {tool}(action='{suggested_action}')",
            },
            "missing_parameter": {
                "error": "Action '{action}' requires parameter '{param}'",
                "suggestion": "Add {param} to your call",
                "example": "{tool}(action='{action}', {param}='value')",
            },
            "invalid_target": {
                "error": "Invalid target format '{target}'",
                "suggestion": "Use session:window format",
                "example": "{tool}(action='{action}', target='session:0')",
            },
        }

        # Add fuzzy matching for typos
        if error_type == "invalid_action" and "action" in details:
            valid_actions = [
                "status",
                "restart",
                "message",
                "kill",
                "info",
                "attach",
                "list",
                "deploy",
                "send",
                "kill-all",
            ]
            suggested = self._fuzzy_match(details["action"], valid_actions)
            if suggested:
                details["suggested_action"] = suggested
            details["valid_actions"] = ", ".join(valid_actions)

        template = templates.get(error_type, {})
        return {
            "success": False,
            "error_type": error_type,
            "message": template.get("error", "Unknown error").format(**details),
            "suggestion": template.get("suggestion", "").format(**details),
            "example": template.get("example", "").format(**details),
            "did_you_mean": details.get("suggested_action"),
        }

    def _fuzzy_match(self, input_str: str, options: list[str]) -> str | None:
        """Simple fuzzy matching for typos."""
        for option in options:
            if input_str.lower() in option.lower() or option.lower() in input_str.lower():
                return option
            # Check for single character difference
            if abs(len(input_str) - len(option)) <= 1:
                diff_count = sum(1 for a, b in zip(input_str, option) if a != b)
                if diff_count <= 1:
                    return option
        return None

    def run_action_parameter_tests(self) -> dict[str, Any]:
        """Run all action parameter tests."""
        results = []

        print("🧪 Running Action Parameter Tests")
        print("=" * 60)

        for test in self.test_cases:
            # Simulate validation
            success = self._validate_action(test)

            if success != test.expected_success:
                print(f"❌ {test.test_id}: {test.description}")
                print(f"   Expected: {test.expected_success}, Got: {success}")
            else:
                print(f"✅ {test.test_id}: {test.description}")

            results.append(
                {"test_id": test.test_id, "passed": success == test.expected_success, "description": test.description}
            )

        passed = sum(1 for r in results if r["passed"])
        return {
            "total_tests": len(results),
            "passed": passed,
            "failed": len(results) - passed,
            "success_rate": (passed / len(results)) * 100,
            "details": results,
        }

    def _validate_action(self, test: ActionParameterTest) -> bool:
        """Validate an action parameter test case."""
        # Check if action is valid
        valid_actions = {
            "agent": ["status", "restart", "message", "kill", "info", "attach", "list", "deploy", "send", "kill-all"],
            "monitor": [
                "dashboard",
                "logs",
                "performance",
                "recovery-logs",
                "recovery-start",
                "recovery-status",
                "recovery-stop",
                "start",
                "status",
                "stop",
            ],
            "spawn": ["agent", "orc", "pm"],
        }

        tool_actions = valid_actions.get(test.tool, [])
        if test.action not in tool_actions:
            return False

        # Check required parameters
        target_required = ["restart", "message", "kill", "info", "attach", "send"]
        if test.action in target_required and "target" not in test.parameters:
            return False

        # Check target format
        if "target" in test.parameters:
            target = test.parameters["target"]
            if not isinstance(target, str) or ":" not in target:
                return False

        # Check message content
        if test.action == "message" and ("args" not in test.parameters or not test.parameters["args"]):
            return False

        return True

    def test_enum_descriptions(self) -> dict[str, Any]:
        """Test enumDescriptions clarity and completeness."""
        print("\n📝 Testing EnumDescriptions")
        print("=" * 60)

        results = []

        for tool, config in self.schema_template.items():
            schema = config.get("schema", {})
            action_prop = schema.get("properties", {}).get("action", {})
            enum_descs = action_prop.get("enumDescriptions", {})

            # Check each enum has a description
            enums = action_prop.get("enum", [])
            for enum_val in enums:
                has_desc = enum_val in enum_descs
                is_clear = False

                if has_desc:
                    desc = enum_descs[enum_val]
                    # Check clarity criteria
                    is_clear = (
                        len(desc) > 10  # Not too short
                        and len(desc) < 100  # Not too long
                        and "requires:" in desc
                        or "Show" in desc
                        or "Get" in desc  # Action verb
                    )

                results.append(
                    {
                        "tool": tool,
                        "action": enum_val,
                        "has_description": has_desc,
                        "is_clear": is_clear,
                        "description": enum_descs.get(enum_val, "MISSING"),
                    }
                )

                if not has_desc:
                    print(f"❌ {tool}.{enum_val}: Missing description")
                elif not is_clear:
                    print(f"⚠️  {tool}.{enum_val}: Description unclear")
                else:
                    print(f"✅ {tool}.{enum_val}: Clear description")

        clear_count = sum(1 for r in results if r["has_description"] and r["is_clear"])
        return {
            "total_enums": len(results),
            "with_descriptions": sum(1 for r in results if r["has_description"]),
            "clear_descriptions": clear_count,
            "clarity_rate": (clear_count / len(results)) * 100 if results else 0,
            "details": results,
        }

    def test_error_messages(self) -> dict[str, Any]:
        """Test error message clarity and LLM-friendliness."""
        print("\n🚨 Testing Error Messages")
        print("=" * 60)

        test_errors = [
            ("invalid_action", {"tool": "agent", "action": "stat"}),
            ("missing_parameter", {"tool": "agent", "action": "restart", "param": "target"}),
            ("invalid_target", {"tool": "agent", "action": "kill", "target": "frontend"}),
        ]

        results = []
        for error_type, details in test_errors:
            error_response = self.format_llm_error(error_type, details)

            # Check error quality
            has_suggestion = bool(error_response.get("suggestion"))
            has_example = bool(error_response.get("example"))
            has_fuzzy_match = bool(error_response.get("did_you_mean"))

            quality_score = 0.0
            if has_suggestion:
                quality_score += 0.4
            if has_example:
                quality_score += 0.4
            if has_fuzzy_match and error_type == "invalid_action":
                quality_score += 0.2

            results.append(
                {
                    "error_type": error_type,
                    "has_suggestion": has_suggestion,
                    "has_example": has_example,
                    "has_fuzzy_match": has_fuzzy_match,
                    "quality_score": quality_score,
                    "response": error_response,
                }
            )

            print(f"{'✅' if quality_score >= 0.8 else '⚠️'} {error_type}: Quality score {quality_score:.1f}")
            print(f"   Message: {error_response['message']}")
            if error_response.get("suggestion"):
                print(f"   Suggestion: {error_response['suggestion']}")
            if error_response.get("example"):
                print(f"   Example: {error_response['example']}")

        avg_quality = sum(float(r["quality_score"]) for r in results) / len(results)
        return {
            "total_error_types": len(results),
            "average_quality_score": avg_quality,
            "all_have_suggestions": all(r["has_suggestion"] for r in results),
            "all_have_examples": all(r["has_example"] for r in results),
            "details": results,
        }

    def generate_report(self) -> dict[str, Any]:
        """Generate comprehensive test report."""
        print("\n" + "=" * 60)
        print("🔍 COMPREHENSIVE ACTION PARAMETER TEST REPORT")
        print("=" * 60)

        # Run all tests
        action_results = self.run_action_parameter_tests()
        enum_results = self.test_enum_descriptions()
        error_results = self.test_error_messages()

        # Test schema validation
        schema_validation = self.validate_schema_structure("agent")

        # Calculate overall score
        overall_score = (
            action_results["success_rate"] * 0.3
            + enum_results["clarity_rate"] * 0.3
            + error_results["average_quality_score"] * 100 * 0.2
            + schema_validation.llm_friendliness_score * 100 * 0.2
        )

        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "overall_score": overall_score,
            "meets_requirements": overall_score >= 95.0,
            "action_parameter_tests": {
                "success_rate": action_results["success_rate"],
                "passed": action_results["passed"],
                "failed": action_results["failed"],
            },
            "enum_descriptions": {
                "clarity_rate": enum_results["clarity_rate"],
                "with_descriptions": enum_results["with_descriptions"],
                "clear_descriptions": enum_results["clear_descriptions"],
            },
            "error_messages": {
                "quality_score": error_results["average_quality_score"] * 100,
                "all_have_suggestions": error_results["all_have_suggestions"],
                "all_have_examples": error_results["all_have_examples"],
            },
            "schema_validation": {
                "llm_friendliness_score": schema_validation.llm_friendliness_score * 100,
                "has_enum_descriptions": schema_validation.has_enum_descriptions,
                "has_examples": schema_validation.has_examples,
                "has_pattern_validation": schema_validation.has_pattern_validation,
                "has_conditional_requirements": schema_validation.has_conditional_requirements,
            },
        }

        return report


def main():
    """Run action parameter validation tests."""
    validator = ActionParameterValidator()
    report = validator.generate_report()

    print("\n📊 SUMMARY")
    print("=" * 60)
    print(f"Overall Score: {report['overall_score']:.1f}%")
    print(f"Meets Requirements (95%): {'✅ YES' if report['meets_requirements'] else '❌ NO'}")

    print("\nKey Metrics:")
    print(f"  Action Parameter Tests: {report['action_parameter_tests']['success_rate']:.1f}%")
    print(f"  EnumDescription Clarity: {report['enum_descriptions']['clarity_rate']:.1f}%")
    print(f"  Error Message Quality: {report['error_messages']['quality_score']:.1f}%")
    print(f"  Schema LLM-Friendliness: {report['schema_validation']['llm_friendliness_score']:.1f}%")

    # Save report
    report_path = Path(__file__).parent / "action_parameter_validation_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n💾 Detailed report saved to: {report_path}")

    return 0 if report["meets_requirements"] else 1


if __name__ == "__main__":
    exit(main())

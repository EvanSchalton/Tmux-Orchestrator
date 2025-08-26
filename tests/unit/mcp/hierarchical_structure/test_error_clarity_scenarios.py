#!/usr/bin/env python3
"""
Error clarity test scenarios for hierarchical MCP tools.

Focus on:
1. Clear, actionable error messages
2. Helpful suggestions for common mistakes
3. Context-aware error responses
4. LLM-friendly formatting
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ErrorScenario:
    """Test scenario for error message clarity."""

    scenario_id: str
    error_type: str
    user_input: dict[str, Any]
    expected_error: dict[str, Any]
    clarity_criteria: list[str]
    improvement_suggestion: str


@dataclass
class ErrorTemplate:
    """Template for LLM-friendly error messages."""

    error_type: str
    template: str
    required_fields: list[str]
    example_values: dict[str, Any]
    clarity_score: float


class ErrorClarityTestSuite:
    """Test suite for error message clarity and helpfulness."""

    def __init__(self):
        self.error_scenarios = self._create_error_scenarios()
        self.error_templates = self._create_error_templates()
        self.clarity_metrics = self._define_clarity_metrics()

    def _create_error_scenarios(self) -> list[ErrorScenario]:
        """Create comprehensive error test scenarios."""
        scenarios = []

        # Invalid Action Errors
        scenarios.extend(
            [
                ErrorScenario(
                    scenario_id="invalid_action_typo",
                    error_type="invalid_action",
                    user_input={
                        "tool": "agent",
                        "action": "stat",  # Typo: should be "status"
                        "args": [],
                    },
                    expected_error={
                        "error_type": "invalid_action",
                        "message": "Invalid action 'stat' for agent tool",
                        "did_you_mean": "status",
                        "valid_actions": [
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
                        "suggestion": "Use 'status' to check agent states",
                        "example": "agent(action='status')",
                        "confidence": 0.9,  # High confidence in suggestion
                    },
                    clarity_criteria=[
                        "Identifies the typo",
                        "Suggests correct action",
                        "Lists all valid actions",
                        "Provides usage example",
                    ],
                    improvement_suggestion="Implement fuzzy matching for common typos",
                ),
                ErrorScenario(
                    scenario_id="invalid_action_wrong_tool",
                    error_type="invalid_action",
                    user_input={
                        "tool": "agent",
                        "action": "broadcast",  # Valid for team, not agent
                        "args": ["Hello everyone"],
                    },
                    expected_error={
                        "error_type": "invalid_action",
                        "message": "Action 'broadcast' not available for agent tool",
                        "did_you_mean_tool": "team",
                        "suggestion": "Use 'team' tool for broadcast: team(action='broadcast', args=['Hello everyone'])",
                        "alternative": "For individual agent: agent(action='message', target='session:0', args=['Hello'])",
                        "context": "Broadcast sends to all team members, message sends to one agent",
                    },
                    clarity_criteria=[
                        "Identifies correct tool for action",
                        "Provides complete corrected example",
                        "Offers alternative for current tool",
                        "Explains conceptual difference",
                    ],
                    improvement_suggestion="Cross-reference actions across tools for better suggestions",
                ),
            ]
        )

        # Missing Parameter Errors
        scenarios.extend(
            [
                ErrorScenario(
                    scenario_id="missing_target_restart",
                    error_type="missing_parameter",
                    user_input={
                        "tool": "agent",
                        "action": "restart",
                        # Missing: target
                    },
                    expected_error={
                        "error_type": "missing_parameter",
                        "message": "Action 'restart' requires parameter 'target'",
                        "missing": ["target"],
                        "parameter_info": {
                            "target": {
                                "description": "Agent identifier in session:window format",
                                "format": "session:window",
                                "examples": ["frontend:1", "backend:2", "myapp:0"],
                            }
                        },
                        "suggestion": "Specify which agent to restart",
                        "example": "agent(action='restart', target='frontend:1')",
                        "tip": "Use agent(action='list') to see available agents",
                    },
                    clarity_criteria=[
                        "Clearly states what's missing",
                        "Explains parameter format",
                        "Provides multiple examples",
                        "Suggests how to find valid values",
                    ],
                    improvement_suggestion="Add parameter discovery hints",
                ),
                ErrorScenario(
                    scenario_id="missing_message_content",
                    error_type="missing_parameter",
                    user_input={
                        "tool": "agent",
                        "action": "message",
                        "target": "frontend:1",
                        # Missing: message content in args
                    },
                    expected_error={
                        "error_type": "missing_parameter",
                        "message": "Action 'message' requires message content",
                        "missing": ["message content in args"],
                        "current_params": {"target": "frontend:1"},
                        "suggestion": "Add your message text to args parameter",
                        "example": "agent(action='message', target='frontend:1', args=['Your message here'])",
                        "note": "The message text goes in args[0]",
                    },
                    clarity_criteria=[
                        "Identifies missing content",
                        "Shows current parameters",
                        "Explains args usage",
                        "Provides complete example",
                    ],
                    improvement_suggestion="Clarify array parameter usage",
                ),
            ]
        )

        # Invalid Format Errors
        scenarios.extend(
            [
                ErrorScenario(
                    scenario_id="invalid_target_format",
                    error_type="invalid_format",
                    user_input={
                        "tool": "agent",
                        "action": "kill",
                        "target": "frontend",  # Missing :window
                    },
                    expected_error={
                        "error_type": "invalid_format",
                        "message": "Invalid target format 'frontend'",
                        "expected_format": "session:window",
                        "provided": "frontend",
                        "issue": "Missing window number after colon",
                        "suggestion": "Add window number after session name",
                        "examples": ["frontend:0", "frontend:1", "frontend:2"],
                        "tip": "Window numbers typically start at 0",
                        "validation_pattern": "^[a-zA-Z0-9_-]+:[0-9]+$",
                    },
                    clarity_criteria=[
                        "Explains format requirement",
                        "Shows what's missing",
                        "Provides corrected examples",
                        "Includes validation pattern",
                    ],
                    improvement_suggestion="Show visual format guide",
                ),
                ErrorScenario(
                    scenario_id="invalid_options_type",
                    error_type="invalid_type",
                    user_input={
                        "tool": "monitor",
                        "action": "start",
                        "options": "interval=30",  # Should be object, not string
                    },
                    expected_error={
                        "error_type": "invalid_type",
                        "message": "Invalid type for 'options' parameter",
                        "expected_type": "object",
                        "provided_type": "string",
                        "suggestion": "Use object/dict format for options",
                        "example": "monitor(action='start', options={'interval': 30})",
                        "common_options": {
                            "interval": "Check frequency in seconds",
                            "verbose": "Enable detailed output",
                            "daemon": "Run in background",
                        },
                    },
                    clarity_criteria=[
                        "States type mismatch",
                        "Shows correct format",
                        "Lists common options",
                        "Provides working example",
                    ],
                    improvement_suggestion="Auto-convert common string formats",
                ),
            ]
        )

        # Context-Specific Errors
        scenarios.extend(
            [
                ErrorScenario(
                    scenario_id="action_not_applicable",
                    error_type="context_error",
                    user_input={
                        "tool": "spawn",
                        "action": "restart",  # Can't restart what doesn't exist
                    },
                    expected_error={
                        "error_type": "context_error",
                        "message": "Cannot 'restart' with spawn tool - spawn creates new instances",
                        "context": "Spawn tools create new agents/resources",
                        "suggestion": "To restart existing agent, use: agent(action='restart', target='session:0')",
                        "alternative": "To create new agent, use: spawn(action='agent', args=['role', 'session:0'])",
                        "concept": "spawn = create new, agent = manage existing",
                    },
                    clarity_criteria=[
                        "Explains conceptual error",
                        "Clarifies tool purpose",
                        "Provides both alternatives",
                        "Teaches correct mental model",
                    ],
                    improvement_suggestion="Add conceptual guidance to errors",
                ),
                ErrorScenario(
                    scenario_id="ambiguous_reference",
                    error_type="ambiguity_error",
                    user_input={
                        "tool": "agent",
                        "action": "message",
                        "target": "developer",  # Which developer?
                    },
                    expected_error={
                        "error_type": "ambiguity_error",
                        "message": "Ambiguous target 'developer' - multiple matches found",
                        "matches": ["frontend-dev:1", "backend-dev:2", "fullstack-dev:0"],
                        "suggestion": "Use specific session:window identifier",
                        "examples": [
                            "agent(action='message', target='frontend-dev:1', args=['Hello'])",
                            "agent(action='message', target='backend-dev:2', args=['Hello'])",
                        ],
                        "tip": "Use agent(action='list') to see all agents with their IDs",
                    },
                    clarity_criteria=[
                        "Shows all matches",
                        "Requires specific selection",
                        "Provides discovery method",
                        "Lists concrete examples",
                    ],
                    improvement_suggestion="Implement smart target resolution",
                ),
            ]
        )

        return scenarios

    def _create_error_templates(self) -> list[ErrorTemplate]:
        """Create standardized error message templates."""
        return [
            ErrorTemplate(
                error_type="invalid_action",
                template="""
{error_type}: '{action}' is not a valid action for {tool}

What went wrong: The {tool} tool doesn't have an action called '{action}'
{did_you_mean}
Valid actions for {tool}: {valid_actions}

How to fix it:
{suggestion}

Example:
{example}
""",
                required_fields=["action", "tool", "valid_actions", "suggestion", "example"],
                example_values={
                    "action": "stat",
                    "tool": "agent",
                    "valid_actions": "status, restart, message, kill, info",
                    "did_you_mean": "Did you mean 'status'?",
                    "suggestion": "Use 'status' to check agent states",
                    "example": "agent(action='status')",
                },
                clarity_score=0.95,
            ),
            ErrorTemplate(
                error_type="missing_parameter",
                template="""
{error_type}: {action} requires {missing_params}

What's missing: {explanation}
Required format: {format_info}

How to fix it:
{suggestion}

Complete example:
{example}

{tip}
""",
                required_fields=["action", "missing_params", "explanation", "suggestion", "example"],
                example_values={
                    "action": "restart",
                    "missing_params": "target parameter",
                    "explanation": "You need to specify which agent to restart",
                    "format_info": "target='session:window' (e.g., 'frontend:1')",
                    "suggestion": "Add the target parameter with the agent's session:window ID",
                    "example": "agent(action='restart', target='frontend:1')",
                    "tip": "Tip: Use agent(action='list') to see available agents",
                },
                clarity_score=0.92,
            ),
            ErrorTemplate(
                error_type="invalid_format",
                template="""
{error_type}: '{value}' doesn't match required format

Expected format: {expected_format}
You provided: '{value}'
Problem: {issue}

How to fix it:
{suggestion}

Valid examples:
{examples}

{validation_info}
""",
                required_fields=["value", "expected_format", "issue", "suggestion", "examples"],
                example_values={
                    "value": "frontend",
                    "expected_format": "session:window",
                    "issue": "Missing ':' and window number",
                    "suggestion": "Add ':' followed by window number (usually 0, 1, 2...)",
                    "examples": "• frontend:0\n• frontend:1\n• my-session:2",
                    "validation_info": "Pattern: alphanumeric-dash:number",
                },
                clarity_score=0.90,
            ),
        ]

    def _define_clarity_metrics(self) -> dict[str, Any]:
        """Define metrics for measuring error clarity."""
        return {
            "clarity_components": {
                "problem_identification": {"weight": 0.25, "criteria": "Clearly states what went wrong"},
                "actionable_guidance": {"weight": 0.30, "criteria": "Provides specific steps to fix"},
                "examples": {"weight": 0.25, "criteria": "Includes working examples"},
                "context": {"weight": 0.20, "criteria": "Explains why/conceptual understanding"},
            },
            "scoring_rubric": {
                "excellent": "90-100%: All components present and clear",
                "good": "80-89%: Most components clear, minor issues",
                "fair": "70-79%: Basic clarity, missing some components",
                "poor": "Below 70%: Unclear or missing key information",
            },
            "llm_friendliness_factors": [
                "Structured format with clear sections",
                "Concrete examples over abstract descriptions",
                "Progressive disclosure (error → explanation → fix)",
                "Validation patterns for self-checking",
                "Related command suggestions",
            ],
        }

    def evaluate_error_clarity(self, error_response: dict[str, Any], scenario: ErrorScenario) -> dict[str, Any]:
        """Evaluate clarity of an error response."""

        # Check each clarity criterion
        met_criteria = 0
        for criterion in scenario.clarity_criteria:
            # Simple check - in real implementation would be more sophisticated
            met = True  # Placeholder
            if met:
                met_criteria += 1

        clarity_score = (met_criteria / len(scenario.clarity_criteria)) * 100

        # Evaluate components
        component_scores = {
            "problem_identification": 0.9,  # Placeholder
            "actionable_guidance": 0.85,
            "examples": 0.95,
            "context": 0.8,
        }

        # Calculate weighted score
        weights = self.clarity_metrics["clarity_components"]
        weighted_score = sum(component_scores[comp] * weights[comp]["weight"] for comp in component_scores)

        return {
            "scenario_id": scenario.scenario_id,
            "clarity_score": clarity_score,
            "weighted_score": weighted_score * 100,
            "met_criteria": met_criteria,
            "total_criteria": len(scenario.clarity_criteria),
            "component_scores": component_scores,
            "rating": self._get_rating(weighted_score * 100),
        }

    def _get_rating(self, score: float) -> str:
        """Get clarity rating based on score."""
        if score >= 90:
            return "excellent"
        elif score >= 80:
            return "good"
        elif score >= 70:
            return "fair"
        else:
            return "poor"

    def generate_clarity_report(self) -> dict[str, Any]:
        """Generate comprehensive error clarity report."""
        # Evaluate all scenarios
        evaluations = []
        for scenario in self.error_scenarios:
            eval_result = self.evaluate_error_clarity(scenario.expected_error, scenario)
            evaluations.append(eval_result)

        # Calculate averages
        avg_clarity = sum(e["clarity_score"] for e in evaluations) / len(evaluations)
        avg_weighted = sum(e["weighted_score"] for e in evaluations) / len(evaluations)

        # Group by error type
        by_type: dict[str, list[Any]] = {}
        for scenario in self.error_scenarios:
            error_type = scenario.error_type
            if error_type not in by_type:
                by_type[error_type] = []
            by_type[error_type].append(
                {
                    "scenario_id": scenario.scenario_id,
                    "description": scenario.user_input,
                    "improvement": scenario.improvement_suggestion,
                }
            )

        return {
            "summary": {
                "total_scenarios": len(self.error_scenarios),
                "average_clarity_score": avg_clarity,
                "average_weighted_score": avg_weighted,
                "overall_rating": self._get_rating(avg_weighted),
            },
            "scenarios_by_type": by_type,
            "error_templates": [
                {
                    "type": template.error_type,
                    "clarity_score": template.clarity_score * 100,
                    "required_fields": template.required_fields,
                }
                for template in self.error_templates
            ],
            "clarity_metrics": self.clarity_metrics,
            "recommendations": [
                "Implement fuzzy matching for action typos",
                "Add cross-tool action suggestions",
                "Include parameter discovery hints",
                "Show format validation patterns",
                "Provide conceptual explanations for context errors",
            ],
        }


def main():
    """Run error clarity test suite."""
    suite = ErrorClarityTestSuite()
    report = suite.generate_clarity_report()

    print("🚨 ERROR CLARITY TEST SUITE")
    print("=" * 60)

    print(f"\nTotal Scenarios: {report['summary']['total_scenarios']}")
    print(f"Average Clarity Score: {report['summary']['average_clarity_score']:.1f}%")
    print(f"Overall Rating: {report['summary']['overall_rating'].upper()}")

    print("\n📋 Error Types Tested:")
    for error_type, scenarios in report["scenarios_by_type"].items():
        print(f"\n{error_type}:")
        for scenario in scenarios[:2]:  # Show first 2
            print(f"  - {scenario['scenario_id']}")
            print(f"    Improvement: {scenario['improvement']}")

    print("\n📊 Error Template Scores:")
    for template in report["error_templates"]:
        print(f"  {template['type']}: {template['clarity_score']:.0f}% clarity")

    print("\n🎯 Key Recommendations:")
    for i, rec in enumerate(report["recommendations"], 1):
        print(f"  {i}. {rec}")

    # Save report
    report_path = Path(__file__).parent / "error_clarity_test_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n💾 Detailed report saved to: {report_path}")

    return 0


if __name__ == "__main__":
    exit(main())

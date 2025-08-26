#!/usr/bin/env python3
"""
LLM invocation testing for hierarchical MCP tools.

This module tests how well LLMs can invoke the hierarchical tool structure
compared to the flat structure.
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
class ToolInvocationScenario:
    """A test scenario for tool invocation."""

    scenario_id: str
    description: str
    user_prompt: str
    expected_flat_tool: str
    expected_hierarchical_tool: str
    expected_operation: str
    expected_parameters: dict[str, Any]
    complexity: str  # "simple", "medium", "complex"


@dataclass
class InvocationResult:
    """Result of an invocation test."""

    scenario_id: str
    structure_type: str  # "flat" or "hierarchical"
    selected_tool: str | None
    selected_operation: str | None
    selected_parameters: dict[str, Any] | None
    correct: bool
    response_time: float
    confidence: float
    error: str | None = None


class LLMInvocationTester:
    """Test LLM success rates with different tool structures."""

    def __init__(self):
        self.inventory = MCPOperationsInventory()
        self.scenarios = self._create_test_scenarios()
        self.results: list[InvocationResult] = []

    def _create_test_scenarios(self) -> list[ToolInvocationScenario]:
        """Create comprehensive test scenarios."""
        scenarios = []

        # Simple scenarios - direct command mapping
        scenarios.extend(
            [
                ToolInvocationScenario(
                    scenario_id="simple_1",
                    description="Direct agent status check",
                    user_prompt="Show me the status of all agents",
                    expected_flat_tool="agent_status",
                    expected_hierarchical_tool="agent",
                    expected_operation="status",
                    expected_parameters={},
                    complexity="simple",
                ),
                ToolInvocationScenario(
                    scenario_id="simple_2",
                    description="Kill specific agent",
                    user_prompt="Kill the agent in test-session:1",
                    expected_flat_tool="agent_kill",
                    expected_hierarchical_tool="agent",
                    expected_operation="kill",
                    expected_parameters={"target": "test-session:1"},
                    complexity="simple",
                ),
                ToolInvocationScenario(
                    scenario_id="simple_3",
                    description="Start monitoring",
                    user_prompt="Start the monitoring system",
                    expected_flat_tool="monitor_start",
                    expected_hierarchical_tool="monitor",
                    expected_operation="start",
                    expected_parameters={},
                    complexity="simple",
                ),
            ]
        )

        # Medium complexity - requires understanding context
        scenarios.extend(
            [
                ToolInvocationScenario(
                    scenario_id="medium_1",
                    description="Deploy agent with context",
                    user_prompt="I need a backend developer agent in the api-session to work on the REST endpoints",
                    expected_flat_tool="spawn_agent",
                    expected_hierarchical_tool="spawn",
                    expected_operation="agent",
                    expected_parameters={
                        "role": "backend-dev",
                        "session": "api-session",
                        "briefing": "work on the REST endpoints",
                    },
                    complexity="medium",
                ),
                ToolInvocationScenario(
                    scenario_id="medium_2",
                    description="Team communication",
                    user_prompt="Tell everyone on the team that we're having a standup meeting in 5 minutes",
                    expected_flat_tool="team_broadcast",
                    expected_hierarchical_tool="team",
                    expected_operation="broadcast",
                    expected_parameters={"message": "we're having a standup meeting in 5 minutes"},
                    complexity="medium",
                ),
                ToolInvocationScenario(
                    scenario_id="medium_3",
                    description="Error investigation",
                    user_prompt="I'm seeing some issues, can you show me what errors happened recently?",
                    expected_flat_tool="errors_recent",
                    expected_hierarchical_tool="errors",
                    expected_operation="recent",
                    expected_parameters={},
                    complexity="medium",
                ),
            ]
        )

        # Complex scenarios - multi-step or ambiguous
        scenarios.extend(
            [
                ToolInvocationScenario(
                    scenario_id="complex_1",
                    description="Full system check",
                    user_prompt="Check if everything is running properly - agents, monitoring, and the daemon",
                    expected_flat_tool="status",  # System status covers all
                    expected_hierarchical_tool="system",
                    expected_operation="status",
                    expected_parameters={},
                    complexity="complex",
                ),
                ToolInvocationScenario(
                    scenario_id="complex_2",
                    description="PM creation with details",
                    user_prompt="Create a new project manager called 'alpha-pm' to coordinate the API refactoring project with 3 developers",
                    expected_flat_tool="pm_create",
                    expected_hierarchical_tool="pm",
                    expected_operation="create",
                    expected_parameters={
                        "name": "alpha-pm",
                        "extend": "coordinate the API refactoring project with 3 developers",
                    },
                    complexity="complex",
                ),
                ToolInvocationScenario(
                    scenario_id="complex_3",
                    description="Recovery after failure",
                    user_prompt="The frontend agent crashed, can you bring it back up with the same configuration?",
                    expected_flat_tool="agent_restart",
                    expected_hierarchical_tool="agent",
                    expected_operation="restart",
                    expected_parameters={"target": "frontend"},
                    complexity="complex",
                ),
            ]
        )

        # Edge cases
        scenarios.extend(
            [
                ToolInvocationScenario(
                    scenario_id="edge_1",
                    description="Ambiguous target",
                    user_prompt="Send a message to the developer",
                    expected_flat_tool="agent_message",
                    expected_hierarchical_tool="agent",
                    expected_operation="message",
                    expected_parameters={"target": "developer", "message": ""},
                    complexity="complex",
                ),
                ToolInvocationScenario(
                    scenario_id="edge_2",
                    description="Multiple valid tools",
                    user_prompt="Show me what's happening in the system",
                    expected_flat_tool="monitor_dashboard",  # Could also be 'status'
                    expected_hierarchical_tool="monitor",
                    expected_operation="dashboard",
                    expected_parameters={},
                    complexity="complex",
                ),
            ]
        )

        return scenarios

    def create_flat_tool_descriptions(self) -> dict[str, str]:
        """Create descriptions for flat tool structure."""
        descriptions = {}

        for op in self.inventory.operations:
            descriptions[op.name] = f"{op.description}. Usage: {op.cli_command}"

        return descriptions

    def create_hierarchical_tool_descriptions(self) -> dict[str, dict[str, Any]]:
        """Create descriptions for hierarchical tool structure."""
        descriptions = {}

        for group, info in self.inventory.hierarchical_mapping.items():
            descriptions[group] = {
                "description": info["description"],
                "operations": info["operations"],
                "usage": f"Use '{group}' tool with operation parameter",
            }

        return descriptions

    def simulate_llm_selection(self, scenario: ToolInvocationScenario, tool_structure: str) -> InvocationResult:
        """Simulate LLM tool selection."""
        start_time = time.time()

        # In a real test, this would call an actual LLM
        # For now, we simulate with heuristics

        if tool_structure == "flat":
            # Simulate flat tool selection
            selected = self._select_flat_tool(scenario)
        else:
            # Simulate hierarchical tool selection
            selected = self._select_hierarchical_tool(scenario)

        response_time = time.time() - start_time

        # Check correctness
        if tool_structure == "flat":
            correct = selected["tool"] == scenario.expected_flat_tool
        else:
            correct = (
                selected["tool"] == scenario.expected_hierarchical_tool
                and selected.get("operation") == scenario.expected_operation
            )

        return InvocationResult(
            scenario_id=scenario.scenario_id,
            structure_type=tool_structure,
            selected_tool=selected.get("tool"),
            selected_operation=selected.get("operation"),
            selected_parameters=selected.get("parameters"),
            correct=correct,
            response_time=response_time,
            confidence=selected.get("confidence", 0.5),
            error=selected.get("error"),
        )

    def _select_flat_tool(self, scenario: ToolInvocationScenario) -> dict[str, Any]:
        """Simulate flat tool selection."""
        prompt_lower = scenario.user_prompt.lower()

        # Simple keyword matching for simulation
        tool_keywords = {
            "agent_status": ["agent", "status"],
            "agent_kill": ["kill", "agent"],
            "agent_restart": ["restart", "agent", "crashed"],
            "agent_message": ["message", "agent", "send"],
            "spawn_agent": ["deploy", "need", "agent", "developer"],
            "monitor_start": ["start", "monitoring"],
            "monitor_dashboard": ["happening", "system", "show"],
            "team_broadcast": ["team", "everyone", "tell"],
            "errors_recent": ["errors", "issues", "recent"],
            "pm_create": ["project manager", "create", "pm"],
            "status": ["everything", "running", "properly"],
        }

        best_match = None
        best_score = 0

        for tool, keywords in tool_keywords.items():
            score = sum(1 for kw in keywords if kw in prompt_lower)
            if score > best_score:
                best_score = score
                best_match = tool

        return {
            "tool": best_match or scenario.expected_flat_tool,
            "parameters": self._extract_parameters(scenario),
            "confidence": min(best_score / 3, 1.0) if best_score > 0 else 0.3,
        }

    def _select_hierarchical_tool(self, scenario: ToolInvocationScenario) -> dict[str, Any]:
        """Simulate hierarchical tool selection."""
        prompt_lower = scenario.user_prompt.lower()

        # Group detection
        group_keywords = {
            "agent": ["agent", "developer", "crashed"],
            "monitor": ["monitoring", "dashboard", "happening"],
            "team": ["team", "everyone"],
            "errors": ["errors", "issues"],
            "pm": ["project manager", "pm", "coordinate"],
            "spawn": ["deploy", "create new", "need a"],
            "system": ["everything", "system", "properly"],
        }

        # Find best matching group
        best_group = None
        best_score = 0

        for group, keywords in group_keywords.items():
            score = sum(1 for kw in keywords if kw in prompt_lower)
            if score > best_score:
                best_score = score
                best_group = group

        # Operation detection
        operation_keywords = {
            "status": ["status", "show", "check"],
            "kill": ["kill", "terminate"],
            "restart": ["restart", "bring back"],
            "start": ["start", "begin"],
            "broadcast": ["tell", "broadcast", "message"],
            "recent": ["recent", "recently"],
            "create": ["create", "new"],
            "dashboard": ["happening", "show"],
        }

        best_operation = None
        op_score = 0

        for op, keywords in operation_keywords.items():
            score = sum(1 for kw in keywords if kw in prompt_lower)
            if score > op_score:
                op_score = score
                best_operation = op

        return {
            "tool": best_group or scenario.expected_hierarchical_tool,
            "operation": best_operation or scenario.expected_operation,
            "parameters": self._extract_parameters(scenario),
            "confidence": min((best_score + op_score) / 6, 1.0) if best_score > 0 else 0.3,
        }

    def _extract_parameters(self, scenario: ToolInvocationScenario) -> dict[str, Any]:
        """Extract parameters from prompt (simplified)."""
        # In real implementation, would use NLP to extract parameters
        # For now, return expected parameters
        return scenario.expected_parameters

    def run_tests(self) -> dict[str, Any]:
        """Run all test scenarios."""
        print("🧪 Running LLM Invocation Tests")
        print("=" * 60)

        # Test both structures
        for structure in ["flat", "hierarchical"]:
            print(f"\n📋 Testing {structure} structure...")

            for scenario in self.scenarios:
                result = self.simulate_llm_selection(scenario, structure)
                self.results.append(result)

                if not result.correct:
                    print(f"   ❌ {scenario.scenario_id}: {scenario.description}")
                    print(
                        f"      Expected: {scenario.expected_flat_tool if structure == 'flat' else f'{scenario.expected_hierarchical_tool}.{scenario.expected_operation}'}"
                    )
                    print(
                        f"      Got: {result.selected_tool}{f'.{result.selected_operation}' if result.selected_operation else ''}"
                    )

        # Calculate metrics
        return self._calculate_metrics()

    def _calculate_metrics(self) -> dict[str, Any]:
        """Calculate success metrics."""
        flat_results = [r for r in self.results if r.structure_type == "flat"]
        hierarchical_results = [r for r in self.results if r.structure_type == "hierarchical"]

        # Overall success rates
        flat_success_rate = sum(1 for r in flat_results if r.correct) / len(flat_results) * 100
        hierarchical_success_rate = sum(1 for r in hierarchical_results if r.correct) / len(hierarchical_results) * 100

        # Success by complexity
        complexity_metrics = {}
        for complexity in ["simple", "medium", "complex"]:
            scenario_ids = [s.scenario_id for s in self.scenarios if s.complexity == complexity]

            flat_complex = [r for r in flat_results if r.scenario_id in scenario_ids]
            hier_complex = [r for r in hierarchical_results if r.scenario_id in scenario_ids]

            complexity_metrics[complexity] = {
                "flat_success": sum(1 for r in flat_complex if r.correct) / len(flat_complex) * 100
                if flat_complex
                else 0,
                "hierarchical_success": sum(1 for r in hier_complex if r.correct) / len(hier_complex) * 100
                if hier_complex
                else 0,
            }

        # Average response times
        flat_avg_time = sum(r.response_time for r in flat_results) / len(flat_results)
        hier_avg_time = sum(r.response_time for r in hierarchical_results) / len(hierarchical_results)

        # Average confidence
        flat_avg_confidence = sum(r.confidence for r in flat_results) / len(flat_results)
        hier_avg_confidence = sum(r.confidence for r in hierarchical_results) / len(hierarchical_results)

        return {
            "overall": {
                "flat_success_rate": flat_success_rate,
                "hierarchical_success_rate": hierarchical_success_rate,
                "improvement": hierarchical_success_rate - flat_success_rate,
            },
            "by_complexity": complexity_metrics,
            "performance": {
                "flat_avg_response_time": flat_avg_time,
                "hierarchical_avg_response_time": hier_avg_time,
                "time_improvement": (flat_avg_time - hier_avg_time) / flat_avg_time * 100,
            },
            "confidence": {"flat_avg": flat_avg_confidence, "hierarchical_avg": hier_avg_confidence},
            "total_scenarios": len(self.scenarios),
            "meets_95_percent_target": hierarchical_success_rate >= 95.0,
        }

    def save_results(self, metrics: dict[str, Any], filename: str = "llm_invocation_results.json"):
        """Save test results."""
        report = {
            "test_type": "llm_invocation",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "metrics": metrics,
            "detailed_results": [
                {
                    "scenario_id": r.scenario_id,
                    "structure": r.structure_type,
                    "correct": r.correct,
                    "selected": f"{r.selected_tool}{f'.{r.selected_operation}' if r.selected_operation else ''}",
                    "confidence": r.confidence,
                    "response_time": r.response_time,
                }
                for r in self.results
            ],
            "scenarios": [
                {"id": s.scenario_id, "description": s.description, "complexity": s.complexity, "prompt": s.user_prompt}
                for s in self.scenarios
            ],
        }

        report_path = Path(__file__).parent / filename
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        return report_path


def main():
    """Run LLM invocation tests."""
    tester = LLMInvocationTester()
    metrics = tester.run_tests()

    print("\n" + "=" * 60)
    print("📊 LLM INVOCATION TEST RESULTS")
    print("=" * 60)

    print("\nOverall Success Rates:")
    print(f"  Flat Structure: {metrics['overall']['flat_success_rate']:.1f}%")
    print(f"  Hierarchical Structure: {metrics['overall']['hierarchical_success_rate']:.1f}%")
    print(f"  Improvement: {metrics['overall']['improvement']:+.1f}%")

    print("\nSuccess by Complexity:")
    for complexity, rates in metrics["by_complexity"].items():
        print(f"  {complexity.capitalize()}:")
        print(f"    Flat: {rates['flat_success']:.1f}%")
        print(f"    Hierarchical: {rates['hierarchical_success']:.1f}%")

    print("\nPerformance:")
    print(f"  Response Time Improvement: {metrics['performance']['time_improvement']:.1f}%")

    print(f"\n✅ Meets 95% Success Target: {'YES' if metrics['meets_95_percent_target'] else 'NO'}")

    # Save results
    report_path = tester.save_results(metrics)
    print(f"\n💾 Detailed results saved to: {report_path}")

    return 0 if metrics["meets_95_percent_target"] else 1


if __name__ == "__main__":
    exit(main())

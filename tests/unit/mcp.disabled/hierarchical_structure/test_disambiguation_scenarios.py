#!/usr/bin/env python3
"""
Detailed test cases for disambiguation problems in hierarchical MCP tools.

Focus areas:
1. Agent deploy vs spawn confusion
2. Message targeting ambiguity
3. Action selection clarity
4. Similar operation disambiguation
"""

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))


@dataclass
class DisambiguationTest:
    """Test case for disambiguation scenarios."""

    test_id: str
    category: str  # "deploy_spawn", "message_target", "action_clarity", "similar_ops"
    prompt: str
    context: str | None
    expected_tool: str
    expected_action: str
    common_confusion: str
    disambiguation_hint: str
    enhanced_enum_description: str


class DisambiguationTestSuite:
    """Comprehensive test suite for disambiguation scenarios."""

    def __init__(self):
        self.test_cases = self._create_disambiguation_tests()
        self.enhancement_strategies = self._create_enhancement_strategies()

    def _create_disambiguation_tests(self) -> list[DisambiguationTest]:
        """Create detailed disambiguation test cases."""
        tests = []

        # Deploy vs Spawn Confusion Tests
        tests.extend(
            [
                DisambiguationTest(
                    test_id="deploy_spawn_1",
                    category="deploy_spawn",
                    prompt="I need a backend developer agent in the api-session",
                    context="Starting new development work",
                    expected_tool="spawn",
                    expected_action="agent",
                    common_confusion="agent.deploy",
                    disambiguation_hint="'need a' or 'create new' indicates spawning",
                    enhanced_enum_description="spawn.agent: Create a new agent with specified role | Requires: role, session | Ex: 'I need a backend developer'",
                ),
                DisambiguationTest(
                    test_id="deploy_spawn_2",
                    category="deploy_spawn",
                    prompt="Deploy the frontend team to production",
                    context="Team deployment scenario",
                    expected_tool="team",
                    expected_action="deploy",
                    common_confusion="spawn.agent",
                    disambiguation_hint="'deploy team' is team operation, not individual agent",
                    enhanced_enum_description="team.deploy: Deploy a complete team from plan | Requires: plan file | Ex: 'Deploy the frontend team'",
                ),
                DisambiguationTest(
                    test_id="deploy_spawn_3",
                    category="deploy_spawn",
                    prompt="Start up a new QA engineer agent",
                    context="Agent creation",
                    expected_tool="spawn",
                    expected_action="agent",
                    common_confusion="agent.start or agent.deploy",
                    disambiguation_hint="'start up new' means create, not restart",
                    enhanced_enum_description="spawn.agent: Create fresh agent instance | Keywords: new, start up, need, create",
                ),
            ]
        )

        # Message Targeting Ambiguity Tests
        tests.extend(
            [
                DisambiguationTest(
                    test_id="message_target_1",
                    category="message_target",
                    prompt="Send a message to the developer",
                    context="Single agent communication",
                    expected_tool="agent",
                    expected_action="message",
                    common_confusion="team.broadcast or pm.message",
                    disambiguation_hint="Singular 'developer' implies specific agent",
                    enhanced_enum_description="agent.message: Send to specific agent | Target required | Ex: 'message to the developer'",
                ),
                DisambiguationTest(
                    test_id="message_target_2",
                    category="message_target",
                    prompt="Tell all developers about the API changes",
                    context="Group communication",
                    expected_tool="team",
                    expected_action="broadcast",
                    common_confusion="agent.message",
                    disambiguation_hint="'all developers' indicates broadcast",
                    enhanced_enum_description="team.broadcast: Message all team members | Ex: 'Tell all developers', 'inform everyone'",
                ),
                DisambiguationTest(
                    test_id="message_target_3",
                    category="message_target",
                    prompt="Notify the PM about completion",
                    context="PM-specific communication",
                    expected_tool="pm",
                    expected_action="message",
                    common_confusion="agent.message",
                    disambiguation_hint="'the PM' specifically targets project manager",
                    enhanced_enum_description="pm.message: Direct PM communication | Ex: 'Notify the PM', 'Tell project manager'",
                ),
                DisambiguationTest(
                    test_id="message_target_4",
                    category="message_target",
                    prompt="Send update to frontend:1",
                    context="Direct session targeting",
                    expected_tool="agent",
                    expected_action="message",
                    common_confusion="agent.send",
                    disambiguation_hint="Session:window format with 'update' means message",
                    enhanced_enum_description="agent.message: Send text to agent | Format: session:window | 'update' = message content",
                ),
            ]
        )

        # Action Clarity Tests
        tests.extend(
            [
                DisambiguationTest(
                    test_id="action_clarity_1",
                    category="action_clarity",
                    prompt="Check on the monitoring system",
                    context="Status inquiry",
                    expected_tool="monitor",
                    expected_action="status",
                    common_confusion="monitor.dashboard",
                    disambiguation_hint="'check on' typically means status check",
                    enhanced_enum_description="monitor.status: Check if monitoring is active | Keywords: check on, verify, is running",
                ),
                DisambiguationTest(
                    test_id="action_clarity_2",
                    category="action_clarity",
                    prompt="View what's happening with agents",
                    context="Information request",
                    expected_tool="agent",
                    expected_action="status",
                    common_confusion="agent.list or monitor.dashboard",
                    disambiguation_hint="'what's happening' = current status",
                    enhanced_enum_description="agent.status: Show current agent states | Keywords: happening, current, now",
                ),
                DisambiguationTest(
                    test_id="action_clarity_3",
                    category="action_clarity",
                    prompt="Bring back the crashed backend agent",
                    context="Recovery scenario",
                    expected_tool="agent",
                    expected_action="restart",
                    common_confusion="recovery.start or spawn.agent",
                    disambiguation_hint="'bring back crashed' = restart existing",
                    enhanced_enum_description="agent.restart: Restart crashed/stopped agent | Keywords: bring back, recover, crashed",
                ),
            ]
        )

        # Similar Operations Tests
        tests.extend(
            [
                DisambiguationTest(
                    test_id="similar_ops_1",
                    category="similar_ops",
                    prompt="Stop all agents immediately",
                    context="Emergency shutdown",
                    expected_tool="agent",
                    expected_action="kill-all",
                    common_confusion="agent.kill or orchestrator.kill-all",
                    disambiguation_hint="'all agents' with 'stop' = agent.kill-all",
                    enhanced_enum_description="agent.kill-all: Terminate ALL agents | Keywords: stop all, kill everyone, emergency shutdown",
                ),
                DisambiguationTest(
                    test_id="similar_ops_2",
                    category="similar_ops",
                    prompt="Show me the error dashboard",
                    context="Error monitoring",
                    expected_tool="monitor",
                    expected_action="dashboard",
                    common_confusion="errors.recent or errors.summary",
                    disambiguation_hint="'dashboard' is monitoring feature",
                    enhanced_enum_description="monitor.dashboard: Visual system overview | Includes errors, agents, performance",
                ),
                DisambiguationTest(
                    test_id="similar_ops_3",
                    category="similar_ops",
                    prompt="Initialize the monitoring recovery system",
                    context="Recovery setup",
                    expected_tool="monitor",
                    expected_action="recovery-start",
                    common_confusion="recovery.start",
                    disambiguation_hint="'monitoring recovery' is monitor subsystem",
                    enhanced_enum_description="monitor.recovery-start: Enable auto-recovery monitoring | Not general recovery",
                ),
            ]
        )

        return tests

    def _create_enhancement_strategies(self) -> dict[str, dict[str, Any]]:
        """Create strategies for enhancing disambiguation."""
        return {
            "keyword_mapping": {
                "description": "Map common keywords to specific tools/actions",
                "examples": {
                    "need a": "spawn.agent",
                    "deploy team": "team.deploy",
                    "all agents": "agent.* (with -all suffix)",
                    "the PM": "pm.*",
                    "everyone": "*.broadcast",
                    "bring back": "*.restart",
                    "check on": "*.status",
                },
            },
            "context_clues": {
                "description": "Use context to disambiguate",
                "examples": {
                    "session:window format": "Likely agent-specific operation",
                    "plural targets": "Likely broadcast/team operation",
                    "recovery mentioned": "Check if monitor.recovery-* or general recovery.*",
                    "creation words": "Likely spawn.* not *.deploy",
                },
            },
            "enum_description_format": {
                "description": "Standardized format for clear descriptions",
                "template": "{Action verb} {target} | {Requirements} | Keywords: {keywords} | Ex: '{example}'",
                "components": {
                    "action_verb": "Clear action (Create, Send, Check, etc.)",
                    "target": "What it operates on",
                    "requirements": "Required parameters",
                    "keywords": "Common phrases that trigger this",
                    "example": "Real usage example",
                },
            },
            "disambiguation_rules": {
                "description": "Rules to prevent common confusions",
                "rules": [
                    "If 'new' or 'need' appears, prefer spawn over deploy",
                    "If target is singular, prefer specific over broadcast",
                    "If 'all' appears, look for -all variants first",
                    "If session:window format, it's agent-specific",
                    "Status checks use 'status', visual checks use 'dashboard'",
                ],
            },
        }

    def generate_enhanced_enum_descriptions(self) -> dict[str, dict[str, str]]:
        """Generate enhanced enum descriptions based on test cases."""
        descriptions: dict[str, dict[str, str]] = {}

        # Group test cases by tool
        for test in self.test_cases:
            tool = test.expected_tool
            action = test.expected_action

            if tool not in descriptions:
                descriptions[tool] = {}

            # Use the enhanced description from test case
            descriptions[tool][action] = test.enhanced_enum_description

        # Add additional standard descriptions
        descriptions.update(
            {
                "agent": {
                    "status": "Show all agents status | No params | Keywords: check, show, list running",
                    "kill": "Terminate specific agent | Requires: target | Keywords: stop, terminate, end",
                    "info": "Detailed agent information | Requires: target | Keywords: details, about, describe",
                    "attach": "Connect to agent session | Requires: target | Keywords: connect, join, enter",
                    "list": "List all known agents | No params | Keywords: show all, enumerate, inventory",
                    "send": "Send keystrokes to agent | Requires: target, keys | Keywords: type, input, keys",
                },
                "monitor": {
                    "start": "Start monitoring daemon | Options: interval | Keywords: begin, enable, activate monitoring",
                    "stop": "Stop monitoring daemon | No params | Keywords: disable, halt, end monitoring",
                    "logs": "View monitor logs | Options: lines, follow | Keywords: show logs, tail, history",
                    "performance": "Show performance metrics | No params | Keywords: metrics, stats, performance",
                },
                "team": {
                    "status": "Show team member status | No params | Keywords: team state, who's active",
                    "list": "List team members | No params | Keywords: show team, members, roster",
                    "recover": "Recover team from plan | Requires: plan | Keywords: restore team, bring back team",
                },
            }
        )

        return descriptions

    def create_disambiguation_test_report(self) -> dict[str, Any]:
        """Create comprehensive disambiguation test report."""
        # Group tests by category
        by_category: dict[str, list[Any]] = {}
        for test in self.test_cases:
            if test.category not in by_category:
                by_category[test.category] = []
            by_category[test.category].append(
                {
                    "test_id": test.test_id,
                    "prompt": test.prompt,
                    "expected": f"{test.expected_tool}.{test.expected_action}",
                    "common_confusion": test.common_confusion,
                    "disambiguation_hint": test.disambiguation_hint,
                }
            )

        return {
            "total_test_cases": len(self.test_cases),
            "categories": {
                "deploy_spawn": len([t for t in self.test_cases if t.category == "deploy_spawn"]),
                "message_target": len([t for t in self.test_cases if t.category == "message_target"]),
                "action_clarity": len([t for t in self.test_cases if t.category == "action_clarity"]),
                "similar_ops": len([t for t in self.test_cases if t.category == "similar_ops"]),
            },
            "test_cases_by_category": by_category,
            "enhancement_strategies": self.enhancement_strategies,
            "enhanced_descriptions": self.generate_enhanced_enum_descriptions(),
        }


def main():
    """Generate disambiguation test suite and report."""
    suite = DisambiguationTestSuite()
    report = suite.create_disambiguation_test_report()

    print("🎯 DISAMBIGUATION TEST SUITE")
    print("=" * 60)

    print(f"\nTotal Test Cases: {report['total_test_cases']}")
    print("\nTest Categories:")
    for category, count in report["categories"].items():
        print(f"  {category}: {count} tests")

    print("\n📋 Sample Test Cases:")
    for category, tests in report["test_cases_by_category"].items():
        print(f"\n{category.upper()}:")
        for test in tests[:2]:  # Show first 2 of each category
            print(f"  Prompt: '{test['prompt']}'")
            print(f"  Expected: {test['expected']}")
            print(f"  Common Confusion: {test['common_confusion']}")
            print(f"  Hint: {test['disambiguation_hint']}")
            print()

    # Save detailed report
    report_path = Path(__file__).parent / "disambiguation_test_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"💾 Detailed report saved to: {report_path}")

    # Generate enhancement recommendations
    print("\n🔧 KEY ENHANCEMENT RECOMMENDATIONS:")
    print("1. Add keyword mappings to enum descriptions")
    print("2. Include disambiguation hints in error messages")
    print("3. Standardize description format across all tools")
    print("4. Implement context-aware suggestions")

    return 0


if __name__ == "__main__":
    exit(main())

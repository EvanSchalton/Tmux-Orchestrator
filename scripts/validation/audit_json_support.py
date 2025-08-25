#!/usr/bin/env python3
"""
JSON Support Audit Script
Systematically tests all CLI commands for --json support
"""

import asyncio
import json
import subprocess
import time
from typing import Any


class JSONSupportAuditor:
    """Audit JSON support across all CLI commands."""

    def __init__(self):
        self.results = {}
        self.cli_structure = None

    async def get_cli_structure(self) -> dict[str, Any]:
        """Get complete CLI structure."""
        try:
            result = subprocess.run(
                ["tmux-orc", "reflect", "--format", "json"], capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                self.cli_structure = json.loads(result.stdout)
                return self.cli_structure
        except Exception as e:
            print(f"Failed to get CLI structure: {e}")
            return {}

    def extract_all_commands(self) -> list[str]:
        """Extract all command names from CLI structure."""
        if not self.cli_structure:
            return []

        commands = []

        # Direct commands
        for name, info in self.cli_structure.items():
            if isinstance(info, dict) and info.get("type") == "command":
                commands.append(name)

        # Group commands (need to get subcommands)
        groups = [
            name for name, info in self.cli_structure.items() if isinstance(info, dict) and info.get("type") == "group"
        ]

        # Get subcommands for each group
        for group in groups:
            subcommands = self.get_group_subcommands(group)
            for subcmd in subcommands:
                commands.append(f"{group} {subcmd}")

        return sorted(commands)

    def get_group_subcommands(self, group_name: str) -> list[str]:
        """Get subcommands for a group by running --help."""
        try:
            result = subprocess.run(["tmux-orc", group_name, "--help"], capture_output=True, text=True, timeout=10)

            # Parse help output to find subcommands
            lines = result.stdout.split("\n")
            subcommands = []

            in_commands_section = False
            for line in lines:
                if "Commands:" in line:
                    in_commands_section = True
                    continue

                if in_commands_section:
                    if line.startswith("  ") and not line.startswith("    "):
                        # This is a command line
                        cmd = line.strip().split()[0]
                        if cmd and not cmd.startswith("-"):
                            subcommands.append(cmd)
                    elif line.strip() == "" or not line.startswith(" "):
                        # End of commands section
                        break

            return subcommands

        except Exception as e:
            print(f"Failed to get subcommands for {group_name}: {e}")
            return []

    async def test_json_support(self, command_parts: list[str]) -> dict[str, Any]:
        """Test if a command supports --json flag."""
        cmd_name = " ".join(command_parts)
        print(f"Testing JSON support: {cmd_name}")

        # Test 1: Check if --json is in help
        try:
            help_result = subprocess.run(
                ["tmux-orc"] + command_parts + ["--help"], capture_output=True, text=True, timeout=10
            )

            has_json_in_help = "--json" in help_result.stdout

        except Exception as e:
            return {"command": cmd_name, "has_json_flag": False, "help_check_failed": True, "error": str(e)}

        # Test 2: Try executing with --json
        json_works = False
        json_output = None
        execution_error = None

        if has_json_in_help:
            try:
                # Use safe arguments that won't cause side effects
                if any(word in cmd_name.lower() for word in ["deploy", "spawn", "execute", "kill", "restart"]):
                    # Don't test destructive commands with --json
                    json_works = "skipped_destructive"
                else:
                    json_result = subprocess.run(
                        ["tmux-orc"] + command_parts + ["--json"], capture_output=True, text=True, timeout=15
                    )

                    if json_result.returncode == 0:
                        try:
                            json_output = json.loads(json_result.stdout)
                            json_works = True
                        except json.JSONDecodeError:
                            json_works = False
                            execution_error = "Invalid JSON output"
                    else:
                        json_works = False
                        execution_error = json_result.stderr.strip()

            except subprocess.TimeoutExpired:
                json_works = False
                execution_error = "Command timed out"
            except Exception as e:
                json_works = False
                execution_error = str(e)

        return {
            "command": cmd_name,
            "has_json_flag": has_json_in_help,
            "json_works": json_works,
            "json_output_sample": str(json_output)[:200] if json_output else None,
            "execution_error": execution_error,
        }

    async def run_comprehensive_audit(self):
        """Run comprehensive JSON support audit."""
        print("🔍 Starting Comprehensive JSON Support Audit")
        print("=" * 60)

        # Get CLI structure
        await self.get_cli_structure()
        if not self.cli_structure:
            print("❌ Failed to get CLI structure")
            return

        # Get all commands
        all_commands = self.extract_all_commands()
        print(f"📊 Found {len(all_commands)} total commands to test")

        # Test each command
        for i, cmd_name in enumerate(all_commands, 1):
            print(f"\n[{i}/{len(all_commands)}] Testing: {cmd_name}")

            command_parts = cmd_name.split()
            result = await self.test_json_support(command_parts)
            self.results[cmd_name] = result

            # Quick status
            if result.get("has_json_flag"):
                if result.get("json_works") is True:
                    print("  ✅ JSON support working")
                elif result.get("json_works") == "skipped_destructive":
                    print("  ⚠️  JSON flag present (skipped destructive test)")
                else:
                    print(f"  ❌ JSON flag present but not working: {result.get('execution_error', 'Unknown error')}")
            else:
                print("  ⚪ No JSON support")

        # Generate report
        await self.generate_audit_report()

    async def generate_audit_report(self):
        """Generate comprehensive audit report."""
        print("\n" + "=" * 80)
        print("📋 JSON SUPPORT AUDIT REPORT")
        print("=" * 80)

        # Categorize results
        json_working = []
        json_flagged_but_broken = []
        json_skipped_destructive = []
        no_json_support = []

        for cmd, result in self.results.items():
            if result.get("json_works") is True:
                json_working.append(cmd)
            elif result.get("json_works") == "skipped_destructive":
                json_skipped_destructive.append(cmd)
            elif result.get("has_json_flag") and not result.get("json_works"):
                json_flagged_but_broken.append(cmd)
            else:
                no_json_support.append(cmd)

        total = len(self.results)
        working_count = len(json_working)

        print("📊 SUMMARY:")
        print(f"   • Total commands tested: {total}")
        print(f"   • Working JSON support: {working_count}")
        print(f"   • JSON flag but broken: {len(json_flagged_but_broken)}")
        print(f"   • Destructive (skipped): {len(json_skipped_destructive)}")
        print(f"   • No JSON support: {len(no_json_support)}")
        print(f"   • JSON coverage: {(working_count / total * 100):.1f}%")

        # Detailed breakdowns
        print(f"\n✅ COMMANDS WITH WORKING JSON SUPPORT ({len(json_working)}):")
        for cmd in sorted(json_working):
            print(f"   • {cmd}")

        if json_skipped_destructive:
            print(f"\n⚠️  DESTRUCTIVE COMMANDS (JSON FLAG PRESENT, SKIPPED TESTING) ({len(json_skipped_destructive)}):")
            for cmd in sorted(json_skipped_destructive):
                print(f"   • {cmd}")

        if json_flagged_but_broken:
            print(f"\n❌ COMMANDS WITH BROKEN JSON SUPPORT ({len(json_flagged_but_broken)}):")
            for cmd in sorted(json_flagged_but_broken):
                error = self.results[cmd].get("execution_error", "Unknown error")
                print(f"   • {cmd}: {error}")

        print(f"\n⚪ COMMANDS WITHOUT JSON SUPPORT ({len(no_json_support)}):")
        for cmd in sorted(no_json_support):
            print(f"   • {cmd}")

        # Prioritize missing JSON support
        print("\n🎯 PRIORITY RECOMMENDATIONS:")

        # High priority - core operational commands
        high_priority = [
            cmd
            for cmd in no_json_support
            if any(keyword in cmd.lower() for keyword in ["agent", "team", "pm", "spawn", "monitor", "status", "list"])
        ]

        if high_priority:
            print("   HIGH PRIORITY (core operational commands):")
            for cmd in sorted(high_priority):
                print(f"     • {cmd}")

        # Medium priority - workflow commands
        medium_priority = [
            cmd
            for cmd in no_json_support
            if any(keyword in cmd.lower() for keyword in ["tasks", "pubsub", "context", "setup"])
            and cmd not in high_priority
        ]

        if medium_priority:
            print("   MEDIUM PRIORITY (workflow commands):")
            for cmd in sorted(medium_priority):
                print(f"     • {cmd}")

        # Save detailed results
        report_file = "/workspaces/Tmux-Orchestrator/json_support_audit.json"
        with open(report_file, "w") as f:
            json.dump(
                {
                    "timestamp": time.time(),
                    "summary": {
                        "total_commands": total,
                        "working_json": working_count,
                        "broken_json": len(json_flagged_but_broken),
                        "skipped_destructive": len(json_skipped_destructive),
                        "no_json_support": len(no_json_support),
                        "coverage_percentage": working_count / total * 100,
                    },
                    "categories": {
                        "working": json_working,
                        "broken": json_flagged_but_broken,
                        "skipped": json_skipped_destructive,
                        "no_support": no_json_support,
                    },
                    "detailed_results": self.results,
                },
                f,
                indent=2,
            )

        print(f"\n💾 Detailed results saved to: {report_file}")
        print("=" * 80)


async def main():
    """Main execution."""
    auditor = JSONSupportAuditor()
    await auditor.run_comprehensive_audit()


if __name__ == "__main__":
    asyncio.run(main())

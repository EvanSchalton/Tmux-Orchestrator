#!/usr/bin/env python3
"""
Real-time monitoring script for test class conversions.
Tracks changes, identifies patterns, and provides immediate feedback.
"""

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any


class ConversionMonitor:
    """Monitor test file conversions in real-time."""

    def __init__(self):
        self.baseline_file = "test_class_conversion_priority.json"
        self.patterns_file = "conversion_patterns_learned.json"
        self.monitoring_log = "conversion_monitoring_log.txt"
        self.patterns_learned = self.load_patterns()

    def load_patterns(self) -> dict[Any, Any]:
        """Load previously learned conversion patterns."""
        try:
            with open(self.patterns_file) as f:
                data: dict[Any, Any] = json.load(f)
                return data
        except FileNotFoundError:
            return {"fixture_patterns": {}, "naming_patterns": {}, "common_conversions": []}

    def save_patterns(self):
        """Save learned patterns for future use."""
        with open(self.patterns_file, "w") as f:
            json.dump(self.patterns_learned, f, indent=2)

    def check_file_status(self, filepath: Path) -> dict:
        """Check current status of a test file."""
        if not filepath.exists():
            return {"exists": False}

        content = filepath.read_text()

        # Count various patterns
        class_count = content.count("class Test")
        function_count = len([line for line in content.splitlines() if line.strip().startswith("def test_")])
        setup_count = sum(
            1
            for line in content.splitlines()
            if any(pattern in line for pattern in ["def setup", "def setUp", "def teardown", "def tearDown"])
        )
        fixture_count = content.count("@pytest.fixture")

        # Check for common issues
        has_self_refs = "self." in content and "def test_" in content
        has_unittest = "unittest.TestCase" in content

        return {
            "exists": True,
            "classes": class_count,
            "functions": function_count,
            "setup_methods": setup_count,
            "fixtures": fixture_count,
            "has_self_refs": has_self_refs,
            "has_unittest": has_unittest,
            "size": len(content.splitlines()),
        }

    def analyze_conversion(self, before: dict, after: dict, filepath: str) -> dict:
        """Analyze a conversion and extract patterns."""
        analysis: dict[str, Any] = {
            "file": filepath,
            "timestamp": datetime.now().isoformat(),
            "changes": {
                "classes_removed": before["classes"] - after["classes"],
                "functions_added": after["functions"] - before["functions"],
                "setup_converted": before["setup_methods"] - after["setup_methods"],
                "fixtures_added": after["fixtures"] - before["fixtures"],
            },
            "issues": [],
            "patterns": [],
        }

        # Check for issues
        if after["classes"] > 0:
            analysis["issues"].append(f"Still has {after['classes']} test classes")

        if after["has_self_refs"]:
            analysis["issues"].append("Still contains self references")

        if after["has_unittest"]:
            analysis["issues"].append("Still imports unittest.TestCase")

        expected_functions = before["functions"] + (before["classes"] * 5)  # Estimate
        if after["functions"] < expected_functions * 0.8:
            analysis["issues"].append("Possible test loss - fewer functions than expected")

        # Extract patterns
        if before["setup_methods"] > 0 and after["fixtures"] > before["fixtures"]:
            fixture_ratio = after["fixtures"] / before["setup_methods"]
            analysis["patterns"].append(f"Setup-to-fixture ratio: {fixture_ratio:.1f}")
            self.patterns_learned["fixture_patterns"][filepath] = fixture_ratio

        return analysis

    def run_tests(self, filepath: str) -> tuple[bool, int, list[str]]:
        """Run tests for the converted file."""
        try:
            result = subprocess.run(
                ["poetry", "run", "pytest", filepath, "-v", "--tb=short"], capture_output=True, text=True, timeout=30
            )

            # Parse results
            lines = result.stdout.splitlines()
            passed = sum(1 for line in lines if " PASSED" in line)
            failed = sum(1 for line in lines if " FAILED" in line)
            errors = [line for line in lines if " FAILED" in line or " ERROR" in line]

            return result.returncode == 0, passed + failed, errors
        except subprocess.TimeoutExpired:
            return False, 0, ["Test execution timed out"]
        except Exception as e:
            return False, 0, [f"Error running tests: {e}"]

    def generate_feedback(self, analysis: dict, test_results: tuple) -> list[str]:
        """Generate immediate feedback for the developer."""
        feedback = []
        success, test_count, errors = test_results

        # Positive feedback
        if analysis["changes"]["classes_removed"] > 0:
            feedback.append(f"✅ Successfully removed {analysis['changes']['classes_removed']} test classes")

        if analysis["changes"]["fixtures_added"] > 0:
            feedback.append(f"✅ Added {analysis['changes']['fixtures_added']} fixtures")

        if success and test_count > 0:
            feedback.append(f"✅ All {test_count} tests passing")

        # Issues to address
        for issue in analysis["issues"]:
            feedback.append(f"⚠️  {issue}")

        if not success:
            feedback.append(f"❌ {len(errors)} test failures detected")
            for error in errors[:3]:  # Show first 3 errors
                feedback.append(f"   - {error.strip()}")

        # Suggestions based on patterns
        if analysis["patterns"]:
            feedback.append("\n💡 Patterns detected:")
            for pattern in analysis["patterns"]:
                feedback.append(f"   - {pattern}")

        return feedback

    def monitor_file(self, filepath: str):
        """Monitor a specific file conversion."""
        path = Path(filepath)
        print(f"\n=== Monitoring Conversion: {filepath} ===")
        print(f"Time: {datetime.now().strftime('%H:%M:%S')}")

        # Get before state (from saved data or current)
        before = self.check_file_status(path)
        if not before["exists"]:
            print("❌ File not found")
            return

        print(f"\nBefore: {before['classes']} classes, {before['functions']} functions")

        # Wait for changes
        print("\nWaiting for changes... (Press Ctrl+C to stop)")
        last_modified = path.stat().st_mtime

        try:
            while True:
                time.sleep(2)  # Check every 2 seconds

                if path.stat().st_mtime > last_modified:
                    last_modified = path.stat().st_mtime
                    print(f"\n🔄 Change detected at {datetime.now().strftime('%H:%M:%S')}")

                    # Get after state
                    after = self.check_file_status(path)

                    # Analyze conversion
                    analysis = self.analyze_conversion(before, after, filepath)

                    # Run tests
                    print("Running tests...")
                    test_results = self.run_tests(filepath)

                    # Generate feedback
                    feedback = self.generate_feedback(analysis, test_results)

                    print("\n=== Conversion Feedback ===")
                    for line in feedback:
                        print(line)

                    # Log the conversion
                    self.log_conversion(analysis, feedback)

                    # Update patterns
                    self.save_patterns()

                    # Update before state for next iteration
                    before = after

                    if after["classes"] == 0 and test_results[0]:
                        print("\n🎉 Conversion complete! All classes removed and tests passing.")
                        break

        except KeyboardInterrupt:
            print("\n\nMonitoring stopped.")

    def log_conversion(self, analysis: dict, feedback: list[str]):
        """Log conversion details for analysis."""
        with open(self.monitoring_log, "a") as f:
            f.write(f"\n{'=' * 60}\n")
            f.write(f"File: {analysis['file']}\n")
            f.write(f"Time: {analysis['timestamp']}\n")
            f.write(f"Changes: {json.dumps(analysis['changes'], indent=2)}\n")
            f.write("Feedback:\n")
            for line in feedback:
                f.write(f"  {line}\n")

    def show_common_patterns(self):
        """Display commonly seen conversion patterns."""
        print("\n=== Common Conversion Patterns ===")

        if self.patterns_learned["fixture_patterns"]:
            print("\nFixture Conversion Ratios:")
            for file, ratio in self.patterns_learned["fixture_patterns"].items():
                print(f"  {Path(file).name}: {ratio:.1f} fixtures per setup method")

        if self.patterns_learned["common_conversions"]:
            print("\nFrequent Conversions:")
            for pattern in self.patterns_learned["common_conversions"][:5]:
                print(f"  - {pattern}")


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Monitor specific file:  python realtime_conversion_monitor.py <file_path>")
        print("  Show patterns:         python realtime_conversion_monitor.py patterns")
        return 1

    monitor = ConversionMonitor()

    if sys.argv[1] == "patterns":
        monitor.show_common_patterns()
    else:
        monitor.monitor_file(sys.argv[1])

    return 0


if __name__ == "__main__":
    sys.exit(main())

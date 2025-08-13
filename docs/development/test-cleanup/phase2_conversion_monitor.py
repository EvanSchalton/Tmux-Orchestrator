#!/usr/bin/env python3
"""
Monitor script for Phase 2: Test class to function conversion.
Tracks progress and validates conversions maintain test functionality.
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple


def get_test_inventory() -> Dict[str, Set[str]]:
    """Get current test inventory."""
    try:
        result = subprocess.run(["poetry", "run", "pytest", "--collect-only", "-q"], capture_output=True, text=True)

        inventory = {}
        current_file = None

        for line in result.stdout.splitlines():
            if "<Module" in line:
                current_file = line.split("<Module ")[-1].replace(">", "").strip()
                inventory[current_file] = set()
            elif "<Function" in line and current_file:
                test_name = line.split("<Function ")[-1].replace(">", "").strip()
                inventory[current_file].add(test_name)

        return inventory
    except Exception as e:
        print(f"Error collecting tests: {e}")
        return {}


def run_test_file(filepath: str) -> Tuple[bool, int, List[str]]:
    """Run tests for a specific file and return results."""
    try:
        result = subprocess.run(
            ["poetry", "run", "pytest", filepath, "-v", "--tb=short"], capture_output=True, text=True
        )

        # Parse results
        passed = failed = 0
        failures = []

        for line in result.stdout.splitlines():
            if " PASSED" in line:
                passed += 1
            elif " FAILED" in line:
                failed += 1
                failures.append(line.strip())

        success = result.returncode == 0
        total = passed + failed

        return success, total, failures
    except Exception as e:
        return False, 0, [f"Error running tests: {e}"]


def check_file_for_classes(filepath: Path) -> Tuple[int, int]:
    """Check if file still contains test classes."""
    try:
        content = filepath.read_text()
        class_count = content.count("class Test")
        function_count = len([line for line in content.splitlines() if line.strip().startswith("def test_")])
        return class_count, function_count
    except Exception:
        return 0, 0


def load_baseline():
    """Load baseline data."""
    baseline_files = {"inventory": "test_inventory_baseline.json", "class_analysis": "test_class_analysis.json"}

    baseline = {}
    for key, filename in baseline_files.items():
        try:
            with open(filename) as f:
                baseline[key] = json.load(f)
        except FileNotFoundError:
            baseline[key] = {}

    return baseline


def check_conversion_progress() -> Dict:
    """Check overall conversion progress."""
    test_files = list(Path("tests").rglob("*_test.py"))

    progress = {
        "total_files": len(test_files),
        "files_with_classes": 0,
        "files_converted": 0,
        "total_classes_remaining": 0,
        "total_functions": 0,
        "files_status": [],
    }

    for filepath in test_files:
        classes, functions = check_file_for_classes(filepath)

        file_status = {
            "path": str(filepath),
            "has_classes": classes > 0,
            "class_count": classes,
            "function_count": functions,
        }

        if classes > 0:
            progress["files_with_classes"] += 1
            progress["total_classes_remaining"] += classes
        else:
            progress["files_converted"] += 1

        progress["total_functions"] += functions
        progress["files_status"].append(file_status)

    return progress


def validate_conversion(file_path: str, before_tests: Set[str], after_tests: Set[str]) -> Dict:
    """Validate a single file conversion."""
    validation = {
        "file": file_path,
        "status": "unknown",
        "issues": [],
        "test_count_before": len(before_tests),
        "test_count_after": len(after_tests),
    }

    # Check test count
    if len(after_tests) < len(before_tests):
        validation["issues"].append(f"Test count decreased: {len(before_tests)} → {len(after_tests)}")
        validation["status"] = "failed"

    # Check for missing tests
    missing_tests = before_tests - after_tests
    if missing_tests:
        validation["issues"].append(f"Missing tests: {', '.join(sorted(missing_tests)[:5])}")
        validation["status"] = "failed"

    # Run the tests
    success, total, failures = run_test_file(file_path)
    if not success:
        validation["issues"].append(f"Tests failing: {len(failures)} failures")
        validation["status"] = "failed"

    # Check for classes
    path = Path(file_path)
    if path.exists():
        classes, functions = check_file_for_classes(path)
        if classes > 0:
            validation["issues"].append(f"Still has {classes} test classes")
            validation["status"] = "partial"

    if not validation["issues"]:
        validation["status"] = "success"

    return validation


def main(action: str = "monitor"):
    if action == "baseline":
        print("=== Saving Phase 2 Baseline ===")

        # Run class analysis
        subprocess.run([sys.executable, "docs/development/test-cleanup/validate_test_classes.py"])

        # Get test inventory
        inventory = get_test_inventory()
        with open("phase2_baseline_inventory.json", "w") as f:
            json.dump({k: list(v) for k, v in inventory.items()}, f, indent=2)

        print(f"Baseline saved with {len(inventory)} files")

    elif action == "monitor":
        print("=== Phase 2 Conversion Monitor ===")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # Check progress
        progress = check_conversion_progress()

        print(f"Total files: {progress['total_files']}")
        print(
            f"Files converted: {progress['files_converted']} ({progress['files_converted']*100/progress['total_files']:.1f}%)"
        )
        print(f"Files with classes: {progress['files_with_classes']}")
        print(f"Total classes remaining: {progress['total_classes_remaining']}")
        print(f"Total test functions: {progress['total_functions']}")

        # Show files still needing conversion
        if progress["files_with_classes"] > 0:
            print("\n=== Files Still Needing Conversion ===")
            files_with_classes = [f for f in progress["files_status"] if f["has_classes"]]
            for file_info in sorted(files_with_classes, key=lambda x: x["class_count"], reverse=True)[:10]:
                print(
                    f"  {file_info['path']}: {file_info['class_count']} classes, {file_info['function_count']} functions"
                )

        # Check for issues
        current_inventory = get_test_inventory()
        baseline = load_baseline()

        if "inventory" in baseline and baseline["inventory"]:
            baseline_inventory = {k: set(v) for k, v in baseline["inventory"].items()}

            # Compare test counts
            baseline_total = sum(len(tests) for tests in baseline_inventory.values())
            current_total = sum(len(tests) for tests in current_inventory.values())

            print("\n=== Test Count Comparison ===")
            print(f"Baseline: {baseline_total} tests")
            print(f"Current: {current_total} tests")

            if current_total < baseline_total:
                print(f"⚠️  WARNING: {baseline_total - current_total} tests missing!")

        # Save progress report
        report = {
            "timestamp": datetime.now().isoformat(),
            "progress": progress,
            "test_count": sum(len(tests) for tests in current_inventory.values()),
        }

        with open("phase2_progress.json", "w") as f:
            json.dump(report, f, indent=2)

        print("\nProgress report saved to: phase2_progress.json")

    elif action == "validate":
        # Validate specific file conversion
        if len(sys.argv) < 3:
            print("Usage: python phase2_conversion_monitor.py validate <file_path>")
            return 1

        file_path = sys.argv[2]
        print(f"=== Validating Conversion: {file_path} ===")

        # Load baseline
        baseline = load_baseline()
        baseline_tests = set()

        if "inventory" in baseline and baseline["inventory"]:
            for fname, tests in baseline["inventory"].items():
                if fname == file_path or fname.endswith(Path(file_path).name):
                    baseline_tests = set(tests)
                    break

        # Get current tests
        current_inventory = get_test_inventory()
        current_tests = set()

        for fname, tests in current_inventory.items():
            if fname == file_path or fname.endswith(Path(file_path).name):
                current_tests = tests
                break

        # Validate
        validation = validate_conversion(file_path, baseline_tests, current_tests)

        print(f"\nValidation Result: {validation['status'].upper()}")
        if validation["issues"]:
            print("Issues found:")
            for issue in validation["issues"]:
                print(f"  - {issue}")
        else:
            print("✅ Conversion successful!")

        return 0 if validation["status"] == "success" else 1

    else:
        print(f"Usage: {sys.argv[0]} [baseline|monitor|validate]")
        return 1

    return 0


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "monitor"
    sys.exit(main(action))

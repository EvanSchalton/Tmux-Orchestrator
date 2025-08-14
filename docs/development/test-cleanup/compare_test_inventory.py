#!/usr/bin/env python3
"""
Compare test inventory before and after renaming to ensure no tests are lost.
This script performs deep comparison of test functions, not just file counts.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Set, Tuple


def get_detailed_test_inventory() -> Dict[str, Set[str]]:
    """Get detailed inventory of all tests organized by file."""
    try:
        result = subprocess.run(["poetry", "run", "pytest", "--collect-only", "-q"], capture_output=True, text=True)

        inventory: dict[str, set[str]] = {}
        current_file = None

        for line in result.stdout.splitlines():
            if "<Module" in line:
                # Extract filename
                current_file = line.split("<Module ")[-1].replace(">", "").strip()
                inventory[current_file] = set()
            elif "<Function" in line and current_file:
                # Extract test function name
                test_name = line.split("<Function ")[-1].replace(">", "").strip()
                inventory[current_file].add(test_name)

        return inventory
    except Exception as e:
        print(f"Error collecting tests: {e}")
        return {}


def save_inventory(inventory: Dict[str, Set[str]], filename: str):
    """Save inventory to file for comparison."""
    # Convert sets to lists for JSON serialization
    json_inventory = {k: sorted(list(v)) for k, v in inventory.items()}

    with open(filename, "w") as f:
        json.dump(json_inventory, f, indent=2, sort_keys=True)


def load_inventory(filename: str) -> Dict[str, Set[str]]:
    """Load inventory from file."""
    try:
        with open(filename) as f:
            json_inventory = json.load(f)
        # Convert lists back to sets
        return {k: set(v) for k, v in json_inventory.items()}
    except FileNotFoundError:
        return {}


def compare_inventories(before: Dict[str, Set[str]], after: Dict[str, Set[str]]) -> Tuple[bool, Dict]:
    """Compare two test inventories and return differences."""
    all_tests_before = set()
    all_tests_after = set()

    # Collect all test names
    for tests in before.values():
        all_tests_before.update(tests)

    for tests in after.values():
        all_tests_after.update(tests)

    # Find differences
    missing_tests = all_tests_before - all_tests_after
    new_tests = all_tests_after - all_tests_before

    # Map old filenames to new filenames
    file_mapping = {}
    for old_file in before:
        old_base = Path(old_file).stem
        for new_file in after:
            new_base = Path(new_file).stem
            # Check if it's the same file with different naming pattern
            if old_base.replace("test_", "") == new_base.replace("_test", "") or old_base == new_base:
                file_mapping[old_file] = new_file
                break

    differences = {
        "total_before": len(all_tests_before),
        "total_after": len(all_tests_after),
        "missing_tests": sorted(list(missing_tests)),
        "new_tests": sorted(list(new_tests)),
        "file_mapping": file_mapping,
        "files_before": len(before),
        "files_after": len(after),
    }

    is_valid = len(missing_tests) == 0 and len(all_tests_after) >= len(all_tests_before)

    return is_valid, differences


def main(action: str = "check"):
    if action == "save":
        print("=== Saving Current Test Inventory ===")
        inventory = get_detailed_test_inventory()
        save_inventory(inventory, "test_inventory_baseline.json")

        total_tests = sum(len(tests) for tests in inventory.values())
        print(f"Saved inventory with {len(inventory)} files and {total_tests} tests")
        print("Baseline saved to: test_inventory_baseline.json")

    elif action == "check":
        print("=== Comparing Test Inventory ===")

        # Load baseline
        baseline = load_inventory("test_inventory_baseline.json")
        if not baseline:
            print("❌ No baseline found! Run with 'save' argument first.")
            return 1

        # Get current inventory
        current = get_detailed_test_inventory()

        # Compare
        is_valid, diff = compare_inventories(baseline, current)

        print(f"\nBaseline: {diff['files_before']} files, {diff['total_before']} tests")
        print(f"Current:  {diff['files_after']} files, {diff['total_after']} tests")

        if diff["missing_tests"]:
            print(f"\n❌ WARNING: {len(diff['missing_tests'])} tests are missing:")
            for test in diff["missing_tests"][:10]:
                print(f"   - {test}")
            if len(diff["missing_tests"]) > 10:
                print(f"   ... and {len(diff['missing_tests']) - 10} more")

        if diff["new_tests"]:
            print(f"\nℹ️  {len(diff['new_tests'])} new tests found:")
            for test in diff["new_tests"][:5]:
                print(f"   + {test}")
            if len(diff["new_tests"]) > 5:
                print(f"   ... and {len(diff['new_tests']) - 5} more")

        if is_valid:
            print("\n✅ All tests accounted for! Renaming is safe.")
        else:
            print("\n❌ Test inventory mismatch! Review missing tests.")

        # Save comparison report
        with open("test_inventory_comparison.json", "w") as f:
            json.dump(diff, f, indent=2)
        print("\nDetailed comparison saved to: test_inventory_comparison.json")

        return 0 if is_valid else 1

    else:
        print(f"Usage: {sys.argv[0]} [save|check]")
        return 1


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "check"
    sys.exit(main(action))

#!/usr/bin/env python3
"""
Validation script to ensure all renamed test files are discovered by pytest.
This script checks that files following the new *_test.py pattern are properly discovered.
"""

import subprocess
import sys
from pathlib import Path
from typing import List, Set, Tuple


def get_test_files_from_filesystem() -> Set[str]:
    """Find all test files in the filesystem."""
    test_files = set()
    tests_dir = Path("tests")

    # Find files with both old and new patterns
    for pattern in ["test_*.py", "*_test.py"]:
        for file in tests_dir.rglob(pattern):
            if file.name != "__init__.py" and not file.name.startswith("."):
                test_files.add(str(file))

    return test_files


def get_pytest_discovered_files() -> Set[str]:
    """Get list of files discovered by pytest."""
    try:
        result = subprocess.run(
            ["poetry", "run", "pytest", "--collect-only", "--quiet"], capture_output=True, text=True
        )

        discovered_files = set()
        for line in result.stdout.splitlines():
            if "<Module" in line:
                # Extract filename from pytest output
                file_part = line.split("<Module ")[-1].replace(">", "").strip()
                discovered_files.add(file_part)

        return discovered_files
    except Exception as e:
        print(f"Error running pytest: {e}")
        return set()


def get_test_count() -> int:
    """Get total number of tests discovered."""
    try:
        result = subprocess.run(["poetry", "run", "pytest", "--collect-only", "-q"], capture_output=True, text=True)

        for line in result.stderr.splitlines() + result.stdout.splitlines():
            if "collected" in line and "items" in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == "collected" and i + 1 < len(parts):
                        return int(parts[i + 1])
        return 0
    except Exception:
        return 0


def analyze_naming_patterns(files: Set[str]) -> Tuple[List[str], List[str]]:
    """Categorize files by naming pattern."""
    old_pattern = []  # test_*.py
    new_pattern = []  # *_test.py

    for file in sorted(files):
        filename = Path(file).name
        if filename.startswith("test_") and not filename.endswith("_test.py"):
            old_pattern.append(file)
        elif filename.endswith("_test.py") and not filename.startswith("test_"):
            new_pattern.append(file)

    return old_pattern, new_pattern


def main():
    print("=== Test File Discovery Validation ===\n")

    # Get files from filesystem
    fs_files = get_test_files_from_filesystem()
    print(f"Files found in filesystem: {len(fs_files)}")

    # Get files discovered by pytest
    pytest_files = get_pytest_discovered_files()
    print(f"Files discovered by pytest: {len(pytest_files)}")

    # Get test count
    test_count = get_test_count()
    print(f"Total tests collected: {test_count}")

    # Check for missing files
    missing_files = fs_files - pytest_files
    if missing_files:
        print(f"\n❌ WARNING: {len(missing_files)} files not discovered by pytest:")
        for file in sorted(missing_files):
            print(f"   - {file}")
    else:
        print("\n✅ All test files are discovered by pytest")

    # Analyze naming patterns
    old_pattern, new_pattern = analyze_naming_patterns(fs_files)

    print("\n=== Naming Pattern Progress ===")
    print(f"Files with old pattern (test_*.py): {len(old_pattern)}")
    print(f"Files with new pattern (*_test.py): {len(new_pattern)}")
    print(f"Progress: {len(new_pattern)}/{len(fs_files)} ({len(new_pattern) * 100 / len(fs_files):.1f}%)")

    # Show first few files of each pattern
    if old_pattern:
        print("\nRemaining files to rename:")
        for file in old_pattern[:5]:
            print(f"   - {file}")
        if len(old_pattern) > 5:
            print(f"   ... and {len(old_pattern) - 5} more")

    # Baseline comparison
    print("\n=== Baseline Comparison ===")
    print("Expected total tests: 765")
    print(f"Current total tests: {test_count}")
    if test_count < 765:
        print(f"⚠️  WARNING: {765 - test_count} tests missing!")
    elif test_count > 765:
        print(f"ℹ️  Note: {test_count - 765} tests added")
    else:
        print("✅ Test count matches baseline")

    return 0 if len(missing_files) == 0 and test_count == 765 else 1


if __name__ == "__main__":
    sys.exit(main())

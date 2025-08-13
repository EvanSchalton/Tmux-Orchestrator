#!/usr/bin/env python3
"""Remove duplicate fixtures that are now in conftest.py."""

import re
from pathlib import Path

# Fixtures that are now in conftest.py
COMMON_FIXTURES = {
    "mock_tmux": "Create a mock TMUXManager for testing.",
    "logger": "Create a mock logger for testing.",
    "runner": "Create Click test runner.",
    "temp_activity_file": "Create a temporary activity file for testing.",
    "temp_schedule_file": "Create a temporary schedule file for testing.",
    "temp_orchestrator_dir": "Create temporary orchestrator directory.",
}


def remove_duplicate_fixtures(file_path):
    """Remove duplicate fixtures from a test file."""
    with open(file_path) as f:
        content = f.read()

    original_content = content

    # Pattern to match fixture definitions
    for fixture_name in COMMON_FIXTURES:
        # Match the entire fixture definition including decorator and function body
        pattern = rf"@pytest\.fixture[^@]*\ndef {fixture_name}\([^)]*\):[^@]+?(?=\n(?:def|@|class|\Z))"
        content = re.sub(pattern, "", content, flags=re.DOTALL)

    # Clean up extra blank lines
    content = re.sub(r"\n{3,}", "\n\n", content)

    # Only write if changes were made
    if content != original_content:
        with open(file_path, "w") as f:
            f.write(content)
        return True

    return False


def main():
    """Process all test files."""
    test_files = list(Path("tests").rglob("*_test.py"))

    updated_count = 0
    for file_path in sorted(test_files):
        # Skip conftest.py itself
        if file_path.name == "conftest.py":
            continue

        if remove_duplicate_fixtures(file_path):
            print(f"Updated: {file_path}")
            updated_count += 1

    print(f"\nTotal files updated: {updated_count}")


if __name__ == "__main__":
    main()

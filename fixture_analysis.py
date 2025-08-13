#!/usr/bin/env python3
"""Analyze test fixtures for consolidation opportunities."""

import re
from collections import defaultdict
from pathlib import Path


def extract_fixtures(file_path):
    """Extract fixture definitions from a Python file."""
    fixtures = []

    try:
        with open(file_path) as f:
            content = f.read()

        # Find fixtures using regex
        fixture_pattern = r'@pytest\.fixture.*?\ndef\s+(\w+)\([^)]*\):\s*\n\s*"""([^"]*)"""'
        matches = re.findall(fixture_pattern, content, re.DOTALL)

        for name, docstring in matches:
            fixtures.append({"name": name, "docstring": docstring.strip(), "file": str(file_path)})

    except Exception as e:
        print(f"Error processing {file_path}: {e}")

    return fixtures


def analyze_fixtures():
    """Analyze all test fixtures."""
    test_files = list(Path("tests").rglob("*_test.py"))

    # Group fixtures by name
    fixtures_by_name = defaultdict(list)

    for file_path in test_files:
        fixtures = extract_fixtures(file_path)
        for fixture in fixtures:
            fixtures_by_name[fixture["name"]].append(fixture)

    # Report duplicates
    print("=== DUPLICATE FIXTURES ===")
    for name, fixtures in sorted(fixtures_by_name.items()):
        if len(fixtures) > 1:
            print(f"\n{name} ({len(fixtures)} occurrences):")
            for fixture in fixtures:
                print(f"  - {fixture['file']}")
                print(f"    Docstring: {fixture['docstring']}")

    # Find similar fixtures
    print("\n\n=== SIMILAR FIXTURES ===")
    mock_fixtures = {name: fixtures for name, fixtures in fixtures_by_name.items() if "mock" in name.lower()}

    for name, fixtures in sorted(mock_fixtures.items()):
        print(f"\n{name} ({len(fixtures)} occurrences)")

    # Find temp file fixtures
    print("\n\n=== TEMP FILE FIXTURES ===")
    temp_fixtures = {name: fixtures for name, fixtures in fixtures_by_name.items() if "temp" in name.lower()}

    for name, fixtures in sorted(temp_fixtures.items()):
        print(f"\n{name} ({len(fixtures)} occurrences)")


if __name__ == "__main__":
    analyze_fixtures()

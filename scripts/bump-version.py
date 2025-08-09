#!/usr/bin/env python3
"""Version bump utility for tmux-orchestrator."""

import argparse
import re
import subprocess
import sys
from pathlib import Path


def get_current_version():
    """Get current version from pyproject.toml."""
    pyproject = Path("pyproject.toml")
    content = pyproject.read_text()
    match = re.search(r'version = "(\d+\.\d+\.\d+)"', content)
    if match:
        return match.group(1)
    raise ValueError("Could not find version in pyproject.toml")


def bump_version(version, bump_type):
    """Bump version based on type."""
    major, minor, patch = map(int, version.split("."))

    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    else:  # patch
        return f"{major}.{minor}.{patch + 1}"


def update_version_files(new_version):
    """Update version in all relevant files."""
    # Update pyproject.toml
    pyproject = Path("pyproject.toml")
    content = pyproject.read_text()
    content = re.sub(r'version = "\d+\.\d+\.\d+"', f'version = "{new_version}"', content)
    pyproject.write_text(content)

    # Update __init__.py
    init_file = Path("tmux_orchestrator/__init__.py")
    content = init_file.read_text()
    content = re.sub(r'__version__ = "\d+\.\d+\.\d+"', f'__version__ = "{new_version}"', content)
    init_file.write_text(content)


def main():
    parser = argparse.ArgumentParser(description="Bump tmux-orchestrator version")
    parser.add_argument(
        "bump_type",
        choices=["major", "minor", "patch"],
        help="Type of version bump",
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Create git commit with version bump",
    )
    parser.add_argument(
        "--tag",
        action="store_true",
        help="Create git tag for new version",
    )

    args = parser.parse_args()

    try:
        current_version = get_current_version()
        print(f"Current version: {current_version}")

        new_version = bump_version(current_version, args.bump_type)
        print(f"New version: {new_version}")

        update_version_files(new_version)
        print("✓ Updated version files")

        if args.commit:
            subprocess.run(["git", "add", "pyproject.toml", "tmux_orchestrator/__init__.py"], check=True)
            subprocess.run(["git", "commit", "-m", f"chore: Bump version to {new_version}"], check=True)
            print("✓ Created git commit")

            if args.tag:
                subprocess.run(["git", "tag", f"v{new_version}"], check=True)
                print(f"✓ Created git tag v{new_version}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

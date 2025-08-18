#!/usr/bin/env python3
"""Complete the typing modernization for Python 3.11+"""

import re
from pathlib import Path


def modernize_type_hints(content: str) -> tuple[str, int]:
    """Modernize type hints in Python code."""
    changes = 0

    # Replace X | Y with X | Y
    union_pattern = r"\bUnion\[([^\]]+)\]"

    def replace_union(match):
        nonlocal changes
        types = match.group(1).split(",")
        types = [t.strip() for t in types]
        changes += 1
        return " | ".join(types)

    content = re.sub(union_pattern, replace_union, content)

    # Replace X | None with X | None
    optional_pattern = r"\bOptional\[([^\]]+)\]"

    def replace_optional(match):
        nonlocal changes
        changes += 1
        return f"{match.group(1).strip()} | None"

    content = re.sub(optional_pattern, replace_optional, content)

    # Replace list[X] with list[X]
    content_new = re.sub(r"\bList\[", "list[", content)
    changes += len(re.findall(r"\bList\[", content))
    content = content_new

    # Replace dict[X, Y] with dict[X, Y]
    content_new = re.sub(r"\bDict\[", "dict[", content)
    changes += len(re.findall(r"\bDict\[", content))
    content = content_new

    # Replace tuple[...] with tuple[...]
    content_new = re.sub(r"\bTuple\[", "tuple[", content)
    changes += len(re.findall(r"\bTuple\[", content))
    content = content_new

    # Replace set[X] with set[X]
    content_new = re.sub(r"\bSet\[", "set[", content)
    changes += len(re.findall(r"\bSet\[", content))
    content = content_new

    # Clean up imports if we made changes
    if changes > 0:
        # Remove now-unused imports
        lines = content.split("\n")
        new_lines = []
        for line in lines:
            if line.startswith("from typing import"):
                imports = re.findall(r"from typing import (.+)", line)[0]
                imports_list = [imp.strip() for imp in imports.split(",")]

                # Remove modernized types
                to_remove = ["Union", "Optional", "List", "dict", "Tuple", "Set"]
                imports_list = [imp for imp in imports_list if imp not in to_remove]

                if imports_list:
                    new_lines.append(f"from typing import {', '.join(imports_list)}")
                else:
                    # Skip empty import line
                    continue
            else:
                new_lines.append(line)
        content = "\n".join(new_lines)

    return content, changes


def process_file(filepath: Path) -> bool:
    """Process a single Python file."""
    try:
        content = filepath.read_text()
        new_content, changes = modernize_type_hints(content)

        if changes > 0:
            filepath.write_text(new_content)
            print(f"✓ {filepath}: {changes} type hints modernized")
            return True
        return False
    except Exception as e:
        print(f"✗ Error processing {filepath}: {e}")
        return False


def main():
    """Main function to process all Python files."""
    root = Path("/workspaces/Tmux-Orchestrator")
    total_files = 0
    modified_files = 0

    # Process all Python files
    for py_file in root.rglob("*.py"):
        # Skip virtual environments and build directories
        if any(part in py_file.parts for part in [".venv", "venv", "build", "dist", "__pycache__"]):
            continue

        total_files += 1
        if process_file(py_file):
            modified_files += 1

    print("\n📊 Summary:")
    print(f"  Total files scanned: {total_files}")
    print(f"  Files modernized: {modified_files}")

    if modified_files > 0:
        print("\n🎯 Next steps:")
        print("  1. Run: pre-commit run --all-files")
        print("  2. Review changes: git diff")
        print("  3. Commit: git add -A && git commit -m 'chore: modernize type hints to Python 3.11+ syntax'")


if __name__ == "__main__":
    main()

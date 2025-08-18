#!/usr/bin/env python3
"""Fix remaining dict -> dict conversions"""

import re
from pathlib import Path


def fix_dict_types(content: str) -> tuple[str, int]:
    """Fix dict -> dict where dict is used without brackets."""
    changes = 0

    # Replace standalone dict (not Dict[...]) with dict
    # This regex matches dict followed by | or ) or : or whitespace/comma but not [
    pattern = r"\bDict\b(?![[\w])"

    def replace_dict(match):
        nonlocal changes
        changes += 1
        return "dict"

    content = re.sub(pattern, replace_dict, content)

    # Also fix standalone Callable and Any that might be missing imports
    if "Callable" in content or "Any" in content:
        lines = content.split("\n")
        has_typing_import = False
        import_line_idx = -1

        for i, line in enumerate(lines):
            if line.startswith("from typing import"):
                has_typing_import = True
                import_line_idx = i
                break

        if has_typing_import and import_line_idx >= 0:
            # Parse and update imports
            import_line = lines[import_line_idx]
            imports_match = re.match(r"from typing import (.+)", import_line)
            if imports_match:
                imports = [imp.strip() for imp in imports_match.group(1).split(",")]

                # Add missing imports
                if "Any" in content and "Any" not in imports:
                    imports.append("Any")
                if "Callable" in content and "Callable" not in imports:
                    imports.append("Callable")

                lines[import_line_idx] = f"from typing import {', '.join(sorted(set(imports)))}"
                content = "\n".join(lines)
                changes += 1
        elif "Callable" in content or "Any" in content:
            # Need to add typing import
            import_idx = 0
            for i, line in enumerate(lines):
                if line.startswith("import ") or line.startswith("from "):
                    import_idx = i + 1
                elif import_idx > 0 and line.strip() and not line.startswith("#"):
                    break

            imports_needed = []
            if "Any" in content:
                imports_needed.append("Any")
            if "Callable" in content:
                imports_needed.append("Callable")

            if imports_needed:
                lines.insert(import_idx, f"from typing import {', '.join(sorted(imports_needed))}")
                content = "\n".join(lines)
                changes += 1

    return content, changes


def process_file(filepath: Path) -> bool:
    """Process a single file."""
    try:
        content = filepath.read_text()
        new_content, changes = fix_dict_types(content)

        if changes > 0:
            filepath.write_text(new_content)
            print(f"✓ {filepath}: {changes} fixes applied")
            return True
        return False
    except Exception as e:
        print(f"✗ Error processing {filepath}: {e}")
        return False


def main():
    """Main function."""
    # Process all Python files
    root = Path("/workspaces/Tmux-Orchestrator")
    fixed_files = 0

    for py_file in root.rglob("*.py"):
        # Skip virtual environments
        if any(part in py_file.parts for part in [".venv", "venv", "build", "dist", "__pycache__"]):
            continue

        if process_file(py_file):
            fixed_files += 1

    print(f"\n✅ Fixed {fixed_files} files")


if __name__ == "__main__":
    main()

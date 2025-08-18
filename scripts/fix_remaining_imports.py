#!/usr/bin/env python3
"""Fix remaining type hint imports after modernization"""

import re
from pathlib import Path


def fix_imports(filepath: Path) -> bool:
    """Fix missing imports in a file."""
    try:
        content = filepath.read_text()
        original = content

        # Check what typing imports are needed
        needs_any = "Any" in content and "from typing import" in content
        needs_callable = "Callable" in content and "from typing import" in content
        needs_dict_generic = bool(re.search(r"\bDict\b(?!\[)", content))  # dict without brackets

        if needs_dict_generic:
            # Find the typing import line
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if line.startswith("from typing import"):
                    # Parse existing imports
                    imports_match = re.match(r"from typing import (.+)", line)
                    if imports_match:
                        imports = [imp.strip() for imp in imports_match.group(1).split(",")]

                        # Add Any and Callable if needed and not present
                        if needs_any and "Any" not in imports:
                            imports.append("Any")
                        if needs_callable and "Callable" not in imports:
                            imports.append("Callable")

                        # Update the import line
                        lines[i] = f"from typing import {', '.join(sorted(imports))}"
                        content = "\n".join(lines)
                        break
            else:
                # No typing import found, add one if needed
                if needs_any or needs_callable:
                    imports = []
                    if needs_any:
                        imports.append("Any")
                    if needs_callable:
                        imports.append("Callable")

                    # Find where to insert the import
                    import_section_end = 0
                    for i, line in enumerate(lines):
                        if line.startswith("import ") or line.startswith("from "):
                            import_section_end = i + 1
                        elif import_section_end > 0 and line.strip() and not line.startswith("#"):
                            break

                    lines.insert(import_section_end, f"from typing import {', '.join(sorted(imports))}")
                    content = "\n".join(lines)

        if content != original:
            filepath.write_text(content)
            return True
        return False
    except Exception as e:
        print(f"Error fixing {filepath}: {e}")
        return False


def main():
    """Fix specific files with import issues."""
    files_to_fix = [
        "/workspaces/Tmux-Orchestrator/tmux_orchestrator/core/monitoring/cache_layer.py",
        "/workspaces/Tmux-Orchestrator/tmux_orchestrator/core/monitoring/monitor_pubsub_integration.py",
        "/workspaces/Tmux-Orchestrator/tmux_orchestrator/core/monitoring/notification_manager.py",
        "/workspaces/Tmux-Orchestrator/tmux_orchestrator/core/monitoring/pubsub_notification_manager.py",
        "/workspaces/Tmux-Orchestrator/tmux_orchestrator/utils/async_operations.py",
        "/workspaces/Tmux-Orchestrator/tmux_orchestrator/utils/rate_limiter.py",
    ]

    for filepath in files_to_fix:
        path = Path(filepath)
        if path.exists():
            if fix_imports(path):
                print(f"✓ Fixed imports in {path}")
        else:
            print(f"✗ File not found: {path}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Validation script to detect test class usage patterns and monitor class-to-function conversion.
Helps ensure proper conversion during Phase 2 of test cleanup.
"""

import ast
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Set


class TestClassAnalyzer(ast.NodeVisitor):
    """AST visitor to analyze test classes and methods."""

    def __init__(self):
        self.test_classes = []
        self.test_functions = []
        self.current_class = None

    def visit_ClassDef(self, node):
        """Visit class definitions."""
        if node.name.startswith("Test"):
            class_info = {"name": node.name, "line": node.lineno, "methods": [], "fixtures": [], "setup_teardown": []}
            self.current_class = class_info
            self.test_classes.append(class_info)
            self.generic_visit(node)
            self.current_class = None
        else:
            self.generic_visit(node)

    def visit_FunctionDef(self, node):
        """Visit function definitions."""
        if self.current_class:
            # Inside a test class
            if node.name.startswith("test_"):
                self.current_class["methods"].append({"name": node.name, "line": node.lineno})
            elif node.name in ["setup", "teardown", "setup_method", "teardown_method", "setup_class", "teardown_class"]:
                self.current_class["setup_teardown"].append({"name": node.name, "line": node.lineno})
            elif not node.name.startswith("_"):
                # Likely a fixture or helper
                self.current_class["fixtures"].append({"name": node.name, "line": node.lineno})
        else:
            # Top-level function
            if node.name.startswith("test_"):
                self.test_functions.append({"name": node.name, "line": node.lineno})
        self.generic_visit(node)


def analyze_file(filepath: Path) -> Dict:
    """Analyze a single test file for class usage."""
    try:
        content = filepath.read_text()
        tree = ast.parse(content)
        analyzer = TestClassAnalyzer()
        analyzer.visit(tree)

        return {
            "path": str(filepath),
            "test_classes": analyzer.test_classes,
            "test_functions": analyzer.test_functions,
            "total_class_methods": sum(len(c["methods"]) for c in analyzer.test_classes),
            "total_functions": len(analyzer.test_functions),
        }
    except Exception as e:
        return {
            "path": str(filepath),
            "error": str(e),
            "test_classes": [],
            "test_functions": [],
            "total_class_methods": 0,
            "total_functions": 0,
        }


def get_all_test_files() -> List[Path]:
    """Get all test files from the tests directory."""
    tests_dir = Path("tests")
    return list(tests_dir.rglob("*_test.py"))


def analyze_test_organization(file_analysis: Dict) -> Dict[str, List[str]]:
    """Analyze how tests are organized (by feature, by method, etc)."""
    organization = {"by_feature": [], "by_method": [], "mixed": [], "unclear": []}

    for file_info in file_analysis:
        if file_info.get("error"):
            continue

        # Analyze test class organization
        for test_class in file_info["test_classes"]:
            methods = [m["name"] for m in test_class["methods"]]
            if not methods:
                continue

            # Check if methods test different features
            method_prefixes = set()
            for method in methods:
                # Remove 'test_' prefix and extract feature
                feature = method[5:].split("_")[0] if len(method) > 5 else ""
                if feature:
                    method_prefixes.add(feature)

            if len(method_prefixes) == 1:
                organization["by_method"].append(f"{file_info['path']}::{test_class['name']}")
            elif len(method_prefixes) > 3:
                organization["by_feature"].append(f"{file_info['path']}::{test_class['name']}")
            else:
                organization["mixed"].append(f"{file_info['path']}::{test_class['name']}")

    return organization


def get_pytest_groups() -> Dict[str, Set[str]]:
    """Get test grouping information from pytest markers."""
    try:
        result = subprocess.run(
            ["poetry", "run", "pytest", "--collect-only", "-q", "--markers"], capture_output=True, text=True
        )

        markers = set()
        for line in result.stdout.splitlines():
            if line.strip() and ":" in line:
                marker = line.split(":")[0].strip()
                if marker and not marker.startswith("@"):
                    markers.add(marker)

        return {"markers": markers}
    except Exception:
        return {"markers": set()}


def main():
    print("=== Test Class Usage Analysis ===\n")

    # Get all test files
    test_files = get_all_test_files()
    print(f"Found {len(test_files)} test files")

    # Analyze each file
    all_analysis = []
    total_classes = 0
    total_class_methods = 0
    total_functions = 0
    files_with_classes = []

    for filepath in sorted(test_files):
        analysis = analyze_file(filepath)
        all_analysis.append(analysis)

        if analysis["test_classes"]:
            total_classes += len(analysis["test_classes"])
            total_class_methods += analysis["total_class_methods"]
            files_with_classes.append(analysis)

        total_functions += analysis["total_functions"]

    # Summary statistics
    print("\n=== Summary ===")
    print(f"Files with test classes: {len(files_with_classes)}/{len(test_files)}")
    print(f"Total test classes: {total_classes}")
    print(f"Total methods in classes: {total_class_methods}")
    print(f"Total standalone functions: {total_functions}")
    print(f"Total tests: {total_class_methods + total_functions}")

    # Show files that need conversion
    if files_with_classes:
        print("\n=== Files Requiring Class-to-Function Conversion ===")
        for file_info in sorted(files_with_classes, key=lambda x: x["total_class_methods"], reverse=True)[:10]:
            print(f"\n{file_info['path']}:")
            for test_class in file_info["test_classes"]:
                print(f"  - {test_class['name']} ({len(test_class['methods'])} methods)")
                if test_class["setup_teardown"]:
                    print(f"    Setup/Teardown: {', '.join(m['name'] for m in test_class['setup_teardown'])}")
                if len(test_class["methods"]) > 0:
                    print(f"    Sample methods: {', '.join(m['name'] for m in test_class['methods'][:3])}")

    # Analyze organization patterns
    print("\n=== Test Organization Analysis ===")
    organization = analyze_test_organization(all_analysis)
    print(f"Classes organized by method: {len(organization['by_method'])}")
    print(f"Classes organized by feature: {len(organization['by_feature'])}")
    print(f"Classes with mixed organization: {len(organization['mixed'])}")

    # Check for pytest markers
    groups = get_pytest_groups()
    if groups["markers"]:
        print("\n=== Pytest Markers Found ===")
        print(f"Markers in use: {', '.join(sorted(groups['markers']))}")

    # Conversion recommendations
    print("\n=== Conversion Recommendations ===")
    if files_with_classes:
        complex_files = [f for f in files_with_classes if any(tc["setup_teardown"] for tc in f["test_classes"])]
        if complex_files:
            print(f"⚠️  {len(complex_files)} files have setup/teardown methods that need careful conversion")

        large_classes = [f for f in files_with_classes if any(len(tc["methods"]) > 10 for tc in f["test_classes"])]
        if large_classes:
            print(f"⚠️  {len(large_classes)} files have large test classes (>10 methods) that may need splitting")

    # Save detailed report
    import json

    report = {
        "summary": {
            "total_files": len(test_files),
            "files_with_classes": len(files_with_classes),
            "total_classes": total_classes,
            "total_class_methods": total_class_methods,
            "total_functions": total_functions,
        },
        "files_needing_conversion": [
            {"path": f["path"], "classes": len(f["test_classes"]), "methods": f["total_class_methods"]}
            for f in files_with_classes
        ],
        "organization": organization,
    }

    with open("test_class_analysis.json", "w") as f:
        json.dump(report, f, indent=2)

    print("\nDetailed report saved to: test_class_analysis.json")

    return 0 if total_classes == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

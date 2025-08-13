#!/usr/bin/env python3
"""
Generate a priority report for test class conversions.
Identifies complex cases: setup/teardown methods, inheritance, and large classes.
"""

import ast
import json
from pathlib import Path
from typing import Dict


class TestClassInheritanceAnalyzer(ast.NodeVisitor):
    """Enhanced AST visitor to analyze test class inheritance and complexity."""

    def __init__(self):
        self.test_classes = []
        self.imports = {}
        self.current_class = None

    def visit_ImportFrom(self, node):
        """Track imports to understand inheritance."""
        if node.module:
            for alias in node.names:
                import_name = alias.name
                self.imports[import_name] = node.module
        self.generic_visit(node)

    def visit_Import(self, node):
        """Track direct imports."""
        for alias in node.names:
            self.imports[alias.name] = alias.name
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        """Visit class definitions with inheritance analysis."""
        if node.name.startswith("Test") or any(
            base.id == "TestCase" if hasattr(base, "id") else False for base in node.bases
        ):
            class_info = {
                "name": node.name,
                "line": node.lineno,
                "methods": [],
                "test_methods": [],
                "setup_teardown": [],
                "fixtures": [],
                "bases": [],
                "has_inheritance": len(node.bases) > 0,
                "complexity_score": 0,
            }

            # Analyze base classes
            for base in node.bases:
                if hasattr(base, "id"):
                    class_info["bases"].append(base.id)
                elif hasattr(base, "attr"):
                    class_info["bases"].append(f"{base.value.id}.{base.attr}")

            self.current_class = class_info
            self.test_classes.append(class_info)
            self.generic_visit(node)

            # Calculate complexity score
            complexity = 0
            complexity += len(class_info["test_methods"]) * 1
            complexity += len(class_info["setup_teardown"]) * 3  # Setup/teardown add complexity
            complexity += len(class_info["bases"]) * 2  # Inheritance adds complexity
            if any("unittest" in str(base) for base in class_info["bases"]):
                complexity += 5  # unittest.TestCase adds more complexity

            class_info["complexity_score"] = complexity
            self.current_class = None
        else:
            self.generic_visit(node)

    def visit_FunctionDef(self, node):
        """Visit function definitions with detailed categorization."""
        if self.current_class:
            method_info = {
                "name": node.name,
                "line": node.lineno,
                "decorators": [d.id if hasattr(d, "id") else str(d) for d in node.decorator_list],
            }

            if node.name.startswith("test_"):
                self.current_class["test_methods"].append(method_info)
            elif node.name in [
                "setUp",
                "tearDown",
                "setUpClass",
                "tearDownClass",
                "setup",
                "teardown",
                "setup_method",
                "teardown_method",
                "setup_class",
                "teardown_class",
                "setup_function",
                "teardown_function",
            ]:
                self.current_class["setup_teardown"].append(method_info)
            elif not node.name.startswith("_"):
                self.current_class["fixtures"].append(method_info)

            self.current_class["methods"].append(method_info)
        self.generic_visit(node)


def analyze_file_detailed(filepath: Path) -> Dict:
    """Perform detailed analysis of a test file."""
    try:
        content = filepath.read_text()
        tree = ast.parse(content)
        analyzer = TestClassInheritanceAnalyzer()
        analyzer.visit(tree)

        return {
            "path": str(filepath),
            "test_classes": analyzer.test_classes,
            "total_classes": len(analyzer.test_classes),
            "has_setup_teardown": any(tc["setup_teardown"] for tc in analyzer.test_classes),
            "has_inheritance": any(tc["has_inheritance"] for tc in analyzer.test_classes),
            "total_complexity": sum(tc["complexity_score"] for tc in analyzer.test_classes),
        }
    except Exception as e:
        return {
            "path": str(filepath),
            "error": str(e),
            "test_classes": [],
            "total_classes": 0,
            "has_setup_teardown": False,
            "has_inheritance": False,
            "total_complexity": 0,
        }


def generate_priority_report():
    """Generate comprehensive priority report for test class conversions."""
    print("=== Test Class Conversion Priority Report ===\n")

    # Get all test files
    test_files = list(Path("tests").rglob("*_test.py"))
    all_analyses = []

    # Analyze each file
    for filepath in sorted(test_files):
        analysis = analyze_file_detailed(filepath)
        if analysis["total_classes"] > 0:
            all_analyses.append(analysis)

    # Sort by complexity
    all_analyses.sort(key=lambda x: x["total_complexity"], reverse=True)

    # 1. Files with most test classes
    print("=== Files with Most Test Classes ===")
    by_class_count = sorted(all_analyses, key=lambda x: x["total_classes"], reverse=True)[:10]
    for analysis in by_class_count:
        print(f"{analysis['path']}: {analysis['total_classes']} classes")
        for tc in analysis["test_classes"][:3]:  # Show first 3 classes
            print(f"  - {tc['name']} ({len(tc['test_methods'])} test methods)")

    # 2. Files with setup/teardown methods
    print("\n=== Files with Setup/Teardown Methods (Special Attention Required) ===")
    setup_teardown_files = [a for a in all_analyses if a["has_setup_teardown"]]
    print(f"Found {len(setup_teardown_files)} files with setup/teardown methods:\n")

    for analysis in setup_teardown_files:
        print(f"{analysis['path']}:")
        for tc in analysis["test_classes"]:
            if tc["setup_teardown"]:
                print(f"  - {tc['name']}:")
                for method in tc["setup_teardown"]:
                    print(f"    • {method['name']} (line {method['line']})")

    # 3. Files with inheritance
    print("\n=== Files with Class Inheritance (Complex Conversion) ===")
    inheritance_files = [a for a in all_analyses if a["has_inheritance"]]
    print(f"Found {len(inheritance_files)} files with inherited test classes:\n")

    for analysis in inheritance_files:
        print(f"{analysis['path']}:")
        for tc in analysis["test_classes"]:
            if tc["has_inheritance"]:
                bases_str = ", ".join(tc["bases"])
                print(f"  - {tc['name']} inherits from: {bases_str}")
                if "unittest.TestCase" in bases_str:
                    print("    ⚠️  Uses unittest.TestCase - needs careful migration")

    # 4. Complexity ranking
    print("\n=== Top 10 Most Complex Files to Convert ===")
    print("(Complexity based on: method count, setup/teardown, inheritance)\n")

    for i, analysis in enumerate(all_analyses[:10], 1):
        print(f"{i}. {analysis['path']} (complexity: {analysis['total_complexity']})")
        for tc in analysis["test_classes"]:
            if tc["complexity_score"] > 5:
                factors = []
                if tc["test_methods"]:
                    factors.append(f"{len(tc['test_methods'])} tests")
                if tc["setup_teardown"]:
                    factors.append(f"{len(tc['setup_teardown'])} setup/teardown")
                if tc["bases"]:
                    factors.append(f"inherits {', '.join(tc['bases'])}")
                print(f"   - {tc['name']}: {', '.join(factors)}")

    # 5. Summary statistics
    print("\n=== Summary Statistics ===")
    total_setup_teardown = sum(len(tc["setup_teardown"]) for a in all_analyses for tc in a["test_classes"])
    total_inherited = sum(1 for a in all_analyses for tc in a["test_classes"] if tc["has_inheritance"])

    print(f"Total files with test classes: {len(all_analyses)}")
    print(f"Total setup/teardown methods to convert: {total_setup_teardown}")
    print(f"Total classes with inheritance: {total_inherited}")

    # 6. Conversion difficulty categories
    print("\n=== Conversion Difficulty Categories ===")

    easy = []
    medium = []
    hard = []

    for analysis in all_analyses:
        max_complexity = max((tc["complexity_score"] for tc in analysis["test_classes"]), default=0)
        if max_complexity <= 5:
            easy.append(analysis["path"])
        elif max_complexity <= 15:
            medium.append(analysis["path"])
        else:
            hard.append(analysis["path"])

    print(f"Easy (simple classes, no special methods): {len(easy)} files")
    print(f"Medium (some setup/teardown or small inheritance): {len(medium)} files")
    print(f"Hard (complex setup/teardown, inheritance, large classes): {len(hard)} files")

    # Save detailed report
    report_data = {
        "summary": {
            "total_files": len(all_analyses),
            "files_with_setup_teardown": len(setup_teardown_files),
            "files_with_inheritance": len(inheritance_files),
            "total_setup_teardown_methods": total_setup_teardown,
            "total_inherited_classes": total_inherited,
        },
        "priority_order": [
            {
                "path": a["path"],
                "complexity": a["total_complexity"],
                "classes": a["total_classes"],
                "has_setup_teardown": a["has_setup_teardown"],
                "has_inheritance": a["has_inheritance"],
            }
            for a in all_analyses
        ],
        "difficulty_categories": {"easy": easy, "medium": medium, "hard": hard},
    }

    with open("test_class_conversion_priority.json", "w") as f:
        json.dump(report_data, f, indent=2)

    print("\nDetailed report saved to: test_class_conversion_priority.json")


if __name__ == "__main__":
    generate_priority_report()

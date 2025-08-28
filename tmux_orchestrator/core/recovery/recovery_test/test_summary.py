"""Test summary calculation utilities."""

from typing import Any


class TestSummaryCalculator:
    """Calculates summary statistics for recovery tests."""

    def __init__(self):
        """Initialize test summary calculator."""
        pass

    def calculate_test_summary(self, test_results: list[dict[str, Any]]) -> dict[str, Any]:
        """Calculate overall test summary statistics."""
        summary: dict[str, Any] = {
            "total_tests": len(test_results),
            "tests_passed": 0,
            "tests_failed": 0,
            "overall_success_rate": 0.0,
            "test_breakdown": {},
        }

        for test_result in test_results:
            test_name = test_result["test_name"]
            results = test_result["results"]

            # Calculate pass/fail for this test
            if "detection_successful" in results:
                passed = results["detection_successful"]
                failed = results["detection_failed"]
            elif "coordination_successful" in results:
                passed = results["coordination_successful"]
                failed = results["coordination_failed"]
            elif "context_successful" in results:
                passed = results["context_successful"]
                failed = results["context_failed"]
            elif "notification_successful" in results:
                passed = results["notification_successful"]
                failed = results["notification_failed"]
            elif "concurrent_test_successful" in results:
                passed = 1 if results["concurrent_test_successful"] else 0
                failed = 1 - passed
            else:
                passed = failed = 0

            summary["test_breakdown"][test_name] = {
                "passed": passed,
                "failed": failed,
                "success_rate": passed / max(passed + failed, 1) * 100,
            }

            if passed > failed:
                summary["tests_passed"] += 1
            else:
                summary["tests_failed"] += 1

        # Calculate overall success rate
        if summary["total_tests"] > 0:
            summary["overall_success_rate"] = (summary["tests_passed"] / summary["total_tests"]) * 100

        return summary

    def generate_test_report(self, test_results: list[dict[str, Any]], test_session_id: str) -> dict[str, Any]:
        """Generate comprehensive test report.

        Args:
            test_results: List of test results
            test_session_id: Session identifier for the test run

        Returns:
            Dictionary with comprehensive test report
        """
        summary = self.calculate_test_summary(test_results)

        report = {
            "test_session_id": test_session_id,
            "summary": summary,
            "detailed_results": test_results,
            "recommendations": self._generate_recommendations(summary),
        }

        return report

    def _generate_recommendations(self, summary: dict[str, Any]) -> list[str]:
        """Generate recommendations based on test results.

        Args:
            summary: Test summary statistics

        Returns:
            List of recommendation strings
        """
        recommendations = []

        overall_rate = summary.get("overall_success_rate", 0)

        if overall_rate < 50:
            recommendations.append("⚠️  Critical: Recovery system requires immediate attention")
        elif overall_rate < 75:
            recommendations.append("⚡ Warning: Recovery system needs improvement")
        elif overall_rate < 90:
            recommendations.append("ℹ️  Info: Recovery system is mostly functional with minor issues")
        else:
            recommendations.append("✅ Success: Recovery system is performing well")

        # Specific recommendations based on test breakdown
        test_breakdown = summary.get("test_breakdown", {})

        for test_name, test_stats in test_breakdown.items():
            success_rate = test_stats.get("success_rate", 0)
            if success_rate < 50:
                recommendations.append(f"🔧 Fix required: {test_name} test failing ({success_rate:.1f}% success)")
            elif success_rate < 75:
                recommendations.append(
                    f"⚠️  Attention needed: {test_name} test needs improvement ({success_rate:.1f}% success)"
                )

        return recommendations

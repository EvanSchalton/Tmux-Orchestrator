"""Tests for run_quality_checks business logic."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from tmux_orchestrator.server.tools.run_quality_checks import (
    QualityCheckRequest,
    enforce_quality_gates,
    get_check_results,
    run_quality_checks,
    run_single_check,
)
from tmux_orchestrator.utils.tmux import TMUXManager


def test_run_quality_checks_empty_project_path() -> None:
    """Test run_quality_checks with empty project_path returns error."""
    tmux = Mock(spec=TMUXManager)
    request = QualityCheckRequest(project_path="", check_types=["tests"])

    result = run_quality_checks(tmux, request)

    assert not result.success
    assert result.error_message is not None
    assert "Project path cannot be empty" in result.error_message


def test_run_quality_checks_invalid_check_type() -> None:
    """Test run_quality_checks with invalid check type returns error."""
    tmux = Mock(spec=TMUXManager)
    request = QualityCheckRequest(project_path="/test/path", check_types=["invalid"])

    result = run_quality_checks(tmux, request)

    assert not result.success
    assert result.error_message is not None
    assert "Invalid check type 'invalid'" in result.error_message


def test_run_quality_checks_project_not_found() -> None:
    """Test run_quality_checks when project path doesn't exist."""
    tmux = Mock(spec=TMUXManager)
    request = QualityCheckRequest(project_path="/nonexistent/path", check_types=["tests"])

    with patch("pathlib.Path.exists", return_value=False):
        result = run_quality_checks(tmux, request)

        assert not result.success
        assert result.error_message is not None
        assert "Project path '/nonexistent/path' does not exist" in result.error_message


def test_run_quality_checks_successful_all_pass() -> None:
    """Test successful quality checks with all checks passing."""
    tmux = Mock(spec=TMUXManager)
    request = QualityCheckRequest(
        project_path="/test/project", check_types=["tests", "linting", "formatting"], task_id="task_001"
    )

    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("subprocess.run") as mock_run,
        patch("tmux_orchestrator.server.tools.run_quality_checks._save_check_results") as mock_save,
    ):
        # Mock successful subprocess runs
        mock_run.return_value = MagicMock(returncode=0, stdout="All tests passed", stderr="")
        mock_save.return_value = True

        result = run_quality_checks(tmux, request)

        assert result.success
        assert result.all_passed
        assert len(result.check_results) == 3
        assert all(check["passed"] for check in result.check_results)
        assert result.task_id == "task_001"


def test_run_quality_checks_with_failures() -> None:
    """Test quality checks with some failures."""
    tmux = Mock(spec=TMUXManager)
    request = QualityCheckRequest(project_path="/test/project", check_types=["tests", "linting"], fail_fast=False)

    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("subprocess.run") as mock_run,
        patch("tmux_orchestrator.server.tools.run_quality_checks._save_check_results") as mock_save,
    ):
        # Mock mixed results
        def mock_subprocess_run(cmd, *args, **kwargs):
            if "pytest" in cmd:
                return MagicMock(returncode=1, stdout="1 test failed", stderr="Test error")
            else:
                return MagicMock(returncode=0, stdout="No issues found", stderr="")

        mock_run.side_effect = mock_subprocess_run
        mock_save.return_value = True

        result = run_quality_checks(tmux, request)

        assert result.success  # Operation succeeded even with failures
        assert not result.all_passed
        assert len(result.check_results) == 2
        assert result.failed_checks == ["tests"]


def test_run_quality_checks_fail_fast() -> None:
    """Test quality checks with fail_fast enabled."""
    tmux = Mock(spec=TMUXManager)
    request = QualityCheckRequest(
        project_path="/test/project", check_types=["tests", "linting", "formatting"], fail_fast=True
    )

    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("subprocess.run") as mock_run,
        patch("tmux_orchestrator.server.tools.run_quality_checks._save_check_results") as mock_save,
    ):
        # First check fails
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Test failed")
        mock_save.return_value = True

        result = run_quality_checks(tmux, request)

        assert result.success
        assert not result.all_passed
        # Should only run first check due to fail_fast
        assert len(result.check_results) == 1
        assert mock_run.call_count == 1


def test_run_quality_checks_with_report_to_agent() -> None:
    """Test quality checks with report_to_agent option."""
    tmux = Mock(spec=TMUXManager)
    tmux.send_keys.return_value = True

    request = QualityCheckRequest(project_path="/test/project", check_types=["tests"], report_to_agent="pm:0")

    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("subprocess.run") as mock_run,
        patch("tmux_orchestrator.server.tools.run_quality_checks._save_check_results") as mock_save,
    ):
        mock_run.return_value = MagicMock(returncode=0, stdout="All passed", stderr="")
        mock_save.return_value = True

        result = run_quality_checks(tmux, request)

        assert result.success
        # Verify report was sent
        tmux.send_keys.assert_called_once()
        call_args = tmux.send_keys.call_args[0]
        assert call_args[0] == "pm:0"
        assert "QUALITY CHECK REPORT" in call_args[1]


def test_run_single_check_tests() -> None:
    """Test running single test check."""
    request = QualityCheckRequest(project_path="/test/project", check_types=["tests"])

    with patch("pathlib.Path.exists", return_value=True), patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="10 tests passed", stderr="")

        result = run_single_check("tests", request)

        assert result["check_type"] == "tests"
        assert result["passed"]
        assert "pytest" in result["command"]
        assert result["stdout"] == "10 tests passed"


def test_run_single_check_linting() -> None:
    """Test running single linting check."""
    request = QualityCheckRequest(project_path="/test/project", check_types=["linting"])

    with patch("pathlib.Path.exists", return_value=True), patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="All good", stderr="")

        result = run_single_check("linting", request)

        assert result["check_type"] == "linting"
        assert result["passed"]
        assert "ruff" in result["command"]


def test_run_single_check_formatting() -> None:
    """Test running single formatting check."""
    request = QualityCheckRequest(project_path="/test/project", check_types=["formatting"])

    with patch("pathlib.Path.exists", return_value=True), patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="Formatted", stderr="")

        result = run_single_check("formatting", request)

        assert result["check_type"] == "formatting"
        assert result["passed"]
        assert "black" in result["command"]


def test_run_single_check_type_checking() -> None:
    """Test running single type checking."""
    request = QualityCheckRequest(project_path="/test/project", check_types=["type_checking"])

    with patch("pathlib.Path.exists", return_value=True), patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="No type errors", stderr="")

        result = run_single_check("type_checking", request)

        assert result["check_type"] == "type_checking"
        assert result["passed"]
        assert "mypy" in result["command"]


def test_run_single_check_coverage() -> None:
    """Test running single coverage check."""
    request = QualityCheckRequest(project_path="/test/project", check_types=["coverage"], coverage_threshold=80)

    with patch("pathlib.Path.exists", return_value=True), patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="Total coverage: 85%", stderr="")

        result = run_single_check("coverage", request)

        assert result["check_type"] == "coverage"
        assert result["passed"]
        assert "--cov" in result["command"]


def test_run_single_check_security() -> None:
    """Test running single security check."""
    request = QualityCheckRequest(project_path="/test/project", check_types=["security"])

    with patch("pathlib.Path.exists", return_value=True), patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="No security issues", stderr="")

        result = run_single_check("security", request)

        assert result["check_type"] == "security"
        assert result["passed"]
        assert "bandit" in result["command"]


def test_get_check_results_successful() -> None:
    """Test retrieving check results successfully."""
    request = QualityCheckRequest(task_id="task_001")

    with patch("tmux_orchestrator.server.tools.run_quality_checks._load_check_results") as mock_load:
        mock_results = {
            "task_id": "task_001",
            "timestamp": "2025-08-09T12:00:00Z",
            "all_passed": True,
            "check_results": [{"check_type": "tests", "passed": True}],
        }
        mock_load.return_value = mock_results

        result = get_check_results(request)

        assert result.success
        assert result.task_id == "task_001"
        assert result.all_passed


def test_get_check_results_not_found() -> None:
    """Test get_check_results when results not found."""
    request = QualityCheckRequest(task_id="nonexistent")

    with patch("tmux_orchestrator.server.tools.run_quality_checks._load_check_results") as mock_load:
        mock_load.return_value = None

        result = get_check_results(request)

        assert not result.success
        assert result.error_message is not None
        assert "No quality check results found" in result.error_message


def test_enforce_quality_gates_all_pass() -> None:
    """Test enforcing quality gates when all checks pass."""
    tmux = Mock(spec=TMUXManager)
    request = QualityCheckRequest(
        project_path="/test/project", check_types=["tests", "linting"], task_id="task_001", block_on_failure=True
    )

    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("subprocess.run") as mock_run,
        patch("tmux_orchestrator.server.tools.run_quality_checks._save_check_results") as mock_save,
        patch("tmux_orchestrator.server.tools.run_quality_checks._update_task_status") as mock_update,
    ):
        mock_run.return_value = MagicMock(returncode=0, stdout="All good", stderr="")
        mock_save.return_value = True
        mock_update.return_value = True

        result = enforce_quality_gates(tmux, request)

        assert result.success
        assert result.gates_passed
        assert result.all_passed
        # Task status should be updated to quality_verified
        mock_update.assert_called_with("task_001", "quality_verified")


def test_enforce_quality_gates_with_failures() -> None:
    """Test enforcing quality gates when checks fail."""
    tmux = Mock(spec=TMUXManager)
    request = QualityCheckRequest(
        project_path="/test/project", check_types=["tests"], task_id="task_001", block_on_failure=True
    )

    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("subprocess.run") as mock_run,
        patch("tmux_orchestrator.server.tools.run_quality_checks._save_check_results") as mock_save,
        patch("tmux_orchestrator.server.tools.run_quality_checks._update_task_status") as mock_update,
    ):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Tests failed")
        mock_save.return_value = True
        mock_update.return_value = True

        result = enforce_quality_gates(tmux, request)

        assert result.success  # Operation succeeded
        assert not result.gates_passed  # But gates failed
        assert not result.all_passed
        # Task status should be updated to quality_failed
        mock_update.assert_called_with("task_001", "quality_failed")


@pytest.mark.parametrize(
    "check_type",
    ["tests", "linting", "formatting", "type_checking", "coverage", "security"],
)
def test_run_quality_checks_all_valid_types(check_type: str) -> None:
    """Test run_quality_checks accepts all valid check types."""
    tmux = Mock(spec=TMUXManager)
    request = QualityCheckRequest(project_path="/test/project", check_types=[check_type])

    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("subprocess.run") as mock_run,
        patch("tmux_orchestrator.server.tools.run_quality_checks._save_check_results") as mock_save,
    ):
        mock_run.return_value = MagicMock(returncode=0, stdout="Pass", stderr="")
        mock_save.return_value = True

        result = run_quality_checks(tmux, request)

        assert result.success
        assert len(result.check_results) == 1
        assert result.check_results[0]["check_type"] == check_type


def test_run_quality_checks_exception_handling() -> None:
    """Test run_quality_checks handles unexpected exceptions."""
    tmux = Mock(spec=TMUXManager)
    request = QualityCheckRequest(project_path="/test/project", check_types=["tests"])

    with patch("pathlib.Path.exists", side_effect=Exception("Disk error")):
        result = run_quality_checks(tmux, request)

        assert not result.success
        assert result.error_message is not None
        assert "Unexpected error during quality checks" in result.error_message


def test_run_quality_checks_custom_commands() -> None:
    """Test quality checks with custom commands."""
    tmux = Mock(spec=TMUXManager)
    request = QualityCheckRequest(
        project_path="/test/project", check_types=["tests"], custom_commands={"tests": "make test"}
    )

    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("subprocess.run") as mock_run,
        patch("tmux_orchestrator.server.tools.run_quality_checks._save_check_results") as mock_save,
    ):
        mock_run.return_value = MagicMock(returncode=0, stdout="Custom test passed", stderr="")
        mock_save.return_value = True

        result = run_quality_checks(tmux, request)

        assert result.success
        # Verify custom command was used
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args == ["make", "test"]

"""Business logic for running automated quality checks."""

import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

from tmux_orchestrator.utils.tmux import TMUXManager

# Valid quality check types
QualityCheckType = Literal["tests", "linting", "formatting", "type_checking", "coverage", "security"]


@dataclass
class QualityCheckRequest:
    """Request parameters for quality check operations."""

    project_path: str = ""
    check_types: list[str] = field(default_factory=list)
    task_id: Optional[str] = None
    report_to_agent: Optional[str] = None
    fail_fast: bool = True
    custom_commands: Optional[dict[str, str]] = None
    coverage_threshold: int = 80
    block_on_failure: bool = False


@dataclass
class QualityCheckResult:
    """Result of quality check operation."""

    success: bool
    project_path: str = ""
    all_passed: bool = False
    check_results: list[dict] = field(default_factory=list)
    failed_checks: list[str] = field(default_factory=list)
    task_id: Optional[str] = None
    gates_passed: Optional[bool] = None
    error_message: Optional[str] = None


def run_quality_checks(tmux: TMUXManager, request: QualityCheckRequest) -> QualityCheckResult:
    """
    Run automated quality checks on a project.

    Executes various quality checks (tests, linting, formatting, type checking,
    coverage, security) on a project. Supports fail-fast mode, custom commands,
    and reporting results to PM agents. Integrates with the task tracking system
    to update task quality status.

    Args:
        tmux: TMUXManager instance for agent communication
        request: QualityCheckRequest with check configuration

    Returns:
        QualityCheckResult indicating success/failure and check details

    Raises:
        ValueError: If request parameters are invalid
        RuntimeError: If quality check operations fail
    """
    # Validate input parameters
    validation_error = _validate_request(request)
    if validation_error:
        return QualityCheckResult(
            success=False,
            project_path=request.project_path,
            error_message=validation_error,
        )

    try:
        # Verify project path exists
        project_path = Path(request.project_path)
        if not project_path.exists():
            return QualityCheckResult(
                success=False,
                project_path=request.project_path,
                error_message=f"Project path '{request.project_path}' does not exist",
            )

        check_results = []
        failed_checks = []
        all_passed = True

        # Run each requested check
        for check_type in request.check_types:
            # Run the check
            result = run_single_check(check_type, request)
            check_results.append(result)

            # Track failures
            if not result["passed"]:
                failed_checks.append(check_type)
                all_passed = False

                # Stop if fail_fast is enabled
                if request.fail_fast:
                    break

        # Save results if task_id is provided
        if request.task_id:
            _save_check_results(
                {
                    "task_id": request.task_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "all_passed": all_passed,
                    "check_results": check_results,
                    "failed_checks": failed_checks,
                }
            )

        # Report to agent if requested
        if request.report_to_agent:
            _send_report_to_agent(tmux, request.report_to_agent, check_results, all_passed)

        return QualityCheckResult(
            success=True,
            project_path=request.project_path,
            all_passed=all_passed,
            check_results=check_results,
            failed_checks=failed_checks,
            task_id=request.task_id,
        )

    except Exception as e:
        return QualityCheckResult(
            success=False,
            project_path=request.project_path,
            error_message=f"Unexpected error during quality checks: {str(e)}",
        )


def run_single_check(check_type: str, request: QualityCheckRequest) -> dict:
    """
    Run a single quality check.

    Args:
        check_type: Type of check to run
        request: QualityCheckRequest with configuration

    Returns:
        dict with check results including type, passed, command, stdout, stderr
    """
    # Get command for check type
    if request.custom_commands and check_type in request.custom_commands:
        command = request.custom_commands[check_type].split()
    else:
        command = _get_default_command(check_type, request)

    # Change to project directory and run command
    original_cwd = Path.cwd()
    try:
        Path(request.project_path).resolve()

        # Run the command
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            cwd=request.project_path,
        )

        return {
            "check_type": check_type,
            "passed": result.returncode == 0,
            "command": " ".join(command),
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode,
        }

    except Exception as e:
        return {
            "check_type": check_type,
            "passed": False,
            "command": " ".join(command),
            "stdout": "",
            "stderr": str(e),
            "return_code": -1,
        }
    finally:
        # Restore original directory
        try:
            original_cwd.resolve()
        except Exception:
            pass


def get_check_results(request: QualityCheckRequest) -> QualityCheckResult:
    """
    Retrieve previously saved quality check results.

    Args:
        request: QualityCheckRequest with task_id

    Returns:
        QualityCheckResult with saved results or error
    """
    if not request.task_id:
        return QualityCheckResult(
            success=False,
            error_message="Task ID is required to retrieve check results",
        )

    try:
        results = _load_check_results(request.task_id)
        if not results:
            return QualityCheckResult(
                success=False,
                task_id=request.task_id,
                error_message=f"No quality check results found for task '{request.task_id}'",
            )

        return QualityCheckResult(
            success=True,
            task_id=request.task_id,
            all_passed=results.get("all_passed", False),
            check_results=results.get("check_results", []),
            failed_checks=results.get("failed_checks", []),
        )

    except Exception as e:
        return QualityCheckResult(
            success=False,
            task_id=request.task_id,
            error_message=f"Error retrieving check results: {str(e)}",
        )


def enforce_quality_gates(tmux: TMUXManager, request: QualityCheckRequest) -> QualityCheckResult:
    """
    Enforce quality gates by running checks and updating task status.

    Args:
        tmux: TMUXManager instance for agent communication
        request: QualityCheckRequest with enforcement configuration

    Returns:
        QualityCheckResult with gate enforcement status
    """
    # Run quality checks
    result = run_quality_checks(tmux, request)

    if not result.success:
        return result

    # Update task status based on results
    if request.task_id:
        if result.all_passed:
            _update_task_status(request.task_id, "quality_verified")
        else:
            _update_task_status(request.task_id, "quality_failed")

    # Set gates_passed flag
    result.gates_passed = result.all_passed

    return result


def _validate_request(request: QualityCheckRequest) -> Optional[str]:
    """Validate quality check request parameters."""
    # Validate project path
    if not request.project_path.strip():
        return "Project path cannot be empty"

    # Validate check types
    if not request.check_types:
        return "At least one check type must be specified"

    valid_types = ["tests", "linting", "formatting", "type_checking", "coverage", "security"]
    for check_type in request.check_types:
        if check_type not in valid_types:
            return f"Invalid check type '{check_type}'. Must be one of: {', '.join(valid_types)}"

    # Validate coverage threshold
    if request.coverage_threshold < 0 or request.coverage_threshold > 100:
        return "Coverage threshold must be between 0 and 100"

    return None


def _get_default_command(check_type: str, request: QualityCheckRequest) -> list[str]:
    """Get default command for a check type."""
    commands = {
        "tests": ["pytest", "-v"],
        "linting": ["ruff", "check", "."],
        "formatting": ["black", "--check", "."],
        "type_checking": ["mypy", "."],
        "coverage": ["pytest", "--cov", "--cov-report=term-missing", f"--cov-fail-under={request.coverage_threshold}"],
        "security": ["bandit", "-r", "."],
    }
    return commands.get(check_type, [])


def _get_quality_checks_dir() -> Path:
    """Get the directory for storing quality check results."""
    home_dir = Path.home() / ".tmux-orchestrator"
    checks_dir = home_dir / "quality_checks"
    checks_dir.mkdir(parents=True, exist_ok=True)
    return checks_dir


def _save_check_results(results: dict) -> bool:
    """Save quality check results to persistent storage."""
    try:
        checks_dir = _get_quality_checks_dir()
        file_path = checks_dir / f"{results['task_id']}.json"

        with open(file_path, "w") as f:
            json.dump(results, f, indent=2)

        return True

    except Exception:
        return False


def _load_check_results(task_id: str) -> Optional[dict]:
    """Load quality check results from persistent storage."""
    try:
        checks_dir = _get_quality_checks_dir()
        file_path = checks_dir / f"{task_id}.json"

        if not file_path.exists():
            return None

        with open(file_path) as f:
            data = json.load(f)
            return data if isinstance(data, dict) else None

    except Exception:
        return None


def _update_task_status(task_id: str, status: str) -> bool:
    """Update task status in the task tracking system."""
    try:
        # This would integrate with the task status tracking system
        # For now, we'll just return True to indicate the integration point
        return True
    except Exception:
        return False


def _send_report_to_agent(tmux: TMUXManager, agent_id: str, check_results: list[dict], all_passed: bool) -> bool:
    """Send quality check report to specified agent."""
    try:
        # Format report message
        report_lines = [
            "===== QUALITY CHECK REPORT =====",
            f"Overall Status: {'PASSED' if all_passed else 'FAILED'}",
            "",
            "Check Results:",
        ]

        for result in check_results:
            status = "✓" if result["passed"] else "✗"
            report_lines.append(f"  {status} {result['check_type']}: {result['command']}")
            if not result["passed"] and result.get("stderr"):
                report_lines.append(f"    Error: {result['stderr'][:100]}...")

        report_lines.extend(
            [
                "",
                "===== END REPORT =====",
            ]
        )

        message = "\n".join(report_lines)
        return tmux.send_keys(agent_id, message)

    except Exception:
        return False

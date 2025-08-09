"""Business logic for creating GitHub pull requests."""

import json
import re
import subprocess
from dataclasses import dataclass, field
from typing import Any, Optional

from tmux_orchestrator.utils.tmux import TMUXManager


@dataclass
class CreatePullRequestRequest:
    """Request parameters for pull request operations."""

    title: str = ""
    base_branch: str = ""
    head_branch: str = ""
    body: Optional[str] = None
    draft: bool = False
    labels: list[str] = field(default_factory=list)
    assignees: list[str] = field(default_factory=list)
    reviewers: list[str] = field(default_factory=list)
    task_ids: list[str] = field(default_factory=list)
    run_quality_checks: bool = False
    quality_check_types: list[str] = field(default_factory=list)
    block_on_quality_failure: bool = False
    project_path: Optional[str] = None
    pr_number: Optional[int] = None


@dataclass
class CreatePullRequestResult:
    """Result of pull request operation."""

    success: bool
    pr_url: str = ""
    pr_number: int = 0
    title: str = ""
    base_branch: str = ""
    head_branch: str = ""
    body: Optional[str] = None
    draft: bool = False
    labels: list[str] = field(default_factory=list)
    assignees: list[str] = field(default_factory=list)
    state: str = ""
    mergeable: bool = False
    checks_status: str = ""
    quality_checks_passed: Optional[bool] = None
    check_results: list[dict] = field(default_factory=list)
    linked_tasks: list[str] = field(default_factory=list)
    failed_tasks: list[str] = field(default_factory=list)
    error_message: Optional[str] = None


def create_pull_request(tmux: TMUXManager, request: CreatePullRequestRequest) -> CreatePullRequestResult:
    """
    Create a GitHub pull request using the gh CLI.

    Enables agents to create PRs when features are complete, with support for
    quality gate enforcement, task linking, and automated checks. Integrates
    with GitHub's PR workflow for comprehensive project coordination.

    Args:
        tmux: TMUXManager instance (for potential agent notifications)
        request: CreatePullRequestRequest with PR configuration

    Returns:
        CreatePullRequestResult indicating success/failure and PR details

    Raises:
        ValueError: If request parameters are invalid
        RuntimeError: If PR creation fails
    """
    # Validate input parameters
    validation_error = _validate_request(request)
    if validation_error:
        return CreatePullRequestResult(
            success=False,
            error_message=validation_error,
        )

    try:
        # Check if on correct branch
        current_branch = _get_current_branch()
        if current_branch != request.head_branch:
            return CreatePullRequestResult(
                success=False,
                error_message=f"Not on branch '{request.head_branch}'. Current branch is '{current_branch}'",
            )

        # Check for uncommitted changes
        if _has_uncommitted_changes():
            return CreatePullRequestResult(
                success=False,
                error_message="Uncommitted changes detected. Please commit all changes before creating PR",
            )

        # Run quality checks if requested
        if request.run_quality_checks:
            quality_passed = _run_quality_checks(tmux, request)
            if not quality_passed and request.block_on_quality_failure:
                return CreatePullRequestResult(
                    success=False,
                    quality_checks_passed=False,
                    error_message="Quality checks failed. PR creation blocked",
                )

        # Push branch to remote
        push_result = _push_branch(request.head_branch)
        if not push_result:
            return CreatePullRequestResult(
                success=False,
                error_message="Failed to push branch to remote",
            )

        # Create PR using gh CLI
        pr_url = _create_pr_with_gh(request)
        if not pr_url:
            return CreatePullRequestResult(
                success=False,
                error_message="Failed to create pull request",
            )

        # Extract PR number from URL
        pr_number = _extract_pr_number(pr_url)

        # Link to tasks if provided
        if request.task_ids:
            _link_tasks_to_pr(pr_number, request.task_ids)

        return CreatePullRequestResult(
            success=True,
            pr_url=pr_url,
            pr_number=pr_number,
            title=request.title,
            base_branch=request.base_branch,
            head_branch=request.head_branch,
            body=request.body,
            draft=request.draft,
            labels=request.labels,
            assignees=request.assignees,
            quality_checks_passed=quality_passed if request.run_quality_checks else None,
        )

    except FileNotFoundError as e:
        if "gh" in str(e):
            return CreatePullRequestResult(
                success=False,
                error_message="GitHub CLI (gh) is not installed. Please install it to create pull requests",
            )
        raise
    except Exception as e:
        return CreatePullRequestResult(
            success=False,
            error_message=f"Unexpected error during PR creation: {str(e)}",
        )


def get_pr_status(request: CreatePullRequestRequest) -> CreatePullRequestResult:
    """
    Get the status of an existing pull request.

    Args:
        request: CreatePullRequestRequest with pr_number

    Returns:
        CreatePullRequestResult with PR status information
    """
    if not request.pr_number:
        return CreatePullRequestResult(
            success=False,
            error_message="PR number is required to get status",
        )

    try:
        # Get PR info using gh CLI
        result = subprocess.run(
            ["gh", "pr", "view", str(request.pr_number), "--json", "state,mergeable,checks"],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            return CreatePullRequestResult(
                success=False,
                pr_number=request.pr_number,
                error_message=f"Failed to get PR status: {result.stderr}",
            )

        pr_data = json.loads(result.stdout)

        return CreatePullRequestResult(
            success=True,
            pr_number=request.pr_number,
            state=pr_data.get("state", ""),
            mergeable=pr_data.get("mergeable", False),
            checks_status=pr_data.get("checks", {}).get("conclusion", ""),
        )

    except Exception as e:
        return CreatePullRequestResult(
            success=False,
            pr_number=request.pr_number,
            error_message=f"Error getting PR status: {str(e)}",
        )


def link_pr_to_tasks(request: CreatePullRequestRequest) -> CreatePullRequestResult:
    """
    Link a pull request to completed tasks.

    Args:
        request: CreatePullRequestRequest with pr_number and task_ids

    Returns:
        CreatePullRequestResult with linking results
    """
    if not request.pr_number:
        return CreatePullRequestResult(
            success=False,
            error_message="PR number is required to link tasks",
        )

    if not request.task_ids:
        return CreatePullRequestResult(
            success=False,
            error_message="Task IDs are required to link to PR",
        )

    linked_tasks = []
    failed_tasks = []

    for task_id in request.task_ids:
        if _update_task_with_pr(task_id, request.pr_number):
            linked_tasks.append(task_id)
        else:
            failed_tasks.append(task_id)

    return CreatePullRequestResult(
        success=len(linked_tasks) > 0,
        pr_number=request.pr_number,
        linked_tasks=linked_tasks,
        failed_tasks=failed_tasks,
    )


def run_quality_checks_for_pr(tmux: TMUXManager, request: CreatePullRequestRequest) -> CreatePullRequestResult:
    """
    Run quality checks for a pull request.

    Args:
        tmux: TMUXManager instance for agent communication
        request: CreatePullRequestRequest with quality check configuration

    Returns:
        CreatePullRequestResult with quality check results
    """
    if not request.pr_number and not request.head_branch:
        return CreatePullRequestResult(
            success=False,
            error_message="Either PR number or head branch is required for quality checks",
        )

    try:
        # Get branch name if PR number provided
        branch = request.head_branch
        if request.pr_number and not branch:
            pr_branch = _get_pr_branch(request.pr_number)
            if not pr_branch:
                return CreatePullRequestResult(
                    success=False,
                    error_message="Failed to get branch for PR",
                )
            branch = pr_branch

        # Checkout the branch
        checkout_result = subprocess.run(
            ["git", "checkout", branch],
            capture_output=True,
            text=True,
        )
        if checkout_result.returncode != 0:
            return CreatePullRequestResult(
                success=False,
                error_message=f"Failed to checkout branch: {checkout_result.stderr}",
            )

        # Run quality checks
        check_results = []
        all_passed = True
        check_types = request.quality_check_types or ["tests", "linting"]

        for check_type in check_types:
            result = _run_single_quality_check(check_type, request.project_path or ".")
            check_results.append(result)
            if not result["passed"]:
                all_passed = False

        return CreatePullRequestResult(
            success=True,
            pr_number=request.pr_number or 0,
            quality_checks_passed=all_passed,
            check_results=check_results,
        )

    except Exception as e:
        return CreatePullRequestResult(
            success=False,
            error_message=f"Error running quality checks: {str(e)}",
        )


def _validate_request(request: CreatePullRequestRequest) -> Optional[str]:
    """Validate pull request creation parameters."""
    if not request.title.strip():
        return "Title cannot be empty"

    if not request.base_branch.strip():
        return "Base branch cannot be empty"

    if not request.head_branch.strip():
        return "Head branch cannot be empty"

    return None


def _get_current_branch() -> str:
    """Get the current git branch."""
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _has_uncommitted_changes() -> bool:
    """Check if there are uncommitted changes."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True,
    )
    return bool(result.stdout.strip())


def _push_branch(branch: str) -> bool:
    """Push branch to remote."""
    result = subprocess.run(
        ["git", "push", "-u", "origin", branch],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _create_pr_with_gh(request: CreatePullRequestRequest) -> str:
    """Create PR using GitHub CLI."""
    cmd = [
        "gh", "pr", "create",
        "--title", request.title,
        "--base", request.base_branch,
        "--head", request.head_branch,
    ]

    # Add optional flags
    if request.draft:
        cmd.append("--draft")

    if request.labels:
        cmd.extend(["--label", ",".join(request.labels)])

    if request.assignees:
        cmd.extend(["--assignee", ",".join(request.assignees)])

    if request.reviewers:
        cmd.extend(["--reviewer", ",".join(request.reviewers)])

    # Run command with body as stdin if provided
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        input=request.body if request.body else None,
    )

    if result.returncode == 0:
        return result.stdout.strip()
    return ""


def _extract_pr_number(pr_url: str) -> int:
    """Extract PR number from GitHub URL."""
    match = re.search(r'/pull/(\d+)', pr_url)
    if match:
        return int(match.group(1))
    return 0


def _run_quality_checks(tmux: TMUXManager, request: CreatePullRequestRequest) -> bool:
    """Run quality checks before PR creation."""
    check_types = request.quality_check_types or ["tests", "linting"]
    project_path = request.project_path or "."

    for check_type in check_types:
        result = _run_single_quality_check(check_type, project_path)
        if not result["passed"]:
            return False

    return True


def _run_single_quality_check(check_type: str, project_path: str) -> dict[str, Any]:
    """Run a single quality check."""
    commands = {
        "tests": ["pytest", "-v"],
        "linting": ["ruff", "check", "."],
        "formatting": ["black", "--check", "."],
        "type_checking": ["mypy", "."],
    }

    command = commands.get(check_type, [])
    if not command:
        return {"check_type": check_type, "passed": False, "error": "Unknown check type"}

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        cwd=project_path,
    )

    return {
        "check_type": check_type,
        "passed": result.returncode == 0,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def _link_tasks_to_pr(pr_number: int, task_ids: list[str]) -> None:
    """Link tasks to the created PR."""
    for task_id in task_ids:
        _update_task_with_pr(task_id, pr_number)


def _update_task_with_pr(task_id: str, pr_number: int) -> bool:
    """Update task with PR information."""
    try:
        # This would integrate with the task tracking system
        # For now, we'll just return True to indicate the integration point
        return True
    except Exception:
        return False


def _get_pr_branch(pr_number: int) -> Optional[str]:
    """Get the branch name for a PR."""
    try:
        result = subprocess.run(
            ["gh", "pr", "view", str(pr_number), "--json", "headRefName"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            ref_name = data.get("headRefName")
            return ref_name if isinstance(ref_name, str) else None
    except Exception:
        pass
    return None

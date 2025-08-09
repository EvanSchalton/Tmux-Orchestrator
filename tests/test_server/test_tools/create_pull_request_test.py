"""Tests for create_pull_request business logic."""

from unittest.mock import Mock, patch

import pytest

from tmux_orchestrator.server.tools.create_pull_request import (
    CreatePullRequestRequest,
    create_pull_request,
    get_pr_status,
    link_pr_to_tasks,
    run_quality_checks_for_pr,
)
from tmux_orchestrator.utils.tmux import TMUXManager


class TestCreatePullRequest:
    """Test cases for pull request creation functions."""

    def test_create_pull_request_empty_title(self) -> None:
        """Test create_pull_request with empty title returns error."""
        tmux = Mock(spec=TMUXManager)
        request = CreatePullRequestRequest(title="", base_branch="main", head_branch="feature/test")

        result = create_pull_request(tmux, request)

        assert not result.success
        assert result.error_message is not None
        assert "Title cannot be empty" in result.error_message

    def test_create_pull_request_empty_base_branch(self) -> None:
        """Test create_pull_request with empty base_branch returns error."""
        tmux = Mock(spec=TMUXManager)
        request = CreatePullRequestRequest(title="Test PR", base_branch="", head_branch="feature/test")

        result = create_pull_request(tmux, request)

        assert not result.success
        assert result.error_message is not None
        assert "Base branch cannot be empty" in result.error_message

    def test_create_pull_request_empty_head_branch(self) -> None:
        """Test create_pull_request with empty head_branch returns error."""
        tmux = Mock(spec=TMUXManager)
        request = CreatePullRequestRequest(title="Test PR", base_branch="main", head_branch="")

        result = create_pull_request(tmux, request)

        assert not result.success
        assert result.error_message is not None
        assert "Head branch cannot be empty" in result.error_message

    def test_create_pull_request_not_on_branch(self) -> None:
        """Test create_pull_request when not on the correct branch."""
        tmux = Mock(spec=TMUXManager)
        request = CreatePullRequestRequest(title="Test PR", base_branch="main", head_branch="feature/test")

        with patch("subprocess.run") as mock_run:
            # Mock current branch check
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "different-branch"

            result = create_pull_request(tmux, request)

            assert not result.success
            assert result.error_message is not None
            assert "Not on branch 'feature/test'" in result.error_message

    def test_create_pull_request_uncommitted_changes(self) -> None:
        """Test create_pull_request with uncommitted changes."""
        tmux = Mock(spec=TMUXManager)
        request = CreatePullRequestRequest(title="Test PR", base_branch="main", head_branch="feature/test")

        with patch("subprocess.run") as mock_run:
            # Mock git status with uncommitted changes
            def mock_subprocess(cmd, *args, **kwargs):
                if "branch" in cmd and "--show-current" in cmd:
                    return Mock(returncode=0, stdout="feature/test")
                elif "status" in cmd and "--porcelain" in cmd:
                    return Mock(returncode=0, stdout="M file.txt\n")
                return Mock(returncode=0, stdout="")

            mock_run.side_effect = mock_subprocess

            result = create_pull_request(tmux, request)

            assert not result.success
            assert result.error_message is not None
            assert "Uncommitted changes detected" in result.error_message

    def test_create_pull_request_successful(self) -> None:
        """Test successful pull request creation."""
        tmux = Mock(spec=TMUXManager)
        request = CreatePullRequestRequest(
            title="Add new feature",
            base_branch="main",
            head_branch="feature/test",
            body="This PR adds a new feature",
            draft=False,
            task_ids=["task_001", "task_002"],
        )

        with patch("subprocess.run") as mock_run:
            # Mock all git/gh commands
            def mock_subprocess(cmd, *args, **kwargs):
                if "branch" in cmd and "--show-current" in cmd:
                    return Mock(returncode=0, stdout="feature/test")
                elif "status" in cmd and "--porcelain" in cmd:
                    return Mock(returncode=0, stdout="")
                elif "push" in cmd:
                    return Mock(returncode=0, stdout="Pushed successfully")
                elif "gh" in cmd and "pr" in cmd and "create" in cmd:
                    return Mock(returncode=0, stdout="https://github.com/user/repo/pull/123")
                return Mock(returncode=0, stdout="")

            mock_run.side_effect = mock_subprocess

            result = create_pull_request(tmux, request)

            assert result.success
            assert result.pr_url == "https://github.com/user/repo/pull/123"
            assert result.pr_number == 123
            assert result.title == "Add new feature"
            assert result.base_branch == "main"
            assert result.head_branch == "feature/test"

    def test_create_pull_request_with_quality_checks(self) -> None:
        """Test pull request creation with quality checks enabled."""
        tmux = Mock(spec=TMUXManager)
        request = CreatePullRequestRequest(
            title="Add new feature",
            base_branch="main",
            head_branch="feature/test",
            run_quality_checks=True,
            quality_check_types=["tests", "linting"],
        )

        with patch("subprocess.run") as mock_run, patch(
            "tmux_orchestrator.server.tools.create_pull_request._run_quality_checks"
        ) as mock_quality:
            # Mock successful commands
            def mock_subprocess(cmd, *args, **kwargs):
                if "branch" in cmd and "--show-current" in cmd:
                    return Mock(returncode=0, stdout="feature/test")
                elif "status" in cmd and "--porcelain" in cmd:
                    return Mock(returncode=0, stdout="")
                elif "push" in cmd:
                    return Mock(returncode=0, stdout="Pushed")
                elif "gh" in cmd and "pr" in cmd:
                    return Mock(returncode=0, stdout="https://github.com/user/repo/pull/124")
                return Mock(returncode=0, stdout="")

            mock_run.side_effect = mock_subprocess
            mock_quality.return_value = True

            result = create_pull_request(tmux, request)

            assert result.success
            assert result.quality_checks_passed
            mock_quality.assert_called_once()

    def test_create_pull_request_quality_checks_fail(self) -> None:
        """Test pull request creation when quality checks fail."""
        tmux = Mock(spec=TMUXManager)
        request = CreatePullRequestRequest(
            title="Add new feature",
            base_branch="main",
            head_branch="feature/test",
            run_quality_checks=True,
            block_on_quality_failure=True,
        )

        with patch("subprocess.run") as mock_run, patch(
            "tmux_orchestrator.server.tools.create_pull_request._run_quality_checks"
        ) as mock_quality:
            # Mock commands
            def mock_subprocess(cmd, *args, **kwargs):
                if "branch" in cmd and "--show-current" in cmd:
                    return Mock(returncode=0, stdout="feature/test")
                elif "status" in cmd and "--porcelain" in cmd:
                    return Mock(returncode=0, stdout="")
                return Mock(returncode=0, stdout="")

            mock_run.side_effect = mock_subprocess
            mock_quality.return_value = False

            result = create_pull_request(tmux, request)

            assert not result.success
            assert result.error_message is not None
            assert "Quality checks failed" in result.error_message

    def test_create_pull_request_draft_mode(self) -> None:
        """Test creating a draft pull request."""
        tmux = Mock(spec=TMUXManager)
        request = CreatePullRequestRequest(
            title="WIP: Add new feature", base_branch="main", head_branch="feature/test", draft=True
        )

        with patch("subprocess.run") as mock_run:

            def mock_subprocess(cmd, *args, **kwargs):
                if "branch" in cmd and "--show-current" in cmd:
                    return Mock(returncode=0, stdout="feature/test")
                elif "status" in cmd and "--porcelain" in cmd:
                    return Mock(returncode=0, stdout="")
                elif "push" in cmd:
                    return Mock(returncode=0, stdout="Pushed")
                elif "gh" in cmd and "pr" in cmd:
                    # Verify --draft flag is included
                    assert "--draft" in cmd
                    return Mock(returncode=0, stdout="https://github.com/user/repo/pull/125")
                return Mock(returncode=0, stdout="")

            mock_run.side_effect = mock_subprocess

            result = create_pull_request(tmux, request)

            assert result.success
            assert result.draft

    def test_create_pull_request_with_labels(self) -> None:
        """Test creating pull request with labels."""
        tmux = Mock(spec=TMUXManager)
        request = CreatePullRequestRequest(
            title="Add new feature",
            base_branch="main",
            head_branch="feature/test",
            labels=["enhancement", "needs-review"],
        )

        with patch("subprocess.run") as mock_run:

            def mock_subprocess(cmd, *args, **kwargs):
                if "branch" in cmd and "--show-current" in cmd:
                    return Mock(returncode=0, stdout="feature/test")
                elif "status" in cmd and "--porcelain" in cmd:
                    return Mock(returncode=0, stdout="")
                elif "push" in cmd:
                    return Mock(returncode=0, stdout="Pushed")
                elif "gh" in cmd and "pr" in cmd and "create" in cmd:
                    # Verify labels are included
                    assert "--label" in cmd
                    assert "enhancement,needs-review" in cmd
                    return Mock(returncode=0, stdout="https://github.com/user/repo/pull/126")
                return Mock(returncode=0, stdout="")

            mock_run.side_effect = mock_subprocess

            result = create_pull_request(tmux, request)

            assert result.success
            assert result.labels == ["enhancement", "needs-review"]

    def test_get_pr_status_successful(self) -> None:
        """Test getting PR status successfully."""
        request = CreatePullRequestRequest(pr_number=123)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout='{"state":"open","mergeable":true,"checks":{"conclusion":"success"}}'
            )

            result = get_pr_status(request)

            assert result.success
            assert result.pr_number == 123
            assert result.state == "open"
            assert result.mergeable
            assert result.checks_status == "success"

    def test_get_pr_status_not_found(self) -> None:
        """Test get_pr_status when PR not found."""
        request = CreatePullRequestRequest(pr_number=999)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1, stdout="", stderr="Pull request not found")

            result = get_pr_status(request)

            assert not result.success
            assert result.error_message is not None
            assert "Failed to get PR status" in result.error_message

    def test_link_pr_to_tasks_successful(self) -> None:
        """Test linking PR to tasks successfully."""
        request = CreatePullRequestRequest(pr_number=123, task_ids=["task_001", "task_002", "task_003"])

        with patch("tmux_orchestrator.server.tools.create_pull_request._update_task_with_pr") as mock_update:
            mock_update.return_value = True

            result = link_pr_to_tasks(request)

            assert result.success
            assert result.linked_tasks == ["task_001", "task_002", "task_003"]
            assert mock_update.call_count == 3

    def test_link_pr_to_tasks_partial_failure(self) -> None:
        """Test linking PR to tasks with partial failures."""
        request = CreatePullRequestRequest(pr_number=123, task_ids=["task_001", "task_002", "task_003"])

        with patch("tmux_orchestrator.server.tools.create_pull_request._update_task_with_pr") as mock_update:
            # First two succeed, third fails
            mock_update.side_effect = [True, True, False]

            result = link_pr_to_tasks(request)

            assert result.success  # Partial success is still success
            assert result.linked_tasks == ["task_001", "task_002"]
            assert result.failed_tasks == ["task_003"]

    def test_run_quality_checks_for_pr_successful(self) -> None:
        """Test running quality checks for PR."""
        tmux = Mock(spec=TMUXManager)
        request = CreatePullRequestRequest(
            pr_number=123, quality_check_types=["tests", "linting"], project_path="/test/project"
        )

        with patch("tmux_orchestrator.server.tools.create_pull_request._get_pr_branch") as mock_branch, patch(
            "subprocess.run"
        ) as mock_run:
            mock_branch.return_value = "feature/test"

            # Mock checkout and quality checks
            def mock_subprocess(cmd, *args, **kwargs):
                if "checkout" in cmd:
                    return Mock(returncode=0, stdout="")
                elif "pytest" in cmd or "ruff" in cmd:
                    return Mock(returncode=0, stdout="All checks passed")
                return Mock(returncode=0, stdout="")

            mock_run.side_effect = mock_subprocess

            result = run_quality_checks_for_pr(tmux, request)

            assert result.success
            assert result.quality_checks_passed
            assert len(result.check_results) == 2

    def test_create_pull_request_gh_not_installed(self) -> None:
        """Test create_pull_request when gh CLI is not installed."""
        tmux = Mock(spec=TMUXManager)
        request = CreatePullRequestRequest(title="Test PR", base_branch="main", head_branch="feature/test")

        with patch("subprocess.run") as mock_run:

            def mock_subprocess(cmd, *args, **kwargs):
                if "branch" in cmd and "--show-current" in cmd:
                    return Mock(returncode=0, stdout="feature/test")
                elif "status" in cmd and "--porcelain" in cmd:
                    return Mock(returncode=0, stdout="")
                elif "push" in cmd:
                    return Mock(returncode=0, stdout="Pushed")
                elif "gh" in cmd:
                    raise FileNotFoundError("gh command not found")
                return Mock(returncode=0, stdout="")

            mock_run.side_effect = mock_subprocess

            result = create_pull_request(tmux, request)

            assert not result.success
            assert result.error_message is not None
            assert "GitHub CLI (gh) is not installed" in result.error_message

    def test_create_pull_request_with_assignees(self) -> None:
        """Test creating pull request with assignees."""
        tmux = Mock(spec=TMUXManager)
        request = CreatePullRequestRequest(
            title="Add new feature", base_branch="main", head_branch="feature/test", assignees=["user1", "user2"]
        )

        with patch("subprocess.run") as mock_run:

            def mock_subprocess(cmd, *args, **kwargs):
                if "branch" in cmd and "--show-current" in cmd:
                    return Mock(returncode=0, stdout="feature/test")
                elif "status" in cmd and "--porcelain" in cmd:
                    return Mock(returncode=0, stdout="")
                elif "push" in cmd:
                    return Mock(returncode=0, stdout="Pushed")
                elif "gh" in cmd and "pr" in cmd:
                    # Verify assignees are included
                    assert "--assignee" in cmd
                    assert "user1,user2" in cmd
                    return Mock(returncode=0, stdout="https://github.com/user/repo/pull/127")
                return Mock(returncode=0, stdout="")

            mock_run.side_effect = mock_subprocess

            result = create_pull_request(tmux, request)

            assert result.success
            assert result.assignees == ["user1", "user2"]

    def test_create_pull_request_exception_handling(self) -> None:
        """Test create_pull_request handles unexpected exceptions."""
        tmux = Mock(spec=TMUXManager)
        request = CreatePullRequestRequest(title="Test PR", base_branch="main", head_branch="feature/test")

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = Exception("Unexpected error")

            result = create_pull_request(tmux, request)

            assert not result.success
            assert result.error_message is not None
            assert "Unexpected error during PR creation" in result.error_message

    @pytest.mark.parametrize(
        "body_content",
        [
            "Simple description",
            "Multi-line\ndescription\nwith details",
            "Description with [links](https://example.com)",
            "## Summary\n- Point 1\n- Point 2",
        ],
    )
    def test_create_pull_request_various_body_formats(self, body_content: str) -> None:
        """Test creating PR with various body content formats."""
        tmux = Mock(spec=TMUXManager)
        request = CreatePullRequestRequest(
            title="Test PR", base_branch="main", head_branch="feature/test", body=body_content
        )

        with patch("subprocess.run") as mock_run:

            def mock_subprocess(cmd, *args, **kwargs):
                if "branch" in cmd and "--show-current" in cmd:
                    return Mock(returncode=0, stdout="feature/test")
                elif "status" in cmd and "--porcelain" in cmd:
                    return Mock(returncode=0, stdout="")
                elif "push" in cmd:
                    return Mock(returncode=0, stdout="Pushed")
                elif "gh" in cmd and "pr" in cmd:
                    # Body should be passed via stdin
                    assert kwargs.get("input") == body_content
                    return Mock(returncode=0, stdout="https://github.com/user/repo/pull/128")
                return Mock(returncode=0, stdout="")

            mock_run.side_effect = mock_subprocess

            result = create_pull_request(tmux, request)

            assert result.success
            assert result.body == body_content

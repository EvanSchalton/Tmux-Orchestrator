"""Tests for track_task_status business logic."""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from tmux_orchestrator.server.tools.track_task_status import (
    TaskStatusRequest,
    TaskStatusUpdate,
    get_task_status,
    list_tasks_by_status,
    track_task_status,
    update_task_status,
)
from tmux_orchestrator.utils.tmux import TMUXManager


class TestTrackTaskStatus:
    """Test cases for task status tracking functions."""

    def test_track_task_status_empty_task_id(self) -> None:
        """Test track_task_status with empty task_id returns error."""
        tmux = Mock(spec=TMUXManager)
        request = TaskStatusRequest(task_id="", agent_id="dev:0", status="in_progress")

        result = track_task_status(tmux, request)

        assert not result.success
        assert result.error_message is not None
        assert "Task ID cannot be empty" in result.error_message
        assert result.task_id == ""

    def test_track_task_status_empty_agent_id(self) -> None:
        """Test track_task_status with empty agent_id returns error."""
        tmux = Mock(spec=TMUXManager)
        request = TaskStatusRequest(task_id="task_001", agent_id="", status="in_progress")

        result = track_task_status(tmux, request)

        assert not result.success
        assert result.error_message is not None
        assert "Agent ID cannot be empty" in result.error_message

    def test_track_task_status_invalid_status(self) -> None:
        """Test track_task_status with invalid status returns error."""
        tmux = Mock(spec=TMUXManager)
        request = TaskStatusRequest(task_id="task_001", agent_id="dev:0", status="invalid")

        result = track_task_status(tmux, request)

        assert not result.success
        assert result.error_message is not None
        assert "Invalid status 'invalid'" in result.error_message

    def test_track_task_status_invalid_agent_format(self) -> None:
        """Test track_task_status with invalid agent format returns error."""
        tmux = Mock(spec=TMUXManager)
        request = TaskStatusRequest(task_id="task_001", agent_id="invalid-format", status="in_progress")

        result = track_task_status(tmux, request)

        assert not result.success
        assert result.error_message is not None
        assert "Agent ID must be in format 'session:window'" in result.error_message

    def test_track_task_status_successful_creation(self) -> None:
        """Test successful task status creation."""
        tmux = Mock(spec=TMUXManager)
        request = TaskStatusRequest(
            task_id="task_001",
            agent_id="dev:0",
            status="in_progress",
            description="Implement authentication module",
            priority="high",
            estimated_hours=8
        )

        with patch('tmux_orchestrator.server.tools.track_task_status._save_task_status') as mock_save:
            mock_save.return_value = True

            result = track_task_status(tmux, request)

            assert result.success
            assert result.task_id == "task_001"
            assert result.agent_id == "dev:0"
            assert result.status == "in_progress"
            assert result.description == "Implement authentication module"
            assert result.priority == "high"
            assert result.estimated_hours == 8
            assert result.error_message is None
            mock_save.assert_called_once()

    def test_track_task_status_update_existing(self) -> None:
        """Test updating existing task status."""
        tmux = Mock(spec=TMUXManager)
        request = TaskStatusRequest(task_id="task_001", agent_id="dev:0", status="completed")

        with patch('tmux_orchestrator.server.tools.track_task_status._load_task_status') as mock_load, \
             patch('tmux_orchestrator.server.tools.track_task_status._save_task_status') as mock_save:

            # Mock existing task
            existing_task = TaskStatusUpdate(
                task_id="task_001",
                agent_id="dev:0",
                status="in_progress",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            mock_load.return_value = existing_task
            mock_save.return_value = True

            result = track_task_status(tmux, request)

            assert result.success
            assert result.status == "completed"
            assert result.previous_status == "in_progress"
            mock_save.assert_called_once()

    def test_track_task_status_with_completion_notes(self) -> None:
        """Test task status update with completion notes."""
        tmux = Mock(spec=TMUXManager)
        request = TaskStatusRequest(
            task_id="task_001",
            agent_id="dev:0",
            status="completed",
            completion_notes="All tests passing, feature fully implemented"
        )

        with patch('tmux_orchestrator.server.tools.track_task_status._save_task_status') as mock_save:
            mock_save.return_value = True

            result = track_task_status(tmux, request)

            assert result.success
            assert result.completion_notes == "All tests passing, feature fully implemented"

    def test_track_task_status_with_blockers(self) -> None:
        """Test task status update with blockers."""
        tmux = Mock(spec=TMUXManager)
        request = TaskStatusRequest(
            task_id="task_001",
            agent_id="dev:0",
            status="blocked",
            blockers=["Missing API documentation", "Awaiting design approval"]
        )

        with patch('tmux_orchestrator.server.tools.track_task_status._save_task_status') as mock_save:
            mock_save.return_value = True

            result = track_task_status(tmux, request)

            assert result.success
            assert result.status == "blocked"
            assert result.blockers == ["Missing API documentation", "Awaiting design approval"]

    def test_track_task_status_save_failure(self) -> None:
        """Test task status tracking when save fails."""
        tmux = Mock(spec=TMUXManager)
        request = TaskStatusRequest(task_id="task_001", agent_id="dev:0", status="in_progress")

        with patch('tmux_orchestrator.server.tools.track_task_status._save_task_status') as mock_save:
            mock_save.return_value = False

            result = track_task_status(tmux, request)

            assert not result.success
            assert result.error_message is not None
            assert "Failed to save task status" in result.error_message

    def test_get_task_status_successful(self) -> None:
        """Test successful task status retrieval."""
        request = TaskStatusRequest(task_id="task_001")

        with patch('tmux_orchestrator.server.tools.track_task_status._load_task_status') as mock_load:
            task_status = TaskStatusUpdate(
                task_id="task_001",
                agent_id="dev:0",
                status="in_progress",
                description="Working on authentication",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            mock_load.return_value = task_status

            result = get_task_status(request)

            assert result.success
            assert result.task_id == "task_001"
            assert result.status == "in_progress"

    def test_get_task_status_not_found(self) -> None:
        """Test get_task_status when task not found."""
        request = TaskStatusRequest(task_id="nonexistent")

        with patch('tmux_orchestrator.server.tools.track_task_status._load_task_status') as mock_load:
            mock_load.return_value = None

            result = get_task_status(request)

            assert not result.success
            assert result.error_message is not None
            assert "Task 'nonexistent' not found" in result.error_message

    def test_update_task_status_successful(self) -> None:
        """Test successful task status update."""
        tmux = Mock(spec=TMUXManager)
        request = TaskStatusRequest(
            task_id="task_001",
            agent_id="dev:0",
            status="completed",
            actual_hours=10
        )

        with patch('tmux_orchestrator.server.tools.track_task_status._load_task_status') as mock_load, \
             patch('tmux_orchestrator.server.tools.track_task_status._save_task_status') as mock_save:

            existing_task = TaskStatusUpdate(
                task_id="task_001",
                agent_id="dev:0",
                status="in_progress",
                created_at=datetime.now() - timedelta(hours=2),
                updated_at=datetime.now() - timedelta(hours=2)
            )
            mock_load.return_value = existing_task
            mock_save.return_value = True

            result = update_task_status(tmux, request)

            assert result.success
            assert result.status == "completed"
            assert result.actual_hours == 10
            assert result.previous_status == "in_progress"

    def test_update_task_status_not_found(self) -> None:
        """Test update_task_status when task not found."""
        tmux = Mock(spec=TMUXManager)
        request = TaskStatusRequest(task_id="nonexistent", agent_id="dev:0", status="completed")

        with patch('tmux_orchestrator.server.tools.track_task_status._load_task_status') as mock_load:
            mock_load.return_value = None

            result = update_task_status(tmux, request)

            assert not result.success
            assert result.error_message is not None
            assert "Task 'nonexistent' not found" in result.error_message

    def test_list_tasks_by_status_successful(self) -> None:
        """Test successful task listing by status."""
        request = TaskStatusRequest(status="in_progress")

        with patch('tmux_orchestrator.server.tools.track_task_status._load_all_task_statuses') as mock_load:
            tasks = [
                TaskStatusUpdate(
                    task_id="task_001",
                    agent_id="dev:0",
                    status="in_progress",
                    created_at=datetime.now()
                ),
                TaskStatusUpdate(
                    task_id="task_002",
                    agent_id="qa:0",
                    status="completed",
                    created_at=datetime.now()
                ),
                TaskStatusUpdate(
                    task_id="task_003",
                    agent_id="dev:1",
                    status="in_progress",
                    created_at=datetime.now()
                )
            ]
            mock_load.return_value = tasks

            result = list_tasks_by_status(request)

            assert result.success
            assert len(result.tasks) == 2  # Only in_progress tasks
            assert all(task.status == "in_progress" for task in result.tasks)

    def test_list_tasks_by_status_all_tasks(self) -> None:
        """Test listing all tasks when no status filter provided."""
        request = TaskStatusRequest()

        with patch('tmux_orchestrator.server.tools.track_task_status._load_all_task_statuses') as mock_load:
            tasks = [
                TaskStatusUpdate(task_id="task_001", status="in_progress", created_at=datetime.now()),
                TaskStatusUpdate(task_id="task_002", status="completed", created_at=datetime.now()),
            ]
            mock_load.return_value = tasks

            result = list_tasks_by_status(request)

            assert result.success
            assert len(result.tasks) == 2

    def test_list_tasks_by_status_with_agent_filter(self) -> None:
        """Test listing tasks filtered by agent."""
        request = TaskStatusRequest(agent_id="dev:0")

        with patch('tmux_orchestrator.server.tools.track_task_status._load_all_task_statuses') as mock_load:
            tasks = [
                TaskStatusUpdate(task_id="task_001", agent_id="dev:0", status="in_progress", created_at=datetime.now()),
                TaskStatusUpdate(task_id="task_002", agent_id="qa:0", status="completed", created_at=datetime.now()),
                TaskStatusUpdate(task_id="task_003", agent_id="dev:0", status="completed", created_at=datetime.now()),
            ]
            mock_load.return_value = tasks

            result = list_tasks_by_status(request)

            assert result.success
            assert len(result.tasks) == 2  # Only dev:0 tasks
            assert all(task.agent_id == "dev:0" for task in result.tasks)

    @pytest.mark.parametrize(
        "status",
        ["pending", "in_progress", "completed", "blocked", "cancelled"],
    )
    def test_track_task_status_all_valid_statuses(self, status: str) -> None:
        """Test track_task_status accepts all valid status values."""
        tmux = Mock(spec=TMUXManager)
        request = TaskStatusRequest(task_id="task_001", agent_id="dev:0", status=status)

        with patch('tmux_orchestrator.server.tools.track_task_status._save_task_status') as mock_save:
            mock_save.return_value = True

            result = track_task_status(tmux, request)

            assert result.success
            assert result.status == status

    def test_track_task_status_with_progress_percentage(self) -> None:
        """Test task status tracking with progress percentage."""
        tmux = Mock(spec=TMUXManager)
        request = TaskStatusRequest(
            task_id="task_001",
            agent_id="dev:0",
            status="in_progress",
            progress_percentage=75
        )

        with patch('tmux_orchestrator.server.tools.track_task_status._save_task_status') as mock_save:
            mock_save.return_value = True

            result = track_task_status(tmux, request)

            assert result.success
            assert result.progress_percentage == 75

    def test_track_task_status_invalid_progress_percentage(self) -> None:
        """Test task status tracking with invalid progress percentage."""
        tmux = Mock(spec=TMUXManager)
        request = TaskStatusRequest(
            task_id="task_001",
            agent_id="dev:0",
            status="in_progress",
            progress_percentage=150  # Invalid - over 100
        )

        result = track_task_status(tmux, request)

        assert not result.success
        assert result.error_message is not None
        assert "Progress percentage must be between 0 and 100" in result.error_message

    def test_track_task_status_exception_handling(self) -> None:
        """Test task status tracking handles unexpected exceptions."""
        tmux = Mock(spec=TMUXManager)
        request = TaskStatusRequest(task_id="task_001", agent_id="dev:0", status="in_progress")

        with patch('tmux_orchestrator.server.tools.track_task_status._save_task_status') as mock_save:
            mock_save.side_effect = Exception("Disk full")

            result = track_task_status(tmux, request)

            assert not result.success
            assert result.error_message is not None
            assert "Unexpected error during task status tracking" in result.error_message

    def test_track_task_status_metadata_tracking(self) -> None:
        """Test task status tracking includes comprehensive metadata."""
        tmux = Mock(spec=TMUXManager)
        request = TaskStatusRequest(
            task_id="task_001",
            agent_id="dev:0",
            status="in_progress",
            tags=["authentication", "security", "backend"]
        )

        with patch('tmux_orchestrator.server.tools.track_task_status._save_task_status') as mock_save:
            mock_save.return_value = True

            result = track_task_status(tmux, request)

            assert result.success
            assert result.tags == ["authentication", "security", "backend"]
            assert result.tracking_metadata is not None

            metadata = result.tracking_metadata
            assert "tracked_at" in metadata
            assert "session" in metadata
            assert "window" in metadata
            assert metadata["session"] == "dev"
            assert metadata["window"] == "0"

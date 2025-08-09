"""Tests for assign_task business logic."""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from tmux_orchestrator.server.tools.assign_task import (
    AssignTaskRequest,
    assign_task,
    get_agent_workload,
    list_available_agents,
    reassign_task,
)
from tmux_orchestrator.utils.tmux import TMUXManager


class TestAssignTask:
    """Test cases for task assignment functions."""

    def test_assign_task_empty_task_id(self) -> None:
        """Test assign_task with empty task_id returns error."""
        tmux = Mock(spec=TMUXManager)
        request = AssignTaskRequest(task_id="", agent_id="dev:0")

        result = assign_task(tmux, request)

        assert not result.success
        assert result.error_message is not None
        assert "Task ID cannot be empty" in result.error_message
        assert result.task_id == ""

    def test_assign_task_empty_agent_id(self) -> None:
        """Test assign_task with empty agent_id returns error."""
        tmux = Mock(spec=TMUXManager)
        request = AssignTaskRequest(task_id="task_001", agent_id="")

        result = assign_task(tmux, request)

        assert not result.success
        assert result.error_message is not None
        assert "Agent ID cannot be empty" in result.error_message

    def test_assign_task_invalid_agent_format(self) -> None:
        """Test assign_task with invalid agent format returns error."""
        tmux = Mock(spec=TMUXManager)
        request = AssignTaskRequest(task_id="task_001", agent_id="invalid-format")

        result = assign_task(tmux, request)

        assert not result.success
        assert result.error_message is not None
        assert "Agent ID must be in format 'session:window'" in result.error_message

    def test_assign_task_agent_not_accessible(self) -> None:
        """Test assign_task when agent is not accessible."""
        tmux = Mock(spec=TMUXManager)
        tmux.capture_pane.return_value = None  # Agent not found

        request = AssignTaskRequest(task_id="task_001", agent_id="dev:0")

        result = assign_task(tmux, request)

        assert not result.success
        assert result.error_message is not None
        assert "Agent 'dev:0' is not accessible or offline" in result.error_message

    def test_assign_task_successful_assignment(self) -> None:
        """Test successful task assignment."""
        tmux = Mock(spec=TMUXManager)
        tmux.capture_pane.return_value = "Agent is active"
        tmux.send_keys.return_value = True

        request = AssignTaskRequest(
            task_id="task_001",
            agent_id="dev:0",
            task_title="Implement authentication",
            task_description="Add JWT authentication to API endpoints",
            priority="high",
            estimated_hours=8,
            due_date="2025-08-15",
        )

        with (
            patch("tmux_orchestrator.server.tools.assign_task._save_assignment") as mock_save,
            patch("tmux_orchestrator.server.tools.assign_task._update_task_status") as mock_update,
        ):
            mock_save.return_value = True
            mock_update.return_value = True

            result = assign_task(tmux, request)

            assert result.success
            assert result.task_id == "task_001"
            assert result.assigned_agent == "dev:0"
            assert result.priority == "high"
            assert result.estimated_hours == 8
            assert result.due_date == "2025-08-15"
            assert result.error_message is None

            # Verify assignment message was sent
            tmux.send_keys.assert_called_once()
            call_args = tmux.send_keys.call_args[0]
            assert call_args[0] == "dev:0"
            assert "TASK ASSIGNMENT" in call_args[1]

    def test_assign_task_with_dependencies(self) -> None:
        """Test task assignment with dependencies."""
        tmux = Mock(spec=TMUXManager)
        tmux.capture_pane.return_value = "Agent is active"
        tmux.send_keys.return_value = True

        request = AssignTaskRequest(
            task_id="task_002", agent_id="dev:1", task_title="Add unit tests", dependencies=["task_001", "task_003"]
        )

        with (
            patch("tmux_orchestrator.server.tools.assign_task._save_assignment") as mock_save,
            patch("tmux_orchestrator.server.tools.assign_task._update_task_status") as mock_update,
        ):
            mock_save.return_value = True
            mock_update.return_value = True

            result = assign_task(tmux, request)

            assert result.success
            assert result.dependencies == ["task_001", "task_003"]

            # Verify dependencies are mentioned in assignment message
            call_args = tmux.send_keys.call_args[0]
            message = call_args[1]
            assert "DEPENDENCIES:" in message
            assert "task_001" in message
            assert "task_003" in message

    def test_assign_task_save_assignment_fails(self) -> None:
        """Test assign_task when save assignment fails."""
        tmux = Mock(spec=TMUXManager)
        tmux.capture_pane.return_value = "Agent is active"
        tmux.send_keys.return_value = True

        request = AssignTaskRequest(task_id="task_001", agent_id="dev:0")

        with patch("tmux_orchestrator.server.tools.assign_task._save_assignment") as mock_save:
            mock_save.return_value = False

            result = assign_task(tmux, request)

            assert not result.success
            assert result.error_message is not None
            assert "Failed to save task assignment" in result.error_message

    def test_assign_task_send_message_fails(self) -> None:
        """Test assign_task when sending message fails."""
        tmux = Mock(spec=TMUXManager)
        tmux.capture_pane.return_value = "Agent is active"
        tmux.send_keys.return_value = False

        request = AssignTaskRequest(task_id="task_001", agent_id="dev:0")

        result = assign_task(tmux, request)

        assert not result.success
        assert result.error_message is not None
        assert "Failed to send assignment message" in result.error_message

    def test_get_agent_workload_successful(self) -> None:
        """Test successful agent workload retrieval."""
        request = AssignTaskRequest(agent_id="dev:0")

        with patch("tmux_orchestrator.server.tools.assign_task._load_agent_assignments") as mock_load:
            mock_assignments = [
                {
                    "task_id": "task_001",
                    "status": "in_progress",
                    "priority": "high",
                    "estimated_hours": 8,
                    "assigned_at": datetime.now().isoformat(),
                },
                {
                    "task_id": "task_002",
                    "status": "pending",
                    "priority": "medium",
                    "estimated_hours": 4,
                    "assigned_at": datetime.now().isoformat(),
                },
            ]
            mock_load.return_value = mock_assignments

            result = get_agent_workload(request)

            assert result.success
            assert result.agent_id == "dev:0"
            assert result.total_tasks == 2
            assert result.active_tasks == 1
            assert result.pending_tasks == 1
            assert result.total_estimated_hours == 12
            assert len(result.task_list) == 2

    def test_get_agent_workload_agent_not_found(self) -> None:
        """Test get_agent_workload when agent has no assignments."""
        request = AssignTaskRequest(agent_id="new:0")

        with patch("tmux_orchestrator.server.tools.assign_task._load_agent_assignments") as mock_load:
            mock_load.return_value = []

            result = get_agent_workload(request)

            assert result.success
            assert result.total_tasks == 0
            assert result.active_tasks == 0
            assert result.pending_tasks == 0
            assert result.total_estimated_hours == 0

    def test_list_available_agents_successful(self) -> None:
        """Test successful listing of available agents."""
        tmux = Mock(spec=TMUXManager)

        # Mock tmux list-sessions output
        tmux.list_sessions.return_value = [
            {"name": "dev", "created": "123", "attached": "1"},
            {"name": "qa", "created": "124", "attached": "0"},
            {"name": "pm", "created": "125", "attached": "1"},
        ]

        # Mock tmux list-windows for each session
        def mock_list_windows(session):
            if session == "dev":
                return [{"index": "0", "name": "main", "active": "1"}, {"index": "1", "name": "test", "active": "0"}]
            elif session == "qa":
                return [{"index": "0", "name": "main", "active": "1"}]
            elif session == "pm":
                return [{"index": "0", "name": "main", "active": "1"}]
            return []

        tmux.list_windows.side_effect = mock_list_windows

        # Mock agent accessibility
        tmux.capture_pane.return_value = "Agent is active"

        request = AssignTaskRequest()

        with patch("tmux_orchestrator.server.tools.assign_task._load_agent_assignments") as mock_load:

            def mock_load_assignments(agent_id):
                if agent_id == "dev:0":
                    return [{"task_id": "task_001", "status": "in_progress"}]
                return []

            mock_load.side_effect = mock_load_assignments

            result = list_available_agents(tmux, request)

            assert result.success
            assert len(result.available_agents) == 4  # dev:0, dev:1, qa:0, pm:0

            # Check workload info is included
            dev_0_agent = next(agent for agent in result.available_agents if agent["agent_id"] == "dev:0")
            assert dev_0_agent["active_tasks"] == 1
            assert dev_0_agent["load_score"] > 0

    def test_list_available_agents_with_role_filter(self) -> None:
        """Test listing agents filtered by role."""
        tmux = Mock(spec=TMUXManager)
        tmux.list_sessions.return_value = [
            {"name": "dev", "created": "123", "attached": "1"},
            {"name": "qa", "created": "124", "attached": "0"},
            {"name": "pm", "created": "125", "attached": "1"},
        ]
        tmux.list_windows.return_value = [{"index": "0", "name": "main", "active": "1"}]
        tmux.capture_pane.return_value = "Agent is active"

        request = AssignTaskRequest(required_skills=["python", "api"])

        with (
            patch("tmux_orchestrator.server.tools.assign_task._load_agent_assignments") as mock_load,
            patch("tmux_orchestrator.server.tools.assign_task._get_agent_skills") as mock_skills,
        ):
            mock_load.return_value = []
            mock_skills.side_effect = lambda agent_id: ["python", "api"] if "dev" in agent_id else ["testing"]

            result = list_available_agents(tmux, request)

            assert result.success
            # Only dev agents should match skill requirements
            dev_agents = [agent for agent in result.available_agents if agent["agent_id"].startswith("dev")]
            assert len(dev_agents) >= 1

    def test_reassign_task_successful(self) -> None:
        """Test successful task reassignment."""
        tmux = Mock(spec=TMUXManager)
        tmux.capture_pane.return_value = "Agent is active"
        tmux.send_keys.return_value = True

        request = AssignTaskRequest(
            task_id="task_001", agent_id="dev:1", reason="Load balancing - original agent overloaded"
        )

        with (
            patch("tmux_orchestrator.server.tools.assign_task._load_assignment") as mock_load,
            patch("tmux_orchestrator.server.tools.assign_task._save_assignment") as mock_save,
            patch("tmux_orchestrator.server.tools.assign_task._update_task_status") as mock_update,
        ):
            # Mock existing assignment
            existing_assignment = {
                "task_id": "task_001",
                "agent_id": "dev:0",
                "assigned_at": datetime.now().isoformat(),
                "status": "in_progress",
            }
            mock_load.return_value = existing_assignment
            mock_save.return_value = True
            mock_update.return_value = True

            result = reassign_task(tmux, request)

            assert result.success
            assert result.task_id == "task_001"
            assert result.assigned_agent == "dev:1"
            assert result.previous_agent == "dev:0"
            assert result.reason == "Load balancing - original agent overloaded"

    def test_reassign_task_not_found(self) -> None:
        """Test reassign_task when original task assignment not found."""
        tmux = Mock(spec=TMUXManager)
        request = AssignTaskRequest(task_id="nonexistent", agent_id="dev:1")

        with patch("tmux_orchestrator.server.tools.assign_task._load_assignment") as mock_load:
            mock_load.return_value = None

            result = reassign_task(tmux, request)

            assert not result.success
            assert result.error_message is not None
            assert "Task assignment 'nonexistent' not found" in result.error_message

    def test_assign_task_invalid_priority(self) -> None:
        """Test assign_task with invalid priority."""
        tmux = Mock(spec=TMUXManager)
        request = AssignTaskRequest(task_id="task_001", agent_id="dev:0", priority="invalid")

        result = assign_task(tmux, request)

        assert not result.success
        assert result.error_message is not None
        assert "Invalid priority 'invalid'" in result.error_message

    @pytest.mark.parametrize(
        "priority",
        ["low", "medium", "high", "critical"],
    )
    def test_assign_task_all_valid_priorities(self, priority: str) -> None:
        """Test assign_task accepts all valid priority levels."""
        tmux = Mock(spec=TMUXManager)
        tmux.capture_pane.return_value = "Agent is active"
        tmux.send_keys.return_value = True

        request = AssignTaskRequest(task_id="task_001", agent_id="dev:0", priority=priority)

        with (
            patch("tmux_orchestrator.server.tools.assign_task._save_assignment") as mock_save,
            patch("tmux_orchestrator.server.tools.assign_task._update_task_status") as mock_update,
        ):
            mock_save.return_value = True
            mock_update.return_value = True

            result = assign_task(tmux, request)

            assert result.success
            assert result.priority == priority

    def test_assign_task_with_completion_criteria(self) -> None:
        """Test task assignment with completion criteria."""
        tmux = Mock(spec=TMUXManager)
        tmux.capture_pane.return_value = "Agent is active"
        tmux.send_keys.return_value = True

        request = AssignTaskRequest(
            task_id="task_001",
            agent_id="dev:0",
            completion_criteria=["All unit tests pass", "Code review approved", "Documentation updated"],
        )

        with (
            patch("tmux_orchestrator.server.tools.assign_task._save_assignment") as mock_save,
            patch("tmux_orchestrator.server.tools.assign_task._update_task_status") as mock_update,
        ):
            mock_save.return_value = True
            mock_update.return_value = True

            result = assign_task(tmux, request)

            assert result.success
            assert result.completion_criteria == [
                "All unit tests pass",
                "Code review approved",
                "Documentation updated",
            ]

            # Verify criteria are included in assignment message
            call_args = tmux.send_keys.call_args[0]
            message = call_args[1]
            assert "COMPLETION CRITERIA:" in message
            assert "unit tests pass" in message

    def test_assign_task_exception_handling(self) -> None:
        """Test assign_task handles unexpected exceptions."""
        tmux = Mock(spec=TMUXManager)
        tmux.capture_pane.side_effect = Exception("Connection error")

        request = AssignTaskRequest(task_id="task_001", agent_id="dev:0")

        result = assign_task(tmux, request)

        assert not result.success
        assert result.error_message is not None
        assert "Unexpected error during task assignment" in result.error_message

    def test_assign_task_load_balancing_metadata(self) -> None:
        """Test assign_task includes load balancing metadata."""
        tmux = Mock(spec=TMUXManager)
        tmux.capture_pane.return_value = "Agent is active"
        tmux.send_keys.return_value = True

        request = AssignTaskRequest(task_id="task_001", agent_id="dev:0", load_balance=True)

        with (
            patch("tmux_orchestrator.server.tools.assign_task._save_assignment") as mock_save,
            patch("tmux_orchestrator.server.tools.assign_task._update_task_status") as mock_update,
            patch("tmux_orchestrator.server.tools.assign_task._calculate_load_score") as mock_load_score,
        ):
            mock_save.return_value = True
            mock_update.return_value = True
            mock_load_score.return_value = 0.3

            result = assign_task(tmux, request)

            assert result.success
            assert result.assignment_metadata is not None

            metadata = result.assignment_metadata
            assert "assigned_at" in metadata
            assert "load_balanced" in metadata
            assert metadata["load_balanced"] is True
            assert "load_score" in metadata
            assert metadata["load_score"] == 0.3

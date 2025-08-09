"""Tests for get_agent_status business logic tool."""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tmux_orchestrator.server.tools.get_agent_status import (
    AgentHealthMetrics,
    AgentStatusRequest,
    AgentStatusResult,
    HealthStatus,
    get_agent_status,
)
from tmux_orchestrator.server.tools.report_activity import ActivityType


@pytest.fixture
def mock_tmux():
    """Create a mock TMUXManager for testing."""
    mock = MagicMock()

    # Mock list_agents with default agents
    mock.list_agents.return_value = [
        {
            "session": "frontend-project",
            "window": "0",
            "type": "Frontend",
            "status": "Active",
        },
        {
            "session": "backend-project",
            "window": "1",
            "type": "Backend",
            "status": "Idle",
        },
        {
            "session": "team-alpha",
            "window": "2",
            "type": "PM",
            "status": "Active",
        },
    ]

    # Mock capture_pane with default response
    mock.capture_pane.return_value = "Agent working on feature implementation..."

    return mock


@pytest.fixture
def temp_activity_file():
    """Create a temporary activity file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        temp_path = Path(f.name)
        # Initialize empty activity file
        json.dump([], f)
    yield temp_path
    # Clean up
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def sample_activity_data():
    """Create sample activity records for testing."""
    base_time = datetime.now()
    return [
        {
            "record_id": "rec-001",
            "agent_id": "frontend-project:0",
            "activity_type": "working",
            "description": "Implementing user dashboard",
            "timestamp": (base_time - timedelta(minutes=5)).isoformat(),
            "session_id": "frontend-project",
            "team_id": "team-alpha",
            "tags": ["ui", "feature"],
            "metadata": {"priority": "high"},
        },
        {
            "record_id": "rec-002",
            "agent_id": "backend-project:1",
            "activity_type": "idle",
            "description": "Waiting for next task",
            "timestamp": (base_time - timedelta(minutes=30)).isoformat(),
            "session_id": "backend-project",
            "team_id": "team-alpha",
            "tags": [],
            "metadata": {},
        },
        {
            "record_id": "rec-003",
            "agent_id": "team-alpha:2",
            "activity_type": "blocked",
            "description": "Waiting for API approval",
            "timestamp": (base_time - timedelta(hours=2)).isoformat(),
            "session_id": "team-alpha",
            "team_id": "team-alpha",
            "tags": ["blocked", "api"],
            "metadata": {"blocked_by": "external_approval"},
        },
    ]


class TestHealthStatus:
    """Test HealthStatus enum."""

    def test_health_status_values(self):
        """Test all required health status types are defined."""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.IDLE.value == "idle"
        assert HealthStatus.BLOCKED.value == "blocked"
        assert HealthStatus.OFFLINE.value == "offline"
        assert HealthStatus.UNRESPONSIVE.value == "unresponsive"
        assert HealthStatus.DEGRADED.value == "degraded"


class TestAgentHealthMetrics:
    """Test AgentHealthMetrics dataclass."""

    def test_agent_health_metrics_minimal(self):
        """Test AgentHealthMetrics with minimal required fields."""
        metrics = AgentHealthMetrics(
            agent_id="test-agent",
            health_status=HealthStatus.HEALTHY,
            session_active=True,
        )

        assert metrics.agent_id == "test-agent"
        assert metrics.health_status == HealthStatus.HEALTHY
        assert metrics.session_active is True
        assert metrics.last_activity_time is None
        assert metrics.last_activity_type is None
        assert metrics.last_activity_description is None
        assert metrics.responsiveness_score is None
        assert metrics.session_info == {}
        assert metrics.team_id is None
        assert metrics.activity_tags == []

    def test_agent_health_metrics_full(self):
        """Test AgentHealthMetrics with all fields."""
        last_activity = datetime.now() - timedelta(minutes=10)

        metrics = AgentHealthMetrics(
            agent_id="pm-agent:123",
            health_status=HealthStatus.BLOCKED,
            session_active=True,
            last_activity_time=last_activity,
            last_activity_type=ActivityType.BLOCKED,
            last_activity_description="Waiting for code review",
            responsiveness_score=0.7,
            session_info={"session": "team-alpha", "window": "2", "type": "PM"},
            team_id="team-alpha",
            activity_tags=["blocked", "code-review"],
        )

        assert metrics.agent_id == "pm-agent:123"
        assert metrics.health_status == HealthStatus.BLOCKED
        assert metrics.session_active is True
        assert metrics.last_activity_time == last_activity
        assert metrics.last_activity_type == ActivityType.BLOCKED
        assert metrics.last_activity_description == "Waiting for code review"
        assert metrics.responsiveness_score == 0.7
        assert metrics.session_info == {"session": "team-alpha", "window": "2", "type": "PM"}
        assert metrics.team_id == "team-alpha"
        assert metrics.activity_tags == ["blocked", "code-review"]


class TestAgentStatusRequest:
    """Test AgentStatusRequest dataclass."""

    def test_agent_status_request_single_agent(self):
        """Test AgentStatusRequest for single agent by agent_id."""
        request = AgentStatusRequest(agent_id="frontend-project:0")

        assert request.agent_id == "frontend-project:0"
        assert request.target is None
        assert request.team_id is None
        assert request.include_activity_history is False
        assert request.activity_limit == 10

    def test_agent_status_request_by_target(self):
        """Test AgentStatusRequest by session:window target."""
        request = AgentStatusRequest(target="team-alpha:2")

        assert request.agent_id is None
        assert request.target == "team-alpha:2"
        assert request.team_id is None
        assert request.include_activity_history is False
        assert request.activity_limit == 10

    def test_agent_status_request_team_health_check(self):
        """Test AgentStatusRequest for team health check."""
        request = AgentStatusRequest(team_id="team-alpha", include_activity_history=True, activity_limit=25)

        assert request.agent_id is None
        assert request.target is None
        assert request.team_id == "team-alpha"
        assert request.include_activity_history is True
        assert request.activity_limit == 25

    def test_agent_status_request_post_init_defaults(self):
        """Test that __post_init__ sets default values correctly."""
        request = AgentStatusRequest()

        assert request.agent_id is None
        assert request.target is None
        assert request.team_id is None
        assert request.include_activity_history is False
        assert request.activity_limit == 10


class TestAgentStatusResult:
    """Test AgentStatusResult dataclass."""

    def test_agent_status_result_success_single(self):
        """Test successful AgentStatusResult for single agent."""
        metrics = AgentHealthMetrics(
            agent_id="test-agent",
            health_status=HealthStatus.HEALTHY,
            session_active=True,
        )

        result = AgentStatusResult(
            success=True,
            agent_metrics=[metrics],
        )

        assert result.success is True
        assert len(result.agent_metrics) == 1
        assert result.agent_metrics[0].agent_id == "test-agent"
        assert result.error_message is None
        assert result.total_agents == 0

    def test_agent_status_result_failure(self):
        """Test failed AgentStatusResult."""
        result = AgentStatusResult(
            success=False,
            agent_metrics=[],
            error_message="Agent not found",
        )

        assert result.success is False
        assert result.agent_metrics == []
        assert result.error_message == "Agent not found"
        assert result.total_agents == 0

    def test_agent_status_result_team_health(self):
        """Test AgentStatusResult for team health check."""
        metrics1 = AgentHealthMetrics(
            agent_id="agent-1",
            health_status=HealthStatus.HEALTHY,
            session_active=True,
        )
        metrics2 = AgentHealthMetrics(
            agent_id="agent-2",
            health_status=HealthStatus.IDLE,
            session_active=True,
        )

        result = AgentStatusResult(
            success=True,
            agent_metrics=[metrics1, metrics2],
            total_agents=2,
        )

        assert result.success is True
        assert len(result.agent_metrics) == 2
        assert result.total_agents == 2
        assert result.error_message is None


class TestGetAgentStatus:
    """Test get_agent_status function."""

    def test_get_agent_status_invalid_no_criteria(self, mock_tmux, temp_activity_file):
        """Test get_agent_status with no search criteria."""
        request = AgentStatusRequest()

        with patch(
            "tmux_orchestrator.server.tools.get_agent_status._get_activity_file_path", return_value=temp_activity_file
        ):
            result = get_agent_status(mock_tmux, request)

        assert not result.success
        assert result.error_message == "Must specify agent_id, target, or team_id"
        assert result.agent_metrics == []

    def test_get_agent_status_invalid_multiple_criteria(self, mock_tmux, temp_activity_file):
        """Test get_agent_status with multiple conflicting criteria."""
        request = AgentStatusRequest(agent_id="test-agent", target="session:window", team_id="team-alpha")

        with patch(
            "tmux_orchestrator.server.tools.get_agent_status._get_activity_file_path", return_value=temp_activity_file
        ):
            result = get_agent_status(mock_tmux, request)

        assert not result.success
        assert result.error_message == "Only one of agent_id, target, or team_id can be specified"

    def test_get_agent_status_invalid_agent_id_empty(self, mock_tmux, temp_activity_file):
        """Test get_agent_status with empty agent_id."""
        request = AgentStatusRequest(agent_id="")

        with patch(
            "tmux_orchestrator.server.tools.get_agent_status._get_activity_file_path", return_value=temp_activity_file
        ):
            result = get_agent_status(mock_tmux, request)

        assert not result.success
        assert result.error_message == "Agent ID cannot be empty"

    def test_get_agent_status_invalid_target_format(self, mock_tmux, temp_activity_file):
        """Test get_agent_status with invalid target format."""
        request = AgentStatusRequest(target="invalid-target-format")

        with patch(
            "tmux_orchestrator.server.tools.get_agent_status._get_activity_file_path", return_value=temp_activity_file
        ):
            result = get_agent_status(mock_tmux, request)

        assert not result.success
        assert result.error_message == "Target must be in format 'session:window'"

    def test_get_agent_status_single_agent_by_id_success(self, mock_tmux, temp_activity_file, sample_activity_data):
        """Test successful agent status retrieval by agent_id."""
        # Setup activity file with sample data
        with open(temp_activity_file, "w") as f:
            json.dump(sample_activity_data, f)

        request = AgentStatusRequest(agent_id="frontend-project:0")

        with patch(
            "tmux_orchestrator.server.tools.get_agent_status._get_activity_file_path", return_value=temp_activity_file
        ):
            result = get_agent_status(mock_tmux, request)

        assert result.success
        assert len(result.agent_metrics) == 1

        metrics = result.agent_metrics[0]
        assert metrics.agent_id == "frontend-project:0"
        assert metrics.health_status == HealthStatus.HEALTHY
        assert metrics.session_active is True
        assert metrics.last_activity_type == ActivityType.WORKING
        assert metrics.last_activity_description == "Implementing user dashboard"
        assert metrics.team_id == "team-alpha"
        assert "ui" in metrics.activity_tags
        assert "feature" in metrics.activity_tags

    def test_get_agent_status_single_agent_by_target_success(self, mock_tmux, temp_activity_file, sample_activity_data):
        """Test successful agent status retrieval by target."""
        # Setup activity file with sample data
        with open(temp_activity_file, "w") as f:
            json.dump(sample_activity_data, f)

        request = AgentStatusRequest(target="backend-project:1")

        with patch(
            "tmux_orchestrator.server.tools.get_agent_status._get_activity_file_path", return_value=temp_activity_file
        ):
            result = get_agent_status(mock_tmux, request)

        assert result.success
        assert len(result.agent_metrics) == 1

        metrics = result.agent_metrics[0]
        assert metrics.agent_id == "backend-project:1"
        assert metrics.health_status == HealthStatus.IDLE
        assert metrics.session_active is True
        assert metrics.last_activity_type == ActivityType.IDLE
        assert metrics.last_activity_description == "Waiting for next task"

    def test_get_agent_status_agent_not_found(self, mock_tmux, temp_activity_file):
        """Test get_agent_status when agent is not found."""
        request = AgentStatusRequest(agent_id="nonexistent-agent")

        # Mock list_agents to return empty list
        mock_tmux.list_agents.return_value = []

        with patch(
            "tmux_orchestrator.server.tools.get_agent_status._get_activity_file_path", return_value=temp_activity_file
        ):
            result = get_agent_status(mock_tmux, request)

        assert not result.success
        assert result.error_message == "Agent 'nonexistent-agent' not found"
        assert result.agent_metrics == []

    def test_get_agent_status_offline_agent(self, mock_tmux, temp_activity_file, sample_activity_data):
        """Test get_agent_status for agent that exists in activity but not in active sessions."""
        # Setup activity file with sample data
        with open(temp_activity_file, "w") as f:
            json.dump(sample_activity_data, f)

        # Mock list_agents to exclude the agent we're looking for
        mock_tmux.list_agents.return_value = [
            {
                "session": "other-session",
                "window": "0",
                "type": "Other",
                "status": "Active",
            }
        ]

        request = AgentStatusRequest(agent_id="frontend-project:0")

        with patch(
            "tmux_orchestrator.server.tools.get_agent_status._get_activity_file_path", return_value=temp_activity_file
        ):
            result = get_agent_status(mock_tmux, request)

        assert result.success
        assert len(result.agent_metrics) == 1

        metrics = result.agent_metrics[0]
        assert metrics.agent_id == "frontend-project:0"
        assert metrics.health_status == HealthStatus.OFFLINE
        assert metrics.session_active is False
        # Should still have activity data
        assert metrics.last_activity_type == ActivityType.WORKING

    def test_get_agent_status_team_health_check(self, mock_tmux, temp_activity_file, sample_activity_data):
        """Test get_agent_status for team health check."""
        # Setup activity file with sample data
        with open(temp_activity_file, "w") as f:
            json.dump(sample_activity_data, f)

        request = AgentStatusRequest(team_id="team-alpha")

        with patch(
            "tmux_orchestrator.server.tools.get_agent_status._get_activity_file_path", return_value=temp_activity_file
        ):
            result = get_agent_status(mock_tmux, request)

        assert result.success
        assert len(result.agent_metrics) == 3  # All agents in team-alpha
        assert result.total_agents == 3

        # Check that we got all team members
        agent_ids = {metrics.agent_id for metrics in result.agent_metrics}
        expected_ids = {"frontend-project:0", "backend-project:1", "team-alpha:2"}
        assert agent_ids == expected_ids

        # Verify health statuses are correct
        health_statuses = {metrics.agent_id: metrics.health_status for metrics in result.agent_metrics}
        assert health_statuses["frontend-project:0"] == HealthStatus.HEALTHY
        assert health_statuses["backend-project:1"] == HealthStatus.IDLE
        assert health_statuses["team-alpha:2"] == HealthStatus.BLOCKED

    def test_get_agent_status_blocked_agent_from_activity(self, mock_tmux, temp_activity_file, sample_activity_data):
        """Test get_agent_status correctly identifies blocked agents from activity."""
        # Setup activity file with sample data
        with open(temp_activity_file, "w") as f:
            json.dump(sample_activity_data, f)

        request = AgentStatusRequest(agent_id="team-alpha:2")

        with patch(
            "tmux_orchestrator.server.tools.get_agent_status._get_activity_file_path", return_value=temp_activity_file
        ):
            result = get_agent_status(mock_tmux, request)

        assert result.success
        assert len(result.agent_metrics) == 1

        metrics = result.agent_metrics[0]
        assert metrics.agent_id == "team-alpha:2"
        assert metrics.health_status == HealthStatus.BLOCKED
        assert metrics.last_activity_type == ActivityType.BLOCKED
        assert metrics.last_activity_description == "Waiting for API approval"
        assert "blocked" in metrics.activity_tags
        assert "api" in metrics.activity_tags

    def test_get_agent_status_unresponsive_agent(self, mock_tmux, temp_activity_file):
        """Test get_agent_status identifies unresponsive agents."""
        # Create activity data with old timestamp
        old_activity = [
            {
                "record_id": "rec-001",
                "agent_id": "stale-agent:0",
                "activity_type": "working",
                "description": "Last seen hours ago",
                "timestamp": (datetime.now() - timedelta(hours=6)).isoformat(),
                "session_id": "stale-agent",
                "team_id": "team-alpha",
                "tags": [],
                "metadata": {},
            }
        ]

        with open(temp_activity_file, "w") as f:
            json.dump(old_activity, f)

        # Mock list_agents to show agent as active in tmux
        mock_tmux.list_agents.return_value = [
            {
                "session": "stale-agent",
                "window": "0",
                "type": "Developer",
                "status": "Active",
            }
        ]

        request = AgentStatusRequest(agent_id="stale-agent:0")

        with patch(
            "tmux_orchestrator.server.tools.get_agent_status._get_activity_file_path", return_value=temp_activity_file
        ):
            result = get_agent_status(mock_tmux, request)

        assert result.success
        assert len(result.agent_metrics) == 1

        metrics = result.agent_metrics[0]
        assert metrics.agent_id == "stale-agent:0"
        assert metrics.health_status == HealthStatus.UNRESPONSIVE
        assert metrics.session_active is True

    def test_get_agent_status_include_activity_history(self, mock_tmux, temp_activity_file):
        """Test get_agent_status with activity history included."""
        # Create multiple activity records for same agent
        base_time = datetime.now()
        activity_records = []

        for i in range(5):
            record = {
                "record_id": f"rec-{i:03d}",
                "agent_id": "busy-agent:0",
                "activity_type": "working",
                "description": f"Task {i + 1}",
                "timestamp": (base_time - timedelta(minutes=i * 10)).isoformat(),
                "session_id": "busy-project",
                "team_id": "team-alpha",
                "tags": [f"task-{i + 1}"],
                "metadata": {},
            }
            activity_records.append(record)

        with open(temp_activity_file, "w") as f:
            json.dump(activity_records, f)

        request = AgentStatusRequest(agent_id="busy-agent:0", include_activity_history=True, activity_limit=3)

        with patch(
            "tmux_orchestrator.server.tools.get_agent_status._get_activity_file_path", return_value=temp_activity_file
        ):
            result = get_agent_status(mock_tmux, request)

        assert result.success
        assert len(result.agent_metrics) == 1

        metrics = result.agent_metrics[0]
        assert hasattr(metrics, "activity_history")
        # Should have limited to 3 records as requested
        assert len(metrics.activity_history) == 3

    def test_get_agent_status_responsiveness_score_calculation(self, mock_tmux, temp_activity_file):
        """Test responsiveness score calculation based on activity frequency."""
        # Create recent activity records (high responsiveness)
        base_time = datetime.now()
        recent_activities = []

        # 10 activities in last hour (high responsiveness)
        for i in range(10):
            record = {
                "record_id": f"rec-{i:03d}",
                "agent_id": "responsive-agent:0",
                "activity_type": "working",
                "description": f"Task {i + 1}",
                "timestamp": (base_time - timedelta(minutes=i * 5)).isoformat(),
                "session_id": "active-project",
                "team_id": "team-alpha",
                "tags": [],
                "metadata": {},
            }
            recent_activities.append(record)

        with open(temp_activity_file, "w") as f:
            json.dump(recent_activities, f)

        request = AgentStatusRequest(agent_id="responsive-agent:0")

        with patch(
            "tmux_orchestrator.server.tools.get_agent_status._get_activity_file_path", return_value=temp_activity_file
        ):
            result = get_agent_status(mock_tmux, request)

        assert result.success
        metrics = result.agent_metrics[0]
        # Should have a high responsiveness score due to frequent activity
        assert metrics.responsiveness_score is not None
        assert metrics.responsiveness_score > 0.7  # High responsiveness

    def test_get_agent_status_degraded_health_from_tmux_status(
        self, mock_tmux, temp_activity_file, sample_activity_data
    ):
        """Test agent health marked as degraded based on tmux status."""
        # Setup activity file with sample data
        with open(temp_activity_file, "w") as f:
            json.dump(sample_activity_data, f)

        # Mock list_agents to show agent with concerning status
        mock_tmux.list_agents.return_value = [
            {
                "session": "frontend-project",
                "window": "0",
                "type": "Frontend",
                "status": "Degraded",  # Custom status indicating issues
            }
        ]

        request = AgentStatusRequest(agent_id="frontend-project:0")

        with patch(
            "tmux_orchestrator.server.tools.get_agent_status._get_activity_file_path", return_value=temp_activity_file
        ):
            result = get_agent_status(mock_tmux, request)

        assert result.success
        metrics = result.agent_metrics[0]
        # Health should be degraded due to tmux status
        assert metrics.health_status == HealthStatus.DEGRADED

    def test_get_agent_status_file_permission_error(self, mock_tmux, temp_activity_file):
        """Test get_agent_status handles file permission errors."""
        request = AgentStatusRequest(agent_id="test-agent")

        # Mock file operations to raise PermissionError
        with patch(
            "tmux_orchestrator.server.tools.get_agent_status._get_activity_file_path", return_value=temp_activity_file
        ):
            with patch("builtins.open", side_effect=PermissionError("Access denied")):
                result = get_agent_status(mock_tmux, request)

        assert not result.success
        assert "Permission denied" in result.error_message
        assert result.agent_metrics == []

    def test_get_agent_status_json_decode_error(self, mock_tmux, temp_activity_file):
        """Test get_agent_status handles JSON decode errors gracefully."""
        # Write invalid JSON to file
        with open(temp_activity_file, "w") as f:
            f.write("invalid json content")

        request = AgentStatusRequest(agent_id="test-agent")

        with patch(
            "tmux_orchestrator.server.tools.get_agent_status._get_activity_file_path", return_value=temp_activity_file
        ):
            result = get_agent_status(mock_tmux, request)

        assert not result.success
        assert "Invalid JSON" in result.error_message or "JSON" in result.error_message
        assert result.agent_metrics == []

    def test_get_agent_status_unexpected_error(self, mock_tmux, temp_activity_file):
        """Test get_agent_status handles unexpected errors."""
        request = AgentStatusRequest(agent_id="test-agent")

        # Mock to raise unexpected exception during tmux operations
        with patch(
            "tmux_orchestrator.server.tools.get_agent_status._get_activity_file_path", return_value=temp_activity_file
        ):
            mock_tmux.list_agents.side_effect = RuntimeError("Unexpected tmux error")
            result = get_agent_status(mock_tmux, request)

        assert not result.success
        assert "Unexpected error" in result.error_message
        assert result.agent_metrics == []

    def test_get_agent_status_activity_file_not_exist(self, mock_tmux):
        """Test get_agent_status when activity file doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file = Path(temp_dir) / "nonexistent.json"

            request = AgentStatusRequest(agent_id="frontend-project:0")

            with patch(
                "tmux_orchestrator.server.tools.get_agent_status._get_activity_file_path", return_value=temp_file
            ):
                result = get_agent_status(mock_tmux, request)

            # Should still succeed but with no activity data
            assert result.success
            assert len(result.agent_metrics) == 1

            metrics = result.agent_metrics[0]
            assert metrics.last_activity_time is None
            assert metrics.last_activity_type is None

    def test_get_agent_status_mixed_health_states_team(self, mock_tmux, temp_activity_file):
        """Test team health check with agents in various health states."""
        # Create activity data showing different health states
        base_time = datetime.now()
        mixed_activities = [
            # Healthy agent - recent activity
            {
                "record_id": "rec-001",
                "agent_id": "healthy-agent:0",
                "activity_type": "working",
                "description": "Active development",
                "timestamp": (base_time - timedelta(minutes=5)).isoformat(),
                "session_id": "healthy-agent",
                "team_id": "mixed-team",
                "tags": [],
                "metadata": {},
            },
            # Blocked agent
            {
                "record_id": "rec-002",
                "agent_id": "blocked-agent:1",
                "activity_type": "blocked",
                "description": "Waiting for dependency",
                "timestamp": (base_time - timedelta(minutes=15)).isoformat(),
                "session_id": "blocked-agent",
                "team_id": "mixed-team",
                "tags": ["blocked"],
                "metadata": {},
            },
            # Unresponsive agent - very old activity
            {
                "record_id": "rec-003",
                "agent_id": "stale-agent:2",
                "activity_type": "working",
                "description": "Last activity hours ago",
                "timestamp": (base_time - timedelta(hours=8)).isoformat(),
                "session_id": "stale-agent",
                "team_id": "mixed-team",
                "tags": [],
                "metadata": {},
            },
        ]

        with open(temp_activity_file, "w") as f:
            json.dump(mixed_activities, f)

        # Mock agents in tmux (all active)
        mock_tmux.list_agents.return_value = [
            {"session": "healthy-agent", "window": "0", "type": "Developer", "status": "Active"},
            {"session": "blocked-agent", "window": "1", "type": "Developer", "status": "Active"},
            {"session": "stale-agent", "window": "2", "type": "Developer", "status": "Active"},
        ]

        request = AgentStatusRequest(team_id="mixed-team")

        with patch(
            "tmux_orchestrator.server.tools.get_agent_status._get_activity_file_path", return_value=temp_activity_file
        ):
            result = get_agent_status(mock_tmux, request)

        assert result.success
        assert len(result.agent_metrics) == 3
        assert result.total_agents == 3

        # Organize results by agent_id for easier testing
        metrics_by_id = {m.agent_id: m for m in result.agent_metrics}

        # Healthy agent
        healthy = metrics_by_id["healthy-agent:0"]
        assert healthy.health_status == HealthStatus.HEALTHY

        # Blocked agent
        blocked = metrics_by_id["blocked-agent:1"]
        assert blocked.health_status == HealthStatus.BLOCKED

        # Unresponsive agent
        unresponsive = metrics_by_id["stale-agent:2"]
        assert unresponsive.health_status == HealthStatus.UNRESPONSIVE

    def test_get_agent_status_empty_team(self, mock_tmux, temp_activity_file):
        """Test team health check when no agents belong to team."""
        request = AgentStatusRequest(team_id="empty-team")

        # Mock no agents for this team
        mock_tmux.list_agents.return_value = [
            {"session": "other-project", "window": "0", "type": "Developer", "status": "Active"},
        ]

        with patch(
            "tmux_orchestrator.server.tools.get_agent_status._get_activity_file_path", return_value=temp_activity_file
        ):
            result = get_agent_status(mock_tmux, request)

        assert result.success
        assert len(result.agent_metrics) == 0
        assert result.total_agents == 0

"""Basic tests for get_agent_status - models, validation, and error handling."""

from datetime import datetime, timedelta
from unittest.mock import patch

from tmux_orchestrator.server.tools.get_agent_status import (
    AgentHealthMetrics,
    AgentStatusRequest,
    AgentStatusResult,
    HealthStatus,
    get_agent_status,
)
from tmux_orchestrator.server.tools.report_activity import ActivityType


def test_health_status_values() -> None:
    """Test all health status values are defined."""
    assert HealthStatus.HEALTHY.value == "healthy"
    assert HealthStatus.DEGRADED.value == "degraded"
    assert HealthStatus.IDLE.value == "idle"
    assert HealthStatus.BLOCKED.value == "blocked"
    assert HealthStatus.OFFLINE.value == "offline"
    assert HealthStatus.UNRESPONSIVE.value == "unresponsive"


def test_agent_health_metrics_minimal() -> None:
    """Test AgentHealthMetrics with minimal fields."""
    metrics = AgentHealthMetrics(
        agent_id="test-agent:0",
        health_status=HealthStatus.HEALTHY,
        session_active=True,
    )

    assert metrics.agent_id == "test-agent:0"
    assert metrics.health_status == HealthStatus.HEALTHY
    assert metrics.session_active is True
    assert metrics.last_activity_time is None
    assert metrics.last_activity_type is None
    assert metrics.last_activity_description is None
    assert metrics.responsiveness_score is None


def test_agent_health_metrics_full() -> None:
    """Test AgentHealthMetrics with all fields."""
    activity_time = datetime.now() - timedelta(minutes=5)
    metrics = AgentHealthMetrics(
        agent_id="test-agent:0",
        health_status=HealthStatus.DEGRADED,
        session_active=True,
        last_activity_time=activity_time,
        last_activity_type=ActivityType.WORKING,
        last_activity_description="Debugging test failures",
        responsiveness_score=0.6,
        session_info={"status": "Active"},
        team_id="team-alpha",
        activity_tags=["debugging", "tests"],
    )

    assert metrics.agent_id == "test-agent:0"
    assert metrics.health_status == HealthStatus.DEGRADED
    assert metrics.session_active is True
    assert metrics.last_activity_time == activity_time
    assert metrics.last_activity_type == ActivityType.WORKING
    assert metrics.last_activity_description == "Debugging test failures"
    assert metrics.responsiveness_score == 0.6
    assert metrics.session_info == {"status": "Active"}
    assert metrics.team_id == "team-alpha"
    assert metrics.activity_tags == ["debugging", "tests"]


def test_agent_status_request_single_agent() -> None:
    """Test AgentStatusRequest for single agent by ID."""
    request = AgentStatusRequest(agent_id="frontend-dev:0")

    assert request.agent_id == "frontend-dev:0"
    assert request.target is None
    assert request.team_id is None
    assert request.include_activity_history is False


def test_agent_status_request_by_target() -> None:
    """Test AgentStatusRequest for agent by target."""
    request = AgentStatusRequest(target="backend-project:1")

    assert request.agent_id is None
    assert request.target == "backend-project:1"
    assert request.team_id is None
    assert request.include_activity_history is False


def test_agent_status_request_team_health_check() -> None:
    """Test AgentStatusRequest for team health check."""
    request = AgentStatusRequest(team_id="team-alpha")

    assert request.agent_id is None
    assert request.target is None
    assert request.team_id == "team-alpha"
    assert request.include_activity_history is False


def test_agent_status_request_post_init_defaults() -> None:
    """Test AgentStatusRequest post_init sets defaults."""
    request = AgentStatusRequest(agent_id="test:0", include_activity_history=True)

    # Post-init should set include_activity_history to True when specified
    assert request.include_activity_history is True


def test_agent_status_result_success_single() -> None:
    """Test AgentStatusResult for successful single agent query."""
    health_metrics = AgentHealthMetrics(
        agent_id="frontend:0",
        health_status=HealthStatus.HEALTHY,
        session_active=True,
        last_activity_description="Working on task",
    )

    result = AgentStatusResult(
        success=True,
        agent_metrics=[health_metrics],
        total_agents=1,
    )

    assert result.success is True
    assert len(result.agent_metrics) == 1
    assert result.agent_metrics[0] == health_metrics
    assert result.total_agents == 1
    assert result.error_message is None


def test_agent_status_result_failure() -> None:
    """Test AgentStatusResult for failure case."""
    result = AgentStatusResult(
        success=False,
        agent_metrics=[],
        error_message="Agent not found",
    )

    assert result.success is False
    assert result.error_message == "Agent not found"
    assert len(result.agent_metrics) == 0
    assert result.total_agents == 0


def test_agent_status_result_team_health() -> None:
    """Test AgentStatusResult for team health check."""
    team_metrics = [
        AgentHealthMetrics(
            agent_id="frontend:0",
            health_status=HealthStatus.HEALTHY,
            session_active=True,
        ),
        AgentHealthMetrics(
            agent_id="backend:1",
            health_status=HealthStatus.DEGRADED,
            session_active=True,
        ),
        AgentHealthMetrics(
            agent_id="qa:2",
            health_status=HealthStatus.OFFLINE,
            session_active=False,
        ),
    ]

    result = AgentStatusResult(
        success=True,
        agent_metrics=team_metrics,
        total_agents=3,
    )

    assert result.success is True
    assert len(result.agent_metrics) == 3
    assert result.total_agents == 3
    # Verify each agent's health status
    health_map = {m.agent_id: m.health_status for m in result.agent_metrics}
    assert health_map["frontend:0"] == HealthStatus.HEALTHY
    assert health_map["backend:1"] == HealthStatus.DEGRADED
    assert health_map["qa:2"] == HealthStatus.OFFLINE


def test_get_agent_status_invalid_no_criteria(mock_tmux, temp_activity_file) -> None:
    """Test get_agent_status with no criteria specified."""
    request = AgentStatusRequest()

    with patch(
        "tmux_orchestrator.server.tools.get_agent_status._get_activity_file_path", return_value=temp_activity_file
    ):
        result = get_agent_status(mock_tmux, request)

    assert result.success is False
    assert "Must specify agent_id, target, or team_id" in result.error_message


def test_get_agent_status_invalid_multiple_criteria(mock_tmux, temp_activity_file) -> None:
    """Test get_agent_status with multiple criteria specified."""
    request = AgentStatusRequest(agent_id="test:0", target="test:0", team_id="team-alpha")

    with patch(
        "tmux_orchestrator.server.tools.get_agent_status._get_activity_file_path", return_value=temp_activity_file
    ):
        result = get_agent_status(mock_tmux, request)

    assert result.success is False
    assert "Only one of" in result.error_message


def test_get_agent_status_invalid_agent_id_empty(mock_tmux, temp_activity_file) -> None:
    """Test get_agent_status with empty agent_id."""
    request = AgentStatusRequest(agent_id="")

    with patch(
        "tmux_orchestrator.server.tools.get_agent_status._get_activity_file_path", return_value=temp_activity_file
    ):
        result = get_agent_status(mock_tmux, request)

    assert result.success is False
    assert "Agent ID cannot be empty" in result.error_message


def test_get_agent_status_invalid_target_format(mock_tmux, temp_activity_file) -> None:
    """Test get_agent_status with invalid target format."""
    request = AgentStatusRequest(target="invalid-target")

    with patch(
        "tmux_orchestrator.server.tools.get_agent_status._get_activity_file_path", return_value=temp_activity_file
    ):
        result = get_agent_status(mock_tmux, request)

    assert result.success is False
    assert "Target must be in format 'session:window'" in result.error_message

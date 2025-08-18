"""Edge case tests for report_activity - error handling and boundary conditions."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from tmux_orchestrator.server.tools.report_activity import (
    ActivityHistoryRequest,
    ActivityType,
    ReportActivityRequest,
    get_activity_history,
    report_activity,
)


def test_report_activity_file_not_exist(mock_tmux) -> None:
    """Test report_activity creates new file if it doesn't exist."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_file = Path(temp_dir) / "new_activity.json"

        request = ReportActivityRequest(
            agent_id="test-agent", activity_type=ActivityType.WORKING, description="First activity"
        )

        with patch("tmux_orchestrator.server.tools.report_activity._get_activity_file_path", return_value=temp_file):
            result = report_activity(mock_tmux, request)

        assert result.success
        assert temp_file.exists()

        # Verify file contains the activity
        with open(temp_file) as f:
            records = json.load(f)
        assert len(records) == 1


def test_report_activity_file_permission_error(mock_tmux, temp_activity_file) -> None:
    """Test report_activity handles file permission errors."""
    request = ReportActivityRequest(
        agent_id="test-agent", activity_type=ActivityType.WORKING, description="Test activity"
    )

    # Mock file operations to raise PermissionError
    with patch(
        "tmux_orchestrator.server.tools.report_activity._get_activity_file_path", return_value=temp_activity_file
    ):
        with patch("builtins.open", side_effect=PermissionError("Access denied")):
            result = report_activity(mock_tmux, request)

    assert not result.success
    assert result.error_message and "Permission denied" in result.error_message


def test_report_activity_json_decode_error(mock_tmux, temp_activity_file) -> None:
    """Test report_activity handles JSON decode errors gracefully."""
    # Write invalid JSON to file
    with open(temp_activity_file, "w") as f:
        f.write("invalid json content")

    request = ReportActivityRequest(
        agent_id="test-agent", activity_type=ActivityType.WORKING, description="Test activity"
    )

    with patch(
        "tmux_orchestrator.server.tools.report_activity._get_activity_file_path", return_value=temp_activity_file
    ):
        result = report_activity(mock_tmux, request)

    assert not result.success
    assert result.error_message and "Invalid JSON" in result.error_message or "JSON" in result.error_message


def test_report_activity_unexpected_error(mock_tmux, temp_activity_file) -> None:
    """Test report_activity handles unexpected errors."""
    request = ReportActivityRequest(
        agent_id="test-agent", activity_type=ActivityType.WORKING, description="Test activity"
    )

    # Mock to raise unexpected exception during save
    with patch(
        "tmux_orchestrator.server.tools.report_activity._get_activity_file_path", return_value=temp_activity_file
    ):
        with patch(
            "tmux_orchestrator.server.tools.report_activity._save_activities",
            side_effect=RuntimeError("Unexpected error"),
        ):
            result = report_activity(mock_tmux, request)

    assert not result.success
    assert result.error_message and "Unexpected error" in result.error_message


def test_get_activity_history_empty_file(mock_tmux, temp_activity_file) -> None:
    """Test getting history from empty file."""
    request = ActivityHistoryRequest()

    with patch(
        "tmux_orchestrator.server.tools.report_activity._get_activity_file_path", return_value=temp_activity_file
    ):
        result = get_activity_history(mock_tmux, request)

    assert result.success
    assert result.records == []
    assert result.total_records == 0
    assert result.error_message is None


def test_get_activity_history_file_not_exist(mock_tmux) -> None:
    """Test getting history when file doesn't exist."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_file = Path(temp_dir) / "nonexistent.json"

        request = ActivityHistoryRequest()

        with patch("tmux_orchestrator.server.tools.report_activity._get_activity_file_path", return_value=temp_file):
            result = get_activity_history(mock_tmux, request)

        assert result.success
        assert result.records == []
        assert result.total_records == 0


def test_get_activity_history_json_error(mock_tmux, temp_activity_file) -> None:
    """Test get_activity_history handles JSON errors."""
    # Write invalid JSON to file
    with open(temp_activity_file, "w") as f:
        f.write("{invalid json}")

    request = ActivityHistoryRequest()

    with patch(
        "tmux_orchestrator.server.tools.report_activity._get_activity_file_path", return_value=temp_activity_file
    ):
        result = get_activity_history(mock_tmux, request)

    assert not result.success
    assert result.error_message and "Invalid JSON" in result.error_message or "JSON" in result.error_message


def test_get_activity_history_permission_error(mock_tmux, temp_activity_file) -> None:
    """Test get_activity_history handles permission errors."""
    request = ActivityHistoryRequest()

    with patch(
        "tmux_orchestrator.server.tools.report_activity._get_activity_file_path", return_value=temp_activity_file
    ):
        with patch("builtins.open", side_effect=PermissionError("Read denied")):
            result = get_activity_history(mock_tmux, request)

    assert not result.success
    assert result.error_message and "Permission denied" in result.error_message


def test_get_activity_history_unexpected_error(mock_tmux, temp_activity_file) -> None:
    """Test get_activity_history handles unexpected errors."""
    request = ActivityHistoryRequest()

    with patch(
        "tmux_orchestrator.server.tools.report_activity._get_activity_file_path", return_value=temp_activity_file
    ):
        with patch(
            "tmux_orchestrator.server.tools.report_activity._load_activities",
            side_effect=RuntimeError("Unexpected read error"),
        ):
            result = get_activity_history(mock_tmux, request)

    assert not result.success
    assert result.error_message and "Unexpected error" in result.error_message

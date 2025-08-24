"""
JSON output validation tests for CLI reflection auto-generated tools.

Ensures all tool outputs conform to expected JSON schemas with proper
type safety, required fields, and data constraints.
"""

import json
from datetime import datetime
from typing import Any

import jsonschema
import pytest

# JSON Schemas for each auto-generated tool

SPAWN_TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "success": {"type": "boolean"},
        "timestamp": {"type": "string", "format": "date-time"},
        "data": {
            "type": "object",
            "properties": {
                "session": {"type": "string", "minLength": 1},
                "window": {"type": "string", "minLength": 1},
                "target": {"type": "string", "pattern": "^[^:]+:[^:]+$"},
                "agent_type": {
                    "type": "string",
                    "enum": ["developer", "pm", "qa", "devops", "reviewer", "researcher", "docs"],
                },
                "message": {"type": "string"},
            },
            "required": ["session", "window", "target", "agent_type"],
        },
        "error": {"type": ["string", "null"]},
        "error_type": {"type": ["string", "null"]},
    },
    "required": ["success", "timestamp"],
    "additionalProperties": False,
}

LIST_TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "success": {"type": "boolean"},
        "timestamp": {"type": "string", "format": "date-time"},
        "data": {
            "type": "object",
            "properties": {
                "agents": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "target": {"type": "string"},
                            "session": {"type": "string"},
                            "window": {"type": "string"},
                            "agent_type": {"type": "string"},
                            "status": {"type": "string", "enum": ["active", "idle", "busy", "error", "unknown"]},
                            "last_activity": {"type": ["string", "null"]},
                            "health_score": {"type": "number", "minimum": 0, "maximum": 1},
                        },
                        "required": ["target", "session", "window", "status"],
                    },
                    "maxItems": 1000,
                },
                "total_count": {"type": "integer", "minimum": 0},
            },
            "required": ["agents", "total_count"],
        },
    },
    "required": ["success", "timestamp"],
    "additionalProperties": False,
}

STATUS_TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "success": {"type": "boolean"},
        "timestamp": {"type": "string", "format": "date-time"},
        "data": {
            "type": "object",
            "properties": {
                "system_health": {"type": "string", "enum": ["healthy", "warning", "critical", "offline"]},
                "sessions": {"type": "integer", "minimum": 0},
                "agents": {"type": "integer", "minimum": 0},
                "teams": {"type": "integer", "minimum": 0},
                "metrics": {
                    "type": "object",
                    "properties": {
                        "cpu_usage": {"type": "number", "minimum": 0, "maximum": 100},
                        "memory_usage": {"type": "number", "minimum": 0, "maximum": 100},
                        "response_time_avg": {"type": "number", "minimum": 0},
                        "error_rate": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                },
                "alerts": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "level": {"type": "string", "enum": ["info", "warning", "error", "critical"]},
                            "message": {"type": "string"},
                            "timestamp": {"type": "string"},
                        },
                        "required": ["level", "message"],
                    },
                },
            },
            "required": ["system_health", "sessions", "agents"],
        },
    },
    "required": ["success", "timestamp"],
    "additionalProperties": False,
}

EXECUTE_TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "success": {"type": "boolean"},
        "timestamp": {"type": "string", "format": "date-time"},
        "data": {
            "type": "object",
            "properties": {
                "project_name": {"type": "string"},
                "prd_file": {"type": "string"},
                "team_deployed": {"type": "boolean"},
                "team_composition": {
                    "type": "object",
                    "properties": {
                        "team_type": {"type": "string"},
                        "size": {"type": "integer", "minimum": 1, "maximum": 20},
                        "agents": {"type": "array", "items": {"type": "string"}},
                    },
                },
                "project_path": {"type": "string"},
                "execution_id": {"type": "string", "pattern": "^[a-f0-9-]{36}$"},
            },
            "required": ["project_name", "team_deployed"],
        },
    },
    "required": ["success", "timestamp"],
    "additionalProperties": False,
}

TEAM_TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "success": {"type": "boolean"},
        "timestamp": {"type": "string", "format": "date-time"},
        "data": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "enum": ["status", "deploy", "kill", "list"]},
                "result": {"type": "object"},  # Varies by subcommand
            },
            "required": ["command", "result"],
        },
    },
    "required": ["success", "timestamp"],
    "additionalProperties": False,
}

QUICK_DEPLOY_SCHEMA = {
    "type": "object",
    "properties": {
        "success": {"type": "boolean"},
        "timestamp": {"type": "string", "format": "date-time"},
        "data": {
            "type": "object",
            "properties": {
                "team_name": {"type": "string"},
                "team_type": {"type": "string", "enum": ["frontend", "backend", "fullstack", "testing"]},
                "size": {"type": "integer", "minimum": 2, "maximum": 10},
                "agents_deployed": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "target": {"type": "string"},
                            "role": {"type": "string"},
                            "status": {"type": "string"},
                        },
                        "required": ["target", "role"],
                    },
                },
                "deployment_time": {"type": "number", "minimum": 0},
            },
            "required": ["team_name", "team_type", "size", "agents_deployed"],
        },
    },
    "required": ["success", "timestamp"],
    "additionalProperties": False,
}


class TestJSONSchemaValidation:
    """Test JSON schema compliance for all auto-generated tools."""

    def test_spawn_tool_success_response(self, test_uuid: str) -> None:
        """Test spawn tool successful response schema."""
        mock_response = {
            "success": True,
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "session": "test-session",
                "window": "Claude-developer",
                "target": "test-session:Claude-developer",
                "agent_type": "developer",
                "message": "Successfully spawned developer agent",
            },
            "error": None,
            "error_type": None,
        }

        try:
            jsonschema.validate(mock_response, SPAWN_TOOL_SCHEMA)
        except jsonschema.ValidationError as e:
            pytest.fail(f"Spawn success response failed validation: {e} - Test ID: {test_uuid}")

    def test_spawn_tool_error_response(self, test_uuid: str) -> None:
        """Test spawn tool error response schema."""
        mock_response = {
            "success": False,
            "timestamp": datetime.utcnow().isoformat(),
            "error": "Session name cannot be empty",
            "error_type": "ValidationError",
        }

        try:
            jsonschema.validate(mock_response, SPAWN_TOOL_SCHEMA)
        except jsonschema.ValidationError as e:
            pytest.fail(f"Spawn error response failed validation: {e} - Test ID: {test_uuid}")

    def test_list_tool_response_with_agents(self, test_uuid: str) -> None:
        """Test list tool response with multiple agents."""
        mock_response = {
            "success": True,
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "agents": [
                    {
                        "target": "frontend:pm",
                        "session": "frontend",
                        "window": "pm",
                        "agent_type": "pm",
                        "status": "active",
                        "last_activity": "2024-01-01T12:00:00Z",
                        "health_score": 0.95,
                    },
                    {
                        "target": "frontend:dev",
                        "session": "frontend",
                        "window": "dev",
                        "agent_type": "developer",
                        "status": "busy",
                        "last_activity": "2024-01-01T12:05:00Z",
                        "health_score": 0.88,
                    },
                ],
                "total_count": 2,
            },
        }

        try:
            jsonschema.validate(mock_response, LIST_TOOL_SCHEMA)
        except jsonschema.ValidationError as e:
            pytest.fail(f"List response failed validation: {e} - Test ID: {test_uuid}")

    def test_status_tool_comprehensive_response(self, test_uuid: str) -> None:
        """Test status tool with full system metrics."""
        mock_response = {
            "success": True,
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "system_health": "healthy",
                "sessions": 5,
                "agents": 12,
                "teams": 3,
                "metrics": {"cpu_usage": 45.2, "memory_usage": 62.8, "response_time_avg": 0.342, "error_rate": 0.02},
                "alerts": [
                    {
                        "level": "warning",
                        "message": "High memory usage detected",
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                ],
            },
        }

        try:
            jsonschema.validate(mock_response, STATUS_TOOL_SCHEMA)
        except jsonschema.ValidationError as e:
            pytest.fail(f"Status response failed validation: {e} - Test ID: {test_uuid}")

    def test_execute_tool_team_deployment(self, test_uuid: str) -> None:
        """Test execute tool PRD execution response."""
        mock_response = {
            "success": True,
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "project_name": "e-commerce-app",
                "prd_file": "/workspace/prd.md",
                "team_deployed": True,
                "team_composition": {
                    "team_type": "fullstack",
                    "size": 5,
                    "agents": ["pm", "frontend", "backend", "qa", "devops"],
                },
                "project_path": "/workspace/e-commerce-app",
                "execution_id": "550e8400-e29b-41d4-a716-446655440000",
            },
        }

        try:
            jsonschema.validate(mock_response, EXECUTE_TOOL_SCHEMA)
        except jsonschema.ValidationError as e:
            pytest.fail(f"Execute response failed validation: {e} - Test ID: {test_uuid}")

    def test_quick_deploy_response(self, test_uuid: str) -> None:
        """Test quick-deploy tool response schema."""
        mock_response = {
            "success": True,
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "team_name": "frontend-team",
                "team_type": "frontend",
                "size": 3,
                "agents_deployed": [
                    {"target": "frontend-team:pm", "role": "Project Manager", "status": "active"},
                    {"target": "frontend-team:dev", "role": "Frontend Developer", "status": "active"},
                    {"target": "frontend-team:ux", "role": "UX Designer", "status": "active"},
                ],
                "deployment_time": 2.45,
            },
        }

        try:
            jsonschema.validate(mock_response, QUICK_DEPLOY_SCHEMA)
        except jsonschema.ValidationError as e:
            pytest.fail(f"Quick-deploy response failed validation: {e} - Test ID: {test_uuid}")


class TestJSONEdgeCases:
    """Test edge cases and boundary conditions for JSON output."""

    def test_unicode_handling_in_responses(self, test_uuid: str) -> None:
        """Test proper Unicode character handling in JSON."""
        mock_response = {
            "success": True,
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "session": "test-世界",
                "window": "Claude-développeur",
                "target": "test-世界:Claude-développeur",
                "agent_type": "developer",
                "message": "Successfully spawned agent with émojis 🚀 and special chars: àáâãäå",
            },
        }

        # Should validate without issues
        try:
            jsonschema.validate(mock_response, SPAWN_TOOL_SCHEMA)

            # Also test JSON serialization/deserialization
            json_str = json.dumps(mock_response, ensure_ascii=False)
            parsed = json.loads(json_str)
            assert parsed == mock_response, f"Unicode roundtrip failed - Test ID: {test_uuid}"

        except (jsonschema.ValidationError, json.JSONDecodeError) as e:
            pytest.fail(f"Unicode handling failed: {e} - Test ID: {test_uuid}")

    def test_large_agent_list_response(self, test_uuid: str) -> None:
        """Test handling of large agent lists (near max limit)."""
        # Create 999 agents (just under 1000 limit)
        large_agent_list = []
        for i in range(999):
            large_agent_list.append(
                {
                    "target": f"session-{i}:window-{i}",
                    "session": f"session-{i}",
                    "window": f"window-{i}",
                    "status": "active" if i % 2 == 0 else "idle",
                    "agent_type": "developer",
                    "health_score": 0.9,
                }
            )

        mock_response = {
            "success": True,
            "timestamp": datetime.utcnow().isoformat(),
            "data": {"agents": large_agent_list, "total_count": 999},
        }

        try:
            jsonschema.validate(mock_response, LIST_TOOL_SCHEMA)
        except jsonschema.ValidationError as e:
            pytest.fail(f"Large list validation failed: {e} - Test ID: {test_uuid}")

    def test_null_vs_undefined_fields(self, test_uuid: str) -> None:
        """Test proper handling of null vs undefined fields."""
        # Test with explicit null
        response_with_null = {
            "success": True,
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "agents": [
                    {
                        "target": "test:window",
                        "session": "test",
                        "window": "window",
                        "status": "active",
                        "last_activity": None,  # Explicit null
                    }
                ],
                "total_count": 1,
            },
        }

        # Test with field omitted (undefined)
        response_without_field = {
            "success": True,
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "agents": [
                    {
                        "target": "test:window",
                        "session": "test",
                        "window": "window",
                        "status": "active",
                        # last_activity omitted
                    }
                ],
                "total_count": 1,
            },
        }

        # Both should validate
        try:
            jsonschema.validate(response_with_null, LIST_TOOL_SCHEMA)
            jsonschema.validate(response_without_field, LIST_TOOL_SCHEMA)
        except jsonschema.ValidationError as e:
            pytest.fail(f"Null handling validation failed: {e} - Test ID: {test_uuid}")

    def test_numeric_precision_boundaries(self, test_uuid: str) -> None:
        """Test numeric precision at boundaries."""
        mock_response = {
            "success": True,
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "system_health": "healthy",
                "sessions": 0,  # Minimum boundary
                "agents": 2147483647,  # Near max int32
                "teams": 1,
                "metrics": {
                    "cpu_usage": 0.0,  # Minimum
                    "memory_usage": 100.0,  # Maximum
                    "response_time_avg": 0.000001,  # Very small
                    "error_rate": 0.9999999,  # Near 1.0
                },
            },
        }

        try:
            jsonschema.validate(mock_response, STATUS_TOOL_SCHEMA)
        except jsonschema.ValidationError as e:
            pytest.fail(f"Numeric boundary validation failed: {e} - Test ID: {test_uuid}")

    def test_empty_arrays_and_objects(self, test_uuid: str) -> None:
        """Test proper handling of empty collections."""
        mock_response = {
            "success": True,
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "agents": [],  # Empty array
                "total_count": 0,
            },
        }

        try:
            jsonschema.validate(mock_response, LIST_TOOL_SCHEMA)
        except jsonschema.ValidationError as e:
            pytest.fail(f"Empty array validation failed: {e} - Test ID: {test_uuid}")


class TestJSONValidationErrors:
    """Test that invalid JSON is properly rejected."""

    def test_missing_required_fields(self, test_uuid: str) -> None:
        """Test that missing required fields are caught."""
        invalid_response = {
            "success": True
            # Missing timestamp
        }

        with pytest.raises(jsonschema.ValidationError) as exc_info:
            jsonschema.validate(invalid_response, SPAWN_TOOL_SCHEMA)

        assert "timestamp" in str(exc_info.value), f"Should catch missing timestamp - Test ID: {test_uuid}"

    def test_wrong_type_fields(self, test_uuid: str) -> None:
        """Test that wrong field types are rejected."""
        invalid_response = {
            "success": "true",  # Should be boolean, not string
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "agents": "not-an-array",  # Should be array
                "total_count": "five",  # Should be integer
            },
        }

        with pytest.raises(jsonschema.ValidationError) as exc_info:
            jsonschema.validate(invalid_response, LIST_TOOL_SCHEMA)

        error_msg = str(exc_info.value)
        assert "type" in error_msg, f"Should catch type errors - Test ID: {test_uuid}"

    def test_invalid_enum_values(self, test_uuid: str) -> None:
        """Test that invalid enum values are rejected."""
        invalid_response = {
            "success": True,
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "system_health": "fantastic",  # Not in enum
                "sessions": 1,
                "agents": 1,
            },
        }

        with pytest.raises(jsonschema.ValidationError) as exc_info:
            jsonschema.validate(invalid_response, STATUS_TOOL_SCHEMA)

        assert "enum" in str(exc_info.value), f"Should catch enum violations - Test ID: {test_uuid}"

    def test_exceeding_array_limits(self, test_uuid: str) -> None:
        """Test that arrays exceeding maxItems are rejected."""
        # Create 1001 agents (exceeds 1000 limit)
        too_many_agents = []
        for i in range(1001):
            too_many_agents.append({"target": f"s{i}:w{i}", "session": f"s{i}", "window": f"w{i}", "status": "active"})

        invalid_response = {
            "success": True,
            "timestamp": datetime.utcnow().isoformat(),
            "data": {"agents": too_many_agents, "total_count": 1001},
        }

        with pytest.raises(jsonschema.ValidationError) as exc_info:
            jsonschema.validate(invalid_response, LIST_TOOL_SCHEMA)

        assert "maxItems" in str(exc_info.value), f"Should catch array limit violation - Test ID: {test_uuid}"

    def test_additional_properties_rejected(self, test_uuid: str) -> None:
        """Test that unexpected properties are rejected."""
        invalid_response = {
            "success": True,
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "session": "test",
                "window": "test",
                "target": "test:test",
                "agent_type": "developer",
                "unexpected_field": "should not be here",  # Extra field
            },
            "another_unexpected": "also should not be here",  # Extra at root
        }

        with pytest.raises(jsonschema.ValidationError) as exc_info:
            jsonschema.validate(invalid_response, SPAWN_TOOL_SCHEMA)

        assert "additionalProperties" in str(exc_info.value), f"Should catch extra properties - Test ID: {test_uuid}"


# Utility functions for JSON validation
def validate_json_output(output: str, schema: dict[str, Any]) -> bool:
    """Validate JSON string output against schema."""
    try:
        data = json.loads(output)
        jsonschema.validate(data, schema)
        return True
    except (json.JSONDecodeError, jsonschema.ValidationError):
        return False


def get_schema_for_tool(tool_name: str) -> dict[str, Any]:
    """Get the appropriate schema for a tool."""
    schemas = {
        "spawn": SPAWN_TOOL_SCHEMA,
        "list": LIST_TOOL_SCHEMA,
        "status": STATUS_TOOL_SCHEMA,
        "execute": EXECUTE_TOOL_SCHEMA,
        "team": TEAM_TOOL_SCHEMA,
        "quick-deploy": QUICK_DEPLOY_SCHEMA,
    }
    return schemas.get(tool_name, {})


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

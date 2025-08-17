# JSON Output Standards for CLI Commands

**Version**: 1.0
**Date**: 2025-08-16
**Purpose**: Ensure consistent JSON output across all CLI commands for MCP reflection

## Overview

JSON output consistency is critical for CLI reflection and MCP tool generation. This document defines mandatory JSON output standards for all tmux-orchestrator CLI commands.

## 1. Root Structure Standard ✅

### 1.1 Success Response Structure

**✅ MANDATORY**: All successful JSON responses MUST follow this structure:

```json
{
  "success": true,
  "timestamp": "2024-01-01T00:00:00Z",
  "command": "spawn_agent",
  "data": {
    // Command-specific response data
  },
  "error": null,
  "metadata": {
    "version": "2.1.23",
    "execution_time": 1.234,
    "warnings": []
  }
}
```

### 1.2 Error Response Structure

**✅ MANDATORY**: All error JSON responses MUST follow this structure:

```json
{
  "success": false,
  "timestamp": "2024-01-01T00:00:00Z",
  "command": "spawn_agent",
  "data": null,
  "error": {
    "type": "ValidationError",
    "message": "Session name cannot be empty",
    "details": {
      "field": "session_name",
      "value": "",
      "suggestion": "Provide a valid session name"
    },
    "code": "E_VALIDATION_001"
  },
  "metadata": {
    "version": "2.1.23",
    "execution_time": 0.123,
    "warnings": []
  }
}
```

## 2. Data Type Standards ✅

### 2.1 Primitive Types

**✅ REQUIRED**: Consistent type usage:

```json
{
  // Strings: UTF-8 encoded
  "name": "my-session",
  "description": "Frontend development session",

  // Numbers: No quotes
  "count": 42,
  "ratio": 0.95,

  // Booleans: lowercase
  "active": true,
  "deleted": false,

  // Null: lowercase
  "parent": null
}
```

### 2.2 Complex Types

**✅ MANDATORY**: Standard complex type formats:

```json
{
  // Timestamps: ISO 8601 with timezone
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T12:30:45.123Z",

  // Durations: Seconds as float
  "duration": 123.456,
  "timeout": 30.0,

  // File paths: Absolute paths
  "project_path": "/home/user/projects/myapp",
  "config_file": "/etc/tmux-orchestrator/config.json",

  // Lists: Always arrays, never null
  "agents": [],
  "errors": [],

  // Objects: Never null for required fields
  "status": {
    "health": "healthy",
    "uptime": 3600
  }
}
```

## 3. Field Naming Conventions ✅

### 3.1 General Rules

**✅ MANDATORY**: snake_case for all fields:

```json
{
  "session_name": "correct",      // ✅ Correct
  "agent_type": "developer",      // ✅ Correct
  "is_active": true,              // ✅ Correct

  "sessionName": "wrong",         // ❌ Wrong: camelCase
  "agent-type": "wrong",          // ❌ Wrong: kebab-case
  "AgentType": "wrong"            // ❌ Wrong: PascalCase
}
```

### 3.2 Standard Field Names

**✅ REQUIRED**: Use these standard field names:

```json
{
  // Identifiers
  "id": "abc123",
  "uuid": "550e8400-e29b-41d4-a716-446655440000",
  "name": "my-resource",

  // Timestamps
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z",
  "deleted_at": null,

  // Status fields
  "status": "active",
  "health_status": "healthy",
  "is_active": true,
  "is_deleted": false,

  // Relationships
  "parent_id": "parent123",
  "child_ids": ["child1", "child2"],

  // Metadata
  "created_by": "user123",
  "updated_by": "user456",
  "version": "1.0.0",

  // Counts
  "total_count": 100,
  "active_count": 95,
  "error_count": 5
}
```

## 4. Command-Specific Standards ✅

### 4.1 List Commands

**✅ MANDATORY**: List command output structure:

```json
{
  "success": true,
  "command": "list_sessions",
  "data": {
    "sessions": [
      {
        "name": "frontend-dev",
        "created_at": "2024-01-01T00:00:00Z",
        "window_count": 3,
        "is_active": true
      }
    ],
    "total_count": 1,
    "filtered_count": 1,
    "page": 1,
    "page_size": 50
  }
}
```

### 4.2 Get/Show Commands

**✅ MANDATORY**: Single resource output structure:

```json
{
  "success": true,
  "command": "get_agent_status",
  "data": {
    "agent": {
      "id": "agent123",
      "type": "developer",
      "session": "frontend-dev",
      "window": "1",
      "status": "active",
      "health": "healthy",
      "created_at": "2024-01-01T00:00:00Z",
      "last_activity": "2024-01-01T00:10:00Z"
    }
  }
}
```

### 4.3 Action Commands

**✅ MANDATORY**: Action command output structure:

```json
{
  "success": true,
  "command": "spawn_agent",
  "data": {
    "action": "agent_spawned",
    "result": {
      "session": "frontend-dev",
      "window": "Claude-developer-1",
      "agent_type": "developer",
      "target": "frontend-dev:Claude-developer-1"
    },
    "duration": 2.345,
    "message": "Agent spawned successfully"
  }
}
```

## 5. Error Standards ✅

### 5.1 Error Types

**✅ REQUIRED**: Standard error types:

```json
{
  "error": {
    "type": "ValidationError",      // Input validation failed
    "type": "NotFoundError",         // Resource not found
    "type": "ConflictError",         // Resource already exists
    "type": "TimeoutError",          // Operation timed out
    "type": "PermissionError",       // Insufficient permissions
    "type": "ConfigurationError",    // Configuration issue
    "type": "DependencyError",       // Missing dependency
    "type": "InternalError"          // Unexpected error
  }
}
```

### 5.2 Error Codes

**✅ MANDATORY**: Structured error codes:

```json
{
  "error": {
    "code": "E_VALIDATION_001",      // Category_Type_Number
    "code": "E_NOTFOUND_001",
    "code": "E_CONFLICT_001",
    "code": "E_TIMEOUT_001",
    "code": "E_PERMISSION_001",
    "code": "E_CONFIG_001",
    "code": "E_DEPENDENCY_001",
    "code": "E_INTERNAL_001"
  }
}
```

## 6. Special Cases ✅

### 6.1 Empty Results

**✅ REQUIRED**: Handle empty results consistently:

```json
{
  "success": true,
  "data": {
    "sessions": [],           // Empty array, not null
    "total_count": 0,
    "message": "No sessions found"
  }
}
```

### 6.2 Partial Success

**✅ MANDATORY**: Report partial success clearly:

```json
{
  "success": true,
  "data": {
    "total_operations": 5,
    "successful": 3,
    "failed": 2,
    "partial_success": true,
    "results": [
      {"target": "agent1", "success": true, "result": "..."},
      {"target": "agent2", "success": false, "error": "..."}
    ]
  }
}
```

### 6.3 Warnings

**✅ REQUIRED**: Include warnings in metadata:

```json
{
  "success": true,
  "data": { "...": "..." },
  "metadata": {
    "warnings": [
      {
        "code": "W_DEPRECATION_001",
        "message": "Option --old-flag is deprecated, use --new-flag"
      }
    ]
  }
}
```

## 7. Format Validation ✅

### 7.1 JSON Formatting

**✅ MANDATORY**: Consistent JSON formatting:

```python
# Python implementation
import json

def format_json_output(data: dict) -> str:
    return json.dumps(
        data,
        indent=2,              # 2-space indentation
        sort_keys=True,        # Consistent key ordering
        ensure_ascii=False,    # UTF-8 support
        separators=(',', ': ') # Standard separators
    )
```

### 7.2 Content Validation

**✅ REQUIRED**: Validate before output:

```python
def validate_json_response(response: dict) -> bool:
    # Required top-level fields
    required = ['success', 'timestamp', 'command', 'data', 'error', 'metadata']
    if not all(field in response for field in required):
        return False

    # Type validation
    if not isinstance(response['success'], bool):
        return False

    # Timestamp format
    try:
        datetime.fromisoformat(response['timestamp'].replace('Z', '+00:00'))
    except:
        return False

    return True
```

## 8. Migration Examples ✅

### 8.1 Before (Inconsistent)

```json
{
  "status": "ok",
  "sessionName": "test",
  "agentCount": 3,
  "timestamp": "2024-01-01 00:00:00"
}
```

### 8.2 After (Standard)

```json
{
  "success": true,
  "timestamp": "2024-01-01T00:00:00Z",
  "command": "get_session_status",
  "data": {
    "session": {
      "name": "test",
      "agent_count": 3,
      "status": "active"
    }
  },
  "error": null,
  "metadata": {
    "version": "2.1.23",
    "execution_time": 0.234,
    "warnings": []
  }
}
```

## 9. Testing JSON Output ✅

### 9.1 Schema Validation

```python
import jsonschema

# Define schema for response
response_schema = {
    "type": "object",
    "required": ["success", "timestamp", "command", "data", "error", "metadata"],
    "properties": {
        "success": {"type": "boolean"},
        "timestamp": {"type": "string", "format": "date-time"},
        "command": {"type": "string"},
        "data": {"type": ["object", "null"]},
        "error": {"type": ["object", "null"]},
        "metadata": {"type": "object"}
    }
}

# Validate response
def test_json_response(response: dict):
    jsonschema.validate(response, response_schema)
```

### 9.2 Output Testing

```python
def test_spawn_agent_json_output():
    result = runner.invoke(cli, ['spawn', 'agent', '--format', 'json'])
    data = json.loads(result.output)

    # Structure validation
    assert 'success' in data
    assert 'timestamp' in data
    assert 'command' in data
    assert data['command'] == 'spawn_agent'

    # Type validation
    assert isinstance(data['success'], bool)
    assert isinstance(data['metadata']['execution_time'], (int, float))
```

---

**These JSON output standards are MANDATORY for all CLI commands.**

**Purpose**: Enable reliable CLI reflection for MCP tool generation!

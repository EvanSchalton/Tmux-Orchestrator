# MCP Command Examples: Complex Nested Operations

## Overview

This document provides comprehensive examples of complex MCP tool usage in Tmux Orchestrator, demonstrating nested commands, multi-step workflows, and advanced patterns.

## Table of Contents
1. [Basic Command Structure](#basic-command-structure)
2. [Agent Management Examples](#agent-management-examples)
3. [Team Deployment Workflows](#team-deployment-workflows)
4. [Monitoring and Daemon Operations](#monitoring-and-daemon-operations)
5. [PubSub Communication Patterns](#pubsub-communication-patterns)
6. [Complex Multi-Step Workflows](#complex-multi-step-workflows)
7. [Error Recovery Patterns](#error-recovery-patterns)
8. [Advanced Integration Examples](#advanced-integration-examples)

## Basic Command Structure

### Tool Naming Convention
All MCP tools follow the pattern: `tmux-orc_[group]_[action]`

```json
{
  "tool": "tmux-orc_[group]_[action]",
  "arguments": {
    "required_arg": "value",
    "--optional-flag": "value",
    "--boolean-flag": true
  }
}
```

## Agent Management Examples

### Example 1: Complete Agent Lifecycle

```python
# 1. Spawn a developer agent with custom context
{
  "tool": "tmux-orc_spawn_agent",
  "arguments": {
    "agent_type": "developer",
    "session_window": "backend-api:1",
    "--context": "Implement REST API endpoints for user management",
    "--extend": "Use FastAPI framework, follow OpenAPI 3.0 standards"
  }
}

# 2. Monitor agent health
{
  "tool": "tmux-orc_agent_health-check",
  "arguments": {
    "session_window": "backend-api:1"
  }
}

# 3. Send a message to the agent
{
  "tool": "tmux-orc_pubsub_send",
  "arguments": {
    "target": "backend-api:1",
    "message": "Priority change: Focus on authentication endpoints first",
    "--type": "directive"
  }
}

# 4. Check agent status
{
  "tool": "tmux-orc_agent_status",
  "arguments": {
    "session_window": "backend-api:1"
  }
}

# 5. Restart agent if needed
{
  "tool": "tmux-orc_agent_restart",
  "arguments": {
    "session_window": "backend-api:1",
    "--preserve-context": true
  }
}

# 6. Kill agent when done
{
  "tool": "tmux-orc_agent_kill",
  "arguments": {
    "session_window": "backend-api:1",
    "--force": true
  }
}
```

### Example 2: Multi-Agent Coordination

```python
# Spawn multiple agents for a feature
agents = [
    {
        "type": "developer",
        "window": "feature:1",
        "context": "Frontend React components"
    },
    {
        "type": "developer",
        "window": "feature:2",
        "context": "Backend API endpoints"
    },
    {
        "type": "qa-engineer",
        "window": "feature:3",
        "context": "Integration testing"
    }
]

# Spawn all agents
for agent in agents:
    {
        "tool": "tmux-orc_spawn_agent",
        "arguments": {
            "agent_type": agent["type"],
            "session_window": agent["window"],
            "--context": agent["context"]
        }
    }

# Broadcast message to all
{
  "tool": "tmux-orc_pubsub_broadcast",
  "arguments": {
    "message": "Feature kickoff: User authentication system",
    "--session": "feature"
  }
}
```

## Team Deployment Workflows

### Example 3: Deploy Backend Team with Monitoring

```python
# 1. Create team configuration
{
  "tool": "tmux-orc_team_configure",
  "arguments": {
    "name": "backend-team",
    "--agents": "pm,developer,developer,qa-engineer,devops",
    "--session-prefix": "backend"
  }
}

# 2. Deploy the team
{
  "tool": "tmux-orc_team_deploy",
  "arguments": {
    "config": "backend-team.yaml"
  }
}

# 3. Start monitoring on PM window
{
  "tool": "tmux-orc_monitor_start",
  "arguments": {
    "session_window": "backend:0",
    "--interval": "30",
    "--alert-on": "error,critical"
  }
}

# 4. Configure daemon for team
{
  "tool": "tmux-orc_daemon_start",
  "arguments": {
    "--session": "backend",
    "--enable-recovery": true,
    "--heartbeat-interval": "60"
  }
}

# 5. Verify team status
{
  "tool": "tmux-orc_team_status",
  "arguments": {
    "name": "backend-team"
  }
}
```

### Example 4: Quick Deploy with Custom Configuration

```python
# Quick deploy for frontend development
{
  "tool": "tmux-orc_quick-deploy",
  "arguments": {
    "team_type": "frontend",
    "session_prefix": "ui-redesign",
    "--num-developers": "3",
    "--include-qa": true,
    "--custom-context": "React 18 migration project"
  }
}

# Follow up with team-specific configuration
{
  "tool": "tmux-orc_team_update",
  "arguments": {
    "name": "ui-redesign-team",
    "--add-agent": "ux-designer:4",
    "--briefing": "Material UI v5 design system"
  }
}
```

## Monitoring and Daemon Operations

### Example 5: Comprehensive Monitoring Setup

```python
# 1. Start system-wide monitoring
{
  "tool": "tmux-orc_monitor_start",
  "arguments": {
    "session_window": "control:0",
    "--mode": "global",
    "--log-level": "info"
  }
}

# 2. Configure monitoring rules
{
  "tool": "tmux-orc_monitor_configure",
  "arguments": {
    "--rule": "agent-idle",
    "--threshold": "300",  # 5 minutes
    "--action": "alert"
  }
}

# 3. Add custom health check
{
  "tool": "tmux-orc_monitor_add-check",
  "arguments": {
    "name": "api-endpoint",
    "command": "curl -s http://localhost:8000/health",
    "--interval": "60",
    "--timeout": "10"
  }
}

# 4. View monitoring metrics
{
  "tool": "tmux-orc_monitor_metrics",
  "arguments": {
    "--session": "backend",
    "--window": "all",
    "--format": "json"
  }
}

# 5. Export monitoring data
{
  "tool": "tmux-orc_monitor_export",
  "arguments": {
    "--from": "2024-01-01T00:00:00",
    "--to": "2024-01-31T23:59:59",
    "--output": "monitoring-report.json"
  }
}
```

### Example 6: Daemon Recovery Management

```python
# 1. Check daemon status
{
  "tool": "tmux-orc_daemon_status",
  "arguments": {
    "--verbose": true
  }
}

# 2. Configure recovery policies
{
  "tool": "tmux-orc_recovery_configure",
  "arguments": {
    "--policy": "pm-recovery",
    "--max-attempts": "3",
    "--cooldown": "300",  # 5 minutes
    "--grace-period": "180"  # 3 minutes
  }
}

# 3. Trigger manual recovery
{
  "tool": "tmux-orc_recovery_trigger",
  "arguments": {
    "session_window": "backend:1",
    "--reason": "Agent unresponsive",
    "--preserve-state": true
  }
}

# 4. View recovery history
{
  "tool": "tmux-orc_recovery_history",
  "arguments": {
    "--session": "backend",
    "--last": "10"
  }
}
```

## PubSub Communication Patterns

### Example 7: Complex Message Routing

```python
# 1. Subscribe agent to topics
{
  "tool": "tmux-orc_pubsub_subscribe",
  "arguments": {
    "session_window": "backend:1",
    "topics": "api-updates,security-alerts,team-announcements"
  }
}

# 2. Send targeted message with metadata
{
  "tool": "tmux-orc_pubsub_send",
  "arguments": {
    "target": "backend:1",
    "message": "API endpoint /users requires authentication middleware",
    "--type": "task",
    "--priority": "high",
    "--metadata": '{"ticket": "API-123", "deadline": "2024-02-01"}'
  }
}

# 3. Broadcast to topic subscribers
{
  "tool": "tmux-orc_pubsub_publish",
  "arguments": {
    "topic": "security-alerts",
    "message": "New CVE detected in dependency X, update required",
    "--severity": "critical"
  }
}

# 4. Query message history
{
  "tool": "tmux-orc_pubsub_history",
  "arguments": {
    "--session": "backend",
    "--type": "task",
    "--since": "1h",
    "--format": "detailed"
  }
}
```

### Example 8: Team Communication Workflow

```python
# PM sends task assignments
task_assignments = [
    {
        "agent": "backend:1",
        "task": "Implement user authentication API",
        "priority": "high"
    },
    {
        "agent": "backend:2",
        "task": "Create database migration scripts",
        "priority": "medium"
    },
    {
        "agent": "backend:3",
        "task": "Write integration tests",
        "priority": "medium"
    }
]

for assignment in task_assignments:
    {
        "tool": "tmux-orc_pubsub_send",
        "arguments": {
            "target": assignment["agent"],
            "message": assignment["task"],
            "--type": "assignment",
            "--priority": assignment["priority"],
            "--from": "backend:0"  # PM window
        }
    }

# Agents acknowledge receipt
{
  "tool": "tmux-orc_pubsub_ack",
  "arguments": {
    "message_id": "msg_12345",
    "--status": "received",
    "--estimated_time": "2h"
  }
}
```

## Complex Multi-Step Workflows

### Example 9: Full Project Setup and Deployment

```python
# Step 1: Initialize project structure
{
  "tool": "tmux-orc_orchestrator_init",
  "arguments": {
    "project": "microservices-platform",
    "--template": "microservices",
    "--teams": "api,frontend,infrastructure,qa"
  }
}

# Step 2: Deploy teams sequentially
teams = ["api", "frontend", "infrastructure", "qa"]
for team in teams:
    # Deploy team
    {
        "tool": "tmux-orc_quick-deploy",
        "arguments": {
            "team_type": team,
            "session_prefix": f"platform-{team}"
        }
    }

    # Configure team-specific monitoring
    {
        "tool": "tmux-orc_monitor_start",
        "arguments": {
            "session_window": f"platform-{team}:0",
            "--profile": team
        }
    }

    # Set up team communication
    {
        "tool": "tmux-orc_pubsub_create-channel",
        "arguments": {
            "name": f"{team}-updates",
            "--subscribers": f"platform-{team}:*",
            "--moderator": f"platform-{team}:0"
        }
    }

# Step 3: Establish cross-team communication
{
  "tool": "tmux-orc_orchestrator_link-teams",
  "arguments": {
    "teams": "platform-api,platform-frontend,platform-infrastructure,platform-qa",
    "--communication": "mesh",  # all-to-all
    "--shared-channels": "platform-announcements,platform-incidents"
  }
}

# Step 4: Deploy integration monitoring
{
  "tool": "tmux-orc_monitor_integration",
  "arguments": {
    "name": "platform-health",
    "sessions": "platform-*",
    "--dashboard": true,
    "--alerts": "slack,email"
  }
}

# Step 5: Run initial quality checks
{
  "tool": "tmux-orc_orchestrator_quality-check",
  "arguments": {
    "scope": "all",
    "--include": "communication,health,performance",
    "--report": "platform-initial-qc.json"
  }
}
```

### Example 10: Automated Feature Development

```python
# Feature: Add payment processing
feature_plan = {
    "name": "payment-processing",
    "teams": {
        "backend": ["payment-api", "transaction-service"],
        "frontend": ["checkout-ui"],
        "qa": ["payment-testing"]
    }
}

# 1. Create feature branch workspace
{
  "tool": "tmux-orc_orchestrator_create-workspace",
  "arguments": {
    "name": feature_plan["name"],
    "--vcs-branch": "feature/payment-processing",
    "--isolated": true
  }
}

# 2. Deploy specialized agents
for team, components in feature_plan["teams"].items():
    for component in components:
        {
            "tool": "tmux-orc_spawn_agent",
            "arguments": {
                "agent_type": "developer" if team != "qa" else "qa-engineer",
                "session_window": f"payment:{components.index(component)+1}",
                "--context": f"Implement {component}",
                "--skills": "python,fastapi,stripe-api" if "api" in component else "react,typescript"
            }
        }

# 3. Set up continuous integration
{
  "tool": "tmux-orc_orchestrator_setup-ci",
  "arguments": {
    "workspace": "payment-processing",
    "--triggers": "code-change,test-complete",
    "--pipeline": "lint,test,security-scan,deploy-preview"
  }
}

# 4. Configure automated testing
{
  "tool": "tmux-orc_qa_configure",
  "arguments": {
    "session": "payment",
    "--test-types": "unit,integration,e2e,security",
    "--coverage-threshold": "80",
    "--fail-fast": false
  }
}
```

## Error Recovery Patterns

### Example 11: Graceful Error Handling

```python
# Implement retry logic for critical operations
def deploy_with_retry(team_config, max_attempts=3):
    for attempt in range(max_attempts):
        try:
            # Attempt deployment
            result = {
                "tool": "tmux-orc_team_deploy",
                "arguments": {
                    "config": team_config
                }
            }

            if result["success"]:
                return result

        except Exception as e:
            if attempt < max_attempts - 1:
                # Wait before retry
                {
                    "tool": "tmux-orc_orchestrator_wait",
                    "arguments": {
                        "seconds": 30 * (attempt + 1),
                        "--reason": f"Deployment failed: {e}"
                    }
                }

                # Clean up failed deployment
                {
                    "tool": "tmux-orc_team_cleanup",
                    "arguments": {
                        "name": team_config.replace(".yaml", ""),
                        "--force": true
                    }
                }
            else:
                # Final attempt failed, trigger recovery
                {
                    "tool": "tmux-orc_recovery_escalate",
                    "arguments": {
                        "issue": "Team deployment failed",
                        "context": team_config,
                        "--notify": "orchestrator"
                    }
                }
```

### Example 12: Health Check and Auto-Recovery

```python
# Continuous health monitoring with auto-recovery
{
  "tool": "tmux-orc_monitor_health-loop",
  "arguments": {
    "targets": "all-agents",
    "--interval": "60",
    "--checks": [
      {
        "name": "responsiveness",
        "timeout": "30",
        "action_on_fail": "restart"
      },
      {
        "name": "memory_usage",
        "threshold": "80%",
        "action_on_fail": "alert"
      },
      {
        "name": "task_progress",
        "min_rate": "1/hour",
        "action_on_fail": "investigate"
      }
    ]
  }
}

# Handle recovery events
{
  "tool": "tmux-orc_recovery_handler",
  "arguments": {
    "--on-restart": "preserve-context,notify-pm",
    "--on-failure": "capture-logs,escalate",
    "--max-recoveries": "3",
    "--cooldown": "600"  # 10 minutes
  }
}
```

## Advanced Integration Examples

### Example 13: External System Integration

```python
# Integrate with GitHub for automated PR creation
{
  "tool": "tmux-orc_orchestrator_integrate",
  "arguments": {
    "service": "github",
    "--repo": "company/project",
    "--actions": [
      {
        "trigger": "feature-complete",
        "action": "create-pr",
        "template": "feature-pr.md"
      },
      {
        "trigger": "tests-pass",
        "action": "update-pr-status",
        "status": "ready-for-review"
      }
    ]
  }
}

# Set up webhook handlers
{
  "tool": "tmux-orc_orchestrator_webhook",
  "arguments": {
    "endpoint": "/github/pr-review",
    "--handler": "distribute-to-qa",
    "--filter": "status=approved"
  }
}
```

### Example 14: Performance Optimization Workflow

```python
# 1. Baseline performance metrics
{
  "tool": "tmux-orc_monitor_performance",
  "arguments": {
    "session": "production",
    "--metrics": "response-time,throughput,error-rate",
    "--duration": "1h",
    "--output": "baseline.json"
  }
}

# 2. Deploy optimization team
{
  "tool": "tmux-orc_spawn_agent",
  "arguments": {
    "agent_type": "performance-engineer",
    "session_window": "optimize:1",
    "--context": "Analyze baseline.json, identify bottlenecks",
    "--tools": "profiler,load-tester,apm"
  }
}

# 3. Run optimization experiments
experiments = ["caching", "query-optimization", "async-processing"]
for exp in experiments:
    {
        "tool": "tmux-orc_orchestrator_experiment",
        "arguments": {
            "name": exp,
            "branch": f"perf/{exp}",
            "--baseline": "baseline.json",
            "--duration": "30m",
            "--auto-rollback": true
        }
    }

# 4. Compare results and apply best
{
  "tool": "tmux-orc_orchestrator_compare",
  "arguments": {
    "experiments": experiments,
    "--metric": "response-time",
    "--select": "best",
    "--apply": true
  }
}
```

### Example 15: Disaster Recovery Scenario

```python
# Complete system recovery workflow
disaster_recovery = {
    "scenario": "complete-system-failure",
    "priority": "critical",
    "steps": [
        {
            "name": "assess-damage",
            "tool": "tmux-orc_orchestrator_diagnose",
            "arguments": {
                "--deep-scan": true,
                "--include": "sessions,agents,daemons,data"
            }
        },
        {
            "name": "backup-state",
            "tool": "tmux-orc_orchestrator_backup",
            "arguments": {
                "--scope": "all",
                "--destination": "/recovery/backup-{timestamp}"
            }
        },
        {
            "name": "clean-environment",
            "tool": "tmux-orc_orchestrator_reset",
            "arguments": {
                "--preserve": "data,configs",
                "--force": true
            }
        },
        {
            "name": "restore-core",
            "tool": "tmux-orc_orchestrator_restore",
            "arguments": {
                "--from": "last-known-good",
                "--components": "orchestrator,monitoring,pubsub"
            }
        },
        {
            "name": "redeploy-teams",
            "tool": "tmux-orc_orchestrator_redeploy",
            "arguments": {
                "--strategy": "rolling",
                "--verify-each": true,
                "--timeout": "300"
            }
        },
        {
            "name": "verify-recovery",
            "tool": "tmux-orc_orchestrator_verify",
            "arguments": {
                "--checks": "all",
                "--report": "recovery-report.json"
            }
        }
    ]
}

# Execute recovery plan
for step in disaster_recovery["steps"]:
    result = {
        "tool": step["tool"],
        "arguments": step["arguments"]
    }

    if not result["success"]:
        # Escalate if step fails
        {
            "tool": "tmux-orc_orchestrator_alert",
            "arguments": {
                "severity": "critical",
                "message": f"Recovery step '{step['name']}' failed",
                "--channels": "ops-emergency,management"
            }
        }
        break
```

## Best Practices Summary

1. **Always validate before executing**
   - Check session/agent existence
   - Verify prerequisites
   - Test in isolated environments first

2. **Use appropriate error handling**
   - Implement retry logic for transient failures
   - Have fallback strategies
   - Log all critical operations

3. **Optimize for performance**
   - Batch related operations
   - Use async operations where possible
   - Monitor resource usage

4. **Maintain clear communication**
   - Use descriptive messages
   - Include context and metadata
   - Set up proper channels and topics

5. **Plan for failure**
   - Implement health checks
   - Configure auto-recovery
   - Have disaster recovery plans

## Conclusion

These examples demonstrate the power and flexibility of the hierarchical MCP tool structure. By combining tools effectively, you can create sophisticated automation workflows that handle complex scenarios while maintaining reliability and performance.

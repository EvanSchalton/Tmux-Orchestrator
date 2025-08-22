# MCP Examples and Error Handling Guide

## 🎯 Real-World MCP Workflows

This guide provides practical examples of MCP tool usage in common scenarios, along with comprehensive error handling strategies.

## 📚 Table of Contents
1. [Agent Deployment Workflows](#agent-deployment-workflows)
2. [Team Coordination Patterns](#team-coordination-patterns)
3. [Health Monitoring & Recovery](#health-monitoring--recovery)
4. [Communication Workflows](#communication-workflows)
5. [Error Handling Patterns](#error-handling-patterns)
6. [Advanced Automation](#advanced-automation)

---

## 🚀 Agent Deployment Workflows

### Example 1: Safe Agent Deployment with Verification

```python
def deploy_agent_safely(agent_type, role, session_name):
    """Deploy an agent with health verification and rollback capability."""

    # Step 1: Check if session already exists
    list_result = tmux-orc_list(options={"json": true})
    if list_result["success"]:
        existing = [a for a in list_result["result"]["agents"]
                   if a["session"] == session_name]
        if existing:
            return {"error": f"Session {session_name} already exists"}

    # Step 2: Deploy the agent
    deploy_result = tmux-orc_agent_deploy(args=[agent_type, role])
    if not deploy_result["success"]:
        return {"error": f"Deployment failed: {deploy_result['error']}"}

    # Step 3: Wait for agent to initialize
    import time
    time.sleep(3)

    # Step 4: Verify agent is healthy
    target = f"{session_name}:0"
    info_result = tmux-orc_agent_info(args=[target], options={"json": true})

    if not info_result["success"]:
        # Rollback - kill the failed agent
        tmux-orc_agent_kill(args=[target])
        return {"error": "Agent failed health check after deployment"}

    # Step 5: Send initial briefing
    message_result = tmux-orc_agent_message(
        args=[target, f"Welcome! You are a {role} specializing in {agent_type}."]
    )

    return {
        "success": true,
        "target": target,
        "agent_type": agent_type,
        "role": role
    }
```

### Example 2: Team Deployment with Progressive Rollout

```python
def deploy_team_progressively(team_type, size, project_name):
    """Deploy a team one agent at a time with health checks."""

    deployed_agents = []
    failed_deployments = []

    # Enable monitoring first
    tmux-orc_monitor_start(options={"interval": 10})

    for i in range(int(size)):
        agent_name = f"{project_name}:{i}"

        # Deploy individual agent
        result = tmux-orc_spawn_agent(args=[team_type, agent_name])

        if result["success"]:
            deployed_agents.append(agent_name)

            # Verify agent is responsive
            time.sleep(2)
            health = tmux-orc_agent_info(args=[agent_name], options={"json": true})

            if not health["success"] or health["result"]["status"] == "error":
                failed_deployments.append(agent_name)
                # Don't rollback yet, continue with other agents
        else:
            failed_deployments.append(agent_name)

    # Send team briefing to all healthy agents
    if deployed_agents:
        team_message = f"You are part of a {team_type} team for {project_name}"
        tmux-orc_team_broadcast(args=[project_name, team_message])

    # Enable auto-recovery for the team
    if len(deployed_agents) > len(failed_deployments):
        tmux-orc_monitor_recovery_start()

    return {
        "deployed": deployed_agents,
        "failed": failed_deployments,
        "recovery_enabled": len(deployed_agents) > 0
    }
```

---

## 👥 Team Coordination Patterns

### Example 3: Coordinated Team Task Distribution

```python
def distribute_tasks_to_team(team_name, tasks):
    """Distribute tasks evenly across team members."""

    # Get team members
    team_status = tmux-orc_team_status(args=[team_name], options={"json": true})
    if not team_status["success"]:
        return {"error": f"Could not get team status: {team_status['error']}"}

    active_agents = [a for a in team_status["result"]["agents"]
                    if a["status"] == "Active"]

    if not active_agents:
        return {"error": "No active agents in team"}

    # Distribute tasks round-robin
    task_assignments = {}
    for i, task in enumerate(tasks):
        agent = active_agents[i % len(active_agents)]
        agent_target = agent["target"]

        # Send task to agent
        result = tmux-orc_agent_send(
            args=[agent_target, f"NEW TASK: {task}"],
            options={"delay": 0.5}
        )

        if result["success"]:
            if agent_target not in task_assignments:
                task_assignments[agent_target] = []
            task_assignments[agent_target].append(task)

    # Send summary to PM
    pm_target = f"{team_name}:0"  # Assuming PM is always window 0
    summary = f"Distributed {len(tasks)} tasks to {len(active_agents)} agents"
    tmux-orc_agent_message(args=[pm_target, summary])

    return {
        "success": true,
        "assignments": task_assignments,
        "total_tasks": len(tasks),
        "active_agents": len(active_agents)
    }
```

### Example 4: Team Health Check with Auto-Recovery

```python
def monitor_team_health(team_name, recovery_threshold=0.5):
    """Monitor team health and trigger recovery if needed."""

    # Get initial team status
    status = tmux-orc_team_status(args=[team_name], options={"json": true})
    if not status["success"]:
        return {"error": "Could not get team status"}

    total_agents = len(status["result"]["agents"])
    healthy_agents = len([a for a in status["result"]["agents"]
                         if a["health"] == "healthy"])

    health_ratio = healthy_agents / total_agents if total_agents > 0 else 0

    # Check if recovery is needed
    if health_ratio < recovery_threshold:
        # First try to restart unhealthy agents
        unhealthy = [a for a in status["result"]["agents"]
                    if a["health"] != "healthy"]

        restarted = []
        for agent in unhealthy:
            restart_result = tmux-orc_agent_restart(args=[agent["target"]])
            if restart_result["success"]:
                restarted.append(agent["target"])

        # If restarts didn't help, trigger team recovery
        if len(restarted) < len(unhealthy):
            tmux-orc_team_recover(args=[team_name])

            # Notify PM about recovery
            pm_message = f"Team health dropped to {health_ratio:.1%}. Recovery initiated."
            tmux-orc_agent_message(args=[f"{team_name}:0", pm_message])

    return {
        "health_ratio": health_ratio,
        "total_agents": total_agents,
        "healthy_agents": healthy_agents,
        "recovery_triggered": health_ratio < recovery_threshold
    }
```

---

## 🏥 Health Monitoring & Recovery

### Example 5: Comprehensive System Health Check

```python
def comprehensive_health_check():
    """Perform full system health check with detailed reporting."""

    health_report = {
        "timestamp": time.time(),
        "overall_health": "healthy",
        "issues": [],
        "metrics": {}
    }

    # 1. Check system status
    system_status = tmux-orc_status(options={"json": true})
    if system_status["success"]:
        summary = system_status["result"]["summary"]
        health_report["metrics"]["total_sessions"] = summary.get("total_sessions", 0)
        health_report["metrics"]["active_agents"] = summary.get("active_agents", 0)

        if summary.get("critical_errors", 0) > 0:
            health_report["overall_health"] = "critical"
            health_report["issues"].append("System has critical errors")

    # 2. Check monitoring daemon
    monitor_status = tmux-orc_monitor_status(options={"json": true})
    if monitor_status["success"]:
        if not monitor_status["result"].get("daemon_running", false):
            health_report["issues"].append("Monitoring daemon not running")
            # Try to start it
            tmux-orc_monitor_start(options={"interval": 15})

    # 3. Check agent health
    agent_list = tmux-orc_agent_list(options={"json": true})
    if agent_list["success"]:
        agents = agent_list["result"]["agents"]
        error_agents = [a for a in agents if a["status"] == "error"]

        if error_agents:
            health_report["overall_health"] = "warning" if health_report["overall_health"] == "healthy" else health_report["overall_health"]
            health_report["issues"].append(f"{len(error_agents)} agents in error state")
            health_report["error_agents"] = [a["target"] for a in error_agents]

    # 4. Check recovery status
    recovery_status = tmux-orc_monitor_recovery_status(options={"json": true})
    if recovery_status["success"]:
        if not recovery_status["result"].get("enabled", false):
            health_report["issues"].append("Auto-recovery is disabled")
            # Enable it if there are issues
            if health_report["issues"]:
                tmux-orc_monitor_recovery_start()

    # 5. Get performance metrics
    metrics = tmux-orc_monitor_metrics(options={"json": true})
    if metrics["success"]:
        health_report["metrics"]["performance"] = metrics["result"]

    return health_report
```

### Example 6: Automated Recovery Pipeline

```python
def automated_recovery_pipeline(max_retries=3):
    """Automated recovery pipeline for system issues."""

    recovery_log = []

    # Step 1: Run health check
    health = comprehensive_health_check()

    if health["overall_health"] == "healthy":
        return {"status": "healthy", "actions": []}

    # Step 2: Handle error agents
    if "error_agents" in health:
        for agent in health["error_agents"]:
            for retry in range(max_retries):
                restart_result = tmux-orc_agent_restart(args=[agent])

                if restart_result["success"]:
                    recovery_log.append(f"Restarted {agent} (attempt {retry+1})")
                    break

                time.sleep(2 ** retry)  # Exponential backoff
            else:
                # All retries failed, kill and redeploy
                tmux-orc_agent_kill(args=[agent])
                recovery_log.append(f"Killed unrecoverable agent {agent}")

    # Step 3: Check teams and recover if needed
    teams = tmux-orc_team_list(options={"json": true})
    if teams["success"]:
        for team in teams["result"]["teams"]:
            team_health = monitor_team_health(team["name"])
            if team_health["recovery_triggered"]:
                recovery_log.append(f"Triggered recovery for team {team['name']}")

    # Step 4: Ensure monitoring is active
    if not health.get("monitoring_active", false):
        tmux-orc_monitor_start(options={"interval": 15})
        tmux-orc_monitor_recovery_start()
        recovery_log.append("Started monitoring and auto-recovery")

    # Step 5: Generate recovery report
    return {
        "status": "recovered",
        "initial_health": health["overall_health"],
        "issues_found": len(health["issues"]),
        "actions_taken": recovery_log
    }
```

---

## 💬 Communication Workflows

### Example 7: Intelligent Message Routing

```python
def route_message_by_expertise(message, required_skills):
    """Route messages to agents based on their expertise."""

    # Get all agents
    agents = tmux-orc_agent_list(options={"json": true})
    if not agents["success"]:
        return {"error": "Could not get agent list"}

    # Find agents with required skills
    suitable_agents = []
    for agent in agents["result"]["agents"]:
        agent_info = tmux-orc_agent_info(args=[agent["target"]], options={"json": true})
        if agent_info["success"]:
            # Check if agent has required skills (in type or briefing)
            agent_type = agent_info["result"].get("type", "")
            if any(skill.lower() in agent_type.lower() for skill in required_skills):
                suitable_agents.append(agent)

    if not suitable_agents:
        # Broadcast to all if no specific match
        tmux-orc_team_broadcast(args=["all", f"HELP NEEDED: {message}"])
        return {"status": "broadcast", "reason": "No agents with required skills"}

    # Send to most suitable agent (least busy)
    target_agent = min(suitable_agents, key=lambda a: a.get("message_count", 0))

    result = tmux-orc_agent_send(
        args=[target_agent["target"], message],
        options={"delay": 0.5}
    )

    return {
        "status": "routed",
        "target": target_agent["target"],
        "agent_type": target_agent.get("type", "unknown"),
        "success": result["success"]
    }
```

### Example 8: Coordinated Multi-Agent Communication

```python
def coordinate_multi_agent_task(task_description, agent_roles):
    """Coordinate a task across multiple specialized agents."""

    coordination_log = []

    # Step 1: Notify all involved agents
    for role, targets in agent_roles.items():
        role_message = f"COORDINATION: {task_description}\nYour role: {role}"

        for target in targets:
            result = tmux-orc_agent_message(args=[target, role_message])
            coordination_log.append({
                "target": target,
                "role": role,
                "notified": result["success"]
            })

    # Step 2: Set up pub/sub channel for coordination
    channel_name = f"task_{int(time.time())}"

    # Subscribe all agents to the channel
    for targets in agent_roles.values():
        for target in targets:
            tmux-orc_pubsub_subscribe(args=[channel_name, target])

    # Step 3: Publish task details
    task_details = {
        "description": task_description,
        "roles": agent_roles,
        "channel": channel_name,
        "timestamp": time.time()
    }

    tmux-orc_pubsub_publish(args=[channel_name, json.dumps(task_details)])

    # Step 4: Monitor progress via channel
    coordination_log.append({
        "channel_created": channel_name,
        "subscribers": sum(len(targets) for targets in agent_roles.values())
    })

    return {
        "success": true,
        "channel": channel_name,
        "coordination_log": coordination_log
    }
```

---

## 🛡️ Error Handling Patterns

### Example 9: Comprehensive Error Handler

```python
def execute_with_error_handling(tool_function, args=None, options=None, retries=3):
    """Execute MCP tool with comprehensive error handling."""

    args = args or []
    options = options or {}
    last_error = None

    for attempt in range(retries):
        try:
            # Execute the tool
            if args and options:
                result = tool_function(args=args, options=options)
            elif args:
                result = tool_function(args=args)
            elif options:
                result = tool_function(options=options)
            else:
                result = tool_function()

            # Check for MCP-level success
            if result.get("success", false):
                return result

            # Handle specific error types
            error = result.get("error", "Unknown error")

            if "not found" in error.lower():
                # Entity doesn't exist - no point retrying
                return result

            elif "timeout" in error.lower():
                # Timeout - wait longer before retry
                time.sleep(2 ** attempt)
                last_error = error
                continue

            elif "permission" in error.lower():
                # Permission issue - can't fix automatically
                return result

            else:
                # Generic error - exponential backoff
                time.sleep(0.5 * (attempt + 1))
                last_error = error

        except Exception as e:
            # Python-level exception
            last_error = str(e)
            time.sleep(0.5 * (attempt + 1))

    # All retries exhausted
    return {
        "success": false,
        "error": f"Failed after {retries} attempts. Last error: {last_error}",
        "attempts": retries
    }
```

### Example 10: Error Recovery Strategies

```python
class MCPErrorRecovery:
    """Comprehensive error recovery strategies for MCP operations."""

    @staticmethod
    def handle_agent_not_found(target):
        """Handle case where agent doesn't exist."""
        # Extract session and window
        parts = target.split(":")
        if len(parts) != 2:
            return {"error": "Invalid target format"}

        session, window = parts

        # Try to create the agent
        result = tmux-orc_spawn_agent(args=["general", target])
        if result["success"]:
            return {"recovered": true, "action": "spawned_new_agent"}

        return {"recovered": false, "error": "Could not spawn replacement agent"}

    @staticmethod
    def handle_communication_failure(target, message, max_retries=3):
        """Handle communication failures with fallback strategies."""
        strategies = [
            # Strategy 1: Direct message
            lambda: tmux-orc_agent_message(args=[target, message]),

            # Strategy 2: Advanced send with delay
            lambda: tmux-orc_agent_send(args=[target, message], options={"delay": 1.0}),

            # Strategy 3: Execute echo command
            lambda: tmux-orc_execute(args=[target, f"echo '{message}'"]),

            # Strategy 4: Broadcast to team
            lambda: tmux-orc_team_broadcast(args=["all", f"@{target}: {message}"])
        ]

        for i, strategy in enumerate(strategies):
            result = execute_with_error_handling(strategy, retries=max_retries)
            if result.get("success", false):
                return {
                    "success": true,
                    "strategy_used": i + 1,
                    "strategy_name": strategy.__name__
                }

        return {"success": false, "error": "All communication strategies failed"}

    @staticmethod
    def handle_deployment_failure(agent_type, role, recovery_options=None):
        """Handle deployment failures with multiple recovery options."""
        recovery_options = recovery_options or {
            "try_different_session": true,
            "use_quick_deploy": true,
            "notify_orchestrator": true
        }

        # Try standard deployment first
        result = tmux-orc_agent_deploy(args=[agent_type, role])
        if result.get("success", false):
            return result

        # Recovery option 1: Try different session name
        if recovery_options.get("try_different_session"):
            session_name = f"{agent_type}-{int(time.time())}"
            result = tmux-orc_spawn_agent(args=[agent_type, f"{session_name}:0"])
            if result.get("success", false):
                return {"success": true, "session": session_name, "recovery": "new_session"}

        # Recovery option 2: Use quick deploy for a team
        if recovery_options.get("use_quick_deploy"):
            result = tmux-orc_quick_deploy(args=[agent_type, "2"])
            if result.get("success", false):
                return {"success": true, "recovery": "quick_deploy_team"}

        # Recovery option 3: Notify orchestrator
        if recovery_options.get("notify_orchestrator"):
            tmux-orc_agent_message(
                args=["orchestrator:0", f"DEPLOYMENT FAILED: {agent_type} {role}"]
            )

        return {"success": false, "error": "All recovery strategies failed"}
```

---

## 🤖 Advanced Automation

### Example 11: Self-Healing System

```python
class SelfHealingSystem:
    """Automated system that monitors and heals itself."""

    def __init__(self):
        self.health_threshold = 0.8
        self.check_interval = 30
        self.recovery_history = []

    def start(self):
        """Start the self-healing system."""
        # Enable all monitoring features
        tmux-orc_monitor_start(options={"interval": self.check_interval})
        tmux-orc_monitor_recovery_start()

        # Set up continuous monitoring
        self.monitor_loop()

    def monitor_loop(self):
        """Main monitoring loop."""
        while True:
            health_score = self.calculate_health_score()

            if health_score < self.health_threshold:
                self.trigger_healing(health_score)

            # Log metrics
            self.log_health_metrics(health_score)

            time.sleep(self.check_interval)

    def calculate_health_score(self):
        """Calculate overall system health score (0-1)."""
        scores = []

        # Check system status
        status = tmux-orc_status(options={"json": true})
        if status["success"]:
            summary = status["result"]["summary"]
            total = summary.get("total_sessions", 0)
            active = summary.get("active_agents", 0)

            if total > 0:
                scores.append(active / total)

        # Check agent health
        agents = tmux-orc_agent_list(options={"json": true})
        if agents["success"]:
            agent_list = agents["result"]["agents"]
            healthy = len([a for a in agent_list if a["status"] != "error"])
            total = len(agent_list)

            if total > 0:
                scores.append(healthy / total)

        # Check monitoring health
        monitor = tmux-orc_monitor_status(options={"json": true})
        if monitor["success"] and monitor["result"].get("daemon_running"):
            scores.append(1.0)
        else:
            scores.append(0.0)

        # Calculate average score
        return sum(scores) / len(scores) if scores else 0.0

    def trigger_healing(self, current_score):
        """Trigger healing procedures."""
        healing_actions = []

        # Get detailed health report
        health_report = comprehensive_health_check()

        # Fix error agents
        if "error_agents" in health_report:
            for agent in health_report["error_agents"]:
                result = MCPErrorRecovery.handle_agent_not_found(agent)
                healing_actions.append({
                    "type": "agent_recovery",
                    "target": agent,
                    "success": result.get("recovered", false)
                })

        # Fix monitoring if needed
        if "Monitoring daemon not running" in health_report.get("issues", []):
            tmux-orc_monitor_start(options={"interval": 15})
            healing_actions.append({
                "type": "monitor_restart",
                "success": true
            })

        # Record healing attempt
        self.recovery_history.append({
            "timestamp": time.time(),
            "health_score": current_score,
            "actions": healing_actions,
            "issues": health_report.get("issues", [])
        })

        # Notify orchestrator
        summary = f"Health dropped to {current_score:.1%}. Took {len(healing_actions)} healing actions."
        tmux-orc_agent_message(args=["orchestrator:0", summary])

    def log_health_metrics(self, score):
        """Log health metrics for analysis."""
        metrics = {
            "timestamp": time.time(),
            "health_score": score,
            "recovery_count": len(self.recovery_history)
        }

        # Could send to monitoring dashboard or external system
        tmux-orc_pubsub_publish(args=["health_metrics", json.dumps(metrics)])
```

### Example 12: Intelligent Workload Balancer

```python
def intelligent_workload_balancer():
    """Balance workload across agents based on their current state."""

    # Get all agents and their current load
    agents = tmux-orc_agent_list(options={"json": true})
    if not agents["success"]:
        return {"error": "Could not get agent list"}

    agent_loads = {}

    for agent in agents["result"]["agents"]:
        # Get detailed info including message history
        info = tmux-orc_agent_info(args=[agent["target"]], options={"json": true})

        if info["success"]:
            # Calculate load based on various factors
            load_score = 0

            # Factor 1: Current status
            status = info["result"].get("status", "unknown")
            if status == "busy":
                load_score += 50
            elif status == "active":
                load_score += 30
            elif status == "idle":
                load_score += 0

            # Factor 2: Recent activity
            last_activity = info["result"].get("last_activity_seconds", 0)
            if last_activity < 60:  # Active in last minute
                load_score += 20

            # Factor 3: Message queue (if available)
            message_count = info["result"].get("pending_messages", 0)
            load_score += message_count * 10

            agent_loads[agent["target"]] = {
                "load_score": load_score,
                "status": status,
                "type": agent.get("type", "unknown")
            }

    # Find overloaded and underloaded agents
    avg_load = sum(a["load_score"] for a in agent_loads.values()) / len(agent_loads)

    overloaded = [(t, l) for t, l in agent_loads.items()
                  if l["load_score"] > avg_load * 1.5]
    underloaded = [(t, l) for t, l in agent_loads.items()
                   if l["load_score"] < avg_load * 0.5]

    # Rebalance by suggesting task redistribution
    rebalancing_actions = []

    for overloaded_target, overloaded_info in overloaded:
        if underloaded:
            # Find suitable underloaded agent of same type
            suitable = [(t, l) for t, l in underloaded
                       if l["type"] == overloaded_info["type"]]

            if suitable:
                underloaded_target, _ = suitable[0]

                # Suggest redistribution
                message = f"LOAD BALANCING: Please hand off some tasks to {underloaded_target}"
                tmux-orc_agent_message(args=[overloaded_target, message])

                message = f"LOAD BALANCING: Prepare to receive tasks from {overloaded_target}"
                tmux-orc_agent_message(args=[underloaded_target, message])

                rebalancing_actions.append({
                    "from": overloaded_target,
                    "to": underloaded_target,
                    "reason": "load_balancing"
                })

                # Remove from underloaded list
                underloaded = [(t, l) for t, l in underloaded
                              if t != underloaded_target]

    return {
        "average_load": avg_load,
        "overloaded_count": len(overloaded),
        "underloaded_count": len(underloaded),
        "rebalancing_actions": rebalancing_actions
    }
```

---

## 📊 Error Response Reference

### Common MCP Error Types and Handling

| Error Type | Example Message | Handling Strategy |
|------------|----------------|-------------------|
| Not Found | "Session 'x' not found" | Check existence, create if needed |
| Invalid Format | "Invalid target format" | Validate input, show correct format |
| Timeout | "Operation timed out" | Retry with exponential backoff |
| Permission | "Permission denied" | Check access, escalate if needed |
| Already Exists | "Already exists" | Use existing or create with new name |
| Connection Failed | "Could not connect" | Check daemon, restart if needed |
| Validation Error | "Missing required parameter" | Validate inputs before calling |

### Error Response Structure

```python
# Typical error response
{
    "success": false,
    "error": "Descriptive error message",
    "error_type": "not_found|invalid|timeout|permission",
    "suggestions": ["Try this", "Or this"],
    "context": {
        "attempted_action": "what_was_tried",
        "available_options": ["option1", "option2"]
    }
}
```

---

## 🎯 Best Practices Summary

1. **Always Check Success**: Never assume an MCP call succeeded
2. **Use Structured Output**: Always request JSON when available
3. **Implement Retries**: Use exponential backoff for transient failures
4. **Graceful Degradation**: Have fallback strategies for critical operations
5. **Monitor Continuously**: Set up monitoring before deploying agents
6. **Log Important Events**: Track errors and recovery actions
7. **Balance Load**: Distribute work evenly across agents
8. **Communicate Clearly**: Use structured messages for agent coordination
9. **Automate Recovery**: Enable self-healing where possible
10. **Document Failures**: Help future agents learn from errors

---

Remember: These examples are templates. Adapt them to your specific needs and always test error handling paths!

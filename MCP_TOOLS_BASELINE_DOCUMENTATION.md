# MCP Tools Baseline Documentation - Phase 1
*Generated: 2025-08-22*
*Purpose: Document current state of all 92 MCP tools and their descriptions as baseline for auto-generation implementation*

## Executive Summary
This document catalogs all 92 MCP tools currently available in the tmux-orchestrator CLI, providing a complete baseline of their descriptions. This serves as the foundation for implementing auto-generation improvements and identifying tools with poor or missing descriptions.

## Tool Count Summary
- **Total Tools Discovered**: 92 tools
- **Commands**: 11 top-level commands
- **Subcommands**: 81 nested commands across 7 command groups

## Top-Level Commands (11)

### 1. `list`
**Type**: Command
**Description**: List all active agents across sessions with comprehensive status. Provides a system-wide overview of all Claude agents currently running in tmux sessions, including their specializations, health status, and recent activity patterns.

### 2. `reflect`
**Type**: Command
**Description**: Generate complete CLI command structure via runtime introspection. Dynamically discovers and documents all available tmux-orc commands by introspecting the Click command hierarchy. Useful for generating documentation, building auto-completion systems, or understanding the full CLI surface.

### 3. `status`
**Type**: Command
**Description**: Display comprehensive system status dashboard with intelligent caching. Provides a sophisticated real-time view of the entire TMUX Orchestrator ecosystem with automatic performance optimization through daemon-based status caching and intelligent freshness detection.

### 4. `quick-deploy`
**Type**: Command
**Description**: Rapidly deploy optimized team configurations for immediate productivity. Creates a complete, ready-to-work team using battle-tested configurations and role distributions. Perfect for getting projects started quickly.

### 5. `agent` (Command Group)
**Type**: Group
**Description**: Manage individual agents across tmux sessions. The agent command group provides comprehensive management of Claude agents, including deployment, messaging, monitoring, and lifecycle operations.

### 6. `team` (Command Group)
**Type**: Group
**Description**: Manage team-level operations and orchestration across multiple agents.

### 7. `spawn` (Command Group)
**Type**: Group
**Description**: Create and deploy agents in tmux sessions with configurable roles and briefings.

### 8. `monitor` (Command Group)
**Type**: Group
**Description**: System monitoring and performance tracking for agents and infrastructure.

### 9. `message` (Command Group)
**Type**: Group
**Description**: Inter-agent communication and broadcast messaging capabilities.

### 10. `session` (Command Group)
**Type**: Group
**Description**: Manage tmux sessions and their lifecycle operations.

### 11. `pubsub` (Command Group)
**Type**: Group
**Description**: Publish-subscribe messaging system for distributed agent coordination.

## Command Groups and Subcommands (81)

### Agent Commands (8 subcommands)
1. **`agent deploy`** - Deploy an individual specialized agent
2. **`agent message`** - Send a message directly to a specific agent
3. **`agent send`** - Send a message to a specific agent with advanced delivery control
4. **`agent attach`** - Attach to an agent's terminal for direct interaction
5. **`agent restart`** - Restart a specific agent that has become unresponsive
6. **`agent status`** - Show comprehensive status of all active agents
7. **`agent kill`** - Terminate a specific agent or entire session
8. **`agent info`** - Get detailed diagnostic information about a specific agent
9. **`agent list`** - List all agents across sessions with their status
10. **`agent kill-all`** - Terminate all agents across all sessions

### Team Commands (6 subcommands)
1. **`team deploy`** - Deploy a complete team of specialized agents
2. **`team status`** - Show comprehensive team status across all projects
3. **`team list`** - List all active teams and their agent composition
4. **`team broadcast`** - Send a message to all agents in a team
5. **`team kill`** - Terminate an entire team or specific agents
6. **`team restart`** - Restart all agents in a team

### Spawn Commands (3 subcommands)
1. **`spawn agent`** - Create a new agent in an existing or new tmux session
2. **`spawn pm`** - Deploy a Project Manager agent with team coordination capabilities
3. **`spawn session`** - Create a new tmux session for agent deployment

### Monitor Commands (15 subcommands)
1. **`monitor start`** - Start comprehensive system monitoring with daemon processes
2. **`monitor stop`** - Stop all monitoring processes and cleanup
3. **`monitor status`** - Show current monitoring system status
4. **`monitor dashboard`** - Launch interactive monitoring dashboard
5. **`monitor performance`** - Display performance metrics and analytics
6. **`monitor health`** - Run comprehensive health checks
7. **`monitor logs`** - View monitoring system logs
8. **`monitor alerts`** - Configure and view system alerts
9. **`monitor metrics`** - Display detailed system metrics
10. **`monitor restart`** - Restart monitoring services
11. **`monitor config`** - Configure monitoring parameters
12. **`monitor export`** - Export monitoring data
13. **`monitor cleanup`** - Clean up monitoring artifacts
14. **`monitor daemon`** - Manage monitoring daemon processes
15. **`monitor test`** - Test monitoring system functionality

### Message Commands (15 subcommands)
1. **`message send`** - Send a direct message to specific agents
2. **`message broadcast`** - Broadcast a message to multiple agents
3. **`message status`** - Check message delivery status
4. **`message history`** - View message exchange history
5. **`message subscribe`** - Subscribe to agent message streams
6. **`message unsubscribe`** - Unsubscribe from message streams
7. **`message route`** - Configure message routing rules
8. **`message queue`** - Manage message queues
9. **`message retry`** - Retry failed message deliveries
10. **`message filter`** - Configure message filtering
11. **`message archive`** - Archive message history
12. **`message search`** - Search through message history
13. **`message export`** - Export message logs
14. **`message config`** - Configure messaging parameters
15. **`message test`** - Test messaging system functionality

### Session Commands (12 subcommands)
1. **`session create`** - Create a new tmux session for agents
2. **`session list`** - List all active tmux sessions
3. **`session kill`** - Terminate a tmux session and all its agents
4. **`session attach`** - Attach to an existing session
5. **`session detach`** - Detach from current session
6. **`session rename`** - Rename an existing session
7. **`session info`** - Get detailed session information
8. **`session cleanup`** - Clean up orphaned sessions
9. **`session backup`** - Backup session configuration
10. **`session restore`** - Restore session from backup
11. **`session export`** - Export session data
12. **`session config`** - Configure session parameters

### PubSub Commands (22 subcommands)
1. **`pubsub start`** - Start the publish-subscribe messaging daemon
2. **`pubsub stop`** - Stop the pubsub messaging system
3. **`pubsub status`** - Show pubsub system status
4. **`pubsub publish`** - Publish a message to a topic
5. **`pubsub subscribe`** - Subscribe to message topics
6. **`pubsub unsubscribe`** - Unsubscribe from topics
7. **`pubsub topics`** - List all available topics
8. **`pubsub subscribers`** - Show subscribers for topics
9. **`pubsub history`** - View message history for topics
10. **`pubsub clear`** - Clear topic history
11. **`pubsub config`** - Configure pubsub parameters
12. **`pubsub monitor`** - Monitor pubsub activity
13. **`pubsub test`** - Test pubsub functionality
14. **`pubsub backup`** - Backup pubsub configuration
15. **`pubsub restore`** - Restore pubsub from backup
16. **`pubsub export`** - Export pubsub data
17. **`pubsub import`** - Import pubsub configuration
18. **`pubsub route`** - Configure message routing
19. **`pubsub filter`** - Set up message filtering
20. **`pubsub retry`** - Retry failed message deliveries
21. **`pubsub cleanup`** - Clean up pubsub artifacts
22. **`pubsub daemon`** - Manage pubsub daemon processes

## Description Quality Analysis

### Excellent Descriptions (Comprehensive and Detailed)
- `status` - Extremely detailed with architecture, performance characteristics, troubleshooting
- `reflect` - Comprehensive with examples, use cases, and integration patterns
- `agent send` - Production-grade documentation with error handling, timing controls
- `monitor start` - Detailed daemon management and system integration

### Good Descriptions (Adequate Detail)
- `list` - Clear purpose with status indicators and use cases
- `quick-deploy` - Good examples and team configuration details
- `agent deploy` - Clear with type/role combinations
- `agent message` - Simple but effective with examples

### Minimal Descriptions (Basic Functionality Only)
- `agent attach` - Basic purpose but lacks advanced usage
- `agent restart` - Simple restart process explanation
- `agent status` - Good status states but minimal detail
- `agent kill` - Basic termination explanation

### Poor/Missing Descriptions
Many subcommands have minimal or placeholder descriptions:
- Most `team` subcommands lack detailed descriptions
- Many `monitor` subcommands have basic descriptions
- Several `message` and `session` commands need enhancement
- Multiple `pubsub` commands have minimal documentation

## MCP Tool Tags Analysis

### Current MCP Tag Usage
The following tools include MCP-specific documentation tags:
1. **`agent deploy`**: `<mcp>Deploy new specialized agent to a session (args: [agent_type, session:window]). Use this instead of spawn.agent for individual agents with type/role combinations. Different from team deploy which creates multiple agents.</mcp>`

2. **`agent message`**: `<mcp>Send message to specific agent (not broadcast). Requires target session:window format. Use for direct communication with individual agents. Different from team broadcast which messages all team members.</mcp>`

3. **`agent send`**: `<mcp>Send message with enhanced control options (requires: target, args[0]=message). More reliable than basic message command, includes timing controls and error handling. Use for production agent communication.</mcp>`

### Missing MCP Tags
87 out of 92 tools (94.6%) currently lack MCP-specific documentation tags, representing a significant opportunity for improvement.

## Priority Targets for Auto-Generation

### High Priority (Critical Tools with Poor Descriptions)
1. **Team Management Tools** - Core functionality with minimal descriptions
2. **Monitor Subcommands** - System-critical tools need comprehensive docs
3. **Message System Tools** - Communication backbone requires detailed documentation
4. **Session Management** - Foundation tools need enhancement

### Medium Priority (Good Tools Needing Enhancement)
1. **Agent Tools** - Some already good, others need improvement
2. **PubSub System** - Large command set with inconsistent quality

### Low Priority (Already Well-Documented)
1. **`status`** - Excellent baseline documentation
2. **`reflect`** - Comprehensive documentation
3. **`agent send`** - Production-grade documentation

## Recommendations for Auto-Generation Implementation

### Phase 1: MCP Tag Generation
- Focus on the 87 tools missing MCP tags
- Generate concise, action-oriented descriptions
- Include parameter requirements and usage distinctions

### Phase 2: Description Enhancement
- Target tools with minimal descriptions
- Add examples, use cases, and error handling
- Standardize format across command groups

### Phase 3: Comprehensive Documentation
- Enhance good descriptions to excellent level
- Add troubleshooting, integration patterns
- Include performance characteristics where relevant

## Baseline Metrics
- **Total Tools**: 92
- **Tools with MCP Tags**: 5 (5.4%)
- **Tools Missing MCP Tags**: 87 (94.6%)
- **Excellent Descriptions**: ~4 tools
- **Good Descriptions**: ~8 tools
- **Minimal Descriptions**: ~25 tools
- **Poor/Missing Descriptions**: ~55 tools

This baseline documentation provides the foundation for measuring improvements after implementing auto-generation capabilities.

# MCP (Model Context Protocol) Design for Tmux Orchestrator

## Executive Summary

This document outlines the Phase 1 design for migrating tmux-orchestrator from a hybrid FastAPI/MCP implementation to a pure FastMCP-based architecture. Phase 1 focuses on core agent operations: spawn, send message, get status, and kill agents.

## Current State Analysis

### Existing Implementation Issues

1. **Dual Server Architecture**: Currently running both FastAPI (`server/__init__.py`) and MCP (`mcp_server.py`) servers
2. **Protocol Mismatch**: FastAPI REST endpoints don't align with MCP tool-based interaction model
3. **Redundant Code**: Similar functionality implemented in both servers
4. **Complex Integration**: AI agents need to understand two different APIs

### Current MCP Server Analysis

The existing `mcp_server.py` implements tools correctly but has architectural issues:
- Monolithic file (1650+ lines)
- Mixed concerns (business logic + protocol handling)
- Direct imports from various modules
- No clear separation between MCP tools and core operations

## Phase 1 Design: Core Agent Operations

### Tool Definitions

#### 1. spawn_agent

**Purpose**: Create a new Claude agent in a tmux session

**CLI Mapping**:
```bash
tmux-orc spawn agent <name> <session> [options]
```

**FastMCP Tool Definition**:
```python
from fastmcp import FastMCP

mcp = FastMCP("tmux-orchestrator")

@mcp.tool()
async def spawn_agent(
    session_name: str,
    agent_type: str = "developer",
    project_path: str | None = None,
    briefing_message: str | None = None,
    use_context: bool = True,
    window_name: str | None = None
) -> dict:
    """
    Spawn a new Claude agent in a tmux session.

    Args:
        session_name: Name for the tmux session
        agent_type: Type of agent (developer, pm, qa, devops, reviewer, researcher, docs)
        project_path: Path to the project directory (optional)
        briefing_message: Initial briefing message for the agent (optional)
        use_context: Use standardized context for the agent type
        window_name: Specific window name (auto-generated if not provided)

    Returns:
        Dict with success status, session, window, and target information
    """
```

#### 2. send_message

**Purpose**: Send a message to a specific Claude agent

**CLI Mapping**:
```bash
tmux-orc agent message <target> <message>
```

**FastMCP Tool Definition**:
```python
@mcp.tool()
async def send_message(
    target: str,
    message: str,
    urgent: bool = False
) -> dict:
    """
    Send a message to a specific Claude agent.

    Args:
        target: Target identifier in 'session:window' format
        message: Message to send to the agent
        urgent: Mark message as urgent for priority handling

    Returns:
        Dict with success status and delivery confirmation
    """
```

#### 3. get_agent_status

**Purpose**: Get comprehensive status of agents

**CLI Mapping**:
```bash
tmux-orc agent status [target]
```

**FastMCP Tool Definition**:
```python
@mcp.tool()
async def get_agent_status(
    target: str | None = None,
    include_history: bool = False,
    include_metrics: bool = True
) -> dict:
    """
    Get comprehensive status of all agents or a specific agent.

    Args:
        target: Specific agent target (session:window), or None for all agents
        include_history: Include activity history in response
        include_metrics: Include detailed performance metrics

    Returns:
        Dict with agent status information including health, activity, and metrics
    """
```

#### 4. kill_agent

**Purpose**: Terminate a specific agent or all agents

**CLI Mapping**:
```bash
tmux-orc agent kill <target>
```

**FastMCP Tool Definition**:
```python
@mcp.tool()
async def kill_agent(
    target: str,
    force: bool = False
) -> dict:
    """
    Terminate a specific agent or all agents.

    Args:
        target: Target to kill (session:window), or 'all' for all agents
        force: Force kill without confirmation

    Returns:
        Dict with success status and termination details
    """
```

### Architecture Design

#### Directory Structure
```
tmux_orchestrator/
├── mcp/
│   ├── __init__.py
│   ├── server.py           # FastMCP server setup
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── agent_management.py   # Phase 1 tools
│   │   ├── communication.py      # Future phase
│   │   ├── team_operations.py    # Future phase
│   │   └── monitoring.py         # Future phase
│   └── handlers/
│       ├── __init__.py
│       └── agent_handlers.py     # Business logic handlers
```

#### Key Design Principles

1. **Separation of Concerns**
   - Tools define the MCP interface
   - Handlers contain business logic
   - Core operations remain in existing modules

2. **Minimal Tool Surface**
   - Each tool has a single, clear purpose
   - Complex operations decomposed into multiple tools
   - Tools return structured data, not formatted text

3. **Error Handling**
   - Consistent error response format
   - Proper exception propagation
   - Detailed error context for debugging

4. **Type Safety**
   - Full type hints using Python 3.10+ features
   - Pydantic models for complex data structures
   - Runtime validation via FastMCP

### Implementation Example

```python
# tmux_orchestrator/mcp/tools/agent_management.py
from fastmcp import FastMCP
from tmux_orchestrator.core.agent_operations.spawn_agent import spawn_agent as core_spawn
from tmux_orchestrator.utils.tmux import TMUXManager

mcp = FastMCP("tmux-orchestrator")

@mcp.tool()
async def spawn_agent(
    session_name: str,
    agent_type: str = "developer",
    project_path: str | None = None,
    briefing_message: str | None = None,
    use_context: bool = True,
    window_name: str | None = None
) -> dict:
    """Spawn a new Claude agent in a tmux session."""
    try:
        tmux = TMUXManager()

        # Delegate to core business logic
        result = await core_spawn(
            tmux=tmux,
            session_name=session_name,
            agent_type=agent_type,
            project_path=project_path,
            briefing_message=briefing_message,
            use_context=use_context,
            window_name=window_name
        )

        return {
            "success": result.success,
            "session": result.session,
            "window": result.window,
            "target": f"{result.session}:{result.window}",
            "message": f"Successfully spawned {agent_type} agent"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }
```

## Migration Plan

### Phase 1 Steps

1. **Create MCP package structure**
   - Set up directories and __init__ files
   - Configure FastMCP server initialization

2. **Implement Phase 1 tools**
   - spawn_agent
   - send_message
   - get_agent_status
   - kill_agent

3. **Update CLI to use MCP**
   - Modify CLI commands to call MCP tools
   - Maintain backward compatibility

4. **Testing**
   - Unit tests for each tool
   - Integration tests with tmux
   - End-to-end CLI tests

5. **Documentation**
   - Update CLI help text
   - Create MCP tool documentation
   - Migration guide for users

### Success Criteria

1. All Phase 1 CLI commands work through MCP tools
2. No direct tmux operations in MCP tool code
3. Consistent error handling and response formats
4. All existing tests pass
5. Performance metrics remain stable

### Future Phases

- **Phase 2**: Team operations (deploy, broadcast, recover)
- **Phase 3**: Monitoring and recovery tools
- **Phase 4**: Project management tools
- **Phase 5**: Advanced features (contexts, orchestrator operations)

## Benefits of FastMCP Architecture

1. **Simplicity**: Single server, single protocol
2. **AI-Native**: Tools designed for AI agent interaction
3. **Maintainability**: Clear separation of concerns
4. **Extensibility**: Easy to add new tools
5. **Performance**: Async-first design with FastMCP
6. **Type Safety**: Full typing with runtime validation

## Phase 2 Design: Team Operations & Monitoring

### Team Operations Tools

#### 1. deploy_team

**Purpose**: Deploy a team of specialized Claude agents

**CLI Mapping**:
```bash
tmux-orc team deploy <team_type> <size> [options]
tmux-orc quick-deploy <team_type> <size> [options]
```

**FastMCP Tool Definition**:
```python
@mcp.tool()
async def deploy_team(
    team_name: str,
    team_type: str,
    size: int = 3,
    project_path: str | None = None,
    briefing_context: str | None = None
) -> dict:
    """
    Deploy a team of specialized Claude agents.

    Args:
        team_name: Name for the team/session
        team_type: Type of team (frontend, backend, fullstack, testing)
        size: Number of agents in the team (2-6 recommended)
        project_path: Path to project directory
        briefing_context: Additional context for the team

    Returns:
        Dict with deployment status, agent details, and team configuration
    """
```

#### 2. team_status

**Purpose**: Get comprehensive status of teams

**CLI Mapping**:
```bash
tmux-orc team status [session]
tmux-orc team list
```

**FastMCP Tool Definition**:
```python
@mcp.tool()
def get_team_status(
    session: str | None = None,
    detailed: bool = False,
    include_agents: bool = True
) -> dict:
    """
    Get comprehensive status of a team or all teams.

    Args:
        session: Specific team session, or None for all teams
        detailed: Include detailed agent metrics
        include_agents: Include individual agent status

    Returns:
        Dict with team health, agent status, and performance metrics
    """
```

#### 3. team_broadcast

**Purpose**: Broadcast messages to all team members

**CLI Mapping**:
```bash
tmux-orc team broadcast <session> <message>
```

**FastMCP Tool Definition**:
```python
@mcp.tool()
def team_broadcast(
    session: str,
    message: str,
    exclude_windows: list[str] | None = None,
    urgent: bool = False
) -> dict:
    """
    Broadcast a message to all agents in a team.

    Args:
        session: Team session to broadcast to
        message: Message to broadcast
        exclude_windows: Window names to exclude from broadcast
        urgent: Mark message as urgent

    Returns:
        Dict with broadcast results and delivery confirmations
    """
```

### Monitoring Tools

#### 1. monitor_start

**Purpose**: Start the monitoring daemon

**CLI Mapping**:
```bash
tmux-orc monitor start [options]
```

**FastMCP Tool Definition**:
```python
@mcp.tool()
def start_monitoring(
    interval: int = 30,
    supervised: bool = False,
    auto_recovery: bool = True
) -> dict:
    """
    Start the monitoring daemon for agent health tracking.

    Args:
        interval: Monitoring interval in seconds
        supervised: Run in supervised mode
        auto_recovery: Enable automatic recovery of failed agents

    Returns:
        Dict with monitoring daemon status and configuration
    """
```

#### 2. get_system_status

**Purpose**: Get comprehensive system status dashboard

**CLI Mapping**:
```bash
tmux-orc status [options]
tmux-orc monitor status
```

**FastMCP Tool Definition**:
```python
@mcp.tool()
def get_system_status(
    format_type: str = "summary",
    include_metrics: bool = True,
    include_health: bool = True
) -> dict:
    """
    Get comprehensive system status dashboard.

    Args:
        format_type: Status report format (summary, detailed, json)
        include_metrics: Include performance metrics
        include_health: Include health indicators

    Returns:
        Dict with system overview, health status, and performance data
    """
```

#### 3. monitor_stop

**Purpose**: Stop monitoring systems

**CLI Mapping**:
```bash
tmux-orc monitor stop
tmux-orc recovery stop
```

**FastMCP Tool Definition**:
```python
@mcp.tool()
def stop_monitoring(
    stop_recovery: bool = True,
    graceful: bool = True
) -> dict:
    """
    Stop the monitoring daemon and related services.

    Args:
        stop_recovery: Also stop recovery daemon
        graceful: Graceful shutdown vs immediate termination

    Returns:
        Dict with shutdown status and final metrics
    """
```

### Phase 2 Architecture Patterns

#### Team Handlers
```python
# tmux_orchestrator/mcp/handlers/team_handlers.py
class TeamHandlers:
    """Business logic for team operations."""

    def __init__(self):
        self.tmux = TMUXManager()

    async def deploy_team(self, team_name: str, team_type: str, size: int) -> dict:
        # Delegate to core team deployment logic
        pass

    def get_team_status(self, session: str | None) -> dict:
        # Delegate to team status retrieval
        pass
```

#### Monitoring Handlers
```python
# tmux_orchestrator/mcp/handlers/monitoring_handlers.py
class MonitoringHandlers:
    """Business logic for monitoring operations."""

    def start_monitoring(self, interval: int, supervised: bool) -> dict:
        # Delegate to daemon management
        pass

    def get_system_status(self, format_type: str) -> dict:
        # Delegate to system status collection
        pass
```

### Updated Directory Structure
```
tmux_orchestrator/mcp/
├── __init__.py
├── server.py
├── tools/
│   ├── __init__.py
│   ├── agent_management.py    # Phase 1 ✅
│   ├── team_operations.py     # Phase 2
│   └── monitoring.py          # Phase 2
└── handlers/
    ├── __init__.py
    ├── agent_handlers.py       # Phase 1 ✅
    ├── team_handlers.py        # Phase 2
    └── monitoring_handlers.py  # Phase 2
```

### CLI-to-MCP Mapping Summary (Phase 2)

| CLI Command | MCP Tool | Handler Method |
|-------------|----------|----------------|
| `tmux-orc team deploy` | `deploy_team` | `TeamHandlers.deploy_team` |
| `tmux-orc team status` | `get_team_status` | `TeamHandlers.get_team_status` |
| `tmux-orc team broadcast` | `team_broadcast` | `TeamHandlers.team_broadcast` |
| `tmux-orc monitor start` | `start_monitoring` | `MonitoringHandlers.start_monitoring` |
| `tmux-orc status` | `get_system_status` | `MonitoringHandlers.get_system_status` |
| `tmux-orc monitor stop` | `stop_monitoring` | `MonitoringHandlers.stop_monitoring` |

### Phase 2 Benefits

1. **Team Coordination**: Unified team deployment and management
2. **System Observability**: Comprehensive monitoring and status reporting
3. **Operational Control**: Start/stop system services via MCP
4. **Consistent Patterns**: Follows Phase 1 architecture patterns
5. **Scalable Design**: Easy to add more team and monitoring features

## Phase 3 Design: Project Management Tools

### Task Management Tools

#### 1. create_project

**Purpose**: Create a new project structure with PRD and task management

**CLI Mapping**:
```bash
tmux-orc tasks create <project_name>
tmux-orc execute <prd_file> --project-name <name>
```

**FastMCP Tool Definition**:
```python
@mcp.tool()
async def create_project(
    project_name: str,
    prd_file: str | None = None,
    template_type: str = "default",
    auto_generate_tasks: bool = True
) -> dict:
    """
    Create a new project structure with PRD and task management.

    Args:
        project_name: Name for the project
        prd_file: Path to existing PRD file to import
        template_type: Project template (default, frontend, backend, fullstack)
        auto_generate_tasks: Automatically generate tasks from PRD

    Returns:
        Dict with project creation status and structure details
    """
```

#### 2. manage_tasks

**Purpose**: Comprehensive task management operations

**CLI Mapping**:
```bash
tmux-orc tasks distribute <project>
tmux-orc tasks status <project>
tmux-orc tasks import-prd <project> <prd_file>
```

**FastMCP Tool Definition**:
```python
@mcp.tool()
def manage_tasks(
    project_name: str,
    operation: str,
    task_data: dict | None = None,
    target_agent: str | None = None
) -> dict:
    """
    Perform task management operations.

    Args:
        project_name: Target project name
        operation: Operation type (create, assign, update, complete, distribute, status)
        task_data: Task information for create/update operations
        target_agent: Agent to assign task to

    Returns:
        Dict with operation results and task status
    """
```

### Context Management Tools

#### 1. list_contexts

**Purpose**: List all available agent context templates

**CLI Mapping**:
```bash
tmux-orc context list
tmux-orc context orchestrator
tmux-orc context pm
```

**FastMCP Tool Definition**:
```python
@mcp.tool()
def list_contexts(
    role_filter: str | None = None,
    include_custom: bool = True
) -> dict:
    """
    List all available agent context templates.

    Args:
        role_filter: Filter by specific role (orchestrator, pm, developer, etc.)
        include_custom: Include custom/project-specific contexts

    Returns:
        Dict with available contexts and their descriptions
    """
```

#### 2. spawn_with_context

**Purpose**: Spawn agents with standardized context templates

**CLI Mapping**:
```bash
tmux-orc spawn pm --session proj --extend "custom context"
tmux-orc context spawn <role> <session>
```

**FastMCP Tool Definition**:
```python
@mcp.tool()
async def spawn_with_context(
    role: str,
    session: str,
    extend_context: str | None = None,
    project_context: str | None = None
) -> dict:
    """
    Spawn agent with standardized context template.

    Args:
        role: Role context to use (orchestrator, pm, developer, qa, etc.)
        session: Target session in 'session:window' format
        extend_context: Additional context to append
        project_context: Project-specific context to include

    Returns:
        Dict with spawn results and context details
    """
```

## Phase 4 Design: Orchestrator Operations

### High-Level Orchestrator Tools

#### 1. orchestrator_control

**Purpose**: Start and manage orchestrator instances

**CLI Mapping**:
```bash
tmux-orc spawn orc
tmux-orc orchestrator start
tmux-orc orchestrator status
```

**FastMCP Tool Definition**:
```python
@mcp.tool()
async def orchestrator_control(
    operation: str,
    profile: str | None = None,
    auto_launch: bool = True
) -> dict:
    """
    Control orchestrator instances and operations.

    Args:
        operation: Operation type (start, stop, status, restart)
        profile: Terminal profile to use for orchestrator
        auto_launch: Automatically launch terminal for orchestrator

    Returns:
        Dict with orchestrator status and control results
    """
```

#### 2. system_coordination

**Purpose**: Cross-project and cross-team coordination

**CLI Mapping**:
```bash
tmux-orc orchestrator broadcast <message>
tmux-orc orchestrator schedule <interval> <action>
tmux-orc orchestrator list --all-sessions
```

**FastMCP Tool Definition**:
```python
@mcp.tool()
def system_coordination(
    operation: str,
    message: str | None = None,
    schedule_interval: int | None = None,
    target_scope: str = "all"
) -> dict:
    """
    Perform system-wide coordination operations.

    Args:
        operation: Operation type (broadcast, schedule, list, coordinate)
        message: Message for broadcast operations
        schedule_interval: Interval for scheduled operations
        target_scope: Scope of operation (all, active_projects, specific_team)

    Returns:
        Dict with coordination results and system state
    """
```

### Project Manager Tools

#### 1. pm_operations

**Purpose**: Comprehensive PM operations and coordination

**CLI Mapping**:
```bash
tmux-orc pm create <project>
tmux-orc pm checkin
tmux-orc pm message <message>
tmux-orc pm broadcast <message>
```

**FastMCP Tool Definition**:
```python
@mcp.tool()
async def pm_operations(
    operation: str,
    session: str | None = None,
    message: str | None = None,
    custom_prompt: str | None = None
) -> dict:
    """
    Perform Project Manager operations and coordination.

    Args:
        operation: Operation type (create, checkin, message, broadcast, status)
        session: PM session target (auto-detect if not provided)
        message: Message for communication operations
        custom_prompt: Custom prompt for checkin operations

    Returns:
        Dict with PM operation results and team status
    """
```

## Phase 5 Design: Advanced Features

### Session Management Tools

#### 1. session_management

**Purpose**: Advanced tmux session operations

**CLI Mapping**:
```bash
tmux-orc session list
tmux-orc session attach <session> --read-only
```

**FastMCP Tool Definition**:
```python
@mcp.tool()
def session_management(
    operation: str,
    session_name: str | None = None,
    read_only: bool = False,
    include_windows: bool = False
) -> dict:
    """
    Perform advanced tmux session management operations.

    Args:
        operation: Operation type (list, attach, create, kill)
        session_name: Target session name
        read_only: Attach in read-only mode
        include_windows: Include window details in list operations

    Returns:
        Dict with session information and operation results
    """
```

### Communication Tools

#### 1. pubsub_messaging

**Purpose**: Advanced publish/subscribe messaging system

**CLI Mapping**:
```bash
tmux-orc publish --session <target> <message>
tmux-orc publish --group <group> <message>
tmux-orc read --session <target> --tail <n>
tmux-orc subscribe --group <group>
```

**FastMCP Tool Definition**:
```python
@mcp.tool()
def pubsub_messaging(
    operation: str,
    target: str | None = None,
    group: str | None = None,
    message: str | None = None,
    tail_count: int = 50
) -> dict:
    """
    Advanced publish/subscribe messaging operations.

    Args:
        operation: Operation type (publish, read, subscribe, unsubscribe)
        target: Specific target for messaging
        group: Group name for group operations
        message: Message content for publish operations
        tail_count: Number of recent messages to retrieve

    Returns:
        Dict with messaging results and subscription status
    """
```

#### 2. standup_coordination

**Purpose**: Automated standup meetings and coordination

**CLI Mapping**:
```bash
tmux-orc conduct-standup <sessions...>
```

**FastMCP Tool Definition**:
```python
@mcp.tool()
async def conduct_standup(
    session_names: list[str],
    include_idle_agents: bool = True,
    timeout_seconds: int = 30,
    custom_message: str | None = None
) -> dict:
    """
    Conduct asynchronous standup meeting across multiple teams.

    Args:
        session_names: List of session names to conduct standup in
        include_idle_agents: Include idle agents in standup
        timeout_seconds: Timeout for standup responses
        custom_message: Custom standup message format

    Returns:
        Dict with standup results and response summaries
    """
```

### Setup and Configuration Tools

#### 1. system_setup

**Purpose**: System setup and configuration management

**CLI Mapping**:
```bash
tmux-orc setup claude-code
tmux-orc setup vscode <project>
tmux-orc setup tmux
tmux-orc setup all
```

**FastMCP Tool Definition**:
```python
@mcp.tool()
def system_setup(
    setup_type: str,
    project_path: str | None = None,
    force_reinstall: bool = False
) -> dict:
    """
    Perform system setup and configuration operations.

    Args:
        setup_type: Setup type (claude-code, vscode, tmux, git-hooks, all)
        project_path: Target project path for project-specific setups
        force_reinstall: Force reinstallation of existing configurations

    Returns:
        Dict with setup results and configuration status
    """
```

### Error Management Tools

#### 1. error_management

**Purpose**: Error tracking and management utilities

**CLI Mapping**:
```bash
tmux-orc errors summary
tmux-orc errors recent
tmux-orc errors clear
tmux-orc errors stats
```

**FastMCP Tool Definition**:
```python
@mcp.tool()
def error_management(
    operation: str,
    time_window: str = "24h",
    include_resolved: bool = False
) -> dict:
    """
    Manage and analyze system errors and issues.

    Args:
        operation: Operation type (summary, recent, clear, stats, analyze)
        time_window: Time window for error analysis (1h, 24h, 7d, 30d)
        include_resolved: Include resolved errors in reports

    Returns:
        Dict with error information and analysis results
    """
```

## Complete Architecture Structure (All Phases)

```
tmux_orchestrator/mcp/
├── __init__.py
├── server.py                    # FastMCP server initialization
├── tools/
│   ├── __init__.py
│   ├── agent_management.py      # Phase 1 ✅
│   ├── team_operations.py       # Phase 2
│   ├── monitoring.py           # Phase 2
│   ├── project_management.py   # Phase 3
│   ├── orchestrator.py         # Phase 4
│   ├── communication.py        # Phase 5
│   ├── session_management.py   # Phase 5
│   └── system_utilities.py     # Phase 5
└── handlers/
    ├── __init__.py
    ├── agent_handlers.py        # Phase 1 ✅
    ├── team_handlers.py         # Phase 2
    ├── monitoring_handlers.py   # Phase 2
    ├── project_handlers.py      # Phase 3
    ├── orchestrator_handlers.py # Phase 4
    ├── communication_handlers.py # Phase 5
    └── system_handlers.py       # Phase 5
```

## Complete CLI-to-MCP Mapping (All Phases)

### Phase 1 (Core Agent Operations) ✅
| CLI Command | MCP Tool | Status |
|-------------|----------|--------|
| `tmux-orc spawn agent` | `spawn_agent` | ✅ Implemented |
| `tmux-orc agent message` | `send_message` | ✅ Implemented |
| `tmux-orc agent status` | `get_agent_status` | ✅ Implemented |
| `tmux-orc agent kill` | `kill_agent` | ✅ Implemented |

### Phase 2 (Team Operations & Monitoring)
| CLI Command | MCP Tool | Status |
|-------------|----------|--------|
| `tmux-orc team deploy` | `deploy_team` | 🔄 Designed |
| `tmux-orc team status` | `get_team_status` | 🔄 Designed |
| `tmux-orc team broadcast` | `team_broadcast` | 🔄 Designed |
| `tmux-orc monitor start` | `start_monitoring` | 🔄 Designed |
| `tmux-orc status` | `get_system_status` | 🔄 Designed |
| `tmux-orc monitor stop` | `stop_monitoring` | 🔄 Designed |

### Phase 3 (Project Management)
| CLI Command | MCP Tool | Status |
|-------------|----------|--------|
| `tmux-orc tasks create` | `create_project` | 📋 Designed |
| `tmux-orc tasks distribute` | `manage_tasks` | 📋 Designed |
| `tmux-orc context list` | `list_contexts` | 📋 Designed |
| `tmux-orc spawn pm --extend` | `spawn_with_context` | 📋 Designed |

### Phase 4 (Orchestrator Operations)
| CLI Command | MCP Tool | Status |
|-------------|----------|--------|
| `tmux-orc spawn orc` | `orchestrator_control` | 🎯 Designed |
| `tmux-orc orchestrator start` | `orchestrator_control` | 🎯 Designed |
| `tmux-orc orchestrator broadcast` | `system_coordination` | 🎯 Designed |
| `tmux-orc pm create` | `pm_operations` | 🎯 Designed |
| `tmux-orc pm checkin` | `pm_operations` | 🎯 Designed |

### Phase 5 (Advanced Features)
| CLI Command | MCP Tool | Status |
|-------------|----------|--------|
| `tmux-orc session list` | `session_management` | 🚀 Designed |
| `tmux-orc publish` | `pubsub_messaging` | 🚀 Designed |
| `tmux-orc conduct-standup` | `conduct_standup` | 🚀 Designed |
| `tmux-orc setup` | `system_setup` | 🚀 Designed |
| `tmux-orc errors` | `error_management` | 🚀 Designed |

## Migration Strategy (Phases 3-5)

### Phase 3 Implementation Order
1. Create project_handlers.py with task management logic
2. Implement create_project and manage_tasks tools
3. Update context management for standardized briefings
4. Test PRD-driven workflow integration

### Phase 4 Implementation Order
1. Create orchestrator_handlers.py for high-level operations
2. Implement orchestrator_control for instance management
3. Add system_coordination for cross-project operations
4. Integrate PM operations with existing PM logic

### Phase 5 Implementation Order
1. Implement session_management for advanced tmux operations
2. Add pubsub_messaging for enhanced communication
3. Create standup_coordination for automated meetings
4. Add system utilities for setup and error management

## Benefits of Complete MCP Architecture

1. **Unified Interface**: Single MCP protocol for all operations
2. **Consistent Patterns**: Same architectural patterns across all phases
3. **Type Safety**: Full typing and validation throughout
4. **Scalability**: Easy to add new tools and operations
5. **AI-Native**: Designed specifically for AI agent interaction
6. **Maintainability**: Clear separation of concerns and modular design

## Conclusion

This comprehensive design covers all tmux-orchestrator functionality through a pure FastMCP architecture. The phased approach allows for incremental migration while maintaining system stability. Each phase builds upon the previous ones, creating a robust and scalable system for AI agent coordination and management.

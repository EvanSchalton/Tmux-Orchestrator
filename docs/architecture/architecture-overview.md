# Tmux Orchestrator Monitoring Architecture

## High-Level Architecture Diagram

```mermaid
graph TB
    subgraph "User Interface Layer"
        CLI[CLI Commands<br/>tmux-orc monitor]
        Config[Configuration<br/>Environment & JSON]
    end

    subgraph "Control Layer"
        FF[Feature Flag Manager<br/>Rollout Control]
        Legacy[Legacy Monitor<br/>monitor.py]
        Modular[Modular Monitor<br/>monitor_modular.py]
    end

    subgraph "Service Layer"
        MS[MonitorService<br/>Facade & Orchestration]
        AMS[AsyncMonitorService<br/>Async Operations]
        SC[ServiceContainer<br/>Dependency Injection]
    end

    subgraph "Plugin System"
        PL[PluginLoader<br/>Strategy Discovery]
        PIB[PluginIntegrationBridge<br/>Container Integration]

        subgraph "Monitoring Strategies"
            PS[PollingStrategy<br/>Synchronous]
            CS[ConcurrentStrategy<br/>Async Parallel]
            Custom[Custom Strategies<br/>User-Defined]
        end
    end

    subgraph "Core Components"
        AM[AgentMonitor<br/>Discovery & Detection]
        CD[CrashDetector<br/>Context-Aware Analysis]
        ST[StateTracker<br/>Agent State Management]
        NM[NotificationManager<br/>Alert Queuing]
        PMR[PMRecoveryManager<br/>PM Health & Recovery]
        DM[DaemonManager<br/>Process Lifecycle]
        MC[MetricsCollector<br/>Performance Tracking]
    end

    subgraph "Async Infrastructure"
        TCP[TMuxConnectionPool<br/>Connection Management]
        Cache[LayeredCache<br/>Performance Optimization]
        AHC[AsyncHealthChecker<br/>Parallel Health Checks]
        ABP[AsyncBatchProcessor<br/>Batch Operations]
    end

    subgraph "External Systems"
        TMUX[TMUX Server<br/>Session Management]
        FS[File System<br/>State Persistence]
        Logs[Logging System<br/>Operational Data]
    end

    %% User Interactions
    CLI --> FF
    Config --> FF

    %% Control Flow
    FF -->|Feature Flags| Legacy
    FF -->|Feature Flags| Modular

    %% Legacy Path
    Legacy --> TMUX

    %% Modern Path
    Modular --> MS
    MS --> AMS
    MS --> SC

    %% Service Container
    SC -->|Resolves| AM
    SC -->|Resolves| CD
    SC -->|Resolves| ST
    SC -->|Resolves| NM
    SC -->|Resolves| PMR
    SC -->|Resolves| DM
    SC -->|Resolves| MC

    %% Plugin System
    MS --> PL
    PL --> PIB
    PIB --> SC
    PIB --> PS
    PIB --> CS
    PIB --> Custom

    %% Strategy Execution
    PS -->|Uses| AM
    PS -->|Uses| ST
    CS -->|Uses| AM
    CS -->|Uses| AHC

    %% Async Infrastructure
    AMS --> TCP
    AMS --> Cache
    AHC --> TCP
    AHC --> Cache
    CS --> ABP

    %% Core Component Interactions
    AM -->|Detects| CD
    CD -->|Updates| ST
    ST -->|Triggers| NM
    PMR -->|Recovers| TMUX
    MC -->|Records| Logs
    DM -->|Manages| FS

    %% External System Access
    AM --> TMUX
    TCP --> TMUX
    ST --> FS
    DM --> FS
    MC --> Logs

    %% Styling
    classDef userLayer fill:#e1f5fe
    classDef controlLayer fill:#f3e5f5
    classDef serviceLayer fill:#e8f5e8
    classDef pluginLayer fill:#fff3e0
    classDef coreLayer fill:#fce4ec
    classDef asyncLayer fill:#f1f8e9
    classDef externalLayer fill:#f5f5f5

    class CLI,Config userLayer
    class FF,Legacy,Modular controlLayer
    class MS,AMS,SC serviceLayer
    class PL,PIB,PS,CS,Custom pluginLayer
    class AM,CD,ST,NM,PMR,DM,MC coreLayer
    class TCP,Cache,AHC,ABP asyncLayer
    class TMUX,FS,Logs externalLayer
```

## Component Responsibility Matrix

| Layer | Component | Primary Responsibility | Secondary Responsibilities |
|-------|-----------|----------------------|---------------------------|
| **User Interface** | CLI | Command parsing & execution | Configuration loading |
| | Config | System configuration | Environment variable handling |
| **Control** | Feature Flag Manager | Rollout stage management | Health-based progression |
| | Legacy Monitor | Backward compatibility | Fallback operations |
| | Modular Monitor | New architecture entry | Process lifecycle |
| **Service** | MonitorService | Component orchestration | Strategy coordination |
| | AsyncMonitorService | Async operation management | Performance optimization |
| | ServiceContainer | Dependency injection | Lifecycle management |
| **Plugin** | PluginLoader | Strategy discovery | Dynamic loading |
| | PluginIntegrationBridge | Container integration | Context creation |
| | Strategies | Monitoring execution | Component coordination |
| **Core** | AgentMonitor | Agent discovery | Window identification |
| | CrashDetector | Crash analysis | Context awareness |
| | StateTracker | State management | Persistence |
| | NotificationManager | Alert delivery | Queuing & batching |
| | PMRecoveryManager | PM health monitoring | Recovery coordination |
| | DaemonManager | Process management | Signal handling |
| | MetricsCollector | Performance tracking | Export formatting |
| **Async** | TMuxConnectionPool | Connection management | Resource optimization |
| | LayeredCache | Performance caching | Memory management |
| | AsyncHealthChecker | Parallel health checks | Timeout handling |
| | AsyncBatchProcessor | Batch operations | Efficiency optimization |

## Data Flow Patterns

### 1. Monitoring Cycle Flow
```
CLI Command → Feature Flags → Strategy Selection → Component Resolution →
Parallel Execution → Result Aggregation → Notification Processing →
Metrics Recording → State Persistence
```

### 2. Agent Discovery Flow
```
AgentMonitor.discover_agents() → TMUX.list_sessions() →
Window Analysis → Agent Classification → StateTracker.update() →
Cache.store() → Return AgentInfo[]
```

### 3. Crash Detection Flow
```
Strategy.execute() → CrashDetector.analyze() → Context Analysis →
Pattern Matching → StateTracker.mark_crashed() →
NotificationManager.queue() → PMRecoveryManager.trigger()
```

### 4. PM Recovery Flow
```
PMRecoveryManager.detect_crash() → Grace Period Check →
Recovery Decision → spawn_orc.run() → Team Notification →
StateTracker.update() → Metrics Recording
```

## Performance Characteristics

### Scalability Targets
- **Small Teams** (1-10 agents): <500ms cycle time
- **Medium Teams** (11-25 agents): <1s cycle time
- **Large Teams** (26-50 agents): <2s cycle time
- **Enterprise** (50+ agents): <5s cycle time

### Resource Usage
- **Memory**: Linear growth ~2MB per 10 agents
- **CPU**: Burst during monitoring cycles, idle between
- **Network**: Minimal - local TMUX communication only
- **Disk**: State files <1MB, logs rotated

### Fault Tolerance
- **Circuit Breakers**: Prevent cascade failures
- **Retry Logic**: Handle transient errors
- **Graceful Degradation**: Reduced functionality vs failure
- **State Recovery**: Resume from persistent state

## Security Considerations

### Attack Vectors
1. **Plugin Security**: Malicious strategy injection
2. **Command Injection**: TMUX command construction
3. **State Tampering**: Persistent state modification
4. **Resource Exhaustion**: Connection pool abuse

### Mitigation Strategies
1. **Plugin Validation**: Signature verification, sandboxing
2. **Input Sanitization**: Command parameter validation
3. **File Permissions**: Restricted state file access
4. **Resource Limits**: Connection timeouts, pool limits

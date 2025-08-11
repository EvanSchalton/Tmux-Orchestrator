# Monitoring Daemon Working But Not Notifying PM

## Issue: Daemon Detects Idle Agents But Fails to Notify Project Manager

### Problem Description
The monitoring daemon is now functional and correctly detecting idle agents, but it's not sending notifications to the PM about these issues. This breaks the feedback loop for agent management.

### Evidence of Daemon Functionality

#### Daemon Status - WORKING ✅
```
✓ Monitor is running (PID: 23398)
Native Python daemon with bulletproof detection
Log size: 779704 bytes
```

#### Recent Log Activity - DETECTING IDLE AGENTS ✅
```
2025-08-10 23:42:22,037 - Agent kanban-project:0 is idle with Claude interface
2025-08-10 23:42:23,897 - Agent kanban-project:2 is idle with Claude interface
2025-08-10 23:42:04,879 - Agent kanban-project:5 is idle with Claude interface
2025-08-10 23:42:04,880 - Auto-submitting stuck message for kanban-project:5 (attempt #2)
```

#### Agent Detection Working ✅
- **Cycle #763**: Successfully finding and monitoring 4 agents
- **Idle Detection**: Correctly identifying idle agents with Claude interface
- **Auto-retry**: Attempting to auto-submit stuck messages
- **Regular Cycles**: Running every ~10 seconds consistently

### The Missing Link - PM Notification ❌

#### What Should Happen
When agents are detected as idle, the daemon should:
1. **Alert the PM**: Send message to kanban-project:0 about idle agents
2. **Provide Details**: Which agents are idle and for how long
3. **Suggest Actions**: Recommend PM interventions (restart, reassign, etc.)
4. **Escalate**: After multiple cycles of idle behavior

#### What Actually Happens
1. **Detection**: ✅ Daemon correctly identifies idle agents
2. **Logging**: ✅ Events logged to idle-monitor.log
3. **Auto-retry**: ✅ Attempts to auto-submit stuck messages  
4. **PM Notification**: ❌ **NO MESSAGES SENT TO PM**

### Specific Idle Agents Detected
From logs, these agents are consistently idle:
- **kanban-project:0** (PM) - Ironic, the PM is idle
- **kanban-project:2** (Backend Developer) - Critical for fixing API issues
- **kanban-project:5** (Unknown agent) - Should be investigated

### Impact Assessment
- **Medium Severity**: Daemon working but feedback loop broken
- PM unaware of team productivity issues
- Idle developers not being managed or reassigned
- Manual intervention required to identify and fix idle agents
- Defeats the purpose of automated monitoring

### Root Cause Analysis
The daemon has two functions:
1. **Detection** ✅ - Working perfectly
2. **Notification** ❌ - Not implemented or broken

Possible issues:
- PM notification function not implemented
- Message delivery to PM failing silently
- Notification threshold not configured properly
- PM agent ID not correctly identified for notifications

### Expected Daemon Behavior
PM should receive messages like:
```
"Alert: 3 agents have been idle for >5 minutes:
- kanban-project:2 (Backend Dev) - idle 8 minutes
- kanban-project:5 (Agent) - idle 12 minutes  
- Recommend: Check on these agents or reassign tasks"
```

### Recommended Fixes

#### 1. Implement PM Notification
- Add PM message delivery to daemon
- Send alerts when agents idle >5 minutes
- Include agent details and recommendations

#### 2. Escalation Logic  
- First alert: Simple notification
- Second alert: Suggest intervention
- Third alert: Recommend agent restart

#### 3. Configuration
- Make PM notification configurable
- Set idle thresholds per agent type
- Allow PM to acknowledge alerts

### Workaround Applied
Manual monitoring using logs and direct PM messages about idle agents.

### Progress Made
This represents significant improvement over previous total daemon failure (see tmux-orchestrator-feedback-2.1.13-1.md). The daemon now works but needs the final notification component.

---
*Reported: 2025-08-10*
*Version: tmux-orchestrator v2.1.13*
*Document: tmux-orchestrator-feedback-2.1.13-10*
*Priority: P2 - MEDIUM (daemon working, needs notification feature)*
*Status: Partially resolved - detection works, notification missing*
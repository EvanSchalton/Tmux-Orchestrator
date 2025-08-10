# PRD: Fix Critical Daemon and Message Delivery Issues

## Overview
The tmux-orchestrator monitoring daemon and agent recovery systems are currently non-functional due to a critical issue: messages cannot be programmatically submitted to Claude agents in tmux sessions. This breaks the entire coordination and recovery system.

## Problem Statement
1. **Monitoring daemon cannot notify PM** - Messages sent via `tmux send-keys` appear in Claude's input box but are never submitted
2. **Agent recovery fails** - Recovery daemon cannot send restart/resume commands to idle agents
3. **Inter-agent communication broken** - Agents cannot coordinate work or hand off tasks
4. **Initial briefings not delivered** - Spawned agents sit idle waiting for first message

## Root Cause
The Claude terminal interface requires specific key sequences or methods to submit messages that differ from standard terminal behavior. Standard methods (`C-m`, `Enter`, newline) do not trigger message submission.

## Requirements

### 1. Investigate Claude Message Submission (CRITICAL)
- **Requirement**: Determine the exact method to programmatically submit messages to Claude in tmux
- **Acceptance Criteria**:
  - Can reliably submit messages to Claude agents via tmux commands
  - Messages are actually processed by Claude, not just displayed
  - Method works consistently across all agent types

### 2. Fix TMUXManager.send_message Implementation
- **Requirement**: Update the send_message method to use the correct submission technique
- **Acceptance Criteria**:
  - `tmux-orc agent send` successfully delivers and submits messages
  - Messages trigger Claude responses
  - No manual intervention required

### 3. Verify Monitoring Daemon Message Delivery
- **Requirement**: Ensure monitoring daemon can notify PM of idle/crashed agents
- **Acceptance Criteria**:
  - PM receives and processes idle agent notifications
  - Notifications trigger appropriate PM actions
  - Full automation loop is restored

### 4. Test Agent Recovery System
- **Requirement**: Validate that recovery daemon can restart crashed agents
- **Acceptance Criteria**:
  - Crashed agents are detected and restarted
  - Idle agents receive wake-up messages
  - Recovery is fully automated

## Implementation Approach

### Phase 1: Research & Discovery
1. Analyze Claude's terminal interface behavior
2. Test various key combinations and timing sequences
3. Review Claude documentation for terminal automation
4. Consider alternative approaches (API, file-based communication)

### Phase 2: Implementation
1. Update ClaudeInterface class with working submission method
2. Modify TMUXManager.send_message to use new method
3. Add verification to confirm message was submitted
4. Implement fallback mechanisms

### Phase 3: Testing & Validation
1. Test direct message sending via CLI
2. Verify monitoring daemon notifications work
3. Test full recovery cycle with crashed agent
4. Validate inter-agent communication

## Success Metrics
- Message delivery success rate: 100%
- Agent recovery automation: Fully functional
- PM notification delivery: 100% reliable
- No manual intervention required for any messaging

## Non-Goals
- UI/UX improvements
- Performance optimization
- New features beyond fixing core messaging

## Technical Considerations
- May need to use alternative approaches if terminal automation proves impossible
- Consider implementing message queue or file-based communication as fallback
- Ensure solution works across different terminal emulators

## Timeline
- Research: 2 hours
- Implementation: 4 hours
- Testing: 2 hours
- Total: 8 hours (1 day)

# Agent Stability Issues - Recurring Crashes

## Issue: Agents Randomly Exit/Crash Without Warning

### Problem Description
Claude agents randomly exit or crash during normal operation without any error messages or warnings. This happens repeatedly to the same agents, suggesting an underlying stability issue.

### Observed Behavior
- Developer agent in `kanban-project:2` crashed multiple times
- Agent was working normally, then Claude session terminated
- No error messages in tmux pane
- No crash logs or stack traces
- Monitoring daemon did not detect the crash
- Agent had to be manually restarted multiple times

### Pattern Analysis
1. **Initial State**: Agent working normally, responding to messages
2. **Crash Event**: Claude session silently exits
3. **Result**: Empty tmux pane or bash prompt
4. **Detection**: Only found through manual checks
5. **Recovery**: Manual restart required each time

### Impact
- **High severity** - Disrupts workflow and loses agent context
- Agents lose their working memory and context
- Work in progress is lost
- No automatic recovery means extended downtime
- Team coordination breaks down when agents disappear

### Reproduction Attempts
- Occurs randomly, no clear trigger identified
- Happens to different agents at different times
- More frequent under active use
- Possibly related to:
  - Long-running sessions
  - Memory issues
  - Network interruptions
  - Rate limiting

### Workaround Applied
1. Created manual monitoring script (`monitor-agents.sh`)
2. Regular health checks every few minutes
3. Manual restart when crashes detected
4. PM notified to rehydrate agent context

### Suggested Improvements
1. **Add crash detection**: Monitor for Claude process exit
2. **Implement auto-restart**: Automatically restart crashed agents
3. **Preserve context**: Save agent state periodically for recovery
4. **Add logging**: Capture Claude stderr/stdout to diagnose crashes
5. **Health endpoint**: HTTP endpoint to check agent health
6. **Retry logic**: Automatic retry with exponential backoff
7. **Notification system**: Alert when agents crash

### Related Issues
- See `tmux-orchestrator-feedback-2.1.13-1.md` for monitoring daemon failure
- Without working monitoring, these crashes go undetected
- Manual intervention required for every crash

---
*Reported: 2025-08-10*
*Version: tmux-orchestrator v2.1.13*
*Document: tmux-orchestrator-feedback-2.1.13-5*
*Priority: P0 - CRITICAL*
*Status: Recurring issue affecting production use*
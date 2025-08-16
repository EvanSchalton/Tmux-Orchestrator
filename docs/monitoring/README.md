# Monitoring System Documentation

*Last Updated: 2025-08-16*

## Overview

The Tmux Orchestrator monitoring system provides continuous health checking, automatic recovery, and intelligent crash detection for all agents including Project Managers.

## Key Features

### ✅ Context-Aware Crash Detection (v2.1.24)
- Prevents false positives when agents discuss errors or failures
- Detects Claude UI presence before declaring crashes
- Implemented in commit 381bf99
- [Full Documentation](./context-aware-crash-detection.md)

### ✅ PM Recovery Grace Period
- 3-minute default grace period after PM recovery
- Configurable via `monitoring.pm_recovery_grace_period_minutes`
- Prevents premature health checks during initialization
- [Configuration Guide](./configuration-guide.md)

### ✅ Progressive Recovery Delays
- Delays: [2, 5, 10] seconds between attempts
- 5-minute cooldown between recovery cycles
- Dynamic initialization wait based on attempt number

## Quick Start

### Enable Monitoring
```bash
tmux-orc monitor start
```

### Check Status
```bash
tmux-orc monitor status
```

### Configure Grace Period
```json
{
  "monitoring": {
    "pm_recovery_grace_period_minutes": 5
  }
}
```

## Documentation Index

### User Guides
- [Configuration Guide](./configuration-guide.md) - All configuration options
- [Context-Aware Crash Detection](./context-aware-crash-detection.md) - How it works

### Implementation Details
- [Monitoring Fix Summary](./MONITORING_FIX_SUMMARY.md) - Technical implementation
- [Monitor Auto Submit Success](./MONITOR_AUTO_SUBMIT_SUCCESS.md) - Auto-submit feature

### Development Notes
- [Monitoring Improvements Notes](./monitoring-improvements-notes.md)
- [Refactoring Plan](./REFACTORING_PLAN_monitor_check_agent_status.md)

### Test Reports
- [Integration Test Report](./MONITORING_FEATURES_INTEGRATION_TEST_REPORT.md)
- [Rate Limit Validation](./RATE_LIMIT_FIXTURE_VALIDATION_REPORT.md)

## Recent Improvements

### Version 2.1.24
- **Fixed**: False positive PM crash detection
- **Added**: Context-aware pattern matching
- **Added**: Claude UI detection
- **Result**: System stable with monitoring enabled

### Version 2.1.7
- **Added**: Rate limit handling with auto-pause
- **Fixed**: Compaction state detection
- **Improved**: Message queue detection

## Troubleshooting

### Common Issues

1. **PM killed unexpectedly**
   - Check logs for what triggered the crash detection
   - Verify grace period is configured correctly
   - Review [Context-Aware Detection](./context-aware-crash-detection.md)

2. **Grace period not working**
   - Verify configuration is loaded
   - Check PM recovery timestamp tracking
   - See [Configuration Guide](./configuration-guide.md)

3. **High CPU usage**
   - Increase monitoring interval
   - Reduce number of monitored agents
   - Check for recovery loops

## Architecture

The monitoring system consists of:

1. **Monitor Daemon** (`monitor.py`)
   - Main monitoring loop
   - Agent state detection
   - Recovery coordination

2. **Helper Functions** (`monitor_helpers.py`)
   - Context-aware crash detection
   - Claude UI detection
   - State analysis utilities

3. **Recovery System**
   - PM manager for spawning/recovery
   - Grace period tracking
   - Progressive delay implementation

## Future Enhancements

- Machine learning for crash patterns
- Configurable crash detection patterns
- Enhanced telemetry and metrics
- Web-based monitoring dashboard

---

For questions or issues, please check the [troubleshooting guide](./context-aware-crash-detection.md#troubleshooting) or file an issue in the repository.

# Monitoring Configuration Guide

*Last Updated: 2025-08-16*

## Overview

This guide covers configuration options for the Tmux Orchestrator monitoring system, including the daemon recovery improvements and context-aware crash detection features.

## PM Recovery Grace Period

### What It Does
After a Project Manager (PM) is recovered, the monitoring daemon will skip health checks for a configurable grace period. This prevents false positive crash detections while the PM initializes and gets back to work.

### Configuration

**Config Key**: `monitoring.pm_recovery_grace_period_minutes`
**Default**: 3 minutes
**Type**: Integer (minutes)

### How to Configure

#### Method 1: Configuration File
Create or edit your configuration file:

```json
{
  "monitoring": {
    "pm_recovery_grace_period_minutes": 5
  }
}
```

#### Method 2: Environment Variable
```bash
export TMUX_ORC_PM_RECOVERY_GRACE_PERIOD_MINUTES=5
```

#### Method 3: Programmatic (if using as library)
```python
config = {
    "monitoring": {
        "pm_recovery_grace_period_minutes": 5
    }
}
```

### Recommended Values

| Use Case | Recommended Value | Rationale |
|----------|-------------------|-----------|
| Fast systems | 2-3 minutes | Quick initialization expected |
| Standard | 3-5 minutes (default) | Balanced for most cases |
| Slow/Complex | 5-10 minutes | Heavy workloads or slow systems |
| Testing | 1 minute | Quick feedback during development |

## Other Monitoring Configuration

### Monitoring Interval
**Config Key**: `monitoring.check_interval_seconds`
**Default**: 30 seconds
**Description**: How often the daemon checks agent health

### Failure Threshold
**Config Key**: `monitoring.failure_threshold`
**Default**: 3 failures
**Description**: Consecutive failures before triggering recovery

### Recovery Cooldown
**Config Key**: `monitoring.recovery_cooldown_seconds`
**Default**: 300 seconds (5 minutes)
**Description**: Minimum time between recovery attempts for the same agent

## Context-Aware Crash Detection

The context-aware crash detection feature is enabled by default and requires no configuration. It automatically:

- Detects Claude UI presence
- Ignores crash keywords in safe contexts
- Applies intelligent pattern matching

To customize crash detection patterns, you would need to modify the `_should_ignore_crash_indicator()` method in the source code.

## Example Complete Configuration

```json
{
  "monitoring": {
    "pm_recovery_grace_period_minutes": 5,
    "check_interval_seconds": 30,
    "failure_threshold": 3,
    "recovery_cooldown_seconds": 300,
    "enable_auto_recovery": true,
    "enable_pm_notifications": true
  }
}
```

## Troubleshooting

### Grace Period Not Working
1. Check configuration is loaded: Look for "Grace period set to X minutes" in logs
2. Verify PM recovery timestamp is being tracked
3. Check system time synchronization

### Still Getting False Positives
1. Increase grace period if PM needs more initialization time
2. Check `/var/log/tmux-orchestrator/monitor.log` for details
3. Review the specific output that triggered the false positive

## Related Documentation

- [Context-Aware Crash Detection](./context-aware-crash-detection.md)
- [Agent Recovery Guide](../agent-recovery.md)
- [Monitoring Dashboard](../monitoring-daemon-fix.md)

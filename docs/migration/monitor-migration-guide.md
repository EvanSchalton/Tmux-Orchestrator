# Monitor Migration Guide

## Overview
This guide provides step-by-step instructions for migrating from the monolithic `monitor.py` to the new modular monitoring system.

## Migration Strategy

### Phase 1: Preparation (No Downtime)
1. **Review current state**
   ```bash
   tmux-orc monitor status
   ```

2. **Create backup**
   ```bash
   cp -r ~/.tmux_orchestrator/state ~/.tmux_orchestrator/state.backup
   cp ~/.tmux_orchestrator/logs/idle-monitor.log ~/.tmux_orchestrator/logs/idle-monitor.log.backup
   ```

3. **Run compatibility check**
   ```bash
   python -m pytest tests/test_core/monitoring/test_migration.py -v
   ```

### Phase 2: Parallel Testing (Optional but Recommended)
1. **Enable shadow mode** (runs both monitors, uses old for decisions)
   ```bash
   export TMUX_ORCHESTRATOR_SHADOW_MODE=true
   tmux-orc monitor restart
   ```

2. **Monitor for 24-48 hours**
   - Check logs for discrepancies
   - Compare performance metrics
   - Validate agent detection consistency

3. **Review shadow mode results**
   ```bash
   grep "SHADOW_DIFF" ~/.tmux_orchestrator/logs/idle-monitor.log
   ```

### Phase 3: Migration

#### Option A: Gradual Migration (Recommended)
1. **Enable feature flag**
   ```bash
   export TMUX_ORCHESTRATOR_USE_MODULAR_MONITOR=true
   ```

2. **Restart monitor**
   ```bash
   tmux-orc monitor stop
   tmux-orc monitor start
   ```

3. **Verify operation**
   ```bash
   tmux-orc monitor status
   tail -f ~/.tmux_orchestrator/logs/idle-monitor.log
   ```

4. **Monitor for issues** (keep feature flag for easy rollback)

#### Option B: Direct Migration
1. **Stop current monitor**
   ```bash
   tmux-orc monitor stop
   ```

2. **Update configuration**
   ```bash
   # Edit ~/.tmux_orchestrator/config.yaml
   monitoring:
     use_modular: true
   ```

3. **Start new monitor**
   ```bash
   tmux-orc monitor start
   ```

### Phase 4: Validation

Run validation checks:
```bash
# Check agent discovery
tmux-orc monitor check-agents

# Verify idle detection
tmux-orc monitor test-idle

# Test notifications
tmux-orc monitor test-notify

# Performance benchmark
python tests/benchmarks/monitoring_performance.py
```

Expected results:
- ✅ All agents discovered
- ✅ Idle detection accurate
- ✅ Notifications delivered
- ✅ Performance improved or stable

### Phase 5: Cleanup
1. **After successful validation** (1-2 weeks)
   ```bash
   # Remove feature flag
   unset TMUX_ORCHESTRATOR_USE_MODULAR_MONITOR

   # Clean up backups
   rm -rf ~/.tmux_orchestrator/state.backup
   ```

2. **Update documentation**
   - Update team runbooks
   - Document any custom configurations

## Rollback Procedure

If issues arise, rollback immediately:

1. **Quick rollback** (if using feature flag)
   ```bash
   export TMUX_ORCHESTRATOR_USE_MODULAR_MONITOR=false
   tmux-orc monitor restart
   ```

2. **Full rollback**
   ```bash
   # Stop monitor
   tmux-orc monitor stop

   # Restore state
   cp -r ~/.tmux_orchestrator/state.backup/* ~/.tmux_orchestrator/state/

   # Revert config
   # Edit ~/.tmux_orchestrator/config.yaml
   monitoring:
     use_modular: false

   # Start old monitor
   tmux-orc monitor start
   ```

## State File Compatibility

### Old Format (v1)
```json
{
  "agents": {
    "session:window": {
      "last_activity": "2024-01-01T12:00:00",
      "submission_count": 5,
      "consecutive_idle_count": 2,
      "is_fresh": false
    }
  },
  "version": "1.0"
}
```

### New Format (v2)
```json
{
  "agents": {
    "session:window": {
      "target": "session:window",
      "session": "session",
      "window": "window",
      "last_activity": "2024-01-01T12:00:00",
      "last_content_hash": "abc123",
      "consecutive_idle_count": 2,
      "submission_attempts": 5,
      "last_submission_time": "2024-01-01T11:00:00",
      "is_fresh": false,
      "error_count": 0,
      "last_error_time": null
    }
  },
  "version": "2.0",
  "compatibility": {
    "min_version": "1.0"
  }
}
```

**Note**: New system reads old format automatically. Old system ignores extra fields in new format.

## Performance Expectations

### Improvements
- **50 agents**: ~10x faster (30ms → 3ms)
- **100 agents**: ~8x faster (80ms → 10ms)
- **Memory usage**: 30% reduction
- **TMUX commands**: 50% reduction

### Benchmarking
Compare before/after:
```bash
# Before migration
python tests/benchmarks/monitoring_performance.py --output before/

# After migration
python tests/benchmarks/monitoring_performance.py --output after/

# Compare
diff before/latest.json after/latest.json
```

## Troubleshooting

### Common Issues

1. **Agents not discovered**
   - Check TMUX connection: `tmux ls`
   - Verify agent windows have correct names
   - Check logs for discovery errors

2. **State file errors**
   ```bash
   # Validate state file
   python -m json.tool ~/.tmux_orchestrator/state/monitor_state.json

   # Reset if corrupted
   mv ~/.tmux_orchestrator/state/monitor_state.json ~/.tmux_orchestrator/state/monitor_state.json.bad
   ```

3. **Performance degradation**
   - Check CPU usage: `top -p $(cat ~/.tmux_orchestrator/idle-monitor.pid)`
   - Review logs for errors
   - Run performance benchmarks

4. **Notification failures**
   - Verify PM windows exist
   - Check notification queue: `grep "notification" ~/.tmux_orchestrator/logs/idle-monitor.log`

### Debug Mode
Enable detailed logging:
```bash
export TMUX_ORCHESTRATOR_LOG_LEVEL=DEBUG
tmux-orc monitor restart
```

## Migration Checklist

- [ ] Backup created
- [ ] Compatibility tests pass
- [ ] Shadow mode tested (optional)
- [ ] Feature flag set
- [ ] Monitor restarted
- [ ] Validation checks pass
- [ ] Team notified
- [ ] Monitoring alerts updated
- [ ] Documentation updated
- [ ] Rollback tested

## Support

If you encounter issues:
1. Check logs: `~/.tmux_orchestrator/logs/idle-monitor.log`
2. Run diagnostics: `tmux-orc monitor diagnose`
3. Contact team with:
   - Log excerpts
   - State file sample
   - Performance metrics

## Post-Migration

After successful migration:
1. Monitor performance trends
2. Collect team feedback
3. Document custom configurations
4. Plan removal of old code (after 30 days)

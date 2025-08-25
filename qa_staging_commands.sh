#!/bin/bash
# QA Preparation: Selective Staging Commands
# Execute after Senior Dev completes MyPy fixes

set -e

echo "🔄 QA STAGING: Preparing selective git staging..."

# 1. Stage .pre-commit-config.yaml
echo "📝 Staging pre-commit config..."
git add .pre-commit-config.yaml

# 2. Stage all modified Python files (fixes from Senior Dev)
echo "🐍 Staging Python files..."
git add \
  scripts/validation/audit_json_support.py \
  scripts/validation/test_mcp_parity.py \
  scripts/validation/test_mcp_server_direct.py \
  scripts/validation/test_mcp_tool_execution.py \
  scripts/validation/test_mcp_tools.py \
  scripts/validation/test_mcp_tools_simple.py \
  scripts/validation/validate_mcp_fix.py \
  tests/conftest.py \
  tests/conftest_mcp.py \
  tests/docs/reports/debug_sleep_duration_detailed.py \
  tests/integration/mcp_integration/test_mcp_integration.py \
  tests/unit/cli/cli_module_validation.py \
  tests/unit/cli/final_rate_limit_validation.py \
  tests/unit/cli/rate_limit_workflow_test_suite.py \
  tests/unit/cli/test_daemon_sleep_behavior.py \
  tests/unit/core/test_monitoring/false_positive_fix_verification_test.py \
  tests/unit/core/test_monitoring/qa_pm_recovery_grace_test.py \
  tests/unit/core/test_monitoring/qa_test_false_positive_failed.py \
  tests/unit/core/test_monitoring/qa_test_mcp_protocol.py \
  tests/unit/core/test_monitoring/qa_test_scripts/simulate_pm_failed_output.py \
  tests/unit/core/test_monitoring/test_pm_crash_detection_validation.py \
  tests/unit/core/test_monitoring/test_pm_false_positive_detection.py \
  tests/unit/mcp/hierarchical_structure/FINAL_VALIDATION_SUITE.py \
  tests/unit/mcp/test_cli_reflection_approach.py \
  tests/unit/mcp/test_fresh_mcp_tools_validation.py \
  tests/unit/mcp/test_mcp_commands.py \
  tests/unit/mcp/test_mcp_fixes.py \
  tests/unit/mcp/test_mcp_server.py \
  tmux_orchestrator/cli/setup_claude.py \
  tmux_orchestrator/cli/team_compose.py \
  tmux_orchestrator/core/communication/pm_pubsub_integration.py \
  tmux_orchestrator/core/config.py \
  tmux_orchestrator/core/daemon_supervisor.py \
  tmux_orchestrator/core/mcp/performance_monitor.py \
  tmux_orchestrator/core/messaging_daemon.py \
  tmux_orchestrator/core/monitor.py \
  tmux_orchestrator/core/monitor_async.py \
  tmux_orchestrator/core/monitor_modular.py \
  tmux_orchestrator/core/monitoring/crash_detector.py \
  tmux_orchestrator/core/monitoring/enable_pubsub.py \
  tmux_orchestrator/core/monitoring/metrics_collector.py \
  tmux_orchestrator/core/monitoring/monitor_pubsub_integration.py \
  tmux_orchestrator/core/monitoring/plugin_loader.py \
  tmux_orchestrator/core/monitoring/state_tracker.py \
  tmux_orchestrator/core/monitoring/strategies/polling_strategy.py \
  tmux_orchestrator/core/recovery/pubsub_recovery_coordinator.py \
  tmux_orchestrator/tests/demo_pubsub_integration.py \
  tmux_orchestrator/tests/validate_pubsub_performance.py \
  tmux_orchestrator/utils/input_sanitizer.py

# 3. Ensure dynamic files remain excluded
echo "🚫 Ensuring exclusion of dynamic files..."
git reset HEAD .tmux_orchestrator/status.json 2>/dev/null || true
git reset HEAD .tmux_orchestrator/idle-monitor.startup.lock 2>/dev/null || true

# 4. Verify staging status
echo "✅ Staging complete. Status check:"
git status --porcelain | grep -E "^A|^M|^D" | head -10
echo "..."
echo "Total staged files: $(git status --porcelain | grep -E '^[AM]' | wc -l)"

echo "🎯 QA STAGING READY: Execute 'bash qa_staging_commands.sh' when fixes complete"
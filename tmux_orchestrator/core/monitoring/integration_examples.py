"""
Integration examples for the new monitoring architecture.

This file provides concrete examples for Senior Dev to integrate
the modular components with the existing monitor.py.
"""

import logging
import time
from datetime import datetime
from typing import Any

from tmux_orchestrator.core.config import Config
from tmux_orchestrator.utils.tmux import TMUXManager

from .feature_flags import FeatureFlagManager, RolloutStage
from .monitor_service import MonitorService
from .plugin_integration import PluginIntegrationBridge
from .service_container import ServiceContainer


# Example 1: Basic Integration in monitor_modular.py
def example_basic_integration():
    """Example of basic integration with feature flags."""

    class ModularIdleMonitor:
        def __init__(self, tmux: TMUXManager, config: Config | None = None):
            self.tmux = tmux
            self.config = config or Config.load()
            self.logger = logging.getLogger(__name__)

            # Initialize feature flags
            self.feature_flags = FeatureFlagManager(self.config.orchestrator_base_dir)

            # Initialize service container
            self.container = ServiceContainer(self.logger)

            # Initialize monitor service
            self.monitor_service = MonitorService(self.tmux, self.config, self.logger)

            # Initialize plugin bridge
            self.plugin_bridge = PluginIntegrationBridge(self.container, self.logger)

        def _run_monitoring_daemon(self, interval: int):
            """Run monitoring daemon with feature flag support."""
            # Get current feature flags
            flags = self.feature_flags.get_flags()

            # Initialize components based on flags
            if flags.use_modular_monitor:
                self._run_new_monitoring(interval, flags)
            else:
                # self._run_legacy_monitoring(interval)  # Method not implemented
                pass

        def _run_new_monitoring(self, interval: int, flags):
            """Run the new modular monitoring system."""
            # Initialize monitor service
            if not self.monitor_service.initialize():
                self.logger.error("Failed to initialize monitor service")
                return

            # Load plugins if enabled
            if flags.use_plugin_system:
                self.plugin_bridge.discover_and_register_plugins()
                self.plugin_bridge.set_active_strategy(flags.default_strategy)

            try:
                cycle_count = 0
                # while not self._should_shutdown():  # Method not implemented
                while True:
                    cycle_count += 1

                    # Check if we should use new system this cycle
                    if flags.should_use_new_system(cycle_count):
                        if flags.use_plugin_system:
                            # Use plugin-based strategy
                            # self._run_plugin_cycle()  # Method not implemented
                            pass
                        else:
                            # Use built-in monitoring
                            # self._run_builtin_cycle()  # Method not implemented
                            pass
                    else:
                        # Fall back to legacy for this cycle
                        # self._run_legacy_cycle()  # Method not implemented
                        pass

                    time.sleep(interval)

            finally:
                self.monitor_service.cleanup()


# Example 2: Plugin-Based Monitoring Cycle
def example_plugin_monitoring():
    """Example of running a monitoring cycle with plugins."""

    async def run_plugin_monitoring_cycle(monitor_service, plugin_bridge, logger):
        """Run a single monitoring cycle using the active plugin strategy."""
        # Get the active strategy
        strategy = plugin_bridge.get_active_strategy()

        if not strategy:
            logger.error("No active monitoring strategy")
            return None

        # Create execution context
        context = plugin_bridge.create_strategy_context()

        # Add cycle metadata
        context["cycle_count"] = monitor_service.cycle_count
        context["start_time"] = time.time()

        try:
            # Execute the strategy
            status = await strategy.execute(context)

            # Record metrics if enabled
            if monitor_service.get_component("metrics_collector"):
                metrics = monitor_service.get_component("metrics_collector")
                metrics.record_monitor_cycle(status)

            return status

        except Exception as e:
            logger.error(f"Error in plugin monitoring cycle: {e}")
            return None


# Example 3: Gradual Rollout Implementation
def example_gradual_rollout():
    """Example of implementing gradual rollout."""

    class MonitorWithRollout:
        def __init__(self, config: Config):
            self.config = config
            self.flag_manager = FeatureFlagManager(config.orchestrator_base_dir)

        def start_monitoring(self):
            """Start monitoring with rollout support."""
            flags = self.flag_manager.get_flags()

            # Automatic rollout progression
            if flags.rollout_stage == RolloutStage.CANARY:
                # Monitor canary metrics
                if self._check_canary_health():
                    # Progress to beta after 24 hours
                    if self._hours_since_rollout() > 24:
                        self.flag_manager.update_flags({"rollout_stage": RolloutStage.BETA})

            elif flags.rollout_stage == RolloutStage.BETA:
                # Monitor beta metrics
                if self._check_beta_health():
                    # Progress to production after 72 hours
                    if self._hours_since_rollout() > 72:
                        self.flag_manager.update_flags({"rollout_stage": RolloutStage.PRODUCTION})

        def _check_canary_health(self) -> bool:
            """Check if canary deployment is healthy."""
            # Implement health checks:
            # - Error rate < 1%
            # - Performance within 10% of legacy
            # - No critical failures
            return True

        def _hours_since_rollout(self) -> float:
            """Calculate hours since rollout started."""
            flags = self.flag_manager.get_flags()
            if flags.rollout_started_at:
                delta = datetime.now() - flags.rollout_started_at
                return delta.total_seconds() / 3600
            return 0.0


# Example 4: Performance Comparison Mode
def example_performance_comparison():
    """Example of running both systems in parallel for comparison."""

    class DualMonitor:
        def __init__(self, tmux: TMUXManager, config: Config):
            self.tmux = tmux
            self.config = config
            self.logger = logging.getLogger(__name__)

            # Initialize both systems
            from tmux_orchestrator.core.monitor import IdleMonitor

            self.legacy_monitor = IdleMonitor(tmux, config)
            self.new_monitor = MonitorService(tmux, config, self.logger)

        async def run_comparison_cycle(self):
            """Run both monitoring systems and compare results."""
            # Run legacy monitoring
            legacy_start = time.time()
            legacy_result = self.legacy_monitor.run_monitoring_cycle()
            legacy_duration = time.time() - legacy_start

            # Run new monitoring
            new_start = time.time()
            new_result = await self.new_monitor.run_monitoring_cycle()
            new_duration = time.time() - new_start

            # Compare results
            comparison = {
                "legacy": {
                    "duration": legacy_duration,
                    "agents_found": legacy_result.get("total_agents", 0),
                    "errors": legacy_result.get("errors", 0),
                },
                "new": {
                    "duration": new_duration,
                    "agents_found": new_result.total_agents,
                    "errors": new_result.error_count if hasattr(new_result, "error_count") else 0,
                },
                "performance_improvement": (legacy_duration - new_duration) / legacy_duration * 100,
            }

            self.logger.info(f"Performance comparison: {comparison}")
            return comparison


# Example 5: CLI Integration
def example_cli_integration():
    """Example of integrating with the CLI."""

    def monitor_command(start: bool = False, stop: bool = False, status: bool = False, strategy: str | None = None):
        """Enhanced monitor command with new features."""
        config = Config.load()
        tmux = TMUXManager()

        # Check feature flags
        flag_manager = FeatureFlagManager(config.orchestrator_base_dir)
        flags = flag_manager.get_flags()

        if flags.use_modular_monitor:
            from tmux_orchestrator.core.monitor_modular import ModularIdleMonitor

            monitor: Any = ModularIdleMonitor(tmux, config)
        else:
            from tmux_orchestrator.core.monitor import IdleMonitor

            monitor = IdleMonitor(tmux, config)

        if strategy:
            # Update strategy if using new system
            if flags.use_plugin_system:
                flag_manager.update_flags({"default_strategy": strategy})
                print(f"Updated monitoring strategy to: {strategy}")
            else:
                print("Strategy selection requires plugin system to be enabled")

        if start:
            # Show which system is being used
            system_name = "modular" if flags.use_modular_monitor else "legacy"
            print(f"Starting {system_name} monitoring system...")

            if flags.rollout_stage != RolloutStage.DISABLED:
                print(f"Rollout stage: {flags.rollout_stage.value} ({flags.rollout_percentage}%)")

            monitor.start()

        elif stop:
            monitor.stop()

        elif status:
            # Enhanced status with feature flag info
            is_running = monitor.is_running()
            print(f"Monitor running: {is_running}")

            if is_running and flags.use_modular_monitor:
                print("System: Modular")
                print(f"Strategy: {flags.default_strategy}")
                print(f"Rollout: {flags.rollout_stage.value}")

                if flags.log_performance_metrics:
                    # Show performance metrics
                    metrics = monitor.get_performance_stats()
                    print(f"Metrics: {metrics}")


# Example 6: Metrics Integration
def example_metrics_integration():
    """Example of integrating the metrics collector."""

    from .metrics_collector import MetricsCollector

    class MonitorWithMetrics:
        def __init__(self, config: Config, logger: logging.Logger):
            self.config = config
            self.logger = logger
            self.metrics = MetricsCollector(config, logger)

        async def run_monitoring_with_metrics(self):
            """Run monitoring and collect metrics."""
            # Start timing
            self.metrics.start_timer("monitoring_cycle")

            try:
                # Run monitoring
                status = await self.monitor_service.run_monitoring_cycle()

                # Record metrics
                self.metrics.record_monitor_cycle(status)
                self.metrics.increment_counter("cycles_completed")

                # Record timing
                duration = self.metrics.stop_timer("monitoring_cycle")
                self.metrics.record_histogram("cycle_duration", duration)

                # Set current state gauges
                self.metrics.set_gauge("agents_active", status.total_agents)
                self.metrics.set_gauge("agents_idle", status.idle_agents)
                self.metrics.set_gauge("agents_crashed", status.crashed_agents)

            except Exception as e:
                self.metrics.increment_counter("cycles_failed")
                self.metrics.increment_counter(f"errors_{type(e).__name__}")
                raise

        def export_metrics(self):
            """Export metrics in various formats."""
            # Human-readable report
            report = self.metrics.generate_report()
            print(report)

            # Prometheus format for monitoring tools
            prometheus_data = self.metrics.export_prometheus_format()

            # Save to file for external collectors
            metrics_file = self.config.orchestrator_base_dir / "metrics.prom"
            metrics_file.write_text(prometheus_data)

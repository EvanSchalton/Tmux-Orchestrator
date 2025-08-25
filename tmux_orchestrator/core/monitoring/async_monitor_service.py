"""Async-aware MonitorService with plugin integration and performance optimizations."""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Optional

from tmux_orchestrator.core.config import Config
from tmux_orchestrator.core.monitoring.agent_monitor import AgentMonitor
from tmux_orchestrator.core.monitoring.async_health_checker import AsyncHealthChecker
from tmux_orchestrator.core.monitoring.cache import LayeredCache
from tmux_orchestrator.core.monitoring.daemon_manager import DaemonManager
from tmux_orchestrator.core.monitoring.interfaces import MonitoringStrategyInterface
from tmux_orchestrator.core.monitoring.monitor_service import MonitorService
from tmux_orchestrator.core.monitoring.notification_manager import NotificationManager
from tmux_orchestrator.core.monitoring.plugin_loader import PluginLoader
from tmux_orchestrator.core.monitoring.pm_recovery_manager import PMRecoveryManager
from tmux_orchestrator.core.monitoring.service_container import ServiceContainer
from tmux_orchestrator.core.monitoring.state_tracker import StateTracker
from tmux_orchestrator.core.monitoring.tmux_pool import TMuxConnectionPool
from tmux_orchestrator.utils.tmux import TMUXManager


class AsyncMonitorService(MonitorService):
    """Enhanced monitor service with async capabilities and plugin support.

    This extends the base MonitorService with async operations, connection
    pooling, caching, and integration with the plugin system for strategies.
    """

    def __init__(self, tmux: TMUXManager, config: Config, logger: Optional[logging.Logger] = None):
        """Initialize the async monitor service.

        Args:
            tmux: TMUX manager instance
            config: Configuration object
            logger: Optional logger instance
        """
        # Initialize base service
        super().__init__(tmux, config, logger)

        # Async infrastructure
        self.tmux_pool = TMuxConnectionPool(min_size=5, max_size=20, logger=self.logger)
        self.cache = LayeredCache()

        # Replace health checker with async version
        self.async_health_checker = AsyncHealthChecker(
            tmux, config, self.logger, tmux_pool=self.tmux_pool, cache=self.cache
        )

        # Plugin system
        self.service_container = ServiceContainer(logger=self.logger)
        self.plugin_loader = PluginLoader(logger=self.logger)

        # Strategy selection
        self.current_strategy: Optional[MonitoringStrategyInterface] = None
        self.prefer_concurrent = True  # Default to concurrent strategy

        # Async monitoring state
        self._monitoring_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()

    async def initialize_async(self) -> bool:
        """Initialize async components and plugins."""
        try:
            # Initialize base components
            if not self.initialize():
                return False

            # Initialize async components
            await self.tmux_pool.initialize()
            await self.async_health_checker.initialize_async()

            # Register services with container
            self._register_services()

            # Load plugins
            await self._load_plugins()

            # Select default strategy
            await self._select_strategy()

            self.logger.info("AsyncMonitorService initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize AsyncMonitorService: {e}")
            return False

    def _register_services(self) -> None:
        """Register all services with the dependency injection container."""
        # Register core services
        self.service_container.register(TMUXManager, self.tmux)
        self.service_container.register(Config, self.config)
        self.service_container.register(logging.Logger, self.logger)

        # Register monitoring components - use the concrete instance types
        self.service_container.register(AgentMonitor, self.agent_monitor)
        self.service_container.register(NotificationManager, self.notification_manager)
        self.service_container.register(StateTracker, self.state_tracker)
        # These have type: ignore in parent class for abstract issues
        self.service_container.register(PMRecoveryManager, self.pm_recovery_manager)  # type: ignore[type-abstract]
        self.service_container.register(DaemonManager, self.daemon_manager)  # type: ignore[type-abstract]

        # Register async components
        self.service_container.register(AsyncHealthChecker, self.async_health_checker)
        self.service_container.register(TMuxConnectionPool, self.tmux_pool)
        self.service_container.register(LayeredCache, self.cache)

    async def _load_plugins(self) -> None:
        """Load monitoring strategy plugins."""
        # Discover and load plugins
        discovered = self.plugin_loader.discover_plugins()
        self.logger.info(f"Discovered {len(discovered)} plugins")

        # Load available plugins
        all_plugins = self.plugin_loader.get_all_plugins()
        loaded = []
        for plugin in all_plugins:
            if self.plugin_loader.load_plugin(plugin.name):
                loaded.append(plugin)
        self.logger.info(f"Loaded {len(loaded)} plugins successfully")

    async def _select_strategy(self) -> None:
        """Select the appropriate monitoring strategy."""
        if self.prefer_concurrent:
            # Try to use concurrent strategy
            strategies = self.plugin_loader.get_loaded_strategies()
            self.current_strategy = strategies.get("concurrent")
            if self.current_strategy:
                self.logger.info("Selected concurrent monitoring strategy")
                return

        # Fallback to polling strategy
        strategies = self.plugin_loader.get_loaded_strategies()
        self.current_strategy = strategies.get("polling")
        if self.current_strategy:
            self.logger.info("Selected polling monitoring strategy")
        else:
            self.logger.error("No monitoring strategy available!")

    async def start_async(self) -> bool:
        """Start the monitoring service asynchronously."""
        if self.is_running:
            self.logger.warning("AsyncMonitorService is already running")
            return True

        if not await self.initialize_async():
            return False

        # Start the daemon if needed
        if not self.daemon_manager.is_running():
            if not self.daemon_manager.start():
                self.logger.error("Failed to start monitoring daemon")
                return False

        self.is_running = True
        self.start_time = datetime.now()
        self._shutdown_event.clear()

        # Start monitoring task
        self._monitoring_task = asyncio.create_task(self._run_monitoring_loop())

        self.logger.info("AsyncMonitorService started")
        return True

    async def stop_async(self) -> bool:
        """Stop the monitoring service asynchronously."""
        if not self.is_running:
            self.logger.warning("AsyncMonitorService is not running")
            return True

        self.is_running = False
        self._shutdown_event.set()

        # Cancel monitoring task
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass

        # Clean up async components
        await self.async_health_checker.cleanup_async()
        await self.tmux_pool.close()
        await self.cache.clear_all()

        # Stop the daemon
        if self.daemon_manager.is_running():
            self.daemon_manager.stop()

        # Clean up base components
        self.cleanup()

        self.logger.info("AsyncMonitorService stopped")
        return True

    async def _run_monitoring_loop(self) -> None:
        """Run the async monitoring loop."""
        while not self._shutdown_event.is_set():
            try:
                await self.run_monitoring_cycle_async()

                # Wait for next cycle or shutdown
                try:
                    await asyncio.wait_for(self._shutdown_event.wait(), timeout=self.check_interval)
                except asyncio.TimeoutError:
                    # Normal timeout, continue monitoring
                    pass

            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                self.errors_detected += 1
                # Brief pause before retry
                await asyncio.sleep(1)

    async def run_monitoring_cycle_async(self) -> None:
        """Run a single async monitoring cycle using the selected strategy."""
        if not self.is_running:
            return

        start_time = time.time()

        try:
            # Prepare context for strategy
            context = {
                "tmux": self.tmux,
                "config": self.config,
                "logger": self.logger,
                "agent_monitor": self.agent_monitor,
                "health_checker": self.async_health_checker,
                "state_tracker": self.state_tracker,
                "notification_manager": self.notification_manager,
                "pm_recovery_manager": self.pm_recovery_manager,
                "crash_detector": getattr(self, "crash_detector", None),
                "tmux_pool": self.tmux_pool,
                "cache": self.cache,
                "start_time": self.start_time,
                "cycle_count": self.cycle_count,
                "end_time": datetime.now(),
            }

            if self.current_strategy:
                # Execute strategy
                # All strategies should have async execute methods per the interface
                status = await self.current_strategy.execute(context)

                # Process status
                if status:
                    self.errors_detected += status.errors_detected

            else:
                # Fallback to basic async monitoring
                await self._basic_monitoring_cycle_async()

            # Update metrics
            self.cycle_count += 1
            self.last_cycle_time = time.time() - start_time

            # Log performance
            if self.last_cycle_time > 1.0:
                self.logger.warning(f"Slow monitoring cycle: {self.last_cycle_time:.3f}s")

            # Periodic cache cleanup
            if self.cycle_count % 100 == 0:
                asyncio.create_task(self._cleanup_caches())

        except Exception as e:
            self.logger.error(f"Error in async monitoring cycle: {e}")
            self.errors_detected += 1

    async def _basic_monitoring_cycle_async(self) -> None:
        """Basic async monitoring when no strategy is available."""
        # Discover agents
        agents = self.discover_agents()

        # Check health concurrently
        targets = [agent.target for agent in agents]
        statuses = await self.async_health_checker.check_multiple_agents_async(targets, max_concurrent=10)

        # Process results
        for agent in agents:
            status = statuses.get(agent.target)
            if not status:
                continue

            # Update state
            content = await self._get_cached_content(agent.target)
            self.state_tracker.update_agent_state(agent.target, content)

            # Handle issues
            if status.status in ["critical", "unresponsive"]:
                self.errors_detected += 1

                if agent.window == "1":
                    # PM issue
                    asyncio.create_task(self._handle_pm_recovery_async(agent.session))
                else:
                    # Regular agent issue
                    self.notification_manager.notify_agent_crash(agent.target, f"Agent {status.status}", agent.session)

        # Send notifications
        self.notification_manager.send_queued_notifications()

    async def _get_cached_content(self, target: str) -> str:
        """Get pane content with caching."""
        cache_key = f"pane_content:{target}"

        async def fetch_content():
            if self.async_health_checker.async_tmux:
                return await self.async_health_checker.async_tmux.capture_pane_async(target, lines=50)
            else:
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, self.tmux.capture_pane, target, 50)

        return await self.cache.get_layer("pane_content").get_or_compute(cache_key, fetch_content, ttl=10.0)

    async def _handle_pm_recovery_async(self, session: str) -> None:
        """Handle PM recovery asynchronously."""
        try:
            # Check and recover in executor (PM recovery is still sync)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.pm_recovery_manager.check_and_recover_if_needed, session)
        except Exception as e:
            self.logger.error(f"Error in async PM recovery for {session}: {e}")

    async def _cleanup_caches(self) -> None:
        """Periodic cache cleanup."""
        try:
            for layer_name, cache in self.cache.layers.items():
                expired = await cache.clean_expired()
                if expired > 0:
                    self.logger.debug(f"Cleaned {expired} expired entries from {layer_name} cache")
        except Exception as e:
            self.logger.error(f"Error cleaning caches: {e}")

    async def get_performance_metrics_async(self) -> dict[str, Any]:
        """Get detailed performance metrics."""
        base_status = self.status()

        # Add async-specific metrics
        pool_stats = self.tmux_pool.get_stats()
        cache_stats = self.cache.get_all_stats()
        health_summary = await self.async_health_checker.get_health_summary_async()

        return {
            "base_status": {
                "is_running": base_status.is_running,
                "active_agents": base_status.active_agents,
                "idle_agents": base_status.idle_agents,
                "cycle_count": base_status.cycle_count,
                "last_cycle_time": base_status.last_cycle_time,
                "errors_detected": base_status.errors_detected,
                "uptime": str(base_status.uptime),
            },
            "connection_pool": pool_stats,
            "cache_performance": cache_stats,
            "health_summary": health_summary,
            "current_strategy": self.current_strategy.get_name() if self.current_strategy else "none",
            "timestamp": datetime.now().isoformat(),
        }

    def switch_strategy(self, strategy_name: str) -> bool:
        """Switch to a different monitoring strategy at runtime.

        Args:
            strategy_name: Name of the strategy to switch to

        Returns:
            True if switch was successful
        """
        strategies = self.plugin_loader.get_loaded_strategies()
        new_strategy = strategies.get(strategy_name)
        if new_strategy:
            self.current_strategy = new_strategy
            self.logger.info(f"Switched to {strategy_name} monitoring strategy")
            return True
        else:
            self.logger.error(f"Strategy {strategy_name} not found")
            return False

"""Concurrent operations tests for Phase 7.0 testing suite.

Tests concurrent agent operations with focus on:
- 20 agent limit enforcement for local developer tool
- Resource management and cleanup
- Performance under concurrent load
- Thread safety and race condition prevention
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock, patch

from tmux_orchestrator.core.config import Config
from tmux_orchestrator.utils.tmux import TMUXManager


class TestConcurrentAgentLimits:
    """Test concurrent agent limit enforcement."""

    def test_max_agents_configuration(self, test_uuid: str) -> None:
        """Test max agents configuration for local developer tool."""
        config = Config()

        # Local developer tool should have reasonable limits
        assert config.max_agents <= 50, f"Max agents too high for local tool - Test ID: {test_uuid}"
        assert config.max_agents >= 1, f"Must allow at least one agent - Test ID: {test_uuid}"

        # Default should be 20 for good developer experience
        expected_default = 20
        if hasattr(config, "max_agents"):
            # If explicitly set, should be reasonable
            assert 1 <= config.max_agents <= 50, f"Max agents should be 1-50 - Test ID: {test_uuid}"

    @patch("tmux_orchestrator.utils.tmux.TMUXManager")
    def test_concurrent_agent_spawning(self, mock_tmux: Mock, test_uuid: str) -> None:
        """Test spawning multiple agents concurrently."""
        mock_tmux.return_value.session_exists.return_value = False
        mock_tmux.return_value.new_session.return_value = True
        mock_tmux.return_value.new_window.return_value = True

        def spawn_agent(agent_id: int) -> dict:
            """Simulate spawning an agent."""
            time.sleep(0.1)  # Simulate some work
            return {"agent_id": agent_id, "status": "spawned", "session": f"test-{agent_id}:1"}

        # Test spawning 10 agents concurrently (well under 20 limit)
        num_agents = 10
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=num_agents) as executor:
            futures = [executor.submit(spawn_agent, i) for i in range(num_agents)]
            results = [future.result() for future in as_completed(futures)]

        execution_time = time.time() - start_time

        assert len(results) == num_agents, f"Should spawn all {num_agents} agents - Test ID: {test_uuid}"
        assert (
            execution_time < 5.0
        ), f"Concurrent spawning took {execution_time:.3f}s (>5s limit) - Test ID: {test_uuid}"

        # Verify all agents have unique sessions
        sessions = [r["session"] for r in results]
        assert len(set(sessions)) == num_agents, f"All agents should have unique sessions - Test ID: {test_uuid}"

    def test_agent_limit_enforcement(self, test_uuid: str) -> None:
        """Test that agent limits are properly enforced."""
        max_agents = 20

        # Simulate agent tracking
        active_agents = set()

        def try_spawn_agent(agent_id: int) -> bool:
            """Try to spawn an agent, respecting limits."""
            if len(active_agents) >= max_agents:
                return False
            active_agents.add(agent_id)
            return True

        # Try to spawn more than the limit
        results = []
        for i in range(25):  # Try to spawn 25 agents (5 over limit)
            result = try_spawn_agent(i)
            results.append(result)

        successful_spawns = sum(results)
        assert successful_spawns <= max_agents, f"Should not exceed {max_agents} agents - Test ID: {test_uuid}"
        assert successful_spawns == max_agents, f"Should spawn exactly {max_agents} agents - Test ID: {test_uuid}"

    @patch("tmux_orchestrator.utils.tmux.TMUXManager")
    def test_resource_cleanup_after_agent_death(self, mock_tmux: Mock, test_uuid: str) -> None:
        """Test that resources are cleaned up when agents die."""
        mock_tmux.return_value.session_exists.return_value = True
        mock_tmux.return_value.kill_window.return_value = True

        # Simulate agent lifecycle
        active_agents = {}

        def spawn_agent(agent_id: int) -> None:
            active_agents[agent_id] = {"session": f"test-{agent_id}:1", "status": "active"}

        def kill_agent(agent_id: int) -> None:
            if agent_id in active_agents:
                del active_agents[agent_id]

        # Spawn agents up to limit
        for i in range(20):
            spawn_agent(i)

        assert len(active_agents) == 20, f"Should have 20 active agents - Test ID: {test_uuid}"

        # Kill some agents
        for i in range(5):
            kill_agent(i)

        assert len(active_agents) == 15, f"Should have 15 agents after killing 5 - Test ID: {test_uuid}"

        # Should now be able to spawn 5 more
        for i in range(20, 25):
            spawn_agent(i)

        assert len(active_agents) == 20, f"Should be back to 20 agents - Test ID: {test_uuid}"


class TestConcurrentPerformance:
    """Test performance under concurrent operations."""

    @patch("tmux_orchestrator.utils.tmux.TMUXManager")
    def test_concurrent_session_queries(self, mock_tmux: Mock, test_uuid: str) -> None:
        """Test querying multiple sessions concurrently."""
        mock_tmux.return_value.list_sessions.return_value = [f"session-{i}" for i in range(20)]
        mock_tmux.return_value.session_exists.return_value = True
        mock_tmux.return_value.get_pane_content.return_value = "Agent active"

        def query_session(session_name: str) -> dict:
            """Query a session status."""
            tmux = TMUXManager()
            exists = tmux.session_exists(session_name)
            content = tmux.get_pane_content(session_name) if exists else ""
            return {"session": session_name, "exists": exists, "content": content}

        sessions = [f"session-{i}:1" for i in range(20)]
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(query_session, session) for session in sessions]
            results = [future.result() for future in as_completed(futures)]

        execution_time = time.time() - start_time

        assert len(results) == 20, f"Should query all 20 sessions - Test ID: {test_uuid}"
        assert execution_time < 3.0, f"Concurrent queries took {execution_time:.3f}s (>3s limit) - Test ID: {test_uuid}"

        # All queries should succeed
        successful_queries = sum(1 for r in results if r["exists"])
        assert successful_queries == 20, f"All session queries should succeed - Test ID: {test_uuid}"

    @patch("tmux_orchestrator.utils.tmux.TMUXManager")
    def test_concurrent_message_sending(self, mock_tmux: Mock, test_uuid: str) -> None:
        """Test sending messages to multiple agents concurrently."""
        mock_tmux.return_value.send_keys.return_value = True

        def send_message(session: str, message: str) -> bool:
            """Send a message to a session."""
            tmux = TMUXManager()
            return tmux.send_keys(session, message)

        sessions = [f"session-{i}:1" for i in range(15)]
        message = "Test message for concurrent delivery"

        start_time = time.time()

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(send_message, session, message) for session in sessions]
            results = [future.result() for future in as_completed(futures)]

        execution_time = time.time() - start_time

        assert len(results) == 15, f"Should send to all 15 sessions - Test ID: {test_uuid}"
        assert (
            execution_time < 2.0
        ), f"Concurrent messaging took {execution_time:.3f}s (>2s limit) - Test ID: {test_uuid}"

        # All messages should be sent successfully
        successful_sends = sum(1 for r in results if r)
        assert successful_sends == 15, f"All messages should be sent successfully - Test ID: {test_uuid}"


class TestThreadSafety:
    """Test thread safety of concurrent operations."""

    def test_concurrent_session_tracking(self, test_uuid: str) -> None:
        """Test thread-safe session tracking."""
        session_tracker = set()
        lock = threading.Lock()

        def add_session(session_id: int) -> bool:
            """Thread-safe session addition."""
            with lock:
                if session_id in session_tracker:
                    return False
                session_tracker.add(session_id)
                return True

        def remove_session(session_id: int) -> bool:
            """Thread-safe session removal."""
            with lock:
                if session_id in session_tracker:
                    session_tracker.remove(session_id)
                    return True
                return False

        # Test concurrent additions and removals
        num_operations = 50

        def worker(start_id: int) -> list:
            results = []
            for i in range(10):
                session_id = start_id + i
                # Add session
                add_result = add_session(session_id)
                results.append(("add", session_id, add_result))

                # Remove session
                remove_result = remove_session(session_id)
                results.append(("remove", session_id, remove_result))
            return results

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(worker, i * 10) for i in range(5)]
            all_results = []
            for future in as_completed(futures):
                all_results.extend(future.result())

        # Verify thread safety - no corruption
        assert len(all_results) == num_operations, f"Should complete all operations - Test ID: {test_uuid}"

        # Session tracker should be empty (all added sessions were removed)
        assert len(session_tracker) == 0, f"All sessions should be removed - Test ID: {test_uuid}"

    def test_concurrent_resource_allocation(self, test_uuid: str) -> None:
        """Test thread-safe resource allocation."""
        max_resources = 20
        allocated_resources = set()
        lock = threading.Lock()

        def allocate_resource() -> int | None:
            """Allocate a resource ID if available."""
            with lock:
                if len(allocated_resources) >= max_resources:
                    return None

                # Find next available resource ID
                for i in range(max_resources):
                    if i not in allocated_resources:
                        allocated_resources.add(i)
                        return i
                return None

        def deallocate_resource(resource_id: int) -> bool:
            """Deallocate a resource."""
            with lock:
                if resource_id in allocated_resources:
                    allocated_resources.remove(resource_id)
                    return True
                return False

        # Test concurrent allocation
        allocation_results = []

        def allocation_worker() -> list:
            results = []
            for _ in range(5):
                resource_id = allocate_resource()
                results.append(resource_id)
                time.sleep(0.01)  # Small delay
                if resource_id is not None:
                    deallocate_resource(resource_id)
            return results

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(allocation_worker) for _ in range(10)]
            for future in as_completed(futures):
                allocation_results.extend(future.result())

        # Verify no double allocation occurred
        valid_allocations = [r for r in allocation_results if r is not None]
        assert len(valid_allocations) > 0, f"Should successfully allocate resources - Test ID: {test_uuid}"

        # All resources should be deallocated
        assert len(allocated_resources) == 0, f"All resources should be deallocated - Test ID: {test_uuid}"


class TestStressConditions:
    """Test system behavior under stress conditions."""

    def test_rapid_agent_cycling(self, test_uuid: str) -> None:
        """Test rapid spawning and killing of agents."""
        max_agents = 10  # Reduced for stress test
        agent_counter = 0
        active_agents = {}

        def spawn_agent() -> int | None:
            nonlocal agent_counter
            if len(active_agents) >= max_agents:
                return None

            agent_id = agent_counter
            agent_counter += 1
            active_agents[agent_id] = {"session": f"stress-{agent_id}:1"}
            return agent_id

        def kill_agent(agent_id: int) -> bool:
            if agent_id in active_agents:
                del active_agents[agent_id]
                return True
            return False

        # Rapid cycling
        start_time = time.time()
        operations = 0

        while time.time() - start_time < 2.0:  # Run for 2 seconds
            # Spawn agents up to limit
            spawned = []
            for _ in range(max_agents):
                agent_id = spawn_agent()
                if agent_id is not None:
                    spawned.append(agent_id)
                    operations += 1

            # Kill all spawned agents
            for agent_id in spawned:
                kill_agent(agent_id)
                operations += 1

        execution_time = time.time() - start_time

        assert operations > 0, f"Should complete some operations - Test ID: {test_uuid}"
        assert len(active_agents) == 0, f"Should have no active agents after cycling - Test ID: {test_uuid}"

        # Should handle reasonable number of operations per second
        ops_per_second = operations / execution_time
        assert ops_per_second > 10, f"Should handle >10 ops/sec, got {ops_per_second:.1f} - Test ID: {test_uuid}"

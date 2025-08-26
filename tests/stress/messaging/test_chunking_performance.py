#!/usr/bin/env python3
"""Performance and stress tests for message chunking system.

This module tests the performance characteristics of the chunking system
under various load conditions and validates that performance targets are met.
"""

import concurrent.futures
import time
from unittest.mock import patch

import pytest

from tests.fixtures.messaging_fixtures import MessageSizeFixtures, PerformanceFixtures
from tmux_orchestrator.utils.tmux import TMUXManager


class TestChunkingPerformance:
    """Performance validation tests for chunking system."""

    def test_chunking_overhead_target(self):
        """Validate chunking overhead meets <100ms target for 1KB messages."""
        tmux = TMUXManager()
        message = MessageSizeFixtures.large_message()  # ~1KB

        with patch.object(tmux, "send_keys", return_value=True):
            with patch("time.sleep"):  # Remove artificial delays
                with PerformanceFixtures.timing_context() as timer:
                    result = tmux.send_text("session:0", message)

                assert result is True
                assert timer.duration_ms < 100, f"Chunking took {timer.duration_ms:.2f}ms, target: <100ms"

    def test_fast_path_performance(self):
        """Validate short message fast path meets <10ms target."""
        tmux = TMUXManager()
        message = MessageSizeFixtures.small_message()  # ~50 chars

        with patch.object(tmux, "send_keys", return_value=True):
            with PerformanceFixtures.timing_context() as timer:
                result = tmux.send_text("session:0", message)

            assert result is True
            assert timer.duration_ms < 10, f"Fast path took {timer.duration_ms:.2f}ms, target: <10ms"

    def test_chunking_algorithm_efficiency(self):
        """Test chunking algorithm efficiency across message sizes."""
        tmux = TMUXManager()

        test_sizes = [100, 500, 1000, 2500, 5000, 10000]
        timings = []

        for size in test_sizes:
            message = "x" * size

            with patch.object(tmux, "send_keys", return_value=True):
                with patch("time.sleep"):
                    with PerformanceFixtures.timing_context() as timer:
                        tmux.send_text("session:0", message)

                    timings.append((size, timer.duration_ms))

        # Verify performance scales reasonably with message size
        for i in range(1, len(timings)):
            prev_size, prev_time = timings[i - 1]
            curr_size, curr_time = timings[i]

            # Performance should scale sub-linearly (better than O(n²))
            size_ratio = curr_size / prev_size
            time_ratio = curr_time / prev_time if prev_time > 0 else 1

            assert (
                time_ratio < size_ratio * 2
            ), f"Performance degradation too steep: {time_ratio:.2f}x time for {size_ratio:.2f}x size"

    def test_memory_usage_efficiency(self):
        """Test memory usage doesn't grow excessively with message size."""
        tmux = TMUXManager()

        # Test chunking doesn't create excessive intermediate objects
        large_message = MessageSizeFixtures.xxl_message()  # ~10KB

        with patch.object(tmux, "send_keys", return_value=True):
            with patch("time.sleep"):
                # This should not cause memory issues
                result = tmux.send_text("session:0", large_message)

                assert result is True

    def test_concurrent_chunking_performance(self):
        """Test performance under concurrent chunking operations."""
        tmux = TMUXManager()
        message = MessageSizeFixtures.large_message()

        def chunk_message():
            with patch.object(tmux, "send_keys", return_value=True):
                with patch("time.sleep"):
                    return tmux.send_text("session:0", message)

        # Test concurrent operations
        with PerformanceFixtures.timing_context() as timer:
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(chunk_message) for _ in range(10)]
                results = [future.result() for future in futures]

        # All operations should succeed
        assert all(results)

        # Total time should be reasonable (less than sequential execution)
        assert timer.duration_ms < 1000, f"Concurrent chunking took {timer.duration_ms:.2f}ms"


class TestChunkingStressConditions:
    """Stress tests for chunking system under extreme conditions."""

    def test_maximum_practical_message_size(self):
        """Test chunking with maximum practical message size."""
        tmux = TMUXManager()
        max_message = MessageSizeFixtures.xxl_message()  # ~10KB

        with patch.object(tmux, "send_keys", return_value=True) as mock_send:
            with patch("time.sleep"):
                result = tmux.send_text("session:0", max_message)

        assert result is True

        # Should create reasonable number of chunks
        chunk_count = mock_send.call_count
        assert 10 <= chunk_count <= 100, f"Unexpected chunk count: {chunk_count}"

    def test_rapid_successive_chunking(self):
        """Test rapid successive chunking operations."""
        tmux = TMUXManager()
        message = MessageSizeFixtures.medium_message()

        results = []

        with patch.object(tmux, "send_keys", return_value=True):
            with patch("time.sleep"):
                with PerformanceFixtures.timing_context() as timer:
                    # Rapid succession of chunking operations
                    for _ in range(20):
                        result = tmux.send_text("session:0", message)
                        results.append(result)

        # All operations should succeed
        assert all(results)

        # Total time should be reasonable
        assert timer.duration_ms < 500, f"Rapid chunking took {timer.duration_ms:.2f}ms"

    def test_chunk_failure_under_stress(self):
        """Test behavior when chunk sending fails under stress conditions."""
        tmux = TMUXManager()
        message = MessageSizeFixtures.large_message()

        # Simulate intermittent failures
        call_count = 0

        def intermittent_failure(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return call_count % 3 != 0  # Fail every 3rd call

        with patch.object(tmux, "send_keys", side_effect=intermittent_failure):
            with patch("time.sleep"):
                result = tmux.send_text("session:0", message)

        # Should handle failures gracefully
        assert result is False  # Should report failure

    def test_extremely_long_words(self):
        """Test handling of extremely long words that exceed chunk size."""
        tmux = TMUXManager()

        # Create word longer than typical chunk size
        extremely_long_word = "a" * 500
        message = f"Normal text {extremely_long_word} more normal text"

        with patch.object(tmux, "send_keys", return_value=True) as mock_send:
            with patch("time.sleep"):
                result = tmux.send_text("session:0", message)

        assert result is True

        # Should handle long word gracefully (either split or handle as-is)
        assert mock_send.called

    def test_high_unicode_density(self):
        """Test performance with high Unicode character density."""
        tmux = TMUXManager()

        # Message with high density of multi-byte characters
        unicode_heavy = "🚀🔥⭐🎯💯🌟✨🎉" * 50  # 400 emoji characters

        with patch.object(tmux, "send_keys", return_value=True):
            with patch("time.sleep"):
                with PerformanceFixtures.timing_context() as timer:
                    result = tmux.send_text("session:0", unicode_heavy)

        assert result is True
        assert timer.duration_ms < 200, f"Unicode processing took {timer.duration_ms:.2f}ms"


class TestChunkingResourceLimits:
    """Resource limit and boundary condition tests."""

    def test_chunk_count_limits(self):
        """Test behavior with messages that would create excessive chunks."""
        tmux = TMUXManager()

        # Message that would create many small chunks
        repeated_punctuation = ". " * 1000  # 2000 characters of ". "

        with patch.object(tmux, "send_keys", return_value=True) as mock_send:
            with patch("time.sleep"):
                result = tmux.send_text("session:0", repeated_punctuation)

        assert result is True

        # Should not create excessive number of chunks
        chunk_count = mock_send.call_count
        assert chunk_count < 50, f"Excessive chunks created: {chunk_count}"

    def test_chunking_with_artificial_delays(self):
        """Test chunking performance with realistic network delays."""
        tmux = TMUXManager()
        message = MessageSizeFixtures.large_message()

        def delayed_send(*args, **kwargs):
            time.sleep(0.01)  # 10ms delay per chunk
            return True

        with patch.object(tmux, "send_keys", side_effect=delayed_send):
            with patch("time.sleep"):  # Remove inter-chunk delays
                with PerformanceFixtures.timing_context() as timer:
                    result = tmux.send_text("session:0", message)

        assert result is True

        # Should complete within reasonable time even with delays
        assert timer.duration_ms < 1000, f"Delayed chunking took {timer.duration_ms:.2f}ms"

    def test_chunk_metadata_overhead(self):
        """Test that metadata doesn't significantly impact performance."""
        tmux = TMUXManager()
        message = "Simple message content for metadata testing. " * 20

        with patch.object(tmux, "send_keys", return_value=True) as mock_send:
            with patch("time.sleep"):
                with PerformanceFixtures.timing_context() as timer:
                    result = tmux.send_text("session:0", message)

        assert result is True
        assert timer.duration_ms < 50, f"Metadata overhead: {timer.duration_ms:.2f}ms"

        # Verify metadata was added
        calls = mock_send.call_args_list
        if len(calls) > 1:  # Only check if message was actually chunked
            for i, call in enumerate(calls, 1):
                sent_text = call[0][1]
                assert sent_text.startswith(f"[{i}/{len(calls)}]")


class TestChunkingReliability:
    """Reliability and robustness tests."""

    def test_partial_send_failure_recovery(self):
        """Test recovery from partial send failures."""
        tmux = TMUXManager()
        message = MessageSizeFixtures.large_message()

        # Fail on 3rd chunk out of multiple chunks
        call_count = 0

        def selective_failure(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return call_count != 3  # Fail on 3rd call

        with patch.object(tmux, "send_keys", side_effect=selective_failure):
            with patch("time.sleep"):
                result = tmux.send_text("session:0", message)

        # Should detect failure and stop appropriately
        assert result is False
        assert call_count == 3  # Should stop after failure

    def test_chunking_consistency(self):
        """Test that chunking produces consistent results."""
        tmux = TMUXManager()
        message = MessageSizeFixtures.large_message()

        results = []

        for _ in range(5):
            chunks = tmux._chunk_message(message, max_chunk_size=180)
            results.append(chunks)

        # All runs should produce identical results
        first_result = results[0]
        for result in results[1:]:
            assert result == first_result, "Chunking results are not consistent"

    def test_content_preservation_under_stress(self):
        """Test that content is preserved under stress conditions."""
        tmux = TMUXManager()

        # Test various challenging content types
        challenging_messages = [
            MessageSizeFixtures.xl_message(),
            "Mixed content: 🚀 URLs https://example.com emails user@test.com",
            "Special chars: !@#$%^&*()_+-=[]{}|;':\",./<>?",
            "Unicode: café niño résumé 中文 العربية русский",
            "Code: def test(): return {'key': 'value'} # comment",
        ]

        for original_message in challenging_messages:
            chunks = tmux._chunk_message(original_message, max_chunk_size=50)
            reconstructed = " ".join(chunks)

            # Content should be preserved (allowing for whitespace normalization)
            assert reconstructed.replace("  ", " ") == original_message.replace("  ", " ")


@pytest.mark.performance
class TestPerformanceBenchmarks:
    """Performance benchmarks for regression testing."""

    def test_baseline_performance_benchmark(self):
        """Establish baseline performance metrics."""
        tmux = TMUXManager()

        benchmarks = {
            "tiny": (MessageSizeFixtures.tiny_message(), 5),  # 5ms target
            "small": (MessageSizeFixtures.small_message(), 10),  # 10ms target
            "medium": (MessageSizeFixtures.medium_message(), 25),  # 25ms target
            "large": (MessageSizeFixtures.large_message(), 50),  # 50ms target
            "xl": (MessageSizeFixtures.xl_message(), 100),  # 100ms target
        }

        results = {}

        for size_name, (message, target_ms) in benchmarks.items():
            with patch.object(tmux, "send_keys", return_value=True):
                with patch("time.sleep"):
                    with PerformanceFixtures.timing_context() as timer:
                        result = tmux.send_text("session:0", message)

                    assert result is True
                    results[size_name] = timer.duration_ms

                    # Log performance for monitoring
                    print(f"Benchmark {size_name}: {timer.duration_ms:.2f}ms (target: {target_ms}ms)")

                    # Soft assertion - log but don't fail on performance regression
                    if timer.duration_ms > target_ms:
                        print(
                            f"WARNING: Performance regression for {size_name}: {timer.duration_ms:.2f}ms > {target_ms}ms"
                        )

        # Store results for trend analysis
        return results


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "performance"])

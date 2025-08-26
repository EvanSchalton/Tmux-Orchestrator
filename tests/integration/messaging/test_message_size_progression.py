#!/usr/bin/env python3
"""Integration tests for message size progression scenarios.

Tests the complete message handling pipeline from 1 byte to 10KB messages,
validating that all components work together correctly across size boundaries.
"""

from unittest.mock import patch

import pytest

from tests.fixtures.messaging_fixtures import MessageSizeFixtures, PerformanceFixtures
from tmux_orchestrator.utils.tmux import TMUXManager


class TestMessageSizeProgression:
    """Integration tests for handling messages of various sizes."""

    def test_size_progression_1_byte_to_10kb(self):
        """Test complete size progression from 1 byte to 10KB."""
        tmux = TMUXManager()

        # Define test size progression
        test_messages = [
            ("1_byte", MessageSizeFixtures.tiny_message()),  # 1 byte
            ("50_chars", MessageSizeFixtures.small_message()),  # ~50 chars
            ("200_chars", MessageSizeFixtures.medium_message()),  # ~200 chars (threshold)
            ("1KB", MessageSizeFixtures.large_message()),  # ~1KB
            ("5KB", MessageSizeFixtures.xl_message()),  # ~5KB
            ("10KB", MessageSizeFixtures.xxl_message()),  # ~10KB
        ]

        results = {}

        for size_name, message in test_messages:
            with patch.object(tmux, "send_keys", return_value=True) as mock_send:
                with patch("time.sleep"):  # Remove delays for testing
                    with PerformanceFixtures.timing_context() as timer:
                        result = tmux.send_text("session:0", message)

                    # Collect results for analysis
                    results[size_name] = {
                        "success": result,
                        "message_length": len(message),
                        "chunk_count": mock_send.call_count,
                        "duration_ms": timer.duration_ms,
                    }

                    # Verify successful handling
                    assert result is True, f"Failed to handle {size_name} message"

        # Validate progression characteristics
        self._validate_size_progression_characteristics(results)

    def _validate_size_progression_characteristics(self, results):
        """Validate that size progression behaves as expected."""
        prev_size = 0
        prev_chunks = 0

        for size_name, metrics in results.items():
            current_size = metrics["message_length"]
            current_chunks = metrics["chunk_count"]

            # Size should increase monotonically
            assert current_size > prev_size, f"Size regression at {size_name}"

            # Chunk count should increase with message size (except for tiny messages)
            if prev_size > 50:  # Skip tiny messages that don't chunk
                assert current_chunks >= prev_chunks, f"Chunk count regression at {size_name}"

            # Performance should remain reasonable
            if current_size > 200:  # Only check chunked messages
                assert (
                    metrics["duration_ms"] < current_size * 0.1
                ), f"Performance issue at {size_name}: {metrics['duration_ms']:.2f}ms for {current_size} bytes"

            prev_size = current_size
            prev_chunks = current_chunks

    def test_chunking_threshold_behavior(self):
        """Test behavior around the chunking threshold (200 characters)."""
        tmux = TMUXManager()

        # Test messages around the chunking threshold
        threshold_tests = [
            ("under_threshold", "x" * 199),  # Just under
            ("at_threshold", "x" * 200),  # Exactly at threshold
            ("over_threshold", "x" * 201),  # Just over
        ]

        for test_name, message in threshold_tests:
            with patch.object(tmux, "send_keys", return_value=True) as mock_send:
                with patch("time.sleep"):
                    result = tmux.send_text("session:0", message)

                assert result is True

                # Verify chunking behavior around threshold
                if len(message) <= 200:
                    # Should not chunk
                    assert mock_send.call_count == 1, f"{test_name}: Expected 1 chunk, got {mock_send.call_count}"
                    # Verify no pagination metadata added
                    sent_text = mock_send.call_args[0][1]
                    assert not sent_text.startswith("["), f"{test_name}: Unexpected pagination in non-chunked message"
                else:
                    # Should chunk
                    assert mock_send.call_count > 1, f"{test_name}: Expected >1 chunks, got {mock_send.call_count}"
                    # Verify pagination metadata present
                    first_chunk = mock_send.call_args_list[0][0][1]
                    assert first_chunk.startswith("[1/"), f"{test_name}: Missing pagination metadata"

    def test_content_preservation_across_sizes(self):
        """Test that content is preserved accurately across all message sizes."""
        tmux = TMUXManager()

        # Test with structured content at various sizes
        base_content = "MARKER_START Hello World MARKER_END"

        size_multipliers = [1, 3, 6, 15, 50, 100]  # Creates various message sizes

        for multiplier in size_multipliers:
            test_message = base_content * multiplier

            with patch.object(tmux, "send_keys", return_value=True) as mock_send:
                with patch("time.sleep"):
                    result = tmux.send_text("session:0", test_message)

                assert result is True

                # Reconstruct message from sent chunks
                sent_chunks = []
                for call_args in mock_send.call_args_list:
                    chunk = call_args[0][1]

                    # Remove pagination metadata if present
                    if chunk.startswith("[") and "]" in chunk:
                        chunk = chunk[chunk.find("]") + 1 :].lstrip()

                    sent_chunks.append(chunk)

                reconstructed = " ".join(sent_chunks)

                # Verify content preservation
                assert "MARKER_START" in reconstructed, f"Missing start marker in {len(test_message)} byte message"
                assert "MARKER_END" in reconstructed, f"Missing end marker in {len(test_message)} byte message"
                assert (
                    reconstructed.count("Hello World") == multiplier
                ), f"Content corruption in {len(test_message)} byte message"

    def test_performance_scaling_across_sizes(self):
        """Test that performance scales reasonably with message size."""
        tmux = TMUXManager()

        # Performance test across size range
        test_sizes = [100, 500, 1000, 2500, 5000, 10000]
        performance_data = []

        for size in test_sizes:
            message = "x" * size

            with patch.object(tmux, "send_keys", return_value=True):
                with patch("time.sleep"):
                    with PerformanceFixtures.timing_context() as timer:
                        result = tmux.send_text("session:0", message)

                    assert result is True
                    performance_data.append((size, timer.duration_ms))

        # Validate performance scaling
        for i in range(1, len(performance_data)):
            prev_size, prev_time = performance_data[i - 1]
            curr_size, curr_time = performance_data[i]

            size_ratio = curr_size / prev_size
            time_ratio = curr_time / prev_time if prev_time > 0 else 1

            # Performance should scale better than O(n²)
            assert (
                time_ratio < size_ratio * 3
            ), f"Poor performance scaling: {time_ratio:.2f}x time for {size_ratio:.2f}x size"

    def test_memory_efficiency_across_sizes(self):
        """Test that memory usage remains efficient across message sizes."""
        tmux = TMUXManager()

        # Test that large messages don't cause memory issues
        large_messages = [
            MessageSizeFixtures.large_message(),  # 1KB
            MessageSizeFixtures.xl_message(),  # 5KB
            MessageSizeFixtures.xxl_message(),  # 10KB
        ]

        for message in large_messages:
            with patch.object(tmux, "send_keys", return_value=True):
                with patch("time.sleep"):
                    # This should not cause memory pressure or OOM
                    result = tmux.send_text("session:0", message)

                    assert result is True, f"Memory issue with {len(message)} byte message"

    def test_unicode_handling_across_sizes(self):
        """Test Unicode handling across various message sizes."""
        tmux = TMUXManager()

        # Unicode content at various sizes
        unicode_base = "Test 🚀 émojis ñ and 中文 characters "

        for multiplier in [1, 5, 10, 20]:
            unicode_message = unicode_base * multiplier

            with patch.object(tmux, "send_keys", return_value=True) as mock_send:
                with patch("time.sleep"):
                    result = tmux.send_text("session:0", unicode_message)

                assert result is True

                # Verify Unicode preservation
                sent_content = []
                for call_args in mock_send.call_args_list:
                    chunk = call_args[0][1]
                    # Remove pagination if present
                    if chunk.startswith("[") and "]" in chunk:
                        chunk = chunk[chunk.find("]") + 1 :].lstrip()
                    sent_content.append(chunk)

                reconstructed = " ".join(sent_content)

                # Check that all Unicode characters are preserved
                assert "🚀" in reconstructed, f"Missing emoji in {len(unicode_message)} byte message"
                assert "ñ" in reconstructed, f"Missing ñ in {len(unicode_message)} byte message"
                assert "中文" in reconstructed, f"Missing Chinese characters in {len(unicode_message)} byte message"


class TestEdgeCaseProgression:
    """Test edge cases across the size progression."""

    def test_boundary_word_splitting_across_sizes(self):
        """Test word boundary behavior across different message sizes."""
        tmux = TMUXManager()

        # Create messages with long words at various sizes
        long_word = "supercalifragilisticexpialidocious"

        for word_count in [1, 3, 10, 20, 50]:
            message = " ".join([long_word] * word_count)

            chunks = tmux._chunk_message(message, max_chunk_size=50)

            # Verify no words were broken inappropriately
            reconstructed = " ".join(chunks)
            assert reconstructed.count(long_word) == word_count, f"Word corruption with {word_count} words"

    def test_punctuation_handling_across_sizes(self):
        """Test punctuation boundary detection across sizes."""
        tmux = TMUXManager()

        sentence = "This is sentence one. This is sentence two! Is this sentence three?"

        for repetitions in [1, 5, 15, 30]:
            message = " ".join([sentence] * repetitions)

            chunks = tmux._chunk_message(message, max_chunk_size=80)

            # Verify sentence boundaries are respected
            reconstructed = " ".join(chunks)
            expected_sentences = repetitions * 3  # 3 sentences per repetition
            actual_sentences = reconstructed.count(".") + reconstructed.count("!") + reconstructed.count("?")

            assert actual_sentences == expected_sentences, f"Sentence corruption with {repetitions} repetitions"

    def test_mixed_content_across_sizes(self):
        """Test mixed content types across various sizes."""
        tmux = TMUXManager()

        mixed_content = (
            "Regular text with URLs https://example.com and emails user@test.com, "
            "emojis 🚀🔥, code `function test() {}`, and numbers 123.45."
        )

        for multiplier in [1, 3, 8, 15]:
            message = mixed_content * multiplier

            with patch.object(tmux, "send_keys", return_value=True):
                with patch("time.sleep"):
                    result = tmux.send_text("session:0", message)

                assert result is True, f"Mixed content failed at {len(message)} bytes"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

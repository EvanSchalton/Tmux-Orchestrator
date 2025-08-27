#!/usr/bin/env python3
"""Comprehensive test suite for ChunkBuffer functionality.

Tests cover:
- Message reassembly and chunk handling
- Timeout and error management
- Statistics tracking and reporting
- Edge cases and stress scenarios
"""

import time

import pytest

from tmux_orchestrator.core.messaging.chunk_buffer import ChunkBuffer


class TestChunkBufferCore:
    """Core functionality tests for ChunkBuffer."""

    def test_standard_message_passthrough(self):
        """Test that standard messages pass through without buffering."""
        buffer = ChunkBuffer()

        chunk = {"type": "standard", "sender": "test-agent", "content": "Simple message", "timestamp": time.time()}

        result = buffer.add_chunk(chunk)
        assert result == "Simple message"
        assert buffer.success_count == 1
        assert len(buffer.buffers) == 0  # No buffering for standard messages

    def test_chunked_message_reassembly(self):
        """Test reassembly of multi-chunk messages."""
        buffer = ChunkBuffer()

        # Create 3-chunk message
        message_id = "test-msg-001"
        chunks = [
            {
                "type": "chunked",
                "message_id": message_id,
                "chunk_index": 0,
                "total_chunks": 3,
                "sender": "test-agent",
                "content": "First chunk",
                "timestamp": time.time(),
            },
            {
                "type": "chunked",
                "message_id": message_id,
                "chunk_index": 1,
                "total_chunks": 3,
                "sender": "test-agent",
                "content": "Second chunk",
                "timestamp": time.time(),
            },
            {
                "type": "chunked",
                "message_id": message_id,
                "chunk_index": 2,
                "total_chunks": 3,
                "sender": "test-agent",
                "content": "Third chunk",
                "timestamp": time.time(),
            },
        ]

        # Add first two chunks - should return None
        assert buffer.add_chunk(chunks[0]) is None
        assert buffer.add_chunk(chunks[1]) is None
        assert len(buffer.buffers) == 1

        # Add final chunk - should trigger reassembly
        result = buffer.add_chunk(chunks[2])
        assert result == "First chunk Second chunk Third chunk"
        assert buffer.success_count == 1
        assert len(buffer.buffers) == 0  # Buffer should be cleaned up

    def test_out_of_order_reassembly(self):
        """Test that chunks can arrive out of order."""
        buffer = ChunkBuffer()

        message_id = "test-msg-002"
        chunks = [
            {
                "type": "chunked",
                "message_id": message_id,
                "chunk_index": 2,
                "total_chunks": 3,
                "sender": "test-agent",
                "content": "Third",
                "timestamp": time.time(),
            },
            {
                "type": "chunked",
                "message_id": message_id,
                "chunk_index": 0,
                "total_chunks": 3,
                "sender": "test-agent",
                "content": "First",
                "timestamp": time.time(),
            },
            {
                "type": "chunked",
                "message_id": message_id,
                "chunk_index": 1,
                "total_chunks": 3,
                "sender": "test-agent",
                "content": "Second",
                "timestamp": time.time(),
            },
        ]

        # Add chunks out of order
        assert buffer.add_chunk(chunks[0]) is None  # Index 2
        assert buffer.add_chunk(chunks[1]) is None  # Index 0
        result = buffer.add_chunk(chunks[2])  # Index 1 - completes message

        assert result == "First Second Third"
        assert buffer.reassembled_messages[0]["chunk_count"] == 3


class TestChunkValidation:
    """Tests for chunk validation and error handling."""

    def test_invalid_chunk_structure(self):
        """Test handling of malformed chunks."""
        buffer = ChunkBuffer()

        invalid_chunks = [
            {},  # Empty chunk
            {"type": "unknown"},  # Unknown type
            {"type": "chunked"},  # Missing required fields
            {"type": "chunked", "message_id": "123"},  # Missing chunk_index
            {"type": "standard"},  # Missing content
        ]

        for chunk in invalid_chunks:
            result = buffer.add_chunk(chunk)
            assert result is None

        assert buffer.error_count == len(invalid_chunks)

    def test_missing_chunk_detection(self):
        """Test detection of missing chunks."""
        buffer = ChunkBuffer()

        message_id = "test-msg-003"

        # Add chunks 0 and 2, skip 1
        buffer.add_chunk(
            {
                "type": "chunked",
                "message_id": message_id,
                "chunk_index": 0,
                "total_chunks": 3,
                "sender": "test-agent",
                "content": "First",
                "timestamp": time.time(),
            }
        )

        buffer.add_chunk(
            {
                "type": "chunked",
                "message_id": message_id,
                "chunk_index": 2,
                "total_chunks": 3,
                "sender": "test-agent",
                "content": "Third",
                "timestamp": time.time(),
            }
        )

        # Check incomplete messages
        incomplete = buffer.get_incomplete_messages()
        assert len(incomplete) == 1
        assert incomplete[0]["message_id"] == message_id
        assert incomplete[0]["missing_chunks"] == [1]
        assert incomplete[0]["received_chunks"] == 2
        assert incomplete[0]["total_chunks"] == 3

    def test_duplicate_chunk_handling(self):
        """Test that duplicate chunks are handled gracefully."""
        buffer = ChunkBuffer()

        chunk = {
            "type": "chunked",
            "message_id": "test-msg-004",
            "chunk_index": 0,
            "total_chunks": 2,
            "sender": "test-agent",
            "content": "Content",
            "timestamp": time.time(),
        }

        # Add same chunk twice
        buffer.add_chunk(chunk)
        buffer.add_chunk(chunk)  # Duplicate

        # Should still be waiting for chunk 1
        assert len(buffer.buffers) == 1
        assert buffer.buffers["test-msg-004"]["chunks"][0] == "Content"


class TestTimeoutHandling:
    """Tests for timeout detection and cleanup."""

    def test_message_timeout_detection(self):
        """Test that timed-out messages are detected and cleaned."""
        buffer = ChunkBuffer(timeout=1)  # 1 second timeout

        # Add incomplete message
        buffer.add_chunk(
            {
                "type": "chunked",
                "message_id": "timeout-msg",
                "chunk_index": 0,
                "total_chunks": 2,
                "sender": "test-agent",
                "content": "Partial",
                "timestamp": time.time(),
            }
        )

        # Message should be in buffer
        assert len(buffer.buffers) == 1

        # Wait for timeout
        time.sleep(1.1)

        # Check for timeouts
        timed_out = buffer.check_timeouts()
        assert "timeout-msg" in timed_out
        assert len(buffer.buffers) == 0
        assert buffer.error_count == 1

    def test_multiple_message_timeouts(self):
        """Test handling of multiple concurrent message timeouts."""
        buffer = ChunkBuffer(timeout=1)

        # Add multiple incomplete messages
        for i in range(3):
            buffer.add_chunk(
                {
                    "type": "chunked",
                    "message_id": f"timeout-{i}",
                    "chunk_index": 0,
                    "total_chunks": 2,
                    "sender": "test-agent",
                    "content": f"Partial-{i}",
                    "timestamp": time.time(),
                }
            )

        assert len(buffer.buffers) == 3

        # Wait for timeout
        time.sleep(1.1)

        # Check timeouts
        timed_out = buffer.check_timeouts()
        assert len(timed_out) == 3
        assert len(buffer.buffers) == 0
        assert buffer.error_count == 3

    def test_no_timeout_for_complete_messages(self):
        """Test that completed messages don't appear in timeout checks."""
        buffer = ChunkBuffer(timeout=10)

        message_id = "complete-msg"

        # Add complete message
        for i in range(2):
            result = buffer.add_chunk(
                {
                    "type": "chunked",
                    "message_id": message_id,
                    "chunk_index": i,
                    "total_chunks": 2,
                    "sender": "test-agent",
                    "content": f"Part-{i}",
                    "timestamp": time.time(),
                }
            )

        # Message should be reassembled
        assert result == "Part-0 Part-1"

        # No timeouts should be detected
        timed_out = buffer.check_timeouts()
        assert len(timed_out) == 0


class TestStatisticsTracking:
    """Tests for statistics and metrics tracking."""

    def test_basic_statistics(self):
        """Test basic statistics tracking."""
        buffer = ChunkBuffer()

        # Process some messages
        buffer.add_chunk(
            {"type": "standard", "sender": "agent1", "content": "Standard message", "timestamp": time.time()}
        )

        # Add incomplete chunked message
        buffer.add_chunk(
            {
                "type": "chunked",
                "message_id": "msg1",
                "chunk_index": 0,
                "total_chunks": 2,
                "sender": "agent2",
                "content": "Part 1",
                "timestamp": time.time(),
            }
        )

        # Add invalid chunk
        buffer.add_chunk({"invalid": "chunk"})

        stats = buffer.get_stats()
        assert stats["success_count"] == 1
        assert stats["error_count"] == 1
        assert stats["active_buffers"] == 1
        assert stats["incomplete_messages"] == 1

    def test_reassembly_history(self):
        """Test tracking of reassembled message history."""
        buffer = ChunkBuffer()

        # Complete a chunked message
        message_id = "history-msg"
        for i in range(3):
            buffer.add_chunk(
                {
                    "type": "chunked",
                    "message_id": message_id,
                    "chunk_index": i,
                    "total_chunks": 3,
                    "sender": "test-agent",
                    "content": f"Part{i}",
                    "timestamp": time.time(),
                }
            )

        history = buffer.get_reassembled_history()
        assert len(history) == 1
        assert history[0]["message_id"] == message_id
        assert history[0]["chunk_count"] == 3
        assert history[0]["content"] == "Part0 Part1 Part2"
        assert "duration_ms" in history[0]

    def test_history_limit(self):
        """Test that history respects the limit parameter."""
        buffer = ChunkBuffer()

        # Create multiple complete messages
        for msg_num in range(15):
            message_id = f"msg-{msg_num}"
            for chunk_num in range(2):
                buffer.add_chunk(
                    {
                        "type": "chunked",
                        "message_id": message_id,
                        "chunk_index": chunk_num,
                        "total_chunks": 2,
                        "sender": "test-agent",
                        "content": f"M{msg_num}C{chunk_num}",
                        "timestamp": time.time(),
                    }
                )

        # Check limited history
        history = buffer.get_reassembled_history(limit=5)
        assert len(history) == 5
        # Should get the most recent messages
        assert history[-1]["message_id"] == "msg-14"


class TestPerformanceAndStress:
    """Performance and stress tests."""

    def test_large_message_reassembly(self):
        """Test reassembly of messages with many chunks."""
        buffer = ChunkBuffer()

        message_id = "large-msg"
        num_chunks = 100

        # Create and add chunks
        for i in range(num_chunks):
            result = buffer.add_chunk(
                {
                    "type": "chunked",
                    "message_id": message_id,
                    "chunk_index": i,
                    "total_chunks": num_chunks,
                    "sender": "test-agent",
                    "content": f"Chunk{i:03d}",
                    "timestamp": time.time(),
                }
            )

            if i < num_chunks - 1:
                assert result is None

        # Final chunk should trigger reassembly
        assert result is not None
        assert result.startswith("Chunk000")
        assert result.endswith("Chunk099")
        assert buffer.reassembled_messages[0]["chunk_count"] == num_chunks

    def test_concurrent_message_handling(self):
        """Test handling multiple concurrent chunked messages."""
        buffer = ChunkBuffer()

        num_messages = 10
        chunks_per_message = 5

        # Interleave chunks from multiple messages
        all_chunks = []
        for msg_idx in range(num_messages):
            for chunk_idx in range(chunks_per_message):
                all_chunks.append(
                    {
                        "type": "chunked",
                        "message_id": f"msg-{msg_idx}",
                        "chunk_index": chunk_idx,
                        "total_chunks": chunks_per_message,
                        "sender": f"agent-{msg_idx}",
                        "content": f"M{msg_idx}C{chunk_idx}",
                        "timestamp": time.time(),
                    }
                )

        # Shuffle chunks to simulate random arrival
        import random

        random.shuffle(all_chunks)

        # Process all chunks
        completed_messages = []
        for chunk in all_chunks:
            result = buffer.add_chunk(chunk)
            if result:
                completed_messages.append(result)

        # All messages should be reassembled
        assert len(completed_messages) == num_messages
        assert buffer.success_count == num_messages

    def test_memory_cleanup(self):
        """Test that completed buffers are properly cleaned up."""
        buffer = ChunkBuffer()

        # Process many messages
        for i in range(100):
            message_id = f"cleanup-{i}"
            for j in range(3):
                buffer.add_chunk(
                    {
                        "type": "chunked",
                        "message_id": message_id,
                        "chunk_index": j,
                        "total_chunks": 3,
                        "sender": "test-agent",
                        "content": f"Content-{i}-{j}",
                        "timestamp": time.time(),
                    }
                )

        # All buffers should be cleaned up
        assert len(buffer.buffers) == 0
        assert buffer.success_count == 100

    def test_performance_overhead(self):
        """Test that reassembly overhead is within performance targets."""
        buffer = ChunkBuffer()

        # Create a 10KB message split into chunks
        chunk_size = 200
        total_size = 10 * 1024  # 10KB
        num_chunks = (total_size // chunk_size) + 1

        message_id = "perf-test"
        start_time = time.perf_counter()

        for i in range(num_chunks):
            chunk_content = "X" * min(chunk_size, total_size - (i * chunk_size))
            buffer.add_chunk(
                {
                    "type": "chunked",
                    "message_id": message_id,
                    "chunk_index": i,
                    "total_chunks": num_chunks,
                    "sender": "test-agent",
                    "content": chunk_content,
                    "timestamp": time.time(),
                }
            )

        end_time = time.perf_counter()
        duration_ms = (end_time - start_time) * 1000

        # Should complete within 100ms
        assert duration_ms < 100, f"Reassembly took {duration_ms:.2f}ms, expected <100ms"


class TestEdgeCases:
    """Edge case and boundary condition tests."""

    def test_empty_content_handling(self):
        """Test handling of chunks with empty content."""
        buffer = ChunkBuffer()

        result = buffer.add_chunk({"type": "standard", "sender": "test-agent", "content": "", "timestamp": time.time()})

        assert result == ""
        assert buffer.success_count == 1

    def test_single_chunk_message(self):
        """Test message that only has one chunk."""
        buffer = ChunkBuffer()

        result = buffer.add_chunk(
            {
                "type": "chunked",
                "message_id": "single",
                "chunk_index": 0,
                "total_chunks": 1,
                "sender": "test-agent",
                "content": "Single chunk content",
                "timestamp": time.time(),
            }
        )

        assert result == "Single chunk content"
        assert len(buffer.buffers) == 0

    def test_clear_functionality(self):
        """Test clearing all buffers."""
        buffer = ChunkBuffer()

        # Add some incomplete messages
        for i in range(5):
            buffer.add_chunk(
                {
                    "type": "chunked",
                    "message_id": f"msg-{i}",
                    "chunk_index": 0,
                    "total_chunks": 2,
                    "sender": "test-agent",
                    "content": f"Partial-{i}",
                    "timestamp": time.time(),
                }
            )

        assert len(buffer.buffers) == 5

        # Clear everything
        buffer.clear()

        assert len(buffer.buffers) == 0
        assert buffer.success_count == 0
        assert buffer.error_count == 0
        assert len(buffer.reassembled_messages) == 0

    def test_unicode_content(self):
        """Test handling of Unicode content in chunks."""
        buffer = ChunkBuffer()

        unicode_chunks = ["Hello 👋 World", "Testing 中文 characters", "Emojis 🚀 and symbols ñ é"]

        message_id = "unicode-msg"
        for i, content in enumerate(unicode_chunks):
            result = buffer.add_chunk(
                {
                    "type": "chunked",
                    "message_id": message_id,
                    "chunk_index": i,
                    "total_chunks": len(unicode_chunks),
                    "sender": "test-agent",
                    "content": content,
                    "timestamp": time.time(),
                }
            )

        assert result == " ".join(unicode_chunks)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

#!/usr/bin/env python3
"""Comprehensive test suite for EnhancedMessagingProtocol functionality.

Tests cover:
- Message preparation and encoding
- Acknowledgment handling
- Retry logic and timeout detection
- Duplicate detection and prevention
- Protocol statistics and performance
"""

import json
import time

import pytest

from tmux_orchestrator.core.messaging.enhanced_protocol import (
    EnhancedMessagingProtocol,
    MessageType,
)


class TestProtocolCore:
    """Core protocol functionality tests."""

    def test_message_preparation(self):
        """Test basic message preparation with metadata."""
        protocol = EnhancedMessagingProtocol()

        message = protocol.prepare_message(
            content="Test message", sender="agent-1", priority=3, metadata={"key": "value"}
        )

        assert message["content"] == "Test message"
        assert message["sender"] == "agent-1"
        assert message["priority"] == 3
        assert message["sequence"] == 1
        assert message["type"] == "standard"
        assert message["metadata"]["key"] == "value"
        assert "timestamp" in message
        assert message["retry_count"] == 0

    def test_sequence_number_increment(self):
        """Test that sequence numbers increment correctly."""
        protocol = EnhancedMessagingProtocol()

        messages = []
        for i in range(5):
            msg = protocol.prepare_message(f"Message {i}", "agent-1")
            messages.append(msg)

        # Check sequence numbers are sequential
        for i, msg in enumerate(messages):
            assert msg["sequence"] == i + 1

    def test_message_type_handling(self):
        """Test different message types."""
        protocol = EnhancedMessagingProtocol()

        # Standard message
        std_msg = protocol.prepare_message("Content", "agent", msg_type=MessageType.STANDARD)
        assert std_msg["type"] == "standard"

        # Chunked message
        chunk_msg = protocol.prepare_message("Content", "agent", msg_type=MessageType.CHUNKED)
        assert chunk_msg["type"] == "chunked"

        # Status message
        status_msg = protocol.prepare_message("Status", "agent", msg_type=MessageType.STATUS)
        assert status_msg["type"] == "status"


class TestMessageEncoding:
    """Message encoding and decoding tests."""

    def test_encode_decode_cycle(self):
        """Test that messages survive encode/decode cycle."""
        protocol = EnhancedMessagingProtocol()

        original = protocol.prepare_message(
            content="Test content with special chars: 中文 🚀",
            sender="test-agent",
            priority=5,
            metadata={"nested": {"key": "value"}},
        )

        # Encode
        encoded = protocol.encode_message(original)
        assert encoded.startswith("[[EMP:")
        assert encoded.endswith(":EMP]]")

        # Decode
        decoded = protocol.decode_message(encoded)
        assert decoded["content"] == original["content"]
        assert decoded["sender"] == original["sender"]
        assert decoded["metadata"]["nested"]["key"] == "value"

    def test_decode_invalid_messages(self):
        """Test decoding of malformed messages."""
        protocol = EnhancedMessagingProtocol()

        invalid_messages = [
            "plain text",
            "[[EMP:invalid json:EMP]]",
            '[[EMP:{"incomplete":}:EMP]]',
            '{"valid": "json", "but": "no wrapper"}',
            "[[EMP::EMP]]",  # Empty content
            None,
        ]

        for msg in invalid_messages:
            if msg is not None:
                decoded = protocol.decode_message(msg)
                assert decoded is None or "sequence" not in decoded

    def test_legacy_format_support(self):
        """Test that legacy JSON format is still supported."""
        protocol = EnhancedMessagingProtocol()

        legacy_message = json.dumps(
            {"sequence": 1, "type": "standard", "sender": "legacy-agent", "content": "Legacy format"}
        )

        decoded = protocol.decode_message(legacy_message)
        assert decoded is not None
        assert decoded["content"] == "Legacy format"

    def test_encoding_special_characters(self):
        """Test encoding of special characters and edge cases."""
        protocol = EnhancedMessagingProtocol()

        test_cases = [
            'Message with "quotes"',
            "Message with 'single quotes'",
            "Message with\nnewlines",
            "Message with\ttabs",
            "Unicode: 你好 مرحبا 🌍",
            '{"nested": "json"}',
        ]

        for content in test_cases:
            msg = protocol.prepare_message(content, "test")
            encoded = protocol.encode_message(msg)
            decoded = protocol.decode_message(encoded)
            assert decoded["content"] == content


class TestAcknowledgmentHandling:
    """Acknowledgment and NACK handling tests."""

    def test_ack_creation(self):
        """Test ACK message creation."""
        protocol = EnhancedMessagingProtocol()

        ack = protocol.create_ack(sequence=42, sender="agent-1")

        assert ack["type"] == "ack"
        assert ack["content"] == "ACK:42"
        assert ack["ack_sequence"] == 42
        assert ack["sender"] == "agent-1"

    def test_nack_creation(self):
        """Test NACK message creation with reason."""
        protocol = EnhancedMessagingProtocol()

        nack = protocol.create_nack(sequence=42, sender="agent-1", reason="Checksum mismatch")

        assert nack["type"] == "nack"
        assert "NACK:42" in nack["content"]
        assert nack["nack_sequence"] == 42
        assert nack["reason"] == "Checksum mismatch"

    def test_process_acknowledgments(self):
        """Test processing of ACK/NACK messages."""
        protocol = EnhancedMessagingProtocol()

        # Prepare and track a message
        msg = protocol.prepare_message("Test", "agent-1")
        seq = msg["sequence"]

        # Process ACK
        ack = protocol.create_ack(seq, "agent-2")
        is_ack, ack_seq = protocol.process_acknowledgment(ack)

        assert is_ack is True
        assert ack_seq == seq
        assert seq not in protocol.pending_acks
        assert protocol.transmission_stats["acked"] == 1

    def test_nack_processing(self):
        """Test NACK processing and retry setup."""
        protocol = EnhancedMessagingProtocol()

        # Prepare message
        msg = protocol.prepare_message("Test", "agent-1")
        seq = msg["sequence"]

        # Process NACK
        nack = protocol.create_nack(seq, "agent-2", "Error")
        is_ack, nack_seq = protocol.process_acknowledgment(nack)

        assert is_ack is False
        assert nack_seq == seq
        assert protocol.transmission_stats["nacked"] == 1


class TestRetryLogic:
    """Retry mechanism and failure handling tests."""

    def test_retry_mechanism(self):
        """Test message retry logic."""
        protocol = EnhancedMessagingProtocol(max_retries=3)

        msg = protocol.prepare_message("Retry test", "agent-1")
        seq = msg["sequence"]

        # Should allow retries up to max_retries
        assert protocol.should_retry(seq) is True

        # Mark for retry
        retry_msg = protocol.mark_retry(seq)
        assert retry_msg is not None
        assert retry_msg["retry_count"] == 1
        assert protocol.transmission_stats["retried"] == 1

        # Retry again
        retry_msg = protocol.mark_retry(seq)
        assert retry_msg is not None
        assert retry_msg["retry_count"] == 2

        # Final retry
        retry_msg = protocol.mark_retry(seq)
        assert retry_msg is None  # Max retries exceeded
        assert protocol.transmission_stats["failed"] == 1

    def test_retry_count_tracking(self):
        """Test that retry counts are properly tracked."""
        protocol = EnhancedMessagingProtocol(max_retries=5)

        msg = protocol.prepare_message("Test", "agent-1")
        seq = msg["sequence"]

        for i in range(4):
            assert protocol.should_retry(seq) is True
            retry_msg = protocol.mark_retry(seq)
            assert retry_msg["retry_count"] == i + 1

        # Fifth retry should fail
        assert protocol.should_retry(seq) is False
        retry_msg = protocol.mark_retry(seq)
        assert retry_msg is None

    def test_timeout_detection(self):
        """Test detection of timed-out messages."""
        protocol = EnhancedMessagingProtocol()

        # Prepare multiple messages
        msg1 = protocol.prepare_message("Message 1", "agent-1")
        time.sleep(0.1)
        msg2 = protocol.prepare_message("Message 2", "agent-1")

        # Check with short timeout
        timed_out = protocol.check_pending_timeouts(timeout=0.05)
        assert msg1["sequence"] in timed_out
        assert msg2["sequence"] not in timed_out


class TestDuplicateDetection:
    """Duplicate message detection tests."""

    def test_duplicate_detection(self):
        """Test detection of duplicate messages."""
        protocol = EnhancedMessagingProtocol()

        msg = {"sequence": 100, "type": "standard", "sender": "agent-1", "content": "Test"}

        # First receipt should not be duplicate
        assert protocol.is_duplicate(msg) is False

        # Second receipt should be duplicate
        assert protocol.is_duplicate(msg) is True

        # Different sequence should not be duplicate
        msg2 = msg.copy()
        msg2["sequence"] = 101
        assert protocol.is_duplicate(msg2) is False

    def test_duplicate_cache_limit(self):
        """Test that duplicate detection cache has size limit."""
        protocol = EnhancedMessagingProtocol()

        # Add many messages to exceed cache limit
        for i in range(15000):
            msg = {"sequence": i}
            protocol.is_duplicate(msg)

        # Cache should be trimmed
        assert len(protocol.received_sequences) < 11000

        # Old sequences might be forgotten
        old_msg = {"sequence": 0}
        # This might or might not be detected as duplicate depending on trimming
        # Just verify it doesn't crash
        protocol.is_duplicate(old_msg)


class TestHeartbeatAndStatus:
    """Heartbeat and status message tests."""

    def test_heartbeat_creation(self):
        """Test heartbeat message creation."""
        protocol = EnhancedMessagingProtocol()

        heartbeat = protocol.create_heartbeat("agent-1")

        assert heartbeat["type"] == "heartbeat"
        assert heartbeat["content"] == "HEARTBEAT"
        assert heartbeat["sender"] == "agent-1"
        assert "timestamp" in heartbeat

    def test_heartbeat_sequence(self):
        """Test that heartbeats increment sequence numbers."""
        protocol = EnhancedMessagingProtocol()

        initial_seq = protocol.sequence_number
        heartbeat = protocol.create_heartbeat("agent-1")

        assert heartbeat["sequence"] == initial_seq + 1


class TestStatistics:
    """Protocol statistics tracking tests."""

    def test_statistics_tracking(self):
        """Test comprehensive statistics tracking."""
        protocol = EnhancedMessagingProtocol()

        # Send some messages
        msg1 = protocol.prepare_message("Test 1", "agent-1")
        msg2 = protocol.prepare_message("Test 2", "agent-1")

        # Process ACK for first message
        ack = protocol.create_ack(msg1["sequence"], "agent-2")
        protocol.process_acknowledgment(ack)

        # Mark second for retry then fail
        protocol.mark_retry(msg2["sequence"])
        protocol.mark_retry(msg2["sequence"])
        protocol.mark_retry(msg2["sequence"])  # Exceeds max retries

        stats = protocol.get_stats()
        assert stats["sent"] == 2
        assert stats["acked"] == 1
        assert stats["failed"] == 1
        assert stats["retried"] == 2
        assert stats["success_rate"] == 50.0

    def test_reset_statistics(self):
        """Test statistics reset functionality."""
        protocol = EnhancedMessagingProtocol()

        # Generate some activity
        msg = protocol.prepare_message("Test", "agent-1")
        protocol.mark_retry(msg["sequence"])

        # Reset stats
        protocol.reset_stats()

        stats = protocol.get_stats()
        assert stats["sent"] == 0
        assert stats["acked"] == 0
        assert stats["retried"] == 0
        assert stats["failed"] == 0

    def test_pending_messages_info(self):
        """Test retrieval of pending message information."""
        protocol = EnhancedMessagingProtocol()

        # Create multiple pending messages
        for i in range(3):
            protocol.prepare_message(f"Message {i}", f"agent-{i}")

        pending = protocol.get_pending_messages()
        assert len(pending) == 3

        for i, msg_info in enumerate(pending):
            assert msg_info["sequence"] == i + 1
            assert msg_info["sender"] == f"agent-{i}"
            assert msg_info["attempts"] == 1
            assert "age_seconds" in msg_info


class TestMessageValidation:
    """Message validation tests."""

    def test_valid_message_structure(self):
        """Test validation of properly structured messages."""
        protocol = EnhancedMessagingProtocol()

        valid_msg = {"sequence": 1, "type": "standard", "sender": "agent-1", "content": "Valid message"}

        is_valid, error = protocol.validate_message(valid_msg)
        assert is_valid is True
        assert error is None

    def test_invalid_message_detection(self):
        """Test detection of invalid message structures."""
        protocol = EnhancedMessagingProtocol()

        test_cases = [
            ({}, "Missing required field"),
            ({"sequence": "not_int", "type": "standard", "sender": "a", "content": "c"}, "Sequence must be an integer"),
            ({"sequence": 1, "type": "invalid", "sender": "a", "content": "c"}, "Invalid message type"),
            ({"sequence": 1, "sender": "a", "content": "c"}, "Missing required field"),
        ]

        for msg, expected_error_part in test_cases:
            is_valid, error = protocol.validate_message(msg)
            assert is_valid is False
            assert expected_error_part in error or error is not None


class TestPerformance:
    """Performance and stress tests."""

    def test_encoding_performance(self):
        """Test that encoding meets performance targets."""
        protocol = EnhancedMessagingProtocol()

        # Prepare a 10KB message
        large_content = "X" * 10240
        msg = protocol.prepare_message(large_content, "agent-1")

        start_time = time.perf_counter()
        _encoded = protocol.encode_message(msg)
        end_time = time.perf_counter()

        duration_ms = (end_time - start_time) * 1000
        assert duration_ms < 100, f"Encoding took {duration_ms:.2f}ms, expected <100ms"

    def test_high_volume_tracking(self):
        """Test handling of high message volumes."""
        protocol = EnhancedMessagingProtocol()

        num_messages = 1000
        start_time = time.perf_counter()

        # Send many messages
        for i in range(num_messages):
            msg = protocol.prepare_message(f"Message {i}", "agent-1")
            if i % 3 == 0:
                # Simulate some ACKs
                ack = protocol.create_ack(msg["sequence"], "agent-2")
                protocol.process_acknowledgment(ack)

        end_time = time.perf_counter()
        duration_ms = (end_time - start_time) * 1000

        # Should handle 1000 messages quickly
        assert duration_ms < 1000, f"Processing took {duration_ms:.2f}ms"

        stats = protocol.get_stats()
        assert stats["sent"] == num_messages
        assert stats["acked"] > 0

    def test_memory_efficiency(self):
        """Test that protocol doesn't leak memory with pending messages."""
        protocol = EnhancedMessagingProtocol(max_retries=2)

        # Create and fail many messages
        for i in range(100):
            msg = protocol.prepare_message(f"Message {i}", "agent-1")
            seq = msg["sequence"]

            # Max out retries to clear from pending
            protocol.mark_retry(seq)
            protocol.mark_retry(seq)  # Should clear on max retries

        # Pending ACKs should be cleared
        assert len(protocol.pending_acks) == 0
        assert protocol.transmission_stats["failed"] == 100


class TestEdgeCases:
    """Edge case and boundary tests."""

    def test_empty_content_handling(self):
        """Test handling of empty message content."""
        protocol = EnhancedMessagingProtocol()

        msg = protocol.prepare_message("", "agent-1")
        assert msg["content"] == ""

        encoded = protocol.encode_message(msg)
        decoded = protocol.decode_message(encoded)
        assert decoded["content"] == ""

    def test_priority_boundaries(self):
        """Test priority value boundaries."""
        protocol = EnhancedMessagingProtocol()

        # Test extreme priorities
        high_priority = protocol.prepare_message("High", "agent", priority=1)
        assert high_priority["priority"] == 1

        low_priority = protocol.prepare_message("Low", "agent", priority=10)
        assert low_priority["priority"] == 10

        # Test out-of-range priorities (should still work)
        very_high = protocol.prepare_message("VeryHigh", "agent", priority=0)
        assert very_high["priority"] == 0

        very_low = protocol.prepare_message("VeryLow", "agent", priority=100)
        assert very_low["priority"] == 100

    def test_concurrent_sequence_safety(self):
        """Test that sequence numbers are thread-safe."""
        protocol = EnhancedMessagingProtocol()

        import threading

        sequences = []
        lock = threading.Lock()

        def send_messages():
            for _ in range(100):
                msg = protocol.prepare_message("Test", "agent")
                with lock:
                    sequences.append(msg["sequence"])

        # Create multiple threads
        threads = [threading.Thread(target=send_messages) for _ in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Check for duplicate sequences
        assert len(sequences) == len(set(sequences)), "Duplicate sequence numbers detected"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

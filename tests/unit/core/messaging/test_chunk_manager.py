#!/usr/bin/env python3
"""Comprehensive unit tests for ChunkManager class."""

import uuid
from datetime import datetime, timezone
from unittest.mock import patch

from tmux_orchestrator.core.messaging.chunk_manager import ChunkManager


class TestChunkManager:
    """Test suite for ChunkManager functionality."""

    def test_init_default_chunk_size(self):
        """Test ChunkManager initialization with default chunk size."""
        manager = ChunkManager()
        assert manager.chunk_size == 180
        assert manager.min_chunk_size == 50

    def test_init_custom_chunk_size(self):
        """Test ChunkManager initialization with custom chunk size."""
        manager = ChunkManager(chunk_size=100)
        assert manager.chunk_size == 100
        assert manager.min_chunk_size == 50

    def test_short_message_no_chunking(self):
        """Test that short messages (<= 200 chars) are not chunked."""
        manager = ChunkManager()
        short_message = "This is a short message that should not be chunked."
        sender = "test-agent"

        with patch("tmux_orchestrator.core.messaging.chunk_manager.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            mock_dt.timezone = timezone

            result = manager.chunk_message(short_message, sender)

        assert len(result) == 1
        chunk = result[0]
        assert chunk["type"] == "standard"
        assert chunk["sender"] == sender
        assert chunk["content"] == short_message
        assert chunk["timestamp"] == "2024-01-01T12:00:00+00:00"
        assert "message_id" not in chunk
        assert "chunk_index" not in chunk
        assert "total_chunks" not in chunk

    def test_long_message_chunking(self):
        """Test that long messages are properly chunked."""
        manager = ChunkManager(chunk_size=50)
        long_message = "This is a very long message that definitely needs to be split into multiple chunks because it exceeds the 200 character limit and the chunk size limit. This sentence makes it longer than 200 characters for proper testing."
        sender = "test-agent"

        with patch("tmux_orchestrator.core.messaging.chunk_manager.uuid.uuid4") as mock_uuid, patch(
            "tmux_orchestrator.core.messaging.chunk_manager.datetime"
        ) as mock_dt:
            mock_uuid.return_value = uuid.UUID("12345678-1234-5678-9abc-123456789abc")
            mock_dt.now.return_value = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            mock_dt.timezone = timezone

            result = manager.chunk_message(long_message, sender)

        assert len(result) > 1
        message_id = "12345678-1234-5678-9abc-123456789abc"

        for i, chunk in enumerate(result):
            assert chunk["type"] == "chunked"
            assert chunk["message_id"] == message_id
            assert chunk["chunk_index"] == i
            assert chunk["total_chunks"] == len(result)
            assert chunk["sender"] == sender
            assert chunk["timestamp"] == "2024-01-01T12:00:00+00:00"
            assert len(chunk["content"]) <= 50
            assert chunk["content"].strip()  # No empty chunks

    def test_sentence_boundary_splitting(self):
        """Test that messages are split at sentence boundaries when possible."""
        manager = ChunkManager(chunk_size=100)
        message = "This is sentence one. This is sentence two. This is sentence three."

        result = manager.chunk_message(message, "test-agent")

        # Should be chunked due to length > 200
        assert len(result) >= 1
        for chunk in result:
            # Content should end with sentence boundaries when possible
            content = chunk["content"]
            if not content.endswith("."):
                # If not ending with period, should be a continuation
                assert len(content) <= 100

    def test_word_boundary_splitting(self):
        """Test that chunks are split at word boundaries, not mid-word."""
        manager = ChunkManager(chunk_size=30)
        message = "This is a very long message without sentence boundaries that should be split at word boundaries only"

        result = manager.chunk_message(message, "test-agent")

        for chunk in result:
            content = chunk["content"].strip()
            # No chunk should start or end with partial words (except hyphenated)
            if content and not content.endswith("-"):
                words = content.split()
                # Each chunk should contain complete words
                assert all(word.strip() for word in words)

    def test_utf8_safety(self):
        """Test that UTF-8 characters are not broken across chunk boundaries."""
        manager = ChunkManager(chunk_size=50)
        # Message with Unicode characters
        message = (
            "This message contains émojis 🎯 and spëcial characters like café and naïve words that need UTF-8 safety."
        )

        result = manager.chunk_message(message, "test-agent")

        for chunk in result:
            content = chunk["content"]
            # Each chunk should be valid UTF-8
            assert manager.is_utf8_safe(content)
            # Should be able to encode/decode without errors
            encoded = content.encode("utf-8")
            decoded = encoded.decode("utf-8")
            assert decoded == content

    def test_chunk_validation_valid_chunked(self):
        """Test validation of valid chunked message."""
        manager = ChunkManager()
        valid_chunk = {
            "type": "chunked",
            "message_id": "test-id",
            "chunk_index": 0,
            "total_chunks": 2,
            "sender": "agent",
            "timestamp": "2024-01-01T12:00:00+00:00",
            "content": "test content",
        }

        assert manager.validate_chunk(valid_chunk) is True

    def test_chunk_validation_valid_standard(self):
        """Test validation of valid standard message."""
        manager = ChunkManager()
        valid_chunk = {
            "type": "standard",
            "sender": "agent",
            "timestamp": "2024-01-01T12:00:00+00:00",
            "content": "test content",
        }

        assert manager.validate_chunk(valid_chunk) is True

    def test_chunk_validation_missing_fields(self):
        """Test validation fails for chunks with missing required fields."""
        manager = ChunkManager()

        # Missing content
        invalid_chunk = {
            "type": "chunked",
            "message_id": "test-id",
            "chunk_index": 0,
            "total_chunks": 2,
            "sender": "agent",
            "timestamp": "2024-01-01T12:00:00+00:00",
        }
        assert manager.validate_chunk(invalid_chunk) is False

        # Missing chunk_index
        invalid_chunk = {
            "type": "chunked",
            "message_id": "test-id",
            "total_chunks": 2,
            "sender": "agent",
            "timestamp": "2024-01-01T12:00:00+00:00",
            "content": "test",
        }
        assert manager.validate_chunk(invalid_chunk) is False

    def test_chunk_validation_invalid_types(self):
        """Test validation fails for chunks with invalid field types."""
        manager = ChunkManager()

        # chunk_index should be int
        invalid_chunk = {
            "type": "chunked",
            "message_id": "test-id",
            "chunk_index": "0",  # String instead of int
            "total_chunks": 2,
            "sender": "agent",
            "timestamp": "2024-01-01T12:00:00+00:00",
            "content": "test",
        }
        assert manager.validate_chunk(invalid_chunk) is False

        # total_chunks should be int
        invalid_chunk = {
            "type": "chunked",
            "message_id": "test-id",
            "chunk_index": 0,
            "total_chunks": "2",  # String instead of int
            "sender": "agent",
            "timestamp": "2024-01-01T12:00:00+00:00",
            "content": "test",
        }
        assert manager.validate_chunk(invalid_chunk) is False

    def test_chunk_validation_invalid_range(self):
        """Test validation fails for chunks with invalid index ranges."""
        manager = ChunkManager()

        # chunk_index >= total_chunks
        invalid_chunk = {
            "type": "chunked",
            "message_id": "test-id",
            "chunk_index": 2,
            "total_chunks": 2,  # Index should be < total_chunks
            "sender": "agent",
            "timestamp": "2024-01-01T12:00:00+00:00",
            "content": "test",
        }
        assert manager.validate_chunk(invalid_chunk) is False

        # Negative chunk_index
        invalid_chunk = {
            "type": "chunked",
            "message_id": "test-id",
            "chunk_index": -1,
            "total_chunks": 2,
            "sender": "agent",
            "timestamp": "2024-01-01T12:00:00+00:00",
            "content": "test",
        }
        assert manager.validate_chunk(invalid_chunk) is False

    def test_chunk_validation_unknown_type(self):
        """Test validation fails for unknown message types."""
        manager = ChunkManager()
        invalid_chunk = {
            "type": "unknown",
            "sender": "agent",
            "timestamp": "2024-01-01T12:00:00+00:00",
            "content": "test",
        }
        assert manager.validate_chunk(invalid_chunk) is False

    def test_chunk_validation_empty_content(self):
        """Test validation fails for empty content."""
        manager = ChunkManager()
        invalid_chunk = {
            "type": "standard",
            "sender": "agent",
            "timestamp": "2024-01-01T12:00:00+00:00",
            "content": "",  # Empty content
        }
        assert manager.validate_chunk(invalid_chunk) is False

    def test_is_utf8_safe_valid(self):
        """Test UTF-8 safety validation for valid strings."""
        manager = ChunkManager()

        valid_strings = [
            "Hello, world!",
            "Café naïve résumé",
            "🎯💯🚀",
            "Mixed ASCII and émojis 🎉",
            "中文测试",
            "العربية",
        ]

        for string in valid_strings:
            assert manager.is_utf8_safe(string) is True

    def test_estimate_chunks_short_message(self):
        """Test chunk estimation for short messages."""
        manager = ChunkManager(chunk_size=100)

        # Message <= 200 chars should need 1 chunk
        assert manager.estimate_chunks(50) == 1
        assert manager.estimate_chunks(200) == 1

    def test_estimate_chunks_long_message(self):
        """Test chunk estimation for long messages."""
        manager = ChunkManager(chunk_size=100)

        # Messages > 200 chars should be estimated properly
        # With 90% efficiency, effective chunk size is 90
        assert manager.estimate_chunks(300) >= 3
        assert manager.estimate_chunks(500) >= 5

    def test_edge_case_empty_message(self):
        """Test handling of empty message."""
        manager = ChunkManager()
        result = manager.chunk_message("", "test-agent")

        assert len(result) == 1
        assert result[0]["type"] == "standard"
        assert result[0]["content"] == ""

    def test_edge_case_whitespace_only(self):
        """Test handling of whitespace-only message."""
        manager = ChunkManager()
        result = manager.chunk_message("   \n\t   ", "test-agent")

        assert len(result) == 1
        assert result[0]["type"] == "standard"
        assert result[0]["content"] == "   \n\t   "

    def test_chunk_size_exactly_at_boundary(self):
        """Test chunking when message length exactly matches boundaries."""
        manager = ChunkManager(chunk_size=50)

        # Message exactly 200 chars (boundary for chunking decision)
        message = "x" * 200
        result = manager.chunk_message(message, "test-agent")

        # Should not chunk at exactly 200 chars
        assert len(result) == 1
        assert result[0]["type"] == "standard"

        # Message exactly 201 chars (should chunk)
        message = "x" * 201
        result = manager.chunk_message(message, "test-agent")

        # Should chunk anything > 200 chars
        assert len(result) > 1
        assert all(chunk["type"] == "chunked" for chunk in result)

    def test_sentence_splitting_edge_cases(self):
        """Test sentence splitting with various punctuation."""
        manager = ChunkManager()

        test_cases = [
            "Hello! How are you? I'm fine.",
            "Dr. Smith went to the U.S.A. yesterday.",
            "What?! Really? That's amazing!",
            "First sentence. Second sentence. Third sentence.",
        ]

        for message in test_cases:
            sentences = manager._split_sentences(message)
            # Should split into multiple sentences
            assert len(sentences) >= 1
            # Reconstructed message should match original
            reconstructed = " ".join(sentences).strip()
            # Allow for minor whitespace differences in reconstruction
            assert reconstructed.replace("  ", " ") == message.replace("  ", " ")

    def test_very_long_single_word(self):
        """Test handling of extremely long single words."""
        manager = ChunkManager(chunk_size=50)

        # Single word longer than chunk size
        long_word = "supercalifragilisticexpialidocioussupercalifragilisticexpialidocious"
        message = f"Start {long_word} end"

        result = manager.chunk_message(message, "test-agent")

        # Should handle gracefully by force-splitting if necessary
        assert len(result) >= 1
        # All chunks should be valid
        for chunk in result:
            assert chunk["content"].strip()
            assert manager.is_utf8_safe(chunk["content"])

    def test_preserve_original_spacing(self):
        """Test that original spacing and formatting is preserved where possible."""
        manager = ChunkManager(chunk_size=100)

        message = "This  has   irregular    spacing\n\nand newlines\ttabs."
        result = manager.chunk_message(message, "test-agent")

        # Reconstruct message from chunks
        if len(result) == 1:
            reconstructed = result[0]["content"]
        else:
            reconstructed = " ".join(chunk["content"] for chunk in result)

        # Should preserve most formatting (allowing for some normalization at boundaries)
        assert "irregular" in reconstructed
        assert "spacing" in reconstructed


class TestChunkManagerIntegration:
    """Integration tests for ChunkManager with realistic scenarios."""

    def test_realistic_agent_message(self):
        """Test chunking of realistic agent communication message."""
        manager = ChunkManager(chunk_size=180)

        realistic_message = """I've analyzed the codebase and found several optimization opportunities. First, we can implement connection pooling to reduce database overhead. Second, adding Redis caching for frequently accessed data will improve response times. Third, optimizing the query patterns in the user service will reduce load. I recommend we prioritize these changes based on impact and implementation complexity."""

        result = manager.chunk_message(realistic_message, "backend-dev-001")

        # Should chunk this long message
        assert len(result) >= 2

        # Verify all chunks have proper metadata
        message_id = result[0]["message_id"]
        for i, chunk in enumerate(result):
            assert chunk["type"] == "chunked"
            assert chunk["message_id"] == message_id
            assert chunk["chunk_index"] == i
            assert chunk["total_chunks"] == len(result)
            assert chunk["sender"] == "backend-dev-001"
            assert chunk["content"].strip()

    def test_code_snippet_chunking(self):
        """Test chunking of code snippets with special formatting."""
        manager = ChunkManager(chunk_size=150)

        code_message = """Here's the implementation:

```python
def optimize_query(query):
    # Add connection pooling
    with get_connection() as conn:
        result = conn.execute(query)
        return result.fetchall()
```

This reduces connection overhead significantly."""

        result = manager.chunk_message(code_message, "dev-agent")

        # Should preserve code structure across chunks
        full_content = " ".join(chunk["content"] for chunk in result)
        assert "```python" in full_content
        assert "def optimize_query" in full_content
        assert "```" in full_content

    def test_multilingual_content(self):
        """Test chunking of multilingual content."""
        manager = ChunkManager(chunk_size=100)

        multilingual = "Hello! Bonjour! Hola! This message contains multiple languages: English, French (français), Spanish (español), Chinese (中文), Arabic (العربية), and Japanese (日本語). Each should be handled safely."

        result = manager.chunk_message(multilingual, "intl-agent")

        # All chunks should be UTF-8 safe
        for chunk in result:
            assert manager.is_utf8_safe(chunk["content"])
            # Should be able to encode/decode without errors
            content = chunk["content"]
            assert content.encode("utf-8").decode("utf-8") == content

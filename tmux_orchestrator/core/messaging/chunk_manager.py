"""ChunkManager for splitting long messages into deliverable chunks."""

import re
import uuid
from datetime import datetime, timezone


class ChunkManager:
    """Manages chunking of long messages for reliable delivery."""

    def __init__(self, chunk_size: int = 180):
        """Initialize ChunkManager.

        Args:
            chunk_size: Maximum size of each chunk (default 180 chars to leave room for metadata)
        """
        self.chunk_size = chunk_size
        self.min_chunk_size = 50  # Minimum chunk size to avoid tiny fragments

    def chunk_message(self, message: str, sender: str) -> list[dict]:
        """Split a message into chunks with metadata.

        Args:
            message: The message to chunk
            sender: ID of the sending agent

        Returns:
            List of chunk dictionaries ready for transmission
        """
        # Short messages don't need chunking
        if len(message) <= 200:
            return [
                {
                    "type": "standard",
                    "sender": sender,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "content": message,
                }
            ]

        # Generate unique message ID
        message_id = str(uuid.uuid4())

        # Split message into chunks
        chunks = self._split_message(message)
        total_chunks = len(chunks)

        # Create chunk dictionaries with metadata
        chunk_dicts = []
        for i, content in enumerate(chunks):
            chunk_dicts.append(
                {
                    "type": "chunked",
                    "message_id": message_id,
                    "chunk_index": i,
                    "total_chunks": total_chunks,
                    "sender": sender,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "content": content,
                }
            )

        return chunk_dicts

    def _split_message(self, message: str) -> list[str]:
        """Split message at word boundaries, ensuring UTF-8 safety.

        Args:
            message: The message to split

        Returns:
            List of message chunks
        """
        if len(message) <= self.chunk_size:
            return [message]

        chunks = []
        current_chunk = ""

        # Try to split at sentence boundaries first
        sentences = self._split_sentences(message)

        for sentence in sentences:
            # If single sentence is too long, split it further
            if len(sentence) > self.chunk_size:
                # Split long sentence by phrases
                sub_chunks = self._split_long_sentence(sentence)
                for sub_chunk in sub_chunks:
                    if current_chunk and len(current_chunk) + len(sub_chunk) + 1 <= self.chunk_size:
                        current_chunk = (current_chunk + " " + sub_chunk).strip()
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = sub_chunk
            else:
                # Try to fit sentence in current chunk
                if current_chunk and len(current_chunk) + len(sentence) + 1 <= self.chunk_size:
                    current_chunk = (current_chunk + " " + sentence).strip()
                else:
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = sentence

        # Add any remaining content
        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences, preserving sentence endings.

        Args:
            text: Text to split

        Returns:
            List of sentences
        """
        # Split on sentence boundaries, but keep the punctuation
        sentences = re.split(r"(?<=[.!?])\s+", text)

        # Handle edge cases where there's no sentence ending
        if not sentences:
            return [text]

        return [s for s in sentences if s.strip()]

    def _split_long_sentence(self, sentence: str) -> list[str]:
        """Split a long sentence into smaller chunks at natural boundaries.

        Args:
            sentence: Long sentence to split

        Returns:
            List of sentence fragments
        """
        chunks = []

        # First try splitting at commas, semicolons, colons
        parts = re.split(r"([,;:])\s*", sentence)

        current_part = ""
        for i, part in enumerate(parts):
            # Skip empty parts
            if not part.strip():
                continue

            # Preserve punctuation by combining with previous part
            if part in ",;:" and current_part:
                current_part += part
                continue

            # If part itself is too long, split by words
            if len(part) > self.chunk_size:
                # Save current part if any
                if current_part:
                    chunks.extend(self._split_by_words(current_part))
                    current_part = ""
                # Split the long part
                chunks.extend(self._split_by_words(part))
            else:
                # Try to combine with current part
                test_combined = (current_part + " " + part).strip() if current_part else part
                if len(test_combined) <= self.chunk_size:
                    current_part = test_combined
                else:
                    # Current part is full, save it
                    if current_part:
                        chunks.append(current_part)
                    current_part = part

        # Add any remaining part
        if current_part:
            if len(current_part) > self.chunk_size:
                chunks.extend(self._split_by_words(current_part))
            else:
                chunks.append(current_part)

        return chunks if chunks else [sentence]

    def _split_by_words(self, text: str) -> list[str]:
        """Split text by words as a last resort.

        Args:
            text: Text to split

        Returns:
            List of text chunks split at word boundaries
        """
        chunks = []
        current_chunk = ""

        words = text.split()
        for word in words:
            # Handle words longer than chunk size
            if len(word) > self.chunk_size:
                # Save current chunk if any
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""

                # Force-split the long word (rare case)
                for i in range(0, len(word), self.chunk_size):
                    chunks.append(word[i : i + self.chunk_size])
            else:
                # Try to add word to current chunk
                test_chunk = (current_chunk + " " + word).strip() if current_chunk else word
                if len(test_chunk) <= self.chunk_size:
                    current_chunk = test_chunk
                else:
                    # Current chunk is full
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = word

        # Add any remaining content
        if current_chunk:
            chunks.append(current_chunk)

        return chunks if chunks else [text]

    def validate_chunk(self, chunk: dict) -> bool:
        """Validate that a chunk has proper structure.

        Args:
            chunk: Chunk dictionary to validate

        Returns:
            True if chunk is valid
        """
        # Check required fields for chunked messages
        if chunk.get("type") == "chunked":
            required_fields = ["type", "message_id", "chunk_index", "total_chunks", "sender", "timestamp", "content"]
            if not all(field in chunk for field in required_fields):
                return False

            # Validate types
            if not isinstance(chunk["chunk_index"], int):
                return False
            if not isinstance(chunk["total_chunks"], int):
                return False
            if chunk["chunk_index"] < 0 or chunk["chunk_index"] >= chunk["total_chunks"]:
                return False

        # Check standard message
        elif chunk.get("type") == "standard":
            required_fields = ["type", "sender", "timestamp", "content"]
            if not all(field in chunk for field in required_fields):
                return False
        else:
            return False

        # Validate content is not empty
        if not chunk.get("content"):
            return False

        return True

    def is_utf8_safe(self, text: str) -> bool:
        """Check if text is UTF-8 safe.

        Args:
            text: Text to check

        Returns:
            True if text can be safely encoded as UTF-8
        """
        try:
            text.encode("utf-8")
            return True
        except UnicodeEncodeError:
            return False

    def estimate_chunks(self, message_length: int) -> int:
        """Estimate number of chunks needed for a message.

        Args:
            message_length: Length of the message

        Returns:
            Estimated number of chunks
        """
        if message_length <= 200:
            return 1

        # Account for word boundaries and overhead
        effective_chunk_size = self.chunk_size * 0.9  # 90% efficiency due to word boundaries
        return max(1, int((message_length + effective_chunk_size - 1) / effective_chunk_size))

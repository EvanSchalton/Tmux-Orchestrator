"""ChunkBuffer for reassembling chunked messages."""

import time
from datetime import datetime, timezone
from typing import Dict, List, Optional


class ChunkBuffer:
    """Manages reassembly of chunked messages with timeout handling."""

    def __init__(self, timeout: int = 60):
        """Initialize ChunkBuffer.

        Args:
            timeout: Seconds to wait for all chunks before timing out (default 60)
        """
        self.timeout = timeout
        self.buffers: Dict[str, Dict] = {}  # message_id -> buffer data
        self.reassembled_messages: List[Dict] = []
        self.error_count = 0
        self.success_count = 0

    def add_chunk(self, chunk: Dict) -> Optional[str]:
        """Add a chunk to the buffer.

        Args:
            chunk: Chunk dictionary with metadata

        Returns:
            Reassembled message if complete, None otherwise
        """
        # Validate chunk structure
        if not self._validate_chunk(chunk):
            self.error_count += 1
            return None

        # Handle standard messages (no chunking)
        if chunk.get("type") == "standard":
            self.success_count += 1
            return chunk.get("content")

        # Process chunked message
        message_id = chunk.get("message_id")
        if not message_id:
            self.error_count += 1
            return None

        # Initialize buffer for new message
        if message_id not in self.buffers:
            self.buffers[message_id] = {
                "chunks": {},
                "total_chunks": chunk.get("total_chunks"),
                "sender": chunk.get("sender"),
                "first_seen": time.time(),
                "last_seen": time.time(),
            }

        buffer = self.buffers[message_id]
        buffer["last_seen"] = time.time()

        # Add chunk to buffer
        chunk_index = chunk.get("chunk_index")
        if chunk_index is not None:
            buffer["chunks"][chunk_index] = chunk.get("content", "")

        # Check if message is complete
        if self._is_complete(message_id):
            reassembled = self._reassemble(message_id)
            self._cleanup_buffer(message_id)
            self.success_count += 1
            return reassembled

        return None

    def _validate_chunk(self, chunk: Dict) -> bool:
        """Validate chunk structure.

        Args:
            chunk: Chunk to validate

        Returns:
            True if valid, False otherwise
        """
        if chunk.get("type") == "standard":
            return "content" in chunk and "sender" in chunk

        if chunk.get("type") == "chunked":
            required = ["message_id", "chunk_index", "total_chunks", "content", "sender"]
            return all(field in chunk for field in required)

        return False

    def _is_complete(self, message_id: str) -> bool:
        """Check if all chunks for a message have been received.

        Args:
            message_id: Message ID to check

        Returns:
            True if complete, False otherwise
        """
        if message_id not in self.buffers:
            return False

        buffer = self.buffers[message_id]
        total_chunks = buffer.get("total_chunks")

        if total_chunks is None:
            return False

        # Check if we have all chunks
        received_chunks = set(buffer["chunks"].keys())
        expected_chunks = set(range(total_chunks))

        return received_chunks == expected_chunks

    def _reassemble(self, message_id: str) -> str:
        """Reassemble a complete message from chunks.

        Args:
            message_id: Message ID to reassemble

        Returns:
            Reassembled message content
        """
        if message_id not in self.buffers:
            return ""

        buffer = self.buffers[message_id]
        chunks = buffer["chunks"]
        total_chunks = buffer.get("total_chunks", 0)

        # Sort chunks by index and concatenate
        reassembled = ""
        for i in range(total_chunks):
            if i in chunks:
                reassembled += chunks[i]
                if i < total_chunks - 1:
                    reassembled += " "  # Add space between chunks

        # Store reassembled message metadata
        self.reassembled_messages.append(
            {
                "message_id": message_id,
                "sender": buffer.get("sender"),
                "content": reassembled,
                "reassembled_at": datetime.now(timezone.utc).isoformat(),
                "chunk_count": total_chunks,
                "duration_ms": int((buffer["last_seen"] - buffer["first_seen"]) * 1000),
            }
        )

        return reassembled.strip()

    def _cleanup_buffer(self, message_id: str) -> None:
        """Remove a message buffer after reassembly.

        Args:
            message_id: Message ID to clean up
        """
        if message_id in self.buffers:
            del self.buffers[message_id]

    def check_timeouts(self) -> List[str]:
        """Check for timed-out messages and clean them up.

        Returns:
            List of timed-out message IDs
        """
        current_time = time.time()
        timed_out = []

        for message_id, buffer in list(self.buffers.items()):
            if current_time - buffer["first_seen"] > self.timeout:
                timed_out.append(message_id)
                self._cleanup_buffer(message_id)
                self.error_count += 1

        return timed_out

    def get_incomplete_messages(self) -> List[Dict]:
        """Get information about incomplete messages.

        Returns:
            List of incomplete message information
        """
        incomplete = []
        current_time = time.time()

        for message_id, buffer in self.buffers.items():
            total_chunks = buffer.get("total_chunks", 0)
            received_chunks = len(buffer["chunks"])

            incomplete.append(
                {
                    "message_id": message_id,
                    "sender": buffer.get("sender"),
                    "received_chunks": received_chunks,
                    "total_chunks": total_chunks,
                    "missing_chunks": list(set(range(total_chunks)) - set(buffer["chunks"].keys())),
                    "age_seconds": int(current_time - buffer["first_seen"]),
                    "last_activity_seconds": int(current_time - buffer["last_seen"]),
                }
            )

        return incomplete

    def get_stats(self) -> Dict:
        """Get buffer statistics.

        Returns:
            Dictionary of statistics
        """
        return {
            "active_buffers": len(self.buffers),
            "reassembled_count": len(self.reassembled_messages),
            "success_count": self.success_count,
            "error_count": self.error_count,
            "incomplete_messages": len(self.buffers),
            "total_chunks_buffered": sum(len(b["chunks"]) for b in self.buffers.values()),
        }

    def clear(self) -> None:
        """Clear all buffers and reset statistics."""
        self.buffers.clear()
        self.reassembled_messages.clear()
        self.error_count = 0
        self.success_count = 0

    def get_reassembled_history(self, limit: int = 10) -> List[Dict]:
        """Get recent reassembled message history.

        Args:
            limit: Maximum number of messages to return

        Returns:
            List of recent reassembled messages
        """
        return self.reassembled_messages[-limit:] if self.reassembled_messages else []

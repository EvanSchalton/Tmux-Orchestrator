"""Enhanced messaging protocol for reliable chunk transmission."""

import json
import time
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class MessageType(Enum):
    """Types of messages in the protocol."""

    STANDARD = "standard"
    CHUNKED = "chunked"
    ACK = "ack"
    NACK = "nack"
    HEARTBEAT = "heartbeat"
    STATUS = "status"
    ERROR = "error"


class EnhancedMessagingProtocol:
    """Protocol for reliable message transmission with acknowledgments."""

    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        """Initialize the messaging protocol.

        Args:
            max_retries: Maximum number of retry attempts for failed transmissions
            retry_delay: Delay in seconds between retry attempts
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.sequence_number = 0
        self.pending_acks: Dict[int, Dict] = {}  # seq_num -> message data
        self.received_sequences: set[int] = set()
        self.transmission_stats = {"sent": 0, "acked": 0, "nacked": 0, "retried": 0, "failed": 0}

    def prepare_message(
        self,
        content: str,
        sender: str,
        msg_type: MessageType = MessageType.STANDARD,
        priority: int = 5,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """Prepare a message for transmission.

        Args:
            content: Message content
            sender: Sender identification
            msg_type: Type of message
            priority: Message priority (1=highest, 10=lowest)
            metadata: Additional metadata

        Returns:
            Prepared message dictionary
        """
        self.sequence_number += 1

        message = {
            "sequence": self.sequence_number,
            "type": msg_type.value,
            "sender": sender,
            "content": content,
            "priority": priority,
            "timestamp": time.time(),
            "retry_count": 0,
            "metadata": metadata or {},
        }

        # Track pending acknowledgment
        self.pending_acks[self.sequence_number] = {"message": message, "sent_at": time.time(), "attempts": 1}

        self.transmission_stats["sent"] += 1
        return message

    def encode_message(self, message: Dict) -> str:
        """Encode a message for transmission.

        Args:
            message: Message dictionary

        Returns:
            JSON-encoded message string
        """
        try:
            # Ensure all fields are serializable
            encoded = json.dumps(message, separators=(",", ":"))

            # Add protocol wrapper for detection
            return f"[[EMP:{encoded}:EMP]]"
        except (TypeError, ValueError) as e:
            raise ValueError(f"Failed to encode message: {e}")

    def decode_message(self, raw_message: str) -> Optional[Dict]:
        """Decode a received message.

        Args:
            raw_message: Raw message string

        Returns:
            Decoded message dictionary or None if invalid
        """
        # Check for protocol wrapper
        if not (raw_message.startswith("[[EMP:") and raw_message.endswith(":EMP]]")):
            # Try to handle legacy format
            try:
                result = json.loads(raw_message)
                return dict(result) if isinstance(result, dict) else None
            except (json.JSONDecodeError, ValueError):
                return None

        # Extract JSON content
        try:
            json_content = raw_message[6:-6]  # Remove [[EMP: and :EMP]]
            message = json.loads(json_content)

            # Validate required fields
            required_fields = ["sequence", "type", "sender", "content"]
            if isinstance(message, dict) and all(field in message for field in required_fields):
                return dict(message)
            return None
        except (json.JSONDecodeError, ValueError):
            return None

    def create_ack(self, sequence: int, sender: str) -> Dict:
        """Create an acknowledgment message.

        Args:
            sequence: Sequence number to acknowledge
            sender: Sender of the acknowledgment

        Returns:
            ACK message dictionary
        """
        return {
            "sequence": self.sequence_number + 1,
            "type": MessageType.ACK.value,
            "sender": sender,
            "content": f"ACK:{sequence}",
            "ack_sequence": sequence,
            "timestamp": time.time(),
        }

    def create_nack(self, sequence: int, sender: str, reason: str = "") -> Dict:
        """Create a negative acknowledgment message.

        Args:
            sequence: Sequence number to NACK
            sender: Sender of the NACK
            reason: Reason for negative acknowledgment

        Returns:
            NACK message dictionary
        """
        return {
            "sequence": self.sequence_number + 1,
            "type": MessageType.NACK.value,
            "sender": sender,
            "content": f"NACK:{sequence}:{reason}",
            "nack_sequence": sequence,
            "reason": reason,
            "timestamp": time.time(),
        }

    def process_acknowledgment(self, message: Dict) -> Tuple[bool, Optional[int]]:
        """Process an acknowledgment message.

        Args:
            message: ACK or NACK message

        Returns:
            Tuple of (is_ack, sequence_number)
        """
        msg_type = message.get("type")

        if msg_type == MessageType.ACK.value:
            seq = message.get("ack_sequence")
            if seq and seq in self.pending_acks:
                del self.pending_acks[seq]
                self.transmission_stats["acked"] += 1
                return True, seq
        elif msg_type == MessageType.NACK.value:
            seq = message.get("nack_sequence")
            if seq:
                self.transmission_stats["nacked"] += 1
                return False, seq

        return False, None

    def should_retry(self, sequence: int) -> bool:
        """Check if a message should be retried.

        Args:
            sequence: Sequence number to check

        Returns:
            True if should retry, False otherwise
        """
        if sequence not in self.pending_acks:
            return False

        pending = self.pending_acks[sequence]
        return bool(pending["attempts"] < self.max_retries)

    def mark_retry(self, sequence: int) -> Optional[Dict]:
        """Mark a message for retry and return updated message.

        Args:
            sequence: Sequence number to retry

        Returns:
            Updated message for retry or None if max retries exceeded
        """
        if sequence not in self.pending_acks:
            return None

        pending = self.pending_acks[sequence]

        if pending["attempts"] >= self.max_retries:
            self.transmission_stats["failed"] += 1
            del self.pending_acks[sequence]
            return None

        pending["attempts"] += 1
        pending["message"]["retry_count"] = pending["attempts"] - 1
        pending["sent_at"] = time.time()
        self.transmission_stats["retried"] += 1

        return dict(pending["message"])

    def is_duplicate(self, message: Dict) -> bool:
        """Check if a message is a duplicate.

        Args:
            message: Message to check

        Returns:
            True if duplicate, False otherwise
        """
        seq = message.get("sequence")
        if seq is None:
            return False

        if seq in self.received_sequences:
            return True

        self.received_sequences.add(seq)

        # Limit set size to prevent memory issues
        if len(self.received_sequences) > 10000:
            # Remove oldest sequences (assuming they increment)
            min_seq = min(self.received_sequences)
            self.received_sequences = {s for s in self.received_sequences if s > min_seq + 1000}

        return False

    def create_heartbeat(self, sender: str) -> Dict:
        """Create a heartbeat message.

        Args:
            sender: Sender identification

        Returns:
            Heartbeat message dictionary
        """
        return {
            "sequence": self.sequence_number + 1,
            "type": MessageType.HEARTBEAT.value,
            "sender": sender,
            "content": "HEARTBEAT",
            "timestamp": time.time(),
        }

    def check_pending_timeouts(self, timeout: float = 30.0) -> List[int]:
        """Check for messages that have timed out waiting for acknowledgment.

        Args:
            timeout: Timeout in seconds

        Returns:
            List of timed-out sequence numbers
        """
        current_time = time.time()
        timed_out = []

        for seq, pending in list(self.pending_acks.items()):
            if current_time - pending["sent_at"] > timeout:
                timed_out.append(seq)
                if not self.should_retry(seq):
                    del self.pending_acks[seq]
                    self.transmission_stats["failed"] += 1

        return timed_out

    def get_stats(self) -> Dict[str, Any]:
        """Get protocol statistics.

        Returns:
            Dictionary of transmission statistics
        """
        stats: Dict[str, Any] = self.transmission_stats.copy()
        stats["pending_acks"] = len(self.pending_acks)
        stats["received_unique"] = len(self.received_sequences)

        # Calculate success rate
        total_completed = stats["acked"] + stats["failed"]
        if total_completed > 0:
            stats["success_rate"] = int(stats["acked"] / total_completed * 100)
        else:
            stats["success_rate"] = 0

        return stats

    def reset_stats(self) -> None:
        """Reset transmission statistics."""
        self.transmission_stats = {"sent": 0, "acked": 0, "nacked": 0, "retried": 0, "failed": 0}

    def validate_message(self, message: Dict) -> Tuple[bool, Optional[str]]:
        """Validate a message structure.

        Args:
            message: Message to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        required_fields = ["sequence", "type", "sender", "content"]

        for field in required_fields:
            if field not in message:
                return False, f"Missing required field: {field}"

        if not isinstance(message.get("sequence"), int):
            return False, "Sequence must be an integer"

        valid_types = [t.value for t in MessageType]
        if message.get("type") not in valid_types:
            return False, f"Invalid message type: {message.get('type')}"

        return True, None

    def get_pending_messages(self) -> List[Dict]:
        """Get list of messages pending acknowledgment.

        Returns:
            List of pending messages with metadata
        """
        pending = []
        current_time = time.time()

        for seq, data in self.pending_acks.items():
            pending.append(
                {
                    "sequence": seq,
                    "sender": data["message"].get("sender"),
                    "type": data["message"].get("type"),
                    "attempts": data["attempts"],
                    "age_seconds": int(current_time - data["sent_at"]),
                }
            )

        return pending

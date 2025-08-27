"""MessageQueue for priority-based ordered message delivery."""

import heapq
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass(order=True)
class PriorityMessage:
    """Message with priority for queue ordering."""

    priority: int
    sequence: int = field(compare=False)
    timestamp: float = field(compare=False)
    content: str = field(compare=False)
    sender: str = field(compare=False)
    metadata: Dict = field(default_factory=dict, compare=False)


class MessageQueue:
    """Thread-safe priority queue for ordered message delivery."""

    def __init__(self, max_size: int = 1000, enable_deduplication: bool = True):
        """Initialize MessageQueue.

        Args:
            max_size: Maximum queue size
            enable_deduplication: Enable duplicate message detection
        """
        self.max_size = max_size
        self.enable_deduplication = enable_deduplication
        self.queue: List[PriorityMessage] = []
        self.lock = threading.Lock()
        self.not_empty = threading.Condition(self.lock)
        self.not_full = threading.Condition(self.lock)
        self.sequence_counter = 0
        self.seen_messages: set[int] = set()
        self.stats: Dict[str, int] = {"enqueued": 0, "dequeued": 0, "dropped": 0, "duplicates": 0, "peak_size": 0}

    def enqueue(self, content: str, sender: str, priority: int = 5, metadata: Optional[Dict] = None) -> bool:
        """Add a message to the queue.

        Args:
            content: Message content
            sender: Sender identification
            priority: Priority level (1=highest, 10=lowest)
            metadata: Additional metadata

        Returns:
            True if enqueued successfully, False if queue full or duplicate
        """
        with self.lock:
            # Check for duplicates
            if self.enable_deduplication:
                msg_hash = hash((content, sender))
                if msg_hash in self.seen_messages:
                    self.stats["duplicates"] += 1
                    return False
                self.seen_messages.add(msg_hash)

                # Limit deduplication cache size
                if len(self.seen_messages) > 10000:
                    self.seen_messages = set(list(self.seen_messages)[-5000:])

            # Check queue capacity
            if len(self.queue) >= self.max_size:
                self.stats["dropped"] += 1
                return False

            # Create and add message
            self.sequence_counter += 1
            message = PriorityMessage(
                priority=priority,
                sequence=self.sequence_counter,
                timestamp=time.time(),
                content=content,
                sender=sender,
                metadata=metadata or {},
            )

            heapq.heappush(self.queue, message)
            self.stats["enqueued"] += 1
            self.stats["peak_size"] = max(self.stats["peak_size"], len(self.queue))

            self.not_empty.notify()
            return True

    def dequeue(self, timeout: Optional[float] = None) -> Optional[PriorityMessage]:
        """Remove and return the highest priority message.

        Args:
            timeout: Maximum time to wait for a message (None = no timeout)

        Returns:
            Message or None if timeout or empty
        """
        with self.not_empty:
            if timeout is not None:
                end_time = time.time() + timeout
                while not self.queue:
                    remaining = end_time - time.time()
                    if remaining <= 0:
                        return None
                    if not self.not_empty.wait(remaining):
                        return None
            else:
                while not self.queue:
                    self.not_empty.wait()

            if self.queue:
                message = heapq.heappop(self.queue)
                self.stats["dequeued"] += 1
                self.not_full.notify()
                return message

            return None

    def peek(self) -> Optional[PriorityMessage]:
        """Look at the highest priority message without removing it.

        Returns:
            Message or None if empty
        """
        with self.lock:
            if self.queue:
                return self.queue[0]
            return None

    def size(self) -> int:
        """Get current queue size.

        Returns:
            Number of messages in queue
        """
        with self.lock:
            return len(self.queue)

    def is_empty(self) -> bool:
        """Check if queue is empty.

        Returns:
            True if empty, False otherwise
        """
        with self.lock:
            return len(self.queue) == 0

    def is_full(self) -> bool:
        """Check if queue is full.

        Returns:
            True if at capacity, False otherwise
        """
        with self.lock:
            return len(self.queue) >= self.max_size

    def clear(self) -> int:
        """Clear all messages from the queue.

        Returns:
            Number of messages cleared
        """
        with self.lock:
            count = len(self.queue)
            self.queue.clear()
            self.seen_messages.clear()
            self.not_full.notify_all()
            return count

    def get_messages_by_priority(self, priority: int) -> List[PriorityMessage]:
        """Get all messages with a specific priority.

        Args:
            priority: Priority level to filter by

        Returns:
            List of messages with the specified priority
        """
        with self.lock:
            return [msg for msg in self.queue if msg.priority == priority]

    def get_messages_by_sender(self, sender: str) -> List[PriorityMessage]:
        """Get all messages from a specific sender.

        Args:
            sender: Sender to filter by

        Returns:
            List of messages from the sender
        """
        with self.lock:
            return [msg for msg in self.queue if msg.sender == sender]

    def remove_by_sender(self, sender: str) -> int:
        """Remove all messages from a specific sender.

        Args:
            sender: Sender whose messages to remove

        Returns:
            Number of messages removed
        """
        with self.lock:
            original_size = len(self.queue)
            self.queue = [msg for msg in self.queue if msg.sender != sender]
            heapq.heapify(self.queue)
            removed = original_size - len(self.queue)

            if removed > 0:
                self.not_full.notify()

            return removed

    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics.

        Returns:
            Dictionary of queue statistics
        """
        with self.lock:
            stats: Dict[str, Any] = self.stats.copy()
            stats["current_size"] = len(self.queue)
            stats["max_size"] = self.max_size
            stats["utilization"] = float(len(self.queue) / self.max_size * 100) if self.max_size > 0 else 0.0

            # Priority distribution
            priority_dist: Dict[int, int] = {}
            for msg in self.queue:
                priority_dist[msg.priority] = priority_dist.get(msg.priority, 0) + 1
            stats["priority_distribution"] = priority_dist

            # Age statistics
            if self.queue:
                current_time = time.time()
                ages = [current_time - msg.timestamp for msg in self.queue]
                stats["oldest_message_age"] = float(max(ages))
                stats["newest_message_age"] = float(min(ages))
                stats["average_message_age"] = float(sum(ages) / len(ages))
            else:
                stats["oldest_message_age"] = 0.0
                stats["newest_message_age"] = 0.0
                stats["average_message_age"] = 0.0

            return stats

    def batch_dequeue(self, max_count: int = 10, timeout: Optional[float] = None) -> List[PriorityMessage]:
        """Dequeue multiple messages at once.

        Args:
            max_count: Maximum number of messages to dequeue
            timeout: Maximum time to wait for first message

        Returns:
            List of dequeued messages
        """
        messages = []

        # Wait for first message with timeout
        first_msg = self.dequeue(timeout)
        if first_msg:
            messages.append(first_msg)

            # Try to get more messages without waiting
            for _ in range(max_count - 1):
                msg = self.dequeue(timeout=0)
                if msg:
                    messages.append(msg)
                else:
                    break

        return messages

    def batch_enqueue(self, messages: List[Tuple[str, str, int, Optional[Dict]]]) -> int:
        """Enqueue multiple messages at once.

        Args:
            messages: List of (content, sender, priority, metadata) tuples

        Returns:
            Number of messages successfully enqueued
        """
        count = 0
        for content, sender, priority, metadata in messages:
            if self.enqueue(content, sender, priority, metadata):
                count += 1
        return count

    def get_queue_snapshot(self) -> List[Dict]:
        """Get a snapshot of all messages in the queue.

        Returns:
            List of message dictionaries
        """
        with self.lock:
            return [
                {
                    "priority": msg.priority,
                    "sequence": msg.sequence,
                    "timestamp": msg.timestamp,
                    "content": msg.content,
                    "sender": msg.sender,
                    "metadata": msg.metadata,
                    "age": time.time() - msg.timestamp,
                }
                for msg in sorted(self.queue)
            ]

    def requeue_message(self, message: PriorityMessage, new_priority: Optional[int] = None) -> bool:
        """Requeue a message with optional priority change.

        Args:
            message: Message to requeue
            new_priority: New priority level (None keeps original)

        Returns:
            True if requeued successfully
        """
        if new_priority is not None:
            message.priority = new_priority

        return self.enqueue(
            content=message.content, sender=message.sender, priority=message.priority, metadata=message.metadata
        )

    def expire_old_messages(self, max_age: float) -> int:
        """Remove messages older than specified age.

        Args:
            max_age: Maximum message age in seconds

        Returns:
            Number of messages expired
        """
        with self.lock:
            current_time = time.time()
            original_size = len(self.queue)

            self.queue = [msg for msg in self.queue if current_time - msg.timestamp <= max_age]
            heapq.heapify(self.queue)

            expired = original_size - len(self.queue)
            if expired > 0:
                self.not_full.notify()

            return expired

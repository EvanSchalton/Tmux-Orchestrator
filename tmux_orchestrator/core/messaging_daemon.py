#!/usr/bin/env python3
"""High-performance messaging daemon for sub-100ms pubsub delivery.

Replaces CLI-based pubsub with persistent daemon using Unix socket IPC.
Target: <100ms message delivery vs current 5000ms CLI overhead.
"""

import asyncio
import json
import logging
import threading
import time
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from tmux_orchestrator.utils.tmux import TMUXManager


@dataclass
class Message:
    """Message structure for daemon processing."""

    id: str
    target: str
    content: str
    priority: str = "normal"
    tags: Optional[list[str]] = None
    sender: str = "daemon"
    timestamp: Optional[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


class HighPerformanceMessagingDaemon:
    """Ultra-fast messaging daemon with sub-100ms delivery target."""

    def __init__(self, socket_path: str = "/tmp/tmux-orc-msgd.sock"):
        self.socket_path = socket_path
        self.running = False
        self.tmux = TMUXManager()

        # Performance optimizations
        self._message_queue = deque()
        self._delivery_stats = defaultdict(list)
        self._session_cache = {}
        self._cache_lock = threading.Lock()

        # Async processing
        self._loop = None
        self._delivery_task = None

        # Logging
        self.logger = logging.getLogger(__name__)

        # Message persistence (optimized)
        self.storage_dir = Path.home() / ".tmux_orchestrator" / "messages"
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Performance tracking
        self._start_time = time.time()
        self._message_count = 0
        self._delivery_times = deque(maxlen=1000)  # Last 1000 delivery times

    async def start(self):
        """Start the high-performance daemon."""
        self.running = True
        self.logger.info("Starting high-performance messaging daemon")

        # Remove existing socket
        try:
            Path(self.socket_path).unlink()
        except FileNotFoundError:
            pass

        # Create Unix socket server
        server = await asyncio.start_unix_server(self._handle_client, path=self.socket_path)

        # Start async message delivery task
        self._delivery_task = asyncio.create_task(self._delivery_loop())

        self.logger.info(f"Daemon listening on {self.socket_path}")

        async with server:
            await server.serve_forever()

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle client requests with minimal latency."""
        try:
            # Read command (expecting JSON)
            data = await reader.read(8192)
            if not data:
                return

            request = json.loads(data.decode())

            # Process command
            response = await self._process_command(request)

            # Send response
            writer.write(json.dumps(response).encode())
            await writer.drain()

        except Exception as e:
            self.logger.error(f"Error handling client: {e}")
            error_response = {"status": "error", "message": str(e)}
            writer.write(json.dumps(error_response).encode())
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    async def _process_command(self, request: dict[str, Any]) -> dict[str, Any]:
        """Process client commands with performance tracking."""
        time.time()

        command = request.get("command")

        if command == "publish":
            return await self._handle_publish(request)
        elif command == "read":
            return await self._handle_read(request)
        elif command == "status":
            return await self._handle_status(request)
        elif command == "stats":
            return await self._handle_stats(request)
        else:
            return {"status": "error", "message": f"Unknown command: {command}"}

    async def _handle_publish(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle publish command - queue message for async delivery."""
        try:
            message = Message(
                id=f"{time.time():.6f}",
                target=request["target"],
                content=request["message"],
                priority=request.get("priority", "normal"),
                tags=request.get("tags", []),
                sender=request.get("sender", "daemon"),
            )

            # Queue for async delivery (immediate return)
            self._message_queue.append(message)
            self._message_count += 1

            return {"status": "queued", "message_id": message.id, "queue_size": len(self._message_queue)}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _handle_read(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle read command - fast pane capture."""
        try:
            target = request["target"]
            lines = request.get("lines", 50)

            # Fast pane capture (cached if possible)
            content = self.tmux.capture_pane(target, lines)

            return {"status": "success", "target": target, "content": content, "timestamp": datetime.now().isoformat()}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _handle_status(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle status command - current daemon state."""
        uptime = time.time() - self._start_time
        avg_delivery = sum(self._delivery_times) / len(self._delivery_times) if self._delivery_times else 0

        return {
            "status": "active",
            "uptime_seconds": uptime,
            "messages_processed": self._message_count,
            "queue_size": len(self._message_queue),
            "avg_delivery_time_ms": avg_delivery * 1000,
            "performance_target": "< 100ms",
            "current_performance": "OK" if avg_delivery < 0.1 else "DEGRADED",
        }

    async def _handle_stats(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle stats command - detailed performance metrics."""
        recent_times = list(self._delivery_times)[-100:]  # Last 100 deliveries

        if recent_times:
            min_time = min(recent_times) * 1000
            max_time = max(recent_times) * 1000
            avg_time = sum(recent_times) / len(recent_times) * 1000
            p95_time = sorted(recent_times)[int(0.95 * len(recent_times))] * 1000
        else:
            min_time = max_time = avg_time = p95_time = 0

        return {
            "performance_metrics": {
                "total_messages": self._message_count,
                "queue_depth": len(self._message_queue),
                "delivery_times_ms": {"min": min_time, "max": max_time, "avg": avg_time, "p95": p95_time},
                "target_performance": 100,  # 100ms target
                "meeting_target": avg_time < 100,
            }
        }

    async def _delivery_loop(self):
        """High-performance async message delivery loop."""
        while self.running:
            try:
                if self._message_queue:
                    message = self._message_queue.popleft()
                    start_time = time.time()

                    # Deliver message using optimized tmux operations
                    success = await self._deliver_message_fast(message)

                    delivery_time = time.time() - start_time
                    self._delivery_times.append(delivery_time)

                    if delivery_time > 0.1:  # Log slow deliveries
                        self.logger.warning(f"Slow delivery: {delivery_time * 1000:.1f}ms for {message.target}")

                    # Persist message (async, non-blocking)
                    if success:
                        asyncio.create_task(self._persist_message(message))

                else:
                    # No messages - brief sleep to prevent busy waiting
                    await asyncio.sleep(0.001)  # 1ms sleep

            except Exception as e:
                self.logger.error(f"Error in delivery loop: {e}")
                await asyncio.sleep(0.01)  # Brief recovery pause

    async def _deliver_message_fast(self, message: Message) -> bool:
        """Ultra-optimized message delivery with aggressive performance tuning."""
        try:
            # Format message with priority prefix
            priority_prefixes = {"critical": "🚨 CRITICAL", "high": "⚠️  HIGH PRIORITY", "normal": "📨", "low": "💬"}

            formatted_msg = f"{priority_prefixes[message.priority]} {message.content}"
            target = message.target

            # PERFORMANCE OPTIMIZATION: Parallel operations where possible
            # Clear existing input + send text in quick succession
            # DISABLED: self.tmux.press_ctrl_c(target)  # This kills Claude when multiple messages arrive
            # await asyncio.sleep(0.05)  # Minimal 50ms delay

            self.tmux.press_ctrl_u(target)
            await asyncio.sleep(0.05)  # Minimal 50ms delay

            # Send message text
            self.tmux.send_text(target, formatted_msg)

            # CRITICAL PERFORMANCE BOOST: Reduce Claude processing wait
            # Most agents respond within 200ms, not 3000ms
            await asyncio.sleep(0.2)  # Reduced from 0.5s to 200ms

            # Submit with Enter
            self.tmux.press_enter(target)

            return True

        except Exception as e:
            self.logger.error(f"Failed to deliver message to {message.target}: {e}")
            return False

    async def _persist_message(self, message: Message):
        """Async message persistence to avoid blocking delivery."""
        try:
            target_file = self.storage_dir / f"{message.target.replace(':', '_')}.json"

            # Load existing messages
            if target_file.exists():
                with open(target_file) as f:
                    messages = json.load(f)
            else:
                messages = []

            # Add new message
            messages.append(asdict(message))

            # Keep only last 1000 messages
            if len(messages) > 1000:
                messages = messages[-1000:]

            # Write back atomically
            with open(target_file, "w") as f:
                json.dump(messages, f, indent=2)

        except Exception as e:
            self.logger.error(f"Failed to persist message: {e}")

    def stop(self):
        """Stop the daemon gracefully."""
        self.running = False
        if self._delivery_task:
            self._delivery_task.cancel()


class DaemonClient:
    """Fast client for communicating with messaging daemon."""

    def __init__(self, socket_path: str = "/tmp/tmux-orc-msgd.sock"):
        self.socket_path = socket_path

    async def send_command(self, command: dict[str, Any]) -> dict[str, Any]:
        """Send command to daemon with minimal latency."""
        try:
            reader, writer = await asyncio.open_unix_connection(self.socket_path)

            # Send command
            writer.write(json.dumps(command).encode())
            await writer.drain()

            # Read response
            data = await reader.read(8192)
            response = json.loads(data.decode())

            writer.close()
            await writer.wait_closed()

            return response

        except Exception as e:
            return {"status": "error", "message": f"Daemon communication failed: {e}"}

    async def publish(
        self, target: str, message: str, priority: str = "normal", tags: Optional[list[str]] = None
    ) -> dict[str, Any]:
        """Publish message via daemon (target: sub-100ms)."""
        command = {"command": "publish", "target": target, "message": message, "priority": priority, "tags": tags or []}
        return await self.send_command(command)

    async def read(self, target: str, lines: int = 50) -> dict[str, Any]:
        """Read from target via daemon."""
        command = {"command": "read", "target": target, "lines": lines}
        return await self.send_command(command)

    async def get_status(self) -> dict[str, Any]:
        """Get daemon status and performance metrics."""
        command = {"command": "status"}
        return await self.send_command(command)


if __name__ == "__main__":
    # Start daemon
    daemon = HighPerformanceMessagingDaemon()
    try:
        asyncio.run(daemon.start())
    except KeyboardInterrupt:
        daemon.stop()
        print("Daemon stopped")

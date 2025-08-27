"""Simple chunking implementation that avoids pressing Enter between chunks."""

import subprocess
import time


class SimpleTmuxChunker:
    """Simple chunking that writes all chunks then presses Enter once."""

    def __init__(self, tmux_cmd: str = "tmux"):
        self.tmux_cmd = tmux_cmd
        self.chunk_size = 180  # Conservative size to avoid tmux buffer issues

    def send_long_message(
        self,
        target: str,
        message: str,
        chunk_pause: float = 0.5,  # Time between chunks (used if no monitor pause available)
        daemon_pause_seconds: int = 3,  # How long to pause daemon before each chunk
    ) -> bool:
        """Send a long message by chunking without pressing Enter between chunks.

        Args:
            target: Tmux target (session:window format)
            message: The full message to send
            chunk_pause: Seconds to wait between chunks (fallback if no monitor pause)
            daemon_pause_seconds: Seconds to pause daemon before writing each chunk

        Returns:
            True if successful
        """
        # Clear the current line first
        if not self._send_keys(target, "C-u"):
            return False
        time.sleep(0.1)

        # If message is short, just send it directly
        if len(message) <= self.chunk_size:
            if not self._send_keys(target, message, literal=True):
                return False
            time.sleep(0.1)
            return self._send_keys(target, "Enter")

        # Chunk the message
        chunks = self._simple_chunk(message)

        # Send all chunks WITHOUT pressing Enter
        for i, chunk in enumerate(chunks):
            # CRITICAL: Pause daemon BEFORE writing each chunk to prevent auto-submit
            # This gives us a safe window to write without interference
            if self._pause_daemon(daemon_pause_seconds):
                # Daemon is paused, we have a safe window to write
                pass
            else:
                # No pause command available, use sleep as fallback
                if i > 0:  # Don't pause before first chunk
                    time.sleep(chunk_pause)

            # Format chunk (add space between chunks for readability)
            if i == 0:
                chunk_text = chunk
            else:
                chunk_text = f" {chunk}"  # Add space to separate from previous chunk

            # Send this chunk while daemon is paused/sleeping
            if not self._send_keys(target, chunk_text, literal=True):
                return False

        # Now press Enter ONCE after all chunks are written
        time.sleep(0.1)
        return self._send_keys(target, "Enter")

    def _simple_chunk(self, text: str) -> list[str]:
        """Simple chunking at word boundaries.

        Args:
            text: Text to chunk

        Returns:
            List of chunks
        """
        if len(text) <= self.chunk_size:
            return [text]

        chunks = []
        words = text.split()
        current_chunk = ""

        for word in words:
            # If word itself is too long, we have to split it (rare case)
            if len(word) > self.chunk_size:
                # Save current chunk if any
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                # Force split the long word
                for i in range(0, len(word), self.chunk_size):
                    chunks.append(word[i : i + self.chunk_size])
            else:
                # Try to add word to current chunk
                test_chunk = f"{current_chunk} {word}".strip() if current_chunk else word
                if len(test_chunk) <= self.chunk_size:
                    current_chunk = test_chunk
                else:
                    # Current chunk is full
                    chunks.append(current_chunk.strip())
                    current_chunk = word

        # Add any remaining content
        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def _send_keys(self, target: str, keys: str, literal: bool = False) -> bool:
        """Send keys to tmux target.

        Args:
            target: Tmux target
            keys: Keys to send
            literal: If True, send as literal text (no special key interpretation)

        Returns:
            True if successful
        """
        try:
            cmd = [self.tmux_cmd, "send-keys", "-t", target]
            if literal:
                cmd.append("-l")
            cmd.append(keys)

            result = subprocess.run(cmd, capture_output=True, timeout=2)
            return result.returncode == 0
        except Exception:
            return False

    def _pause_daemon(self, seconds: int) -> bool:
        """Pause the monitoring daemon for a specified number of seconds.

        Args:
            seconds: Number of seconds to pause the daemon

        Returns:
            True if pause command succeeded, False if not available
        """
        try:
            # Try to pause the monitor daemon
            result = subprocess.run(
                ["tmux-orc", "monitor", "pause", str(seconds)], capture_output=True, timeout=1, text=True
            )

            # If command succeeded, daemon is paused
            if result.returncode == 0:
                return True

            # If command doesn't exist yet, return False to use fallback
            # This allows graceful degradation until pause command is implemented
            return False
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            # Command not available or failed
            return False


# Example usage:
# chunker = SimpleTmuxChunker()
# chunker.send_long_message(
#     "my-session:1",
#     "This is a very long message that needs to be chunked " * 50,
#     chunk_pause=0.5  # Half second between chunks to avoid daemon auto-submit
# )

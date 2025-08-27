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

        # Check for code blocks first
        if "`" in message:
            return self._split_with_code_preservation(message)

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
                        # Check UTF-8 safety before combining
                        test_chunk = current_chunk + " " + sub_chunk
                        if self._is_utf8_safe_split(test_chunk):
                            current_chunk = test_chunk.strip()
                        else:
                            if current_chunk:
                                chunks.append(current_chunk)
                            current_chunk = sub_chunk
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = sub_chunk
            else:
                # Try to fit sentence in current chunk
                if current_chunk and len(current_chunk) + len(sentence) + 1 <= self.chunk_size:
                    test_chunk = current_chunk + " " + sentence
                    if self._is_utf8_safe_split(test_chunk):
                        current_chunk = test_chunk.strip()
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = sentence
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
        # Don't split on ellipses or special punctuation patterns
        # First, temporarily replace ellipses and other patterns to protect them
        protected_text = text.replace("...", "___ELLIPSIS___")
        protected_text = protected_text.replace("--", "___EMDASH___")

        # Split on sentence boundaries, but keep the punctuation
        # Avoid splitting on Dr., Mr., etc.
        sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", protected_text)

        # Restore protected patterns
        sentences = [s.replace("___ELLIPSIS___", "...").replace("___EMDASH___", "--") for s in sentences]

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
        """Split text by words as a last resort, preserving emoji sequences.

        Args:
            text: Text to split

        Returns:
            List of text chunks split at word boundaries
        """
        chunks = []
        current_chunk = ""

        # Use regex to preserve emoji sequences when splitting
        # This pattern matches words while keeping emoji sequences together
        emoji_pattern = (
            r"[\U0001F000-\U0001F9FF\U00002600-\U000027BF\U0001F300-\U0001F64F\U0001F680-\U0001F6FF]+|\S+|\s+"
        )
        words = re.findall(emoji_pattern, text)

        i = 0
        while i < len(words):
            word = words[i]

            # Check if this is part of an emoji sequence with ZWJ
            if i < len(words) - 1 and "\u200d" in words[i + 1]:
                # Combine emoji sequence
                emoji_seq = word
                j = i + 1
                while j < len(words) and ("\u200d" in words[j] or re.match(r"[\U0001F000-\U0001F9FF]", words[j])):
                    emoji_seq += words[j]
                    j += 1
                word = emoji_seq
                i = j - 1

            # Handle words longer than chunk size
            if len(word) > self.chunk_size:
                # Save current chunk if any
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""

                # For emojis or special chars, keep together if possible
                if re.match(r"[\U0001F000-\U0001F9FF]", word):
                    chunks.append(word)
                else:
                    # Force-split the long word (rare case)
                    for k in range(0, len(word), self.chunk_size):
                        chunks.append(word[k : k + self.chunk_size])
            else:
                # Try to add word to current chunk
                test_chunk = current_chunk + word if current_chunk else word
                if len(test_chunk) <= self.chunk_size:
                    current_chunk = test_chunk
                else:
                    # Current chunk is full
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = word

            i += 1

        # Add any remaining content
        if current_chunk:
            chunks.append(current_chunk.strip())

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

    def _split_with_code_preservation(self, message: str) -> list[str]:
        """Split message while preserving code blocks intact.

        Args:
            message: Message containing code blocks

        Returns:
            List of chunks with code blocks preserved
        """
        chunks = []
        current_chunk = ""

        # Find all code blocks (both inline ` and block ```)
        # Improved pattern to properly capture code blocks
        code_pattern = r"(```[^`]*```|`[^`]+`)"
        parts = re.split(code_pattern, message)

        for part in parts:
            if not part:
                continue

            # Check if this is a code block
            is_code = part.startswith("`") and part.endswith("`")

            if is_code:
                # Always preserve code blocks intact if possible
                code_content = part

                if len(code_content) <= self.chunk_size:
                    # Code block fits in a chunk
                    if current_chunk:
                        # Check if it fits with current chunk
                        combined = current_chunk + " " + code_content
                        if len(combined) <= self.chunk_size:
                            current_chunk = combined
                        else:
                            # Save current and start new with code
                            chunks.append(current_chunk)
                            current_chunk = code_content
                    else:
                        current_chunk = code_content
                else:
                    # Code block is too large
                    if current_chunk:
                        chunks.append(current_chunk)
                        current_chunk = ""

                    # For inline code, try to keep it together
                    if part.startswith("`") and not part.startswith("```"):
                        # Single backtick - inline code, should stay together
                        chunks.append(code_content)
                    else:
                        # Multi-line code block - split carefully
                        # Try to preserve the opening and closing ```
                        if part.startswith("```"):
                            lines = part.split("\n")
                            if len(lines) > 2:
                                # Keep opening ``` with first line of code
                                temp = lines[0] + "\n" + lines[1] if len(lines) > 1 else lines[0]
                                for i in range(2, len(lines) - 1):
                                    if len(temp + "\n" + lines[i]) <= self.chunk_size:
                                        temp += "\n" + lines[i]
                                    else:
                                        chunks.append(temp)
                                        temp = lines[i]
                                # Add closing ``` with last line
                                if temp:
                                    temp += "\n" + lines[-1] if lines[-1] else ""
                                    chunks.append(temp)
                            else:
                                chunks.append(part)
                        else:
                            chunks.append(code_content)
            else:
                # Regular text - split normally but preserve structure
                if len(part) > self.chunk_size:
                    text_chunks = self._split_by_words(part)
                    for text_chunk in text_chunks:
                        if current_chunk and len(current_chunk) + len(text_chunk) + 1 <= self.chunk_size:
                            current_chunk = (current_chunk + " " + text_chunk).strip()
                        else:
                            if current_chunk:
                                chunks.append(current_chunk)
                            current_chunk = text_chunk
                else:
                    # Short text, try to combine
                    if current_chunk and len(current_chunk) + len(part) + 1 <= self.chunk_size:
                        current_chunk = (current_chunk + " " + part).strip()
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = part

        if current_chunk:
            chunks.append(current_chunk)

        return chunks if chunks else [message]

    def _is_utf8_safe_split(self, text: str) -> bool:
        """Check if text can be safely split without breaking UTF-8 sequences.

        Args:
            text: Text to check

        Returns:
            True if split is safe
        """
        if not text:
            return True

        try:
            # Check if text encodes/decodes properly
            text.encode("utf-8").decode("utf-8")

            # Check for emoji and special character boundaries
            # Don't split in the middle of emoji sequences
            # Note: emoji pattern checking is done in _find_split_point method

            # Check if we're splitting in a zero-width joiner sequence
            if "\u200d" in text[-5:]:  # ZWJ near end might indicate incomplete emoji
                return False

            # Check for combining characters
            if any(ord(c) in range(0x0300, 0x036F) for c in text[-3:]):
                return False

            return True
        except (UnicodeEncodeError, UnicodeDecodeError):
            return False

    def _find_split_point(self, text: str, max_length: int) -> int:
        """Find a safe split point that preserves character boundaries.

        Args:
            text: Text to split
            max_length: Maximum length for the chunk

        Returns:
            Safe split position
        """
        if len(text) <= max_length:
            return len(text)

        # Start from max_length and work backwards to find safe split
        pos = min(max_length, len(text))

        # Comprehensive emoji pattern using regex for better detection
        emoji_pattern = re.compile(
            r"[\U0001F600-\U0001F64F]|"  # Emoticons
            r"[\U0001F300-\U0001F5FF]|"  # Misc Symbols and Pictographs
            r"[\U0001F680-\U0001F6FF]|"  # Transport and Map Symbols
            r"[\U0001F1E0-\U0001F1FF]|"  # Regional Indicators (flags)
            r"[\U00002600-\U000027BF]|"  # Misc symbols
            r"[\U0001F900-\U0001F9FF]|"  # Supplemental Symbols
            r"[\U00002300-\U000023FF]|"  # Misc Technical
            r"[\U0001FA70-\U0001FAFF]"  # Extended Pictographs
        )

        while pos > 0:
            if pos < len(text):
                # 1) CHECK FOR CODE BLOCKS - don't split inside backticks
                before_text = text[:pos]
                after_text = text[pos:]

                # Count backticks to determine if we're inside a code block
                backticks_before = before_text.count("`")
                # If odd number of backticks before, we're likely inside a code block
                if backticks_before % 2 == 1:
                    # Check if we're near a closing backtick
                    closing_tick = after_text.find("`")
                    if 0 <= closing_tick < 20:
                        # We're close to the end of a code block, move back
                        pos -= 1
                        continue

                # 2) CHECK FOR SPECIAL PUNCTUATION - don't split ... or --
                # Check for ellipsis
                if pos >= 2 and text[pos - 2 : pos + 1] == "...":
                    pos -= 3  # Move before the ellipsis
                    continue
                if pos >= 1 and pos < len(text) - 1 and text[pos - 1 : pos + 2] == "...":
                    pos -= 2
                    continue

                # Check for em dash
                if pos >= 1 and text[pos - 1 : pos + 1] == "--":
                    pos -= 2  # Move before the em dash
                    continue
                if pos < len(text) - 1 and text[pos : pos + 2] == "--":
                    pos -= 1
                    continue

                # 3) CHECK FOR EMOJI BOUNDARIES using regex
                # Look for emoji in surrounding context (wider range for complex sequences)
                check_start = max(0, pos - 5)
                check_end = min(len(text), pos + 5)
                surrounding = text[check_start:check_end]

                # Find all emoji matches in the surrounding area
                emoji_matches = list(emoji_pattern.finditer(surrounding))
                skip_pos = False
                for match in emoji_matches:
                    # Adjust match position to text coordinates
                    match_start = check_start + match.start()
                    match_end = check_start + match.end()

                    # If split point is within an emoji, move before it
                    if match_start <= pos < match_end:
                        pos = match_start - 1
                        skip_pos = True
                        break

                if skip_pos:
                    continue

                # Check for zero-width joiners (complex emoji sequences like families)
                if text[pos : pos + 1] == "\u200d" or (pos > 0 and text[pos - 1 : pos] == "\u200d"):
                    # Find the start of the entire emoji sequence
                    sequence_start = pos
                    while sequence_start > 0:
                        prev_char = text[sequence_start - 1 : sequence_start]
                        # Check if previous character is ZWJ or emoji
                        if prev_char == "\u200d" or emoji_pattern.match(prev_char):
                            sequence_start -= 1
                        else:
                            break
                    pos = max(0, sequence_start - 1)
                    continue

                # Check for emoji variant selectors (FE0F/FE0E)
                if pos < len(text) and ord(text[pos]) in [0xFE0F, 0xFE0E]:
                    # These follow emojis to specify presentation
                    pos = max(0, pos - 2)
                    continue

                # Check for skin tone modifiers
                if pos < len(text) and ord(text[pos]) in range(0x1F3FB, 0x1F3FF + 1):
                    # These follow person/hand emojis
                    pos = max(0, pos - 2)
                    continue

                # Check for combining characters (diacritics)
                if pos < len(text) and ord(text[pos]) in range(0x0300, 0x036F):
                    pos -= 1
                    continue

                # Check for surrogate pairs (UTF-16 compatibility)
                if pos > 0 and 0xD800 <= ord(text[pos - 1]) <= 0xDBFF:
                    pos -= 1
                    continue

                # PREFERRED SPLIT POINTS
                # Look for word boundaries (spaces)
                if text[pos] == " ":
                    return pos

                # Check for safe punctuation boundaries (but avoid special sequences)
                if text[pos] in ",.;:!?\n":
                    # Make sure it's not part of ellipsis or em dash
                    is_special = False
                    if text[pos] == ".":
                        # Check if part of ellipsis
                        if (pos > 0 and text[pos - 1] == ".") or (pos < len(text) - 1 and text[pos + 1] == "."):
                            is_special = True
                    elif text[pos] == "-":
                        # Check if part of em dash
                        if (pos > 0 and text[pos - 1] == "-") or (pos < len(text) - 1 and text[pos + 1] == "-"):
                            is_special = True

                    if not is_special:
                        return pos + 1

            # Try previous position
            pos -= 1

            # Safety check - ensure we make progress
            if pos < max_length - 30:
                # Last resort: find nearest space or safe punctuation
                for i in range(max_length - 10, max(0, max_length - 30), -1):
                    if i < len(text) and text[i] in " ,.;:!?\n":
                        # Final check for special sequences
                        if not (
                            (text[i] == "." and i > 0 and text[i - 1 : min(i + 2, len(text))].count(".") > 1)
                            or (text[i] == "-" and i > 0 and text[i - 1 : min(i + 2, len(text))].count("-") > 1)
                        ):
                            return i
                # Force split at a reasonable position
                return min(max_length - 10, len(text))

        # Fallback to simple truncation if no good split point found
        return min(max_length, len(text))

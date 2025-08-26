#!/usr/bin/env python3
"""Tests for message chunking functionality in TMUXManager."""

from unittest.mock import patch

import pytest

from tmux_orchestrator.utils.tmux import TMUXManager


class TestMessageChunking:
    """Test suite for message chunking functionality."""

    def test_short_message_no_chunking(self):
        """Test that short messages (<200 chars) are sent without chunking."""
        tmux = TMUXManager()
        short_message = "This is a short message"

        with patch.object(tmux, "send_keys") as mock_send:
            mock_send.return_value = True

            result = tmux.send_text("session:0", short_message)

            assert result is True
            mock_send.assert_called_once_with("session:0", short_message, literal=True)

    def test_chunk_message_at_sentence_boundaries(self):
        """Test that messages are chunked at sentence boundaries."""
        tmux = TMUXManager()

        # Message with clear sentence boundaries
        message = "This is the first sentence. This is the second sentence. This is the third sentence."
        chunks = tmux._chunk_message(message, max_chunk_size=30)

        # Should split at sentence boundaries
        assert len(chunks) == 3
        assert chunks[0] == "This is the first sentence."
        assert chunks[1] == "This is the second sentence."
        assert chunks[2] == "This is the third sentence."

    def test_chunk_message_at_word_boundaries(self):
        """Test that long sentences are chunked at word boundaries."""
        tmux = TMUXManager()

        # Single long sentence without punctuation
        message = "This is a very long sentence that needs to be split at word boundaries because it exceeds the maximum chunk size"
        chunks = tmux._chunk_message(message, max_chunk_size=50)

        # Should split at word boundaries
        assert len(chunks) > 1
        # Verify no chunk exceeds max size
        for chunk in chunks:
            assert len(chunk) <= 50
        # Verify all words are preserved
        assert " ".join(chunks) == message

    def test_chunk_message_with_punctuation(self):
        """Test chunking with various punctuation marks."""
        tmux = TMUXManager()

        message = "First item, second item; third item: fourth item. Fifth sentence! Sixth question?"
        chunks = tmux._chunk_message(message, max_chunk_size=35)

        # Should handle various punctuation properly
        assert len(chunks) >= 2
        for chunk in chunks:
            assert len(chunk) <= 35

    def test_very_long_word_handling(self):
        """Test that very long words are force-split if necessary."""
        tmux = TMUXManager()

        # Create a word longer than max chunk size
        long_word = "a" * 200
        message = f"Here is a {long_word} word"
        chunks = tmux._chunk_message(message, max_chunk_size=50)

        # Long word should be force-split
        assert len(chunks) >= 5  # "Here is a" + at least 4 chunks for the long word
        for chunk in chunks:
            assert len(chunk) <= 50

    def test_send_text_with_chunking(self):
        """Test send_text with automatic chunking for long messages."""
        tmux = TMUXManager()

        # Create a message that will be chunked
        long_message = "This is the first sentence. " * 10  # ~280 characters

        with patch.object(tmux, "send_keys") as mock_send:
            mock_send.return_value = True

            with patch("time.sleep") as mock_sleep:
                result = tmux.send_text("session:0", long_message)

                assert result is True
                # Should have multiple calls due to chunking
                assert mock_send.call_count > 1

                # Verify pagination format
                calls = mock_send.call_args_list
                for i, call_args in enumerate(calls, 1):
                    sent_text = call_args[0][1]
                    assert sent_text.startswith(f"[{i}/{len(calls)}]")

                # Verify delays between chunks
                assert mock_sleep.call_count == len(calls) - 1

    def test_send_text_chunking_disabled(self):
        """Test that chunking can be disabled."""
        tmux = TMUXManager()

        long_message = "This is a long message. " * 20  # Very long message

        with patch.object(tmux, "send_keys") as mock_send:
            mock_send.return_value = True

            result = tmux.send_text("session:0", long_message, enable_chunking=False)

            assert result is True
            # Should only have one call when chunking is disabled
            mock_send.assert_called_once_with("session:0", long_message, literal=True)

    def test_send_text_custom_chunk_delay(self):
        """Test custom delay between chunks."""
        tmux = TMUXManager()

        long_message = "This is the first sentence. " * 10
        custom_delay = 0.5

        with patch.object(tmux, "send_keys") as mock_send:
            mock_send.return_value = True

            with patch("time.sleep") as mock_sleep:
                result = tmux.send_text("session:0", long_message, chunk_delay=custom_delay)

                assert result is True
                # Verify custom delay is used
                for call_args in mock_sleep.call_args_list:
                    assert call_args[0][0] == custom_delay

    def test_send_text_chunk_failure_handling(self):
        """Test handling of chunk send failures."""
        tmux = TMUXManager()

        long_message = "This is the first sentence. " * 10

        with patch.object(tmux, "send_keys") as mock_send:
            # Fail on second chunk
            mock_send.side_effect = [True, False, True]

            with patch("time.sleep"):
                result = tmux.send_text("session:0", long_message)

                assert result is False
                # Should stop after failure
                assert mock_send.call_count == 2

    def test_backward_compatibility(self):
        """Test that the API remains backward compatible."""
        tmux = TMUXManager()

        # Old usage pattern should still work
        with patch.object(tmux, "send_keys") as mock_send:
            mock_send.return_value = True

            # Simple call without new parameters
            result = tmux.send_text("session:0", "Test message")

            assert result is True
            mock_send.assert_called_once()

    def test_send_message_with_long_content(self):
        """Test send_message method with long content uses chunking."""
        tmux = TMUXManager()

        long_message = "This is a very long briefing. " * 20

        with patch.object(tmux, "press_ctrl_u") as mock_ctrl_u:
            mock_ctrl_u.return_value = True

            with patch.object(tmux, "press_enter") as mock_enter:
                mock_enter.return_value = True

                with patch.object(tmux, "send_keys") as mock_send:
                    mock_send.return_value = True

                    with patch("time.sleep"):
                        result = tmux.send_message("session:0", long_message)

                        assert result is True
                        # Should chunk the long message
                        assert mock_send.call_count > 1

    def test_chunk_message_preserves_content(self):
        """Test that chunking preserves all content without loss."""
        tmux = TMUXManager()

        test_messages = [
            "Simple message with no special characters",
            "Message with special chars: @#$%^&*()",
            "Multi-line\nmessage\nwith\nnewlines",
            "Message with    multiple     spaces",
            "Message with 'quotes' and \"double quotes\"",
            "Unicode message with émojis 🚀 and símbolos ñ",
        ]

        for original_message in test_messages:
            chunks = tmux._chunk_message(original_message, max_chunk_size=20)

            # Reconstruct message from chunks
            reconstructed = " ".join(chunks)

            # For multi-line messages, newlines might be replaced with spaces
            if "\n" in original_message:
                assert reconstructed.replace(" ", "") == original_message.replace("\n", "").replace(" ", "")
            elif "  " in original_message:  # Multiple spaces get normalized
                # Multiple spaces are normalized to single spaces during chunking
                assert " ".join(reconstructed.split()) == " ".join(original_message.split())
            else:
                assert reconstructed == original_message

    def test_empty_message_handling(self):
        """Test handling of empty messages."""
        tmux = TMUXManager()

        chunks = tmux._chunk_message("", max_chunk_size=50)
        assert chunks == [""]

        with patch.object(tmux, "send_keys") as mock_send:
            mock_send.return_value = True

            result = tmux.send_text("session:0", "")
            assert result is True
            mock_send.assert_called_once_with("session:0", "", literal=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

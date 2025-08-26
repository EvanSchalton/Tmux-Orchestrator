#!/usr/bin/env python3
"""Test fixtures for messaging functionality.

Provides standardized test data, mock objects, and utilities
for messaging system testing across all test levels.
"""

import time
from typing import Generator, List
from unittest.mock import Mock

import pytest


class MessageSizeFixtures:
    """Standard message size fixtures for comprehensive testing."""

    @staticmethod
    def tiny_message() -> str:
        """1-byte message."""
        return "a"

    @staticmethod
    def small_message() -> str:
        """~50 characters."""
        return "This is a small test message for basic functionality."

    @staticmethod
    def medium_message() -> str:
        """~200 characters (chunking threshold)."""
        return (
            "This is a medium-sized message designed to test the chunking "
            "threshold behavior. It should be right around the 200 character "
            "limit where chunking begins to activate."
        )

    @staticmethod
    def large_message() -> str:
        """~1KB message (typical briefing size)."""
        base = (
            "This is a large message that represents a typical agent briefing. "
            "It contains detailed instructions, context, and requirements that "
            "agents need to understand before beginning their tasks. "
        )
        return base * 15  # ~1050 characters

    @staticmethod
    def xl_message() -> str:
        """~5KB message (stress testing)."""
        base = (
            "This is an extra-large message for stress testing the chunking "
            "system. It simulates comprehensive documentation, detailed "
            "briefings, or extensive context that might be sent to agents. "
            "The message needs to be large enough to test performance and "
            "reliability under more demanding conditions. "
        )
        return base * 25  # ~5250 characters

    @staticmethod
    def xxl_message() -> str:
        """~10KB message (maximum practical size)."""
        base = (
            "This is a double-extra-large message representing the upper "
            "bounds of practical message sizes in the system. It might "
            "contain complete project specifications, detailed API "
            "documentation, comprehensive test plans, or other extensive "
            "content that agents occasionally need to process. This tests "
            "the system's ability to handle large data transfers reliably. "
        )
        return base * 35  # ~10,150 characters


class UTF8TestFixtures:
    """UTF-8 and Unicode test fixtures."""

    @staticmethod
    def basic_unicode() -> str:
        """Basic non-ASCII characters."""
        return "Testing unicode: café, niño, résumé"

    @staticmethod
    def emoji_simple() -> str:
        """Simple emoji characters."""
        return "Simple emoji test: 🚀 🔥 ⭐ 🎯"

    @staticmethod
    def emoji_complex() -> str:
        """Complex emoji with modifiers and zero-width joiners."""
        return "Complex emoji: 👨‍👩‍👧‍👦 🧑‍💻 👋🏽 🏳️‍🌈"

    @staticmethod
    def mixed_languages() -> str:
        """Multiple languages and scripts."""
        return "English, Español, Français, 中文, العربية, русский, 日本語"

    @staticmethod
    def combining_characters() -> str:
        """Characters with combining diacritical marks."""
        return "Combining: e\u0301 (é), a\u0300 (à), n\u0303 (ñ)"

    @staticmethod
    def rtl_text() -> str:
        """Right-to-left text."""
        return "RTL test: Hello العالم שלום мир world"


class EdgeCaseFixtures:
    """Edge case and boundary condition fixtures."""

    @staticmethod
    def whitespace_only() -> str:
        """Whitespace-only message."""
        return "   \t  \n  "

    @staticmethod
    def newlines_only() -> str:
        """Multiple newlines."""
        return "\n\n\n\n"

    @staticmethod
    def mixed_whitespace() -> str:
        """Mixed whitespace types."""
        return "Word1\tword2\nword3 word4\r\nword5"

    @staticmethod
    def repeated_punctuation() -> str:
        """Heavy punctuation usage."""
        return "Test!!! Question??? Period... Comma,,, Semicolon;;;"

    @staticmethod
    def long_words() -> str:
        """Very long words that might need force-splitting."""
        return (
            "Short words and antidisestablishmentarianism "
            "pneumonoultramicroscopicsilicovolcanoconiosisfloccinaucinihilipilification"
        )

    @staticmethod
    def mixed_quotes() -> str:
        """Various quote types."""
        return "Mixed \"quotes\" and 'apostrophes' with `backticks`"

    @staticmethod
    def url_and_email() -> str:
        """URLs and email addresses."""
        return "Contact: user@example.com or visit https://example.com/path?query=value#anchor"


class MaliciousInputFixtures:
    """Potentially malicious or problematic input fixtures."""

    @staticmethod
    def control_characters() -> str:
        """Various control characters."""
        return "Text with\x00null\x1b[31mANSI\x7fdelete"

    @staticmethod
    def format_strings() -> str:
        """Potential format string attacks."""
        return "Format test: %s %d %x {0} {1} {{injection}}"

    @staticmethod
    def sql_injection_like() -> str:
        """SQL injection-like patterns."""
        return "'; DROP TABLE messages; --"

    @staticmethod
    def script_tags() -> str:
        """HTML/XML-like content."""
        return "<script>alert('xss')</script> <xml>test</xml>"

    @staticmethod
    def overlong_utf8() -> str:
        """Potentially problematic UTF-8 sequences."""
        return "Normal text \xc0\xaf overlong encoding"


class PerformanceFixtures:
    """Performance testing fixtures."""

    @staticmethod
    def generate_message_series(sizes: List[int]) -> Generator[str, None, None]:
        """Generate messages of specific sizes for performance testing."""
        base_unit = "Performance test message unit. "
        unit_size = len(base_unit)

        for target_size in sizes:
            repetitions = max(1, target_size // unit_size)
            yield base_unit * repetitions

    @staticmethod
    def timing_context():
        """Context manager for timing operations."""

        class TimingContext:
            def __init__(self):
                self.start_time = None
                self.end_time = None
                self.duration_ms = None

            def __enter__(self):
                self.start_time = time.perf_counter()
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                self.end_time = time.perf_counter()
                self.duration_ms = (self.end_time - self.start_time) * 1000

        return TimingContext()


class MockFixtures:
    """Mock objects and utilities for testing."""

    @staticmethod
    def mock_tmux_manager():
        """Create a mock TMUXManager for testing."""
        mock = Mock()
        mock.send_keys.return_value = True
        mock.send_text.return_value = True
        mock.send_message.return_value = True
        mock._chunk_message.return_value = ["test chunk"]
        return mock

    @staticmethod
    def mock_successful_send():
        """Mock that always succeeds."""
        return Mock(return_value=True)

    @staticmethod
    def mock_failing_send():
        """Mock that always fails."""
        return Mock(return_value=False)

    @staticmethod
    def mock_intermittent_send(success_pattern: List[bool]):
        """Mock with specified success/failure pattern."""
        mock = Mock()
        mock.side_effect = success_pattern
        return mock

    @staticmethod
    def mock_network_delay(delay_seconds: float = 0.1):
        """Mock with simulated network delay."""

        def delayed_send(*args, **kwargs):
            time.sleep(delay_seconds)
            return True

        return Mock(side_effect=delayed_send)


class TestScenarios:
    """Complete test scenarios combining fixtures and expected behaviors."""

    @staticmethod
    def get_size_progression_scenario():
        """Scenario testing message size progression."""
        return {
            "tiny": (MessageSizeFixtures.tiny_message(), 1, False),  # (message, expected_chunks, should_chunk)
            "small": (MessageSizeFixtures.small_message(), 1, False),
            "medium": (MessageSizeFixtures.medium_message(), 2, True),
            "large": (MessageSizeFixtures.large_message(), 6, True),
            "xl": (MessageSizeFixtures.xl_message(), 30, True),
            "xxl": (MessageSizeFixtures.xxl_message(), 58, True),
        }

    @staticmethod
    def get_utf8_safety_scenario():
        """Scenario for UTF-8 safety testing."""
        return [
            UTF8TestFixtures.basic_unicode(),
            UTF8TestFixtures.emoji_simple(),
            UTF8TestFixtures.emoji_complex(),
            UTF8TestFixtures.mixed_languages(),
            UTF8TestFixtures.combining_characters(),
            UTF8TestFixtures.rtl_text(),
        ]

    @staticmethod
    def get_boundary_detection_scenario():
        """Scenario for boundary detection testing."""
        return [
            "Sentence one. Sentence two. Sentence three.",  # Sentence boundaries
            "Word word word word word word word word",  # Word boundaries
            EdgeCaseFixtures.repeated_punctuation(),  # Punctuation handling
            EdgeCaseFixtures.url_and_email(),  # Special format preservation
            EdgeCaseFixtures.mixed_quotes(),  # Quote handling
        ]

    @staticmethod
    def get_error_handling_scenario():
        """Scenario for error handling testing."""
        return [
            (MaliciousInputFixtures.control_characters(), "control_chars"),
            (EdgeCaseFixtures.whitespace_only(), "whitespace"),
            (EdgeCaseFixtures.newlines_only(), "newlines"),
            (EdgeCaseFixtures.long_words(), "long_words"),
        ]


# Pytest fixtures
@pytest.fixture
def message_fixtures():
    """Pytest fixture providing message size fixtures."""
    return MessageSizeFixtures()


@pytest.fixture
def utf8_fixtures():
    """Pytest fixture providing UTF-8 test fixtures."""
    return UTF8TestFixtures()


@pytest.fixture
def edge_case_fixtures():
    """Pytest fixture providing edge case fixtures."""
    return EdgeCaseFixtures()


@pytest.fixture
def mock_fixtures():
    """Pytest fixture providing mock objects."""
    return MockFixtures()


@pytest.fixture
def performance_fixtures():
    """Pytest fixture providing performance testing utilities."""
    return PerformanceFixtures()


@pytest.fixture
def test_scenarios():
    """Pytest fixture providing complete test scenarios."""
    return TestScenarios()


# Parametrized fixture for size testing
@pytest.fixture(params=["tiny", "small", "medium", "large", "xl", "xxl"])
def message_size_param(request, message_fixtures):
    """Parametrized fixture for testing different message sizes."""
    size_methods = {
        "tiny": message_fixtures.tiny_message,
        "small": message_fixtures.small_message,
        "medium": message_fixtures.medium_message,
        "large": message_fixtures.large_message,
        "xl": message_fixtures.xl_message,
        "xxl": message_fixtures.xxl_message,
    }
    return request.param, size_methods[request.param]()


# Parametrized fixture for UTF-8 testing
@pytest.fixture(
    params=["basic_unicode", "emoji_simple", "emoji_complex", "mixed_languages", "combining_characters", "rtl_text"]
)
def utf8_param(request, utf8_fixtures):
    """Parametrized fixture for UTF-8 testing."""
    utf8_methods = {
        "basic_unicode": utf8_fixtures.basic_unicode,
        "emoji_simple": utf8_fixtures.emoji_simple,
        "emoji_complex": utf8_fixtures.emoji_complex,
        "mixed_languages": utf8_fixtures.mixed_languages,
        "combining_characters": utf8_fixtures.combining_characters,
        "rtl_text": utf8_fixtures.rtl_text,
    }
    return request.param, utf8_methods[request.param]()

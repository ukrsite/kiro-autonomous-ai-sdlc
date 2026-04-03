"""Unit tests for the input sanitizer."""

import pytest

from scripts.validation.sanitizer import sanitize_input


class TestShellMetacharacterEscaping:
    """Verify all required shell metacharacters are escaped."""

    @pytest.mark.parametrize(
        "char",
        list('$`\\"!|;&()'),
    )
    def test_individual_metacharacter_escaped(self, char: str) -> None:
        result = sanitize_input(char)
        assert result == f"\\{char}"

    def test_command_substitution(self) -> None:
        result = sanitize_input("$(rm -rf /)")
        assert "\\$" in result
        assert "\\(" in result
        assert "\\)" in result

    def test_backtick_command(self) -> None:
        result = sanitize_input("`whoami`")
        assert result == "\\`whoami\\`"

    def test_semicolon_injection(self) -> None:
        result = sanitize_input("'; DROP TABLE;")
        assert "\\;" in result

    def test_pipe_injection(self) -> None:
        result = sanitize_input("hello | cat /etc/passwd")
        assert result == "hello \\| cat /etc/passwd"


class TestHtmlStripping:
    """Verify HTML tags are removed from Jira rich-text."""

    def test_simple_tags(self) -> None:
        assert sanitize_input("<b>bold</b>") == "bold"

    def test_nested_tags(self) -> None:
        assert sanitize_input("<div><p>text</p></div>") == "text"

    def test_self_closing_tag(self) -> None:
        assert sanitize_input("line<br/>break") == "linebreak"

    def test_tag_with_attributes(self) -> None:
        result = sanitize_input('<a href="http://example.com">link</a>')
        assert "<a" not in result
        assert "</a>" not in result
        assert "link" in result


class TestTruncation:
    """Verify inputs exceeding 10,000 characters are truncated."""

    def test_within_limit(self) -> None:
        text = "a" * 10_000
        assert sanitize_input(text) == text

    def test_exceeds_limit(self) -> None:
        text = "a" * 15_000
        result = sanitize_input(text)
        assert len(result) == 10_000


class TestEdgeCases:
    """Miscellaneous edge cases."""

    def test_empty_string(self) -> None:
        assert sanitize_input("") == ""

    def test_plain_text_unchanged(self) -> None:
        assert sanitize_input("Hello world 123") == "Hello world 123"

    def test_non_string_returns_empty(self) -> None:
        assert sanitize_input(42) == ""  # type: ignore[arg-type]

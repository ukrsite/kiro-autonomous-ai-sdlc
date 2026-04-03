"""Unit tests for the Jira issue key validator."""

import pytest

from scripts.validation.issue_key_validator import validate_issue_key


class TestValidateIssueKeyValid:
    """Keys that must be accepted."""

    @pytest.mark.parametrize(
        "key",
        [
            "PROJ-123",
            "AB-1",
            "XY99-42",
            "A1-0",
            "ZZ-999999",
        ],
    )
    def test_valid_keys(self, key: str) -> None:
        valid, msg = validate_issue_key(key)
        assert valid is True
        assert key in msg


class TestValidateIssueKeyInvalid:
    """Keys that must be rejected with a descriptive message."""

    @pytest.mark.parametrize(
        "key",
        [
            "proj-123",
            "",
            "123-ABC",
            "-1",
            "A-",
            "A-B",
            "PROJ",
            "PROJ-",
            "PROJ-abc",
            " PROJ-123",
            "PROJ-123 ",
        ],
    )
    def test_invalid_keys(self, key: str) -> None:
        valid, msg = validate_issue_key(key)
        assert valid is False
        assert len(msg) > 0

    def test_non_string_input(self) -> None:
        valid, msg = validate_issue_key(123)  # type: ignore[arg-type]
        assert valid is False
        assert "string" in msg.lower()

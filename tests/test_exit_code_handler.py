"""Unit tests for the exit code handler module."""

from __future__ import annotations

from scripts.validation.exit_code_handler import classify_exit_code


class TestClassifyExitCode:
    """Tests for classify_exit_code()."""

    def test_zero_returns_success(self) -> None:
        assert classify_exit_code(0) == "success"

    def test_one_returns_failure(self) -> None:
        assert classify_exit_code(1) == "failure"

    def test_137_returns_failure(self) -> None:
        assert classify_exit_code(137) == "failure"

    def test_negative_code_returns_failure(self) -> None:
        assert classify_exit_code(-1) == "failure"

    def test_large_positive_code_returns_failure(self) -> None:
        assert classify_exit_code(255) == "failure"

    def test_only_zero_is_success(self) -> None:
        assert classify_exit_code(0) == "success"
        for code in [1, 2, -1, 127, 137, 255]:
            assert classify_exit_code(code) == "failure"

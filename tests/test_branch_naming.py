"""Unit tests for the branch naming module."""

from __future__ import annotations

import pytest

from scripts.validation.branch_naming import generate_branch_name


class TestGenerateBranchName:
    """Tests for generate_branch_name()."""

    def test_valid_key_produces_correct_branch(self) -> None:
        assert generate_branch_name("PROJ-123") == "workflow/wf1-requirement-to-software/proj-123"

    def test_short_valid_key(self) -> None:
        assert generate_branch_name("AB-1") == "workflow/wf1-requirement-to-software/ab-1"

    def test_key_with_digits_in_project(self) -> None:
        assert generate_branch_name("XY99-42") == "workflow/wf1-requirement-to-software/xy99-42"

    def test_explicit_workflow(self) -> None:
        result = generate_branch_name("SAN-2", workflow="wf4-bug-fix")
        assert result == "workflow/wf4-bug-fix/san-2"

    def test_all_valid_workflows(self) -> None:
        for wf in (
            "wf1-requirement-to-software",
            "wf2-autonomous-refactoring",
            "wf3-dependency-upgrades",
            "wf4-bug-fix",
            "wf5-documentation",
        ):
            result = generate_branch_name("TEST-1", workflow=wf)
            assert result == f"workflow/{wf}/test-1"

    def test_invalid_key_lowercase_raises(self) -> None:
        with pytest.raises(ValueError, match="Cannot generate branch name"):
            generate_branch_name("proj-123")

    def test_empty_key_raises(self) -> None:
        with pytest.raises(ValueError, match="Cannot generate branch name"):
            generate_branch_name("")

    def test_missing_digits_raises(self) -> None:
        with pytest.raises(ValueError, match="Cannot generate branch name"):
            generate_branch_name("PROJ-")

    def test_numeric_prefix_raises(self) -> None:
        with pytest.raises(ValueError, match="Cannot generate branch name"):
            generate_branch_name("123-ABC")

    def test_invalid_workflow_raises(self) -> None:
        with pytest.raises(ValueError, match="invalid workflow"):
            generate_branch_name("PROJ-1", workflow="wf99-invalid")

    def test_branch_starts_with_workflow_prefix(self) -> None:
        result = generate_branch_name("TEST-1")
        assert result.startswith("workflow/")

    def test_branch_contains_lowercase_issue_key(self) -> None:
        result = generate_branch_name("MYPROJ-999")
        assert "myproj-999" in result

    def test_issue_key_is_lowercased(self) -> None:
        result = generate_branch_name("SAN-2")
        assert "SAN-2" not in result
        assert "san-2" in result

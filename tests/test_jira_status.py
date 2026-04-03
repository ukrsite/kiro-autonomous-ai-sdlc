"""Unit tests for the Jira status transition handler module."""

from __future__ import annotations

from scripts.validation.jira_status import (
    build_jira_comment,
    determine_transition,
)


class TestDetermineTransition:
    """Tests for determine_transition()."""

    def test_success_with_mr_transitions_to_in_review(self) -> None:
        assert determine_transition(success=True, mr_created=True) == "In Review"

    def test_success_without_mr_transitions_to_failed(self) -> None:
        assert determine_transition(success=True, mr_created=False) == "AI Dev Failed"

    def test_failure_with_mr_transitions_to_failed(self) -> None:
        assert determine_transition(success=False, mr_created=True) == "AI Dev Failed"

    def test_failure_without_mr_transitions_to_failed(self) -> None:
        assert determine_transition(success=False, mr_created=False) == "AI Dev Failed"


class TestBuildJiraComment:
    """Tests for build_jira_comment()."""

    def test_comment_contains_pipeline_url(self) -> None:
        url = "https://gitlab.example.com/pipelines/123"
        comment = build_jira_comment(
            pipeline_url=url,
            outcome_details="All stages passed.",
        )
        assert url in comment

    def test_comment_contains_outcome_details(self) -> None:
        comment = build_jira_comment(
            pipeline_url="https://gitlab.example.com/pipelines/1",
            outcome_details="Pipeline failed at security-scan stage.",
        )
        assert "Pipeline failed at security-scan stage." in comment

    def test_comment_includes_mr_url_when_provided(self) -> None:
        mr_url = "https://gitlab.example.com/merge_requests/42"
        comment = build_jira_comment(
            pipeline_url="https://gitlab.example.com/pipelines/1",
            outcome_details="Success",
            mr_url=mr_url,
        )
        assert mr_url in comment

    def test_comment_omits_mr_section_when_no_mr(self) -> None:
        comment = build_jira_comment(
            pipeline_url="https://gitlab.example.com/pipelines/1",
            outcome_details="Failed",
        )
        assert "Merge Request" not in comment

"""Unit tests for the merge request content builder module."""

from __future__ import annotations

from scripts.validation.merge_request import build_merge_request


class TestBuildMergeRequest:
    """Tests for build_merge_request()."""

    def _make_config(self, target_branch: str = "main") -> dict:
        return {"target_branch": target_branch, "repo_path": "sample-app/java-module"}

    def test_title_contains_issue_key_and_summary(self) -> None:
        result = build_merge_request(
            issue_key="PROJ-123",
            issue_summary="Implement user login",
            jira_url="https://jira.example.com/browse/PROJ-123",
            workflow_id="wf1-requirement-to-software",
            project_config=self._make_config(),
        )
        assert result["title"] == "PROJ-123: Implement user login"

    def test_target_branch_from_config(self) -> None:
        result = build_merge_request(
            issue_key="PROJ-123",
            issue_summary="Add feature",
            jira_url="https://jira.example.com/browse/PROJ-123",
            workflow_id="wf1-requirement-to-software",
            project_config=self._make_config("develop"),
        )
        assert result["target_branch"] == "develop"

    def test_description_contains_summary(self) -> None:
        result = build_merge_request(
            issue_key="PROJ-1",
            issue_summary="Implement search",
            jira_url="https://jira.example.com/browse/PROJ-1",
            workflow_id="wf1-requirement-to-software",
            project_config=self._make_config(),
        )
        assert "Implement search" in result["description"]

    def test_description_contains_jira_link(self) -> None:
        jira_url = "https://jira.example.com/browse/PROJ-99"
        result = build_merge_request(
            issue_key="PROJ-99",
            issue_summary="Add logging",
            jira_url=jira_url,
            workflow_id="wf1-requirement-to-software",
            project_config=self._make_config(),
        )
        assert jira_url in result["description"]

    def test_description_contains_workflow_id(self) -> None:
        result = build_merge_request(
            issue_key="PROJ-5",
            issue_summary="Feature X",
            jira_url="https://jira.example.com/browse/PROJ-5",
            workflow_id="wf2-autonomous-refactoring",
            project_config=self._make_config(),
        )
        assert "wf2-autonomous-refactoring" in result["description"]

    def test_result_contains_required_keys(self) -> None:
        result = build_merge_request(
            issue_key="AB-1",
            issue_summary="Minimal",
            jira_url="https://jira.example.com/browse/AB-1",
            workflow_id="wf1-requirement-to-software",
            project_config=self._make_config(),
        )
        assert "title" in result
        assert "target_branch" in result
        assert "description" in result

"""GitHub clone/remove helpers driven by issue JSON (no LLM)."""

from repo.git_ops import (
    clone_issue_repo,
    default_issue_json,
    ensure_repo_at_commit,
    git_apply_patch,
    normalize_patch_text,
    read_linked_pr_base_sha,
    remove_issue_repo,
    reset_repo_to_base,
)
from repo.workspace import IssueWorkspace, load_issue_workspace

__all__ = [
    "IssueWorkspace",
    "clone_issue_repo",
    "default_issue_json",
    "ensure_repo_at_commit",
    "git_apply_patch",
    "load_issue_workspace",
    "normalize_patch_text",
    "read_linked_pr_base_sha",
    "remove_issue_repo",
    "reset_repo_to_base",
]

"""Resolve GitHub repo name and local paths from an issue JSON file."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# AgentSmith-Live repo root (parent of ``src/``)
PROJECT_ROOT = Path(__file__).resolve().parents[2]


_GITHUB_ISSUE_RE = re.compile(
    r"https?://github\.com/([^/]+)/([^/]+)/issues/\d+",
    re.IGNORECASE,
)
_GITHUB_REPO_RE = re.compile(
    r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$",
    re.IGNORECASE,
)


def _parse_owner_repo_from_url(url: str) -> Optional[Tuple[str, str]]:
    if not url:
        return None
    m = _GITHUB_ISSUE_RE.match(url.strip())
    if m:
        return m.group(1), m.group(2)
    m = _GITHUB_REPO_RE.match(url.strip())
    if m:
        return m.group(1), m.group(2)
    return None


def _norm_github_repo(s: str) -> Tuple[str, str]:
    s = s.strip().strip("/")
    if "/" not in s:
        raise ValueError(f"Invalid github_repo (expected owner/name): {s!r}")
    owner, name = s.split("/", 1)
    if not owner or not name or "/" in name:
        raise ValueError(f"Invalid github_repo: {s!r}")
    return owner, name


@dataclass(frozen=True)
class IssueWorkspace:
    """Paths derived from ``data/issue_*.json`` for clone / dockerinit / cleanup."""

    issue_json_path: Path
    project_root: Path
    owner: str
    repo_name: str
    local_repo_path: Path
    dockerfile_out: Path

    @property
    def github_repo(self) -> str:
        return f"{self.owner}/{self.repo_name}"

    @property
    def clone_url(self) -> str:
        return f"https://github.com/{self.owner}/{self.repo_name}.git"


def load_issue_workspace(
    issue_json_path: Path | str,
    *,
    project_root: Optional[Path] = None,
) -> IssueWorkspace:
    """
    Load ``issue_json_path`` and resolve GitHub coordinates + local paths.

    JSON fields (optional)::

        "workspace": {{
            "github_repo": "owner/name",
            "local_repo_dir": "data/strix",
            "dockerfile_out": "data/strix/env.dockerfile"
        }}

    If ``workspace`` is missing, ``owner``/``repo`` are inferred from the top-level
    ``url`` (GitHub issue or repo URL). ``local_repo_dir`` defaults to
    ``data/{{owner}}_{{repo_name}}`` under the project root. ``dockerfile_out``
    defaults to ``{{local_repo_dir}}/env.dockerfile``.
    """
    root = (project_root or PROJECT_ROOT).resolve()
    path = Path(issue_json_path).resolve()
    with open(path, encoding="utf-8") as f:
        data: Dict[str, Any] = json.load(f)

    ws = data.get("workspace") or {}
    if not isinstance(ws, dict):
        ws = {}

    github_repo = ws.get("github_repo") or data.get("github_repo")
    if isinstance(github_repo, str) and github_repo.strip():
        owner, repo_name = _norm_github_repo(github_repo)
    else:
        url = data.get("url")
        if not isinstance(url, str):
            raise ValueError("Issue JSON must include `url` or `workspace.github_repo` / `github_repo`")
        parsed = _parse_owner_repo_from_url(url)
        if not parsed:
            raise ValueError(f"Could not parse owner/repo from url: {url!r}")
        owner, repo_name = parsed

    local_dir = ws.get("local_repo_dir") or data.get("local_repo_dir")
    if isinstance(local_dir, str) and local_dir.strip():
        local_repo_path = (root / local_dir.strip()).resolve()
    else:
        local_repo_path = (root / "data" / f"{owner}_{repo_name}").resolve()

    docker_rel = ws.get("dockerfile_out") or data.get("dockerfile_out")
    if isinstance(docker_rel, str) and docker_rel.strip():
        dockerfile_out = (root / docker_rel.strip()).resolve()
    else:
        dockerfile_out = local_repo_path / "env.dockerfile"

    return IssueWorkspace(
        issue_json_path=path,
        project_root=root,
        owner=owner,
        repo_name=repo_name,
        local_repo_path=local_repo_path,
        dockerfile_out=dockerfile_out,
    )

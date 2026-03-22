"""Clone or remove a local GitHub checkout (no LLM)."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

from repo.term import log_line, paint
from repo.workspace import IssueWorkspace, PROJECT_ROOT


def _safe_under_data(path: Path, project_root: Path) -> bool:
    try:
        path.resolve().relative_to((project_root / "data").resolve())
        return True
    except ValueError:
        return False


def clone_issue_repo(ws: IssueWorkspace, *, verbose: bool = False) -> Path:
    """
    ``git clone`` into ``ws.local_repo_path`` if missing. If the directory exists
    and is already a git repo, skip clone.
    """
    dest = ws.local_repo_path
    git_dir = dest / ".git"

    if dest.exists() and git_dir.is_dir():
        if verbose:
            log_line(
                "[repo]",
                paint("90", "skip clone (already a repo)"),
                paint("32", str(dest)),
            )
        return dest

    if dest.exists():
        raise FileExistsError(
            f"Path exists but is not a git repo (no .git): {dest}\n"
            "Remove it or pick another workspace.local_repo_dir in the issue JSON."
        )

    dest.parent.mkdir(parents=True, exist_ok=True)
    url = ws.clone_url
    if verbose:
        print(paint("1;36", "\n========== git clone =========="), file=sys.stderr)
        log_line("[repo]", paint("36", url))
        log_line("[repo]", paint("90", "->"), paint("32", str(dest)))
        print(paint("34", "---------- running git ----------"), file=sys.stderr)

    env = os.environ.copy()
    subprocess.run(
        ["git", "clone", "--depth", "1", url, str(dest)],
        check=True,
        cwd=str(ws.project_root),
        env=env,
    )
    if verbose:
        print(paint("32", "[repo] clone finished"), file=sys.stderr)
        print(paint("1;36", "================================\n"), file=sys.stderr)
    return dest


def remove_issue_repo(
    ws: IssueWorkspace,
    *,
    verbose: bool = False,
    allow_outside_data: bool = False,
) -> None:
    """
    Delete ``ws.local_repo_path``. By default only allows paths under
    ``<project>/data/`` (safety). Set ``allow_outside_data=True`` to force.
    """
    path = ws.local_repo_path
    root = ws.project_root

    if not path.exists():
        if verbose:
            log_line(
                "[repo]",
                paint("90", "nothing to remove (missing)"),
                paint("32", str(path)),
            )
        return

    if not allow_outside_data and not _safe_under_data(path, root):
        raise ValueError(
            f"Refusing to delete outside project data/: {path}\n"
            "Use allow_outside_data=True if you really mean it."
        )

    if verbose:
        print(paint("1;36", "\n========== remove repo =========="), file=sys.stderr)
        log_line("[repo]", paint("31", "removing"), paint("32", str(path)))
        print(paint("34", "---------- shutil.rmtree ----------"), file=sys.stderr)
    shutil.rmtree(path)
    if verbose:
        print(paint("32", "[repo] removed"), file=sys.stderr)
        print(paint("1;36", "==================================\n"), file=sys.stderr)


def default_issue_json(project_root: Optional[Path] = None) -> Path:
    """Example path (may not exist): ``<root>/data/issue_13.json``."""
    root = (project_root or PROJECT_ROOT).resolve()
    return root / "data" / "issue_13.json"

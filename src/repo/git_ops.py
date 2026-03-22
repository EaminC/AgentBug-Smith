"""Clone or remove a local GitHub checkout (no LLM)."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

from repo.term import log_line, paint
from repo.workspace import IssueWorkspace, PROJECT_ROOT

_SHA_RE = re.compile(r"^[0-9a-f]{7,40}$", re.I)


def read_linked_pr_base_sha(issue_json_path: Path | str) -> Optional[str]:
    """
    Return ``base_sha`` from the first ``linked_prs`` entry that has a non-empty ``patch``,
    if present. Used to checkout the tree the unified diff applies to.
    """
    path = Path(issue_json_path).resolve()
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    for pr in data.get("linked_prs") or []:
        if not isinstance(pr, dict):
            continue
        patch = pr.get("patch")
        if not (isinstance(patch, str) and patch.strip()):
            continue
        sha = pr.get("base_sha")
        if isinstance(sha, str) and _SHA_RE.match(sha.strip()):
            return sha.strip()
        return None
    return None


def ensure_repo_at_commit(
    repo_root: Path | str,
    sha: str,
    *,
    verbose: bool = False,
) -> Tuple[bool, str]:
    """
    ``git fetch`` + ``git checkout`` so the working tree matches the PR base commit.

    ``clone_issue_repo`` uses ``--depth 1`` (only current tip). Patches in issue JSON are
    usually against ``base_sha``; without fetching that commit, ``git apply`` can fail with
    ``No such file or directory`` if paths differ from current ``main``.
    """
    rr = Path(repo_root).resolve()
    sha = sha.strip()
    if not sha or not _SHA_RE.match(sha):
        return False, f"Invalid base_sha: {sha!r}"

    if not (rr / ".git").is_dir():
        return False, f"Not a git repository: {rr}"

    def _run(cmd: List[str], *, timeout: int) -> subprocess.CompletedProcess:
        return subprocess.run(cmd, cwd=str(rr), capture_output=True, text=True, timeout=timeout)

    cur = _run(["git", "rev-parse", "HEAD"], timeout=30)
    if cur.returncode != 0:
        return False, (cur.stderr or "git rev-parse failed").strip()

    cur_commit = cur.stdout.strip()
    if cur_commit == sha or cur_commit.startswith(sha):
        if verbose:
            log_line("[repo]", paint("90", "already at"), paint("32", cur_commit[:12]))
        return True, ""

    fetch = _run(["git", "fetch", "origin", sha], timeout=300)
    if fetch.returncode != 0:
        if (rr / ".git" / "shallow").is_file():
            if verbose:
                log_line("[repo]", paint("33", "shallow clone; deepening history..."), "")
            _run(["git", "fetch", "--unshallow"], timeout=600)
            _run(
                ["git", "fetch", "origin", "refs/heads/main:refs/remotes/origin/main", "--depth=2048"],
                timeout=600,
            )
            _run(
                ["git", "fetch", "origin", "refs/heads/master:refs/remotes/origin/master", "--depth=2048"],
                timeout=600,
            )
        fetch2 = _run(["git", "fetch", "origin", sha], timeout=300)
        if fetch2.returncode != 0:
            err = (fetch.stderr or fetch.stdout or "").strip()
            err2 = (fetch2.stderr or fetch2.stdout or "").strip()
            return False, f"git fetch {sha} failed:\n{err}\n{err2}"

    co = _run(["git", "checkout", "-f", sha], timeout=120)
    if co.returncode != 0:
        return False, (co.stderr or co.stdout or "git checkout failed").strip()

    if verbose:
        log_line("[repo]", paint("90", "checked out patch base"), paint("32", sha[:12]))
    return True, ""


def normalize_patch_text(patch_text: str) -> str:
    """CRLF → LF; ensure trailing newline (truncated JSON patches often break ``git apply``)."""
    t = patch_text.replace("\r\n", "\n")
    if not t.endswith("\n"):
        t += "\n"
    return t


def git_apply_patch(repo_root: Path | str, patch_text: str) -> Tuple[bool, str]:
    """Apply a unified diff with ``git apply --whitespace=nowarn``."""
    normalized = normalize_patch_text(patch_text)
    rr = Path(repo_root).resolve()
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".patch",
        delete=False,
        encoding="utf-8",
    ) as tmp:
        tmp.write(normalized)
        tmp_path = tmp.name
    try:
        r = subprocess.run(
            ["git", "apply", "--whitespace=nowarn", tmp_path],
            cwd=str(rr),
            capture_output=True,
            text=True,
            timeout=120,
        )
        err = (r.stderr or "") + (r.stdout or "")
        return (r.returncode == 0, err.strip())
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, str(e)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def reset_repo_to_base(repo_root: Path | str, sha: str) -> Tuple[bool, str]:
    """
    ``git reset --hard <sha>`` — drop local commits and working-tree changes to match ``sha``.
    Use before a new fail2pass iteration after ``git apply`` (untracked files like a new test
    file are not removed; overwrite them in the next step).
    """
    rr = Path(repo_root).resolve()
    sha = sha.strip()
    if not sha or not _SHA_RE.match(sha):
        return False, f"Invalid sha: {sha!r}"
    r = subprocess.run(
        ["git", "reset", "--hard", sha],
        cwd=str(rr),
        capture_output=True,
        text=True,
        timeout=60,
    )
    if r.returncode != 0:
        return False, (r.stderr or r.stdout or "git reset --hard failed").strip()
    return True, ""


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

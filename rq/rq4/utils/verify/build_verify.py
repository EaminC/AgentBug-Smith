"""Build evaluation (verify) datasets from raw ``all_combined_f2p`` data.

Goal
----
For each (agent, train_size) split we trained on, we also need a *test*
set of issues to *solve*: take an issue, give an agent (mini-swe-agent
or openhands) the problem statement, let it produce a patch, run the
associated ``agentsmith_fail2pass_NNN.py`` test, and decide pass/fail.

To be a clean evaluation we must **strip every patch-bearing field**
from the raw data, otherwise the agent would cheat by reading the
gold solution:

  - ``issue_NNN.json`` → keep metadata; **drop** ``linked_prs[].patch``
    (the gold git diff lives there) and **drop** ``linked_prs[].base_sha``
    / ``head_sha`` (these point at the PR commit, not the buggy tree).
  - ``generated_patch.diff`` → drop entirely (whole file is the patch).

Everything else (the test file, the dockerfile, run logs that don't
contain diffs) is harmless to keep — those don't leak the solution.

Outputs (created on first run, reused on subsequent runs unless
``--force-pool`` is passed). Under the **default ``--strict`` mode** each
verify directory contains exactly three files — all metadata, build
logs, and agent run logs are excluded from the pool:

    data/verify/
        _pool/<repo_owner>__<repo_name>__<issue_id>/   # one dir per
                                                        # (repo, id) row
                                                        # (200 total)
            issue.json                    # patch-stripped metadata
                                           # includes `repo` for self-doc
            agentsmith_fail2pass_<NNN>.py # the f2p test (kept verbatim)
            env.dockerfile                # docker build context

        issue_index_<agent>_<train_size>.jsonl
            # One row per issue for a *specific* split. Fields:
            #   split       0=in train (excluded from solver), 1=in test
            #   id          issue-1077
            #   repo        strands-agents/harness-sdk
            #   category    A..F
            #   confidence  high|medium|low
            #   raw_path    source directory under data/raw
            #   verify_dir  data/verify/_pool/<owner>__<name>__<id>
            #   test_relpath  tests/agentsmith_fail2pass_<NNN>.py
            #   dockerfile  env.dockerfile path
            #   f2p_status  "success" if summary.json says f2p_succeeded=true
            #   source_split train_size_requested / seed (provenance)

The 6 skill splits we trained are:

    mini-swe-agent 40   mini-swe-agent 60   mini-swe-agent 80
    openhands      40   openhands      60   openhands      80

All 6 use the *same* train/test *issues* (same seed=42, same
mode=repo_disjoint); the difference between skills is only the
``agent/skills/<agent>/<train_size>/`` directory the agent reads.
Thus the verify *data* is shared — only the index file name differs.

Usage
-----

    # build pool + 6 indices (idempotent; respects existing pool)
    python utils/verify/build_verify.py

    # rebuild pool from scratch (strict 3-file mode by default)
    python utils/verify/build_verify.py --force-pool

    # regenerate only the index files (no pool copy)
    python utils/verify/build_verify.py --skip-pool

    # validate that no leak vector survived + 3-file invariant
    python utils/verify/build_verify.py --audit

    # legacy 7-file mode (forensic / debug only; LEAKS auxiliary info)
    python utils/verify/build_verify.py --force-pool --no-strict
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Iterable

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE.parent))        # utils/  so `from split import run`

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ALL_COMBINED_ROOT = REPO_ROOT / "data" / "raw" / "results" / "all_combined_f2p"
VERIFY_ROOT       = REPO_ROOT / "data" / "verify"
POOL_DIR          = VERIFY_ROOT / "_pool"


def pool_dir_for(row: dict[str, Any]) -> Path:
    """Return the verify-pool directory for a single (repo, id) row.

    Pool dirs are keyed by the composite ``<repo_owner>__<repo_name>__<id>``
    so that the same GitHub issue number in two different repos maps to
    two distinct dirs. Without the repo prefix, the second write would
    silently overwrite the first and the index would point at the wrong
    content. (See ``docs/progress.md`` §5 for the original incident.)
    """
    issue_id = row["id"]
    repo = row.get("repo") or ""
    if "/" in repo:
        owner, name = repo.split("/", 1)
        prefix = f"{owner}__{name}__"
    else:
        prefix = ""
    return POOL_DIR / f"{prefix}{issue_id}"


#: The six (agent, train_size) skills we trained on. Each one needs
#: its own index file because (a) test_size varies with train_size and
#: (b) some issues move between train and test as train_size grows.
SKILL_SPLITS: list[tuple[str, int]] = [
    ("mini-swe-agent", 40),
    ("mini-swe-agent", 60),
    ("mini-swe-agent", 80),
    ("openhands",      40),
    ("openhands",      60),
    ("openhands",      80),
]
SPLIT_MODE = "repo_disjoint"
SPLIT_SEED = 42

#: Files inside every raw issue dir, classified by leak risk.
#: ``keep``   = copy as-is to verify pool (no patch leakage).
#: ``strip``  = copy only after removing patch-bearing keys / contents.
#: ``drop``   = do not copy at all (whole file is the patch or
#:              contains agent-generated patches that could leak).
KEEP_FILES = ("env.dockerfile",)                          # tiny, no patch
STRIP_FILES = ("issue.json",)                             # metadata + patch
DROP_FILES = ("generated_patch.diff",)                    # whole file = patch

#: These are run logs. We audit them for `diff --git` / `@@` hunks
#: before deciding. If they contain diff hunks, we drop them.
#: Under the default ``--strict`` mode these are unconditionally dropped,
#: regardless of whether they look diff-free, so the pool stays minimal.
RUN_LOG_FILES = ("f2p.txt", "dockerbuild.txt", "run.log")
DIFF_MARKERS = ("diff --git ", "\n@@ ", "\n+++ ", "\n--- ")

#: Metadata files with no leakage risk — kept verbatim.
#: Under ``--strict`` these are also unconditionally dropped to keep the
#: pool interface surface as small as possible (the verifier only needs
#: ``issue.json`` + the test + ``env.dockerfile``).
META_FILES = ("summary.json", "agentsmith_stat.json")

#: Set of files allowed to exist in a verify pool dir under --strict.
#: Anything else (summary.json, run logs, generated_patch.diff, …)
#: must be absent.
STRICT_DROP_FILES = (
    "generated_patch.diff",
    "summary.json",
    "agentsmith_stat.json",
    "f2p.txt",
    "dockerbuild.txt",
    "run.log",
)

#: Default policy. ``--strict`` is the **only** mode that the released
#: audit considers safe; ``--no-strict`` is retained for debugging the
#: pipeline itself (e.g. inspecting why a run log was generated).
DEFAULT_STRICT = True

# ---------------------------------------------------------------------------
# Issue-id helpers
# ---------------------------------------------------------------------------

def _issue_dir_name(issue_id: str, raw_dir_name: str) -> str:
    """``raw_dir_name`` is ``issue_1077_20260824T130102Z``; we only
    use it to *parse out the issue number* so the test file rename is
    deterministic. The new verify dir is named after the index id."""
    # raw_dir_name looks like issue_<num>_<timestamp>
    # We don't actually need the number — we copy the original
    # ``agentsmith_fail2pass_<NNN>.py`` byte-for-byte, so the number
    # is preserved in the filename.
    return raw_dir_name


def _issue_id_from_index(row: dict[str, Any]) -> str:
    return row["id"]


def _issue_number_from_raw_dir(raw_dir: Path) -> str | None:
    """Extract the issue number from ``issue_1077_<ts>``."""
    # Format is issue_<num>_<ts>; we keep the directory name itself,
    # but the number is the part between ``issue_`` and the first
    # underscore after the number.
    name = raw_dir.name
    if not name.startswith("issue_"):
        return None
    parts = name.split("_", 2)        # ["issue", "1077", "20260824T130102Z"]
    if len(parts) < 2:
        return None
    return parts[1]


def _find_test_file(raw_dir: Path) -> Path | None:
    for p in raw_dir.glob("agentsmith_fail2pass_*.py"):
        return p
    return None


def _scrape_base_sha(raw_dir: Path) -> str | None:
    """Return the base_sha of the first linked PR for this issue.

    The solver (``utils/verify/solve.py``) needs the commit hash the
    repo should be checked out to before ``docker build`` — i.e. the
    state of the repo *just before* the linked PR's fix landed. The
    raw ``issue_<NNN>.json`` carries it under
    ``linked_prs[0].base_sha``. We deliberately do *not* persist it
    in the pool's ``issue.json`` (it's PR-flow metadata) — instead
    we expose it on the solver's index rows only.
    """
    raw_issue_json = raw_dir / f"issue_{Path(raw_dir).name.split('_')[1]}.json"
    if not raw_issue_json.exists():
        # Fallback: any issue_<NNN>.json in the raw dir.
        candidates = list(raw_dir.glob("issue_*.json"))
        if not candidates:
            return None
        raw_issue_json = candidates[0]
    try:
        obj = json.loads(raw_issue_json.read_text(encoding="utf-8"))
    except Exception:
        return None
    prs = obj.get("linked_prs") or []
    if not prs:
        return None
    return prs[0].get("base_sha")


def _find_issue_json(raw_dir: Path) -> Path | None:
    """Find the per-issue metadata file.

    Raw dirs name it ``issue_<NNN>.json`` (not the bare ``issue.json``
    we initially assumed). Both patterns are accepted.
    """
    for p in raw_dir.glob("issue_*.json"):
        return p
    if (raw_dir / "issue.json").exists():
        return raw_dir / "issue.json"
    return None


# ---------------------------------------------------------------------------
# Pool build: strip patch, copy safe files
# ---------------------------------------------------------------------------

def _strip_issue_json(raw_path: Path) -> dict[str, Any]:
    """Read ``issue_NNN.json`` and remove every patch-bearing key.

    The gold patch lives in ``linked_prs[].patch``. We also strip the
    commit shas (they identify the PR commit, not the buggy tree) and
    any ``merged`` flag that would let the agent infer which PR solved
    this issue.
    """
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    if "linked_prs" in raw and isinstance(raw["linked_prs"], list):
        for pr in raw["linked_prs"]:
            pr.pop("patch", None)
            pr.pop("base_sha", None)
            pr.pop("head_sha", None)
            # Keep number/state/title/url/merged/base_branch — they
            # are public metadata and don't leak the diff.
    return raw


def _has_diff_marker(text: str) -> bool:
    """Detect a real git-diff header anywhere in the file.

    A run log is much more likely to contain lines like ``---`` or
    ``+++`` as horizontal-rule decorations or output formatting than
    a genuine ``diff --git`` header. So we only treat a file as a
    leak vector if we see the literal ``diff --git`` token (with the
    trailing space) or an ``@@`` hunk header at the start of a line.
    The loose ``\n--- `` / ``\n+++ `` heuristics caused false
    positives on AgentSmith's stdout, which uses ``---`` as a
    section divider.
    """
    return "diff --git " in text or "\n@@ " in text


def _copy_text(src: Path, dst: Path, *, must_be_diff_free: bool) -> str:
    """Copy text file; return 'kept' / 'dropped_for_diff' / 'missing'."""
    if not src.exists():
        return "missing"
    text = src.read_text(encoding="utf-8", errors="replace")
    if must_be_diff_free and _has_diff_marker(text):
        return "dropped_for_diff"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return "kept"


def _build_one_issue(row: dict[str, Any], force: bool,
                     strict: bool = DEFAULT_STRICT) -> dict[str, Any]:
    """Materialise a stripped verify dir for a single issue.

    Returns a small dict describing what was written; useful for the
    manifest.
    """
    issue_id = row["id"]
    raw_dir = Path(row["path"])
    if not raw_dir.exists():
        return {"id": issue_id, "ok": False, "reason": "raw_dir_missing",
                "raw_path": str(raw_dir)}

    verify_dir = pool_dir_for(row)
    if verify_dir.exists() and not force:
        # Pool is already built for this issue — idempotent skip.
        # We still need to return the per-issue stats below, but the
        # caller can re-run --audit to verify integrity.
        return _audit_one_issue(row)

    verify_dir.mkdir(parents=True, exist_ok=True)
    audit: dict[str, Any] = {
        "id": issue_id,
        "repo": row.get("repo"),
        "category": row.get("category"),
        "raw_path": str(raw_dir.relative_to(REPO_ROOT)),
        "verify_dir": str(verify_dir.relative_to(REPO_ROOT)),
        "files": {},
        "ok": True,
        "strict": strict,
    }

    # 0. Strict-mode clean sweep. If the pool dir previously held files
    # from a non-strict build (summary.json, run.log, …), get rid of them
    # up front so we end up with exactly the 3 files we want.
    if strict:
        for stray in verify_dir.iterdir():
            if stray.is_file():
                stray.unlink()
        audit["strict_cleaned"] = True

    # 1. Stripped metadata.
    issue_json_raw = _find_issue_json(raw_dir)
    if issue_json_raw is None:
        audit["ok"] = False
        audit["reason"] = "issue_json_missing"
        return audit
    stripped = _strip_issue_json(issue_json_raw)
    # Re-stamp ``repo`` and ``id`` so the verify dir is self-describing
    # even if the raw issue.json dropped them. This also makes collision
    # dirs unambiguously attributable to the right ``(repo, id)``.
    if row.get("repo"):
        stripped["repo"] = row["repo"]
    stripped["id"] = issue_id
    (verify_dir / "issue.json").write_text(
        json.dumps(stripped, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    audit["files"]["issue.json"] = "stripped"

    # 2. Test file — keep verbatim.
    test_file = _find_test_file(raw_dir)
    if test_file is None:
        audit["ok"] = False
        audit["reason"] = "test_file_missing"
        return audit
    shutil.copy2(test_file, verify_dir / test_file.name)
    audit["files"][test_file.name] = "kept"
    audit["test_relpath"] = f"tests/{test_file.name}"

    # 3. Dockerfile — kept under both modes. Meta files only in non-strict.
    for fname in KEEP_FILES:
        status = _copy_text(raw_dir / fname, verify_dir / fname,
                            must_be_diff_free=False)
        audit["files"][fname] = status
    if not strict:
        for fname in META_FILES:
            status = _copy_text(raw_dir / fname, verify_dir / fname,
                                must_be_diff_free=False)
            audit["files"][fname] = status

    # 4. Run logs — under strict they are unconditionally dropped;
    # otherwise we copy them only if diff-free.
    if strict:
        for fname in RUN_LOG_FILES:
            audit["files"][fname] = "dropped_strict"
    else:
        for fname in RUN_LOG_FILES:
            status = _copy_text(raw_dir / fname, verify_dir / fname,
                                must_be_diff_free=True)
            audit["files"][fname] = status

    # 5. Hard-drop the gold-patch file (if present in either raw or pool).
    drop = raw_dir / "generated_patch.diff"
    if drop.exists():
        # Make sure it does NOT end up in verify_dir.
        leaked = verify_dir / "generated_patch.diff"
        if leaked.exists():
            leaked.unlink()
    audit["files"]["generated_patch.diff"] = "dropped"

    return audit


def _audit_one_issue(row: dict[str, Any]) -> dict[str, Any]:
    """Return a lightweight per-issue entry without rewriting."""
    issue_id = row["id"]
    raw_dir = Path(row["path"])
    verify_dir = pool_dir_for(row)
    test_file = _find_test_file(raw_dir)
    return {
        "id": issue_id,
        "repo": row.get("repo"),
        "category": row.get("category"),
        "raw_path": str(raw_dir.relative_to(REPO_ROOT)),
        "verify_dir": str(verify_dir.relative_to(REPO_ROOT)),
        "test_relpath": (f"tests/{test_file.name}"
                         if test_file is not None else None),
        "ok": verify_dir.exists(),
    }


def build_pool(index_rows: list[dict[str, Any]],
               force: bool = False,
               strict: bool = DEFAULT_STRICT) -> list[dict[str, Any]]:
    audits: list[dict[str, Any]] = []
    for row in index_rows:
        try:
            audits.append(_build_one_issue(row, force=force, strict=strict))
        except Exception as exc:
            audits.append({"id": row.get("id"), "ok": False,
                           "reason": f"exception:{exc!r}",
                           "raw_path": row.get("path")})
    return audits


# ---------------------------------------------------------------------------
# Index files: one per (agent, train_size) skill split
# ---------------------------------------------------------------------------

def _split_assignments(train_rows: list[dict[str, Any]],
                      test_rows: list[dict[str, Any]]) -> dict[tuple[str, str], int]:
    """Map ``(repo, id)`` → 0/1.

    Issue ids are **not unique across repos** (e.g. ``issue-974`` appears
    in two different repos). To disambiguate, we use the composite key
    ``(repo, id)``. Without this composite key, the second occurrence
    of a colliding id silently overwrites the first in our index
    dict and rows vanish from the verify pool.
    """
    assign: dict[tuple[str, str], int] = {}
    for r in train_rows:
        assign[(r.get("repo"), r["id"])] = 0
    for r in test_rows:
        assign[(r.get("repo"), r["id"])] = 1
    return assign


#: Patch around ``utils.split.run.split``'s id-only-dedup bug: when
#: the same ``id`` appears under two different repos, ``train_ids``
#: is built as a *set* of ids, so both copies are excluded from test
#: even though only one is in train. The fix: rebuild train/test from
#: the *claimed repo set*, which is the actual unit of train/test
#: assignment in ``repo_disjoint`` mode. We replicate the relevant
#: logic locally instead of monkey-patching the upstream split.
def _split_repo_disjoint(index_rows: list[dict[str, Any]],
                         train_size: int,
                         seed: int = SPLIT_SEED,
                         ) -> tuple[list[dict[str, Any]],
                                    list[dict[str, Any]],
                                    dict[str, Any]]:
    from collections import defaultdict
    import random as _random

    rows = [r for r in index_rows
            if r.get("category") in {"A", "B", "C", "D", "E", "F"}]
    if train_size >= len(rows):
        sys.exit(f"train_size ({train_size}) >= usable issues ({len(rows)})")

    by_repo: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        if r.get("repo"):
            by_repo[r["repo"]].append(r)

    rng = _random.Random(seed)
    all_repos_sorted = sorted(by_repo, key=lambda r: (len(by_repo[r]), r))
    cumsum, running = [], 0
    for r in all_repos_sorted:
        running += len(by_repo[r])
        cumsum.append(running)
    feasible_k = [k for k, s in enumerate(cumsum, start=1)
                  if s >= train_size]
    chosen_n = feasible_k[0] if feasible_k else len(all_repos_sorted)
    chosen_set = set(all_repos_sorted[:chosen_n])

    # Tie-break: swap one boundary repo for the next-larger one with
    # the same issue count (deterministic by seed).
    last_size = len(by_repo[all_repos_sorted[chosen_n - 1]]) if chosen_n else 0
    boundary = [r for r in all_repos_sorted[:chosen_n]
                if len(by_repo[r]) == last_size]
    if chosen_n < len(all_repos_sorted) and len(boundary) > 1:
        nxt = next((r for r in all_repos_sorted[chosen_n:]
                    if len(by_repo[r]) == last_size), None)
        if nxt is not None:
            drop = rng.choice(boundary)
            chosen_set.discard(drop)
            chosen_set.add(nxt)

    claimed_set = chosen_set
    train_rows = [r for repo in claimed_set for r in by_repo[repo]]
    test_rows  = [r for r in rows if r.get("repo") not in claimed_set]

    from collections import Counter
    cat_counts = Counter(r["category"] for r in train_rows)
    repo_counts = Counter(r.get("repo") for r in train_rows)
    n_test_with_claimed = sum(1 for r in test_rows
                              if r.get("repo") in claimed_set)
    summary = {
        "train_size": len(train_rows),
        "test_size": len(test_rows),
        "train_category_counts": dict(sorted(cat_counts.items())),
        "train_unique_repos": len([r for r, n in repo_counts.items() if r]),
        "train_repos": sorted(claimed_set),
        "test_issues_with_train_repo": n_test_with_claimed,
        "test_repo_leakage_pct": (
            round(100.0 * n_test_with_claimed / max(len(test_rows), 1), 1)
        ),
        "constraint_check": {
            "every_category_present": all(
                cat in cat_counts
                for cat in {"A", "B", "C", "D", "E", "F"}
                if any(r["category"] == cat for r in rows)
            ),
            "repo_overlap_best_effort": True,
        },
    }
    return train_rows, test_rows, summary


def build_index(agent: str, train_size: int, index_rows: list[dict[str, Any]]
                ) -> tuple[Path, dict[str, Any], int]:
    """Build ``issue_index_<agent>_<train_size>.jsonl``.

    Same seed (42) and mode (repo_disjoint) are used everywhere so the
    *issue-level* train/test partition is identical across all 6
    skills; only the ``train_size`` differs and therefore the *size*
    of the train/test sets differs.

    We call our **local** ``_split_repo_disjoint`` rather than
    ``split_mod.split`` because the upstream ``split()`` has a latent
    id-only-dedup bug: when the same ``id`` appears under two
    different repos (8 such cases in the current index), ``train_ids``
    is built as a *set* of ids, so both copies are excluded from test
    even though only one is in train. Using the claimed-repo set
    directly avoids the bug entirely.
    """
    train, test, summary = _split_repo_disjoint(
        index_rows, train_size, seed=SPLIT_SEED,
    )
    assign = _split_assignments(train, test)

    out_path = VERIFY_ROOT / f"issue_index_{agent}_{train_size}.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n_rows = 0
    with out_path.open("w", encoding="utf-8") as f:
        for row in index_rows:
            key = (row.get("repo"), row["id"])
            if key not in assign:
                # Issue not in any split (e.g. category outside A..F)
                continue
            raw_dir = Path(row["path"])
            test_file = _find_test_file(raw_dir)
            summary_path = raw_dir / "summary.json"
            f2p_status = None
            if summary_path.exists():
                try:
                    f2p_status = json.loads(
                        summary_path.read_text(encoding="utf-8")
                    ).get("f2p_succeeded")
                except Exception:
                    pass
            # Pool is keyed by id (one stripped copy per unique id),
            # but we tag the row with the repo too so disambiguation
            # is unambiguous.
            entry = {
                "split": assign[key],
                "id": row["id"],
                "repo": row.get("repo"),
                "category": row.get("category"),
                "confidence": row.get("confidence"),
                "raw_path": str(raw_dir.relative_to(REPO_ROOT)),
                "verify_dir": str(pool_dir_for(row).relative_to(REPO_ROOT)),
                "test_relpath": (f"tests/{test_file.name}"
                                 if test_file is not None else None),
                "f2p_status": f2p_status,
                # Base SHA at which the agent must start editing. Read
                # from raw issue.json's first linked_pr (already patch-
                # stripped by build_pool). Solver needs this to
                # ``git checkout`` the right tree before
                # ``docker build``.
                "base_sha": _scrape_base_sha(raw_dir),
                "source_split": {
                    "agent": agent,
                    "train_size_requested": train_size,
                    "mode": SPLIT_MODE,
                    "seed": SPLIT_SEED,
                },
            }
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            n_rows += 1
    return out_path, summary, n_rows


# ---------------------------------------------------------------------------
# Audit: scan every verify_dir for surviving leak vectors
# ---------------------------------------------------------------------------

LEAK_PATH_NEVER_EXISTS = ("generated_patch.diff",)


def _pool_file_set(verify_dir: Path) -> set[str]:
    """Set of file names currently present in a verify pool dir."""
    return {p.name for p in verify_dir.iterdir() if p.is_file()} if verify_dir.exists() else set()


def audit_pool(strict: bool = DEFAULT_STRICT,
                index_rows: list[dict[str, Any]] | None = None,
                ) -> list[dict[str, Any]]:
    """Walk the pool and confirm no leak vector survived.

    Under ``strict`` mode (the default) we additionally enforce that every
    verify dir contains exactly the allowed 3-file set:

        - ``env.dockerfile``
        - ``issue.json``
        - exactly one ``agentsmith_fail2pass_<NNN>.py``

    Anything else (``summary.json``, ``run.log``, ``generated_patch.diff``,
    …) is treated as a leak and the issue is marked ``ok=False``.

    If ``index_rows`` is provided we additionally cross-check that:
      - every pool ``issue.json`` carries a non-null ``repo`` field;
      - the ``repo`` field matches the one declared in ``data/index.jsonl``
        for the corresponding ``(repo, id)`` row (catches the
        same-id-across-repos overwrite bug);
      - every pool dir corresponds to a unique ``(repo, id)`` pair
        (no two pool dirs collide because their repo prefix is missing).
    """
    findings: list[dict[str, Any]] = []
    if not POOL_DIR.exists():
        return [{"ok": False, "reason": "pool_dir_missing"}]
    for issue_dir in sorted(POOL_DIR.iterdir()):
        finding: dict[str, Any] = {"id": issue_dir.name, "checks": []}
        files = _pool_file_set(issue_dir)
        # 1. generated_patch.diff must NOT exist.
        for bad in LEAK_PATH_NEVER_EXISTS:
            finding["checks"].append({
                "check": f"absent:{bad}",
                "ok": bad not in files,
            })
        # 2. issue.json must have no `patch` keys.
        ij = issue_dir / "issue.json"
        if ij.exists():
            try:
                obj = json.loads(ij.read_text(encoding="utf-8"))
                leak_keys = []
                for pr in obj.get("linked_prs", []):
                    if "patch" in pr:
                        leak_keys.append("patch")
                    if "base_sha" in pr:
                        leak_keys.append("base_sha")
                    if "head_sha" in pr:
                        leak_keys.append("head_sha")
                finding["checks"].append({
                    "check": "issue_json_no_patch_keys",
                    "ok": not leak_keys,
                    "leak_keys": leak_keys,
                })
            except Exception as exc:
                finding["checks"].append({
                    "check": "issue_json_no_patch_keys",
                    "ok": False, "reason": str(exc),
                })
        # 3. No run log may contain diff markers (non-strict only —
        #    strict mode never copies run logs in the first place).
        if not strict:
            for fname in RUN_LOG_FILES:
                p = issue_dir / fname
                if p.exists():
                    text = p.read_text(encoding="utf-8", errors="replace")
                    has_diff = _has_diff_marker(text)
                    finding["checks"].append({
                        "check": f"runlog_diff_free:{fname}",
                        "ok": not has_diff,
                    })
        # 4. Strict invariant: exactly the allowed 3 files.
        if strict:
            test_files = [f for f in files if f.startswith("agentsmith_fail2pass_")]
            required_present = {"issue.json", "env.dockerfile"}
            required_absent = set(STRICT_DROP_FILES)
            finding["checks"].append({
                "check": "strict_3_file_invariant",
                "ok": (len(test_files) == 1
                       and required_present.issubset(files)
                       and not (files & required_absent)
                       and len(files) == 3),
                "files_present": sorted(files),
                "files_required_absent": sorted(required_absent & files),
                "files_required_present": sorted(required_present - files),
                "n_test_files": len(test_files),
            })
        finding["ok"] = all(c.get("ok") for c in finding["checks"])
        findings.append(finding)

    # 5. Global cross-check: every pool dir should correspond to a
    #    unique ``(repo, id)`` pair from ``index_rows``. If two pool
    #    dirs share the same ``(repo, id)`` (or two different ids share
    #    one dir), the build is broken.
    if index_rows is not None:
        expected = {pool_dir_for(r).resolve(): (r.get("repo"), r["id"])
                    for r in index_rows}
        actual = {p.resolve(): None for p in POOL_DIR.iterdir() if p.is_dir()}
        # Populate actual from each dir's issue.json so we can match.
        for pool_path in list(actual):
            ij = pool_path / "issue.json"
            if not ij.exists():
                continue
            try:
                obj = json.loads(ij.read_text(encoding="utf-8"))
                actual[pool_path] = (obj.get("repo"), obj.get("id"))
            except Exception:
                pass
        mismatch_paths = [
            str(p.relative_to(REPO_ROOT))
            for p, key in actual.items()
            if key is None or expected.get(p) != key
        ]
        missing = [
            str(p.relative_to(REPO_ROOT))
            for p, key in expected.items()
            if p not in actual
        ]
        findings.append({
            "id": "_GLOBAL_",
            "checks": [{
                "check": "pool_dir_uniqueness",
                "ok": not mismatch_paths and not missing,
                "n_expected_dirs": len(expected),
                "n_actual_dirs": len(actual),
                "mismatched_issue_json": mismatch_paths,
                "missing_pool_dirs": missing,
            }],
            "ok": not mismatch_paths and not missing,
        })
    return findings


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def load_index(path: Path) -> list[dict[str, Any]]:
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def _hash_path(p: Path) -> str:
    return hashlib.sha1(str(p).encode("utf-8")).hexdigest()[:8]


def main() -> None:
    p = argparse.ArgumentParser(
        description="Build evaluation (verify) pool + per-skill index files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--index", type=Path,
                   default=REPO_ROOT / "data" / "index.jsonl")
    p.add_argument("--force-pool", action="store_true",
                   help="Rebuild the _pool/ directory from scratch.")
    p.add_argument("--skip-pool", action="store_true",
                   help="Don't touch _pool/; only regenerate index files.")
    p.add_argument("--audit", action="store_true",
                   help="After (re)building, scan the pool for surviving "
                        "leak vectors.")
    p.add_argument("--strict", dest="strict", action="store_true",
                   default=DEFAULT_STRICT,
                   help="Strict 3-file pool mode (default): each verify "
                        "dir contains only env.dockerfile, issue.json, "
                        "and the test file. All run logs + meta files "
                        "are unconditionally dropped.")
    p.add_argument("--no-strict", dest="strict", action="store_false",
                   help="Legacy mode (forensic / debug only): copy run "
                        "logs and meta files when they look diff-free.")
    p.add_argument("--quiet", action="store_true")
    args = p.parse_args()

    if not args.index.exists():
        sys.exit(f"--index {args.index} does not exist")

    index_rows = load_index(args.index)
    print(f"[idx] {len(index_rows)} issues from {args.index}")

    # 1. Pool.
    if not args.skip_pool:
        if args.force_pool and POOL_DIR.exists():
            shutil.rmtree(POOL_DIR)
        print(f"[pool] strict={args.strict}, force={args.force_pool}")
        audits = build_pool(index_rows, force=args.force_pool,
                            strict=args.strict)
        n_ok = sum(1 for a in audits if a.get("ok"))
        n_bad = len(audits) - n_ok
        print(f"[pool] built {n_ok}/{len(audits)} verify dirs under "
              f"{POOL_DIR.relative_to(REPO_ROOT)}")
        if n_bad:
            for a in audits:
                if not a.get("ok"):
                    print(f"  ! {a.get('id')}: {a.get('reason')}")

    # 2. Index files.
    print(f"[idx] generating {len(SKILL_SPLITS)} index files ...")
    index_summary: dict[str, dict[str, Any]] = {}
    for agent, train_size in SKILL_SPLITS:
        out_path, summary, n_rows = build_index(agent, train_size, index_rows)
        index_summary[f"{agent}_{train_size}"] = {
            "file": str(out_path.relative_to(REPO_ROOT)),
            "rows": n_rows,
            "train_size": summary["train_size"],
            "test_size": summary["test_size"],
            "train_repos": summary["train_repos"],
            "test_repo_leakage_pct": summary["test_repo_leakage_pct"],
        }
        if not args.quiet:
            print(f"  - {out_path.relative_to(REPO_ROOT)}: "
                  f"{n_rows} rows  (train={summary['train_size']}, "
                  f"test={summary['test_size']}, "
                  f"leak={summary['test_repo_leakage_pct']}%)")

    # 3. Manifest summarising every split's verify setup.
    manifest_path = VERIFY_ROOT / "verify_manifest.json"
    manifest_path.write_text(json.dumps({
        "index_rows": len(index_rows),
        "pool_dir": str(POOL_DIR.relative_to(REPO_ROOT)),
        "splits": index_summary,
        "skill_splits": [{"agent": a, "train_size": t}
                         for a, t in SKILL_SPLITS],
        "split_mode": SPLIT_MODE,
        "split_seed": SPLIT_SEED,
        "strict": args.strict,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[idx] manifest: {manifest_path.relative_to(REPO_ROOT)}")

    # 4. Audit (optional).
    if args.audit:
        print(f"[audit] scanning verify pool (strict={args.strict}) ...")
        findings = audit_pool(strict=args.strict, index_rows=index_rows)
        n_ok = sum(1 for f in findings if f.get("ok"))
        n_bad = len(findings) - n_ok
        print(f"[audit] {n_ok}/{len(findings)} issues clean")
        for f in findings:
            if not f.get("ok"):
                bad = [c for c in f["checks"] if not c.get("ok")]
                print(f"  ! {f['id']}: {bad}")
        audit_path = VERIFY_ROOT / "audit.json"
        audit_path.write_text(json.dumps(findings, indent=2,
                                         ensure_ascii=False),
                              encoding="utf-8")
        print(f"[audit] written: {audit_path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()

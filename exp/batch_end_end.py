"""
Batch end-to-end: read a list of issue JSON paths from a manifest file, then run the same
pipeline as ``exp/end-end.py`` for each entry.

Does **not** modify ``end-end.py`` on disk: loads it as a module and sets ``_ISSUE_JSON`` before
each ``_run``, mirroring the ``if __name__ == "__main__"`` wrapper (tee, StatsTool, duration).

Manifest formats (UTF-8 JSON):

- Array of strings: ``["data/issue_71.json", ...]``
- Object with key ``issues``: ``{"issues": ["data/issue_71.json", ...]}``

Paths are resolved relative to the project root (parent of ``exp/``).

Use ``--script`` to run a variant pipeline with the same structure, e.g.::

    python exp/batch_end_end.py data/issue_run_new_manifest.json \
        --script exp/end-end-agentless-ablation.py --continue-on-error
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from datetime import timedelta
from pathlib import Path
from typing import Any
import subprocess

def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


DEFAULT_SCRIPT = "exp/end-end.py"


def _load_end_end_module(script: str | Path = DEFAULT_SCRIPT):
    """
    Load a pipeline script (default ``exp/end-end.py``; hyphenated filenames are fine)
    without editing that file. Relative paths are resolved against the current directory
    first, then the project root.

    The script must expose the same module-level names as ``end-end.py``:
    ``_ISSUE_JSON``, ``_run``, ``_MODEL``, ``_AGENTSMITH_ROOT``, ``StatsTool``,
    ``result_run_with_tee``.
    """
    root = _project_root()
    path = Path(script)
    if not path.is_absolute():
        path = path.resolve() if path.resolve().is_file() else (root / path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"pipeline script not found: {path}")
    spec = importlib.util.spec_from_file_location("end_end_runtime", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module from {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _parse_manifest(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [str(x) for x in raw]
    if isinstance(raw, dict) and "issues" in raw:
        v = raw["issues"]
        if not isinstance(v, list):
            raise ValueError("manifest key 'issues' must be an array")
        return [str(x) for x in v]
    raise ValueError("manifest must be a JSON array or an object with an 'issues' array")


def _issue_image_tag(mod: Any, issue_json: Path) -> str | None:
    """
    Image tag the pipeline builds for this issue: ``test-build-<repo dir name>``
    (same naming as ``dockerbuild`` and ``testrun.verify._docker_image_tag``).
    """
    try:
        ws = mod.load_issue_workspace(issue_json)
        return f"test-build-{Path(ws.local_repo_path).resolve().name.lower()}"
    except Exception as e:
        print(f"[batch] Warning: cannot determine image tag for {issue_json}: {e}", file=sys.stderr)
        return None


def _remove_issue_image(mod: Any, issue_json: Path) -> None:
    """Remove the tagged image built for this issue, if it exists."""
    tag = _issue_image_tag(mod, issue_json)
    if not tag:
        return
    try:
        exists = subprocess.run(
            ["docker", "image", "inspect", tag], capture_output=True, check=False
        ).returncode == 0
        if not exists:
            print(f"[batch] No image '{tag}' to remove.")
            return
        print(f"[batch] Removing issue image '{tag}'...")
        res = subprocess.run(["docker", "rmi", "-f", tag], capture_output=True, text=True, check=False)
        if res.returncode != 0:
            print(f"[batch] Warning: failed to remove image '{tag}': {res.stderr.strip()}", file=sys.stderr)
    except Exception as e:
        print(f"[batch] Warning: image cleanup failed for '{tag}': {e}", file=sys.stderr)


def _run_one_issue(mod: Any, issue_json: Path) -> None:
    """Same control flow as ``end-end.py`` main block."""
    issue_json = issue_json.resolve()
    mod._ISSUE_JSON = issue_json
    start_time = time.time()
    with mod.result_run_with_tee(
        mod._AGENTSMITH_ROOT,
        issue_json,
        banner="[batch end-end] result dir:",
    ) as run_dir:
        _usage_stats = mod.StatsTool(
            model=mod._MODEL,
            verbose=True,
            stats_file=run_dir / "agentsmith_stat.json",
        )
        _usage_stats.start()
        try:
            mod._run(run_dir)
        finally:
            _usage_stats.end()
            end_time = time.time()
            duration = end_time - start_time
            formatted_duration = str(timedelta(seconds=int(duration)))
            print("-" * 30)
            print("Pipeline Execution Complete.")
            print(f"Total Duration: {formatted_duration} ({duration:.2f} seconds)")
            print("-" * 30)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "manifest",
        type=Path,
        help="JSON file listing issue JSON paths (array or {issues: [...]})",
    )
    ap.add_argument(
        "--script",
        default=DEFAULT_SCRIPT,
        help=f"Pipeline script to run for each issue (default: {DEFAULT_SCRIPT}), "
        "e.g. exp/end-end-agentless-ablation.py",
    )
    ap.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Run remaining issues after a failure (default: stop on first error).",
    )
    args = ap.parse_args()

    root = _project_root()
    manifest_path = args.manifest.resolve()
    if not manifest_path.is_file():
        print(f"manifest not found: {manifest_path}", file=sys.stderr)
        sys.exit(2)

    with open(manifest_path, encoding="utf-8") as f:
        paths = _parse_manifest(json.load(f))

    mod = _load_end_end_module(args.script)
    print(f"[batch] pipeline script: {mod.__file__}")
    failed: list[tuple[str, BaseException]] = []

    for rel in paths:
        issue_json = (root / rel).resolve() if not Path(rel).is_absolute() else Path(rel).resolve()
        if not issue_json.is_file():
            err = FileNotFoundError(f"missing issue JSON: {issue_json}")
            if args.continue_on_error:
                failed.append((rel, err))
                print(f"[batch] skip (not found): {issue_json}", file=sys.stderr)
                continue
            raise err

        print(f"\n{'=' * 60}\n[batch] issue JSON: {issue_json}\n{'=' * 60}\n")
        try:
            _run_one_issue(mod, issue_json)
        except SystemExit as e:
            if e.code not in (0, None):
                if args.continue_on_error:
                    failed.append((rel, e))
                    continue
                raise
        except Exception as e:
            if args.continue_on_error:
                failed.append((rel, e))
                print(f"[batch] error: {e}", file=sys.stderr)
                continue
            raise
        finally:
            # Remove this issue's tagged build image (``docker system prune -f`` keeps tagged images)
            _remove_issue_image(mod, issue_json)
            # Clean up dangling Docker images/containers to prevent disk exhaustion
            print("[batch] Running 'docker system prune -f' to clean up artifacts...")
            try:
                subprocess.run(["docker", "system", "prune", "-f"], check=False)
            except Exception as cleanup_err:
                print(f"[batch] Warning: Docker cleanup failed: {cleanup_err}", file=sys.stderr)

    if failed:
        print(f"\n[batch] completed with {len(failed)} failure(s):", file=sys.stderr)
        for rel, err in failed:
            print(f"  - {rel}: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

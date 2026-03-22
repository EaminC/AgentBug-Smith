"""Run output directory, tee logging, and artifact copies for ``exp/end-end.py``."""

from __future__ import annotations

import json
import shutil
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional, TextIO


def create_run_result_dir(project_root: Path | str, issue_json_path: Path | str) -> Path:
    """Create ``result/<issue_stem>_<utc>/`` and return it."""
    root = Path(project_root).resolve()
    ij = Path(issue_json_path).resolve()
    stem = ij.stem
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = root / "result" / f"{stem}_{ts}"
    out.mkdir(parents=True, exist_ok=True)
    return out


DEFAULT_RUN_LOG_NAME = "run.log"


@contextmanager
def result_run_with_tee(
    project_root: Path | str,
    issue_json_path: Path | str,
    *,
    log_name: str = DEFAULT_RUN_LOG_NAME,
    banner: str = "[run] result dir:",
) -> Iterator[Path]:
    """
    Create the run directory, tee ``sys.stdout`` / ``sys.stderr`` to ``<run_dir>/<log_name>``,
    print a one-line banner, yield ``run_dir``, then restore streams and close the log file.
    """
    run_dir = create_run_result_dir(project_root, issue_json_path)
    log_fp = open(run_dir / log_name, "w", encoding="utf-8")
    orig_out, orig_err = sys.stdout, sys.stderr
    sys.stdout = TeeTextStream(orig_out, log_fp)
    sys.stderr = TeeTextStream(orig_err, log_fp)
    try:
        print(f"{banner} {run_dir}", flush=True)
        yield run_dir
    finally:
        sys.stdout = orig_out
        sys.stderr = orig_err
        log_fp.close()


class TeeTextStream:
    """Write to two text streams (e.g. console + log file)."""

    def __init__(self, primary: TextIO, secondary: TextIO) -> None:
        self._primary = primary
        self._secondary = secondary

    def isatty(self) -> bool:
        """Delegate so libraries that gate on TTY (color, progress) still see the real console."""
        p = self._primary
        if hasattr(p, "isatty"):
            return bool(p.isatty())
        return False

    def fileno(self) -> int:
        p = self._primary
        if hasattr(p, "fileno"):
            return int(p.fileno())
        raise OSError("underlying stream has no fileno()")

    @property
    def encoding(self) -> str:
        enc = getattr(self._primary, "encoding", None)
        return enc if isinstance(enc, str) else "utf-8"

    def writable(self) -> bool:
        return True

    def write(self, s: str) -> int:
        self._primary.write(s)
        self._secondary.write(s)
        self._primary.flush()
        self._secondary.flush()
        return len(s)

    def flush(self) -> None:
        self._primary.flush()
        self._secondary.flush()


def append_text(path: Path, title: str, body: str) -> None:
    sep = "\n" + ("=" * 72) + "\n"
    with open(path, "a", encoding="utf-8") as f:
        f.write(sep)
        f.write(title.rstrip() + "\n")
        f.write(body.rstrip() + ("\n" if body and not body.endswith("\n") else ""))


def write_summary_json(
    path: Path,
    *,
    issue_json_path: Path,
    run_dir: Path,
    f2p_succeeded: bool,
    extra: Optional[dict[str, Any]] = None,
) -> None:
    data: dict[str, Any] = {
        "issue_json": str(issue_json_path.resolve()),
        "run_dir": str(run_dir.resolve()),
        "f2p_succeeded": f2p_succeeded,
    }
    if extra:
        data.update(extra)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def finalize_run_artifacts(
    run_dir: Path,
    *,
    issue_json_path: Path,
    repo_root: Path,
    dockerfile_relpath: str,
    test_relpath: str,
) -> None:
    """Copy issue JSON, Dockerfile, and generated test (if present) into ``run_dir``."""
    run_dir = run_dir.resolve()
    ij = Path(issue_json_path).resolve()
    rr = Path(repo_root).resolve()

    shutil.copy2(ij, run_dir / ij.name)

    df = rr / dockerfile_relpath
    if df.is_file():
        shutil.copy2(df, run_dir / Path(dockerfile_relpath).name)

    tf = rr / test_relpath.replace("\\", "/")
    if tf.is_file():
        shutil.copy2(tf, run_dir / Path(test_relpath).name)


__all__ = [
    "DEFAULT_RUN_LOG_NAME",
    "TeeTextStream",
    "append_text",
    "create_run_result_dir",
    "finalize_run_artifacts",
    "result_run_with_tee",
    "write_summary_json",
]

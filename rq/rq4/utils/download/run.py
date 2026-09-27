"""Download the AgentBug-Smith ``all_combined_f2p`` dataset via sparse
git-checkout. We only pull the target subdirectory — no auth needed.

Usage::

    python utils/download/run.py --out data/raw

We clone the repo with --depth 1 --filter=blob:none --sparse, then
``git sparse-checkout set`` the requested subdirectory. Result lives at
``<out>/<remote_subdir>``.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def _run(cmd: list[str], cwd: Path | None = None) -> None:
    """Run ``cmd``, echoing it, raising on failure."""
    print(f"$ {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, cwd=cwd, check=True)


def download(repo: str, remote_subdir: str, out: Path) -> Path:
    """Sparse-checkout ``remote_subdir`` from ``repo`` into ``out``.

    Returns the local directory containing the dataset.
    """
    if not shutil.which("git"):
        sys.exit("git is required on PATH")

    out.mkdir(parents=True, exist_ok=True)
    work = out / ".sparse-clone"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir()

    # Initialize empty repo and add the remote.
    _run(["git", "init", "-q"], cwd=work)
    _run(["git", "remote", "add", "origin", f"https://github.com/{repo}.git"], cwd=work)
    # Configure sparse-checkout BEFORE fetching so we only pull what we need.
    _run(["git", "config", "core.sparseCheckout", "true"], cwd=work)
    (work / ".git" / "info" / "sparse-checkout").write_text(remote_subdir + "\n")
    # --depth 1   : only the latest commit
    # --filter=blob:none : fetch blobs on demand (this is what makes it small)
    _run(["git", "fetch", "--depth=1", "--filter=blob:none", "origin", "HEAD"], cwd=work)
    _run(["git", "checkout", "FETCH_HEAD"], cwd=work)

    # Move the subdirectory out of the bare clone so callers see a clean path.
    src = work / remote_subdir
    if not src.is_dir():
        sys.exit(f"sparse-checkout did not produce {src}")
    final = out / remote_subdir
    if final.exists():
        shutil.rmtree(final)
    shutil.move(str(src), str(final))
    shutil.rmtree(work)

    issue_dirs = [p for p in final.iterdir() if p.is_dir()]
    print(f"Downloaded {len(issue_dirs)} issue directories to {final}")
    return final


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", default="EaminC/AgentBug-Smith")
    p.add_argument("--remote-subdir", default="results/all_combined_f2p")
    p.add_argument("--out", type=Path, default=Path("data/raw"),
                   help="Directory under which <remote-subdir> will be created.")
    args = p.parse_args()
    download(args.repo, args.remote_subdir, args.out)


if __name__ == "__main__":
    main()

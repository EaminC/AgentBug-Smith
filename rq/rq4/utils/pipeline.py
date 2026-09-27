"""End-to-end pipeline: download → classify → split.

Usage::

    python utils/pipeline.py [--train-size 40] [--limit N]
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Make sibling utils/* importable as plain modules.
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from download import run as download_mod  # type: ignore
from classify import run as classify_mod  # type: ignore
from split import run as split_mod  # type: ignore


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    p.add_argument("--index", type=Path, default=Path("data/index.jsonl"))
    p.add_argument("--splits-dir", type=Path, default=Path("data/splits/default"))
    p.add_argument("--train-size", type=int, default=40)
    p.add_argument("--limit", type=int, default=None,
                   help="Cap on issues to classify (smoke-test knob).")
    p.add_argument("--model", default=os.environ.get("DEFAULT_MODEL",
                                                    "gpt-4.1-mini"))
    p.add_argument("--skip-download", action="store_true")
    p.add_argument("--skip-classify", action="store_true")
    p.add_argument("--skip-split", action="store_true")
    args = p.parse_args()

    # 1. Download
    if not args.skip_download:
        subdir = "results/all_combined_f2p"
        final = download_mod.download("EaminC/AgentBug-Smith", subdir,
                                      args.raw_dir)
    else:
        # Try to locate the existing download.
        candidates = list(args.raw_dir.glob("*/"))
        if not candidates:
            sys.exit(f"--skip-download but {args.raw_dir} is empty")
        final = candidates[0]
        print(f"Using existing download at {final}")

    # 2. Classify
    if not args.skip_classify:
        # Build argv for classify/run.py so we don't depend on a subprocess.
        ns = argparse.Namespace(
            inp=final,
            out=args.index,
            taxonomy=Path("docs/taxonomy.md"),
            model=args.model,
            base_url="https://api.tu-zi.com/v1",
            api_key=os.environ.get("TUZI_API_KEY"),
            concurrency=8,
            max_retries=3,
            limit=args.limit,
        )
        # Re-route argv because classify uses argparse.
        saved_argv = sys.argv
        sys.argv = ["classify"]  # dummy program name
        try:
            classify_mod.main.__wrapped__ if hasattr(classify_mod.main, "__wrapped__") else None  # noqa
        except Exception:
            pass
        # Call main() directly with patched sys.argv. Easiest is to mimic
        # parse_args by setting sys.argv and calling main().
        sys.argv = ["classify"] + [
            "--in", str(ns.inp),
            "--out", str(ns.out),
            "--taxonomy", str(ns.taxonomy),
            "--model", ns.model,
            "--base-url", ns.base_url,
            "--api-key", ns.api_key or "",
            "--concurrency", str(ns.concurrency),
            "--max-retries", str(ns.max_retries),
        ]
        if ns.limit:
            sys.argv += ["--limit", str(ns.limit)]
        classify_mod.main()
        sys.argv = saved_argv

    # 3. Split
    if not args.skip_split:
        sys.argv = ["split", "--index", str(args.index),
                    "--out", str(args.splits_dir),
                    "--train-size", str(args.train_size)]
        split_mod.main()

    print("Pipeline complete.")


if __name__ == "__main__":
    main()

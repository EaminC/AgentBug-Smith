#!/usr/bin/env python3
"""
Generate swe-factory judge_fail2pass.py compatible folders from RepoLaunch outputs.

Input: a jsonl where each row contains at least:
  - instance_id
  - docker_image
  - rebuild_cmds (list[str])
  - test_cmds (list[str])
  - test_patch (git diff text)
  - patch (git diff text)  # gold/solution patch

For each instance we will run:
  prev_apply: apply test_patch only -> rebuild -> run tests -> write OMNIGRIL_EXIT_CODE marker
  after_apply: apply test_patch + patch -> rebuild -> run tests -> write marker

Outputs (per instance_id under --out-dir):
  - test_output_prev_apply.txt
  - test_output_after_apply.txt

Then you can run:
  python /home/cc/swe-factory/scripts/judge_fail2pass.py <out-dir> <summary.json>
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Literal


# Make "launch" importable when running from repo root.
sys.path.insert(0, os.path.join(os.getcwd(), "launch"))
from launch.core.runtime import SetupRuntime  # noqa: E402
from launch.scripts.parser import run_parser  # noqa: E402


PREV_FILE_NAME = "test_output_prev_apply.txt"
AFTER_FILE_NAME = "test_output_after_apply.txt"


def _join_cmds(cmds: Any) -> str:
    if cmds is None:
        return ""
    if isinstance(cmds, str):
        return cmds.strip()
    if isinstance(cmds, list):
        parts = []
        for c in cmds:
            if c is None:
                continue
            s = str(c).strip()
            if s:
                parts.append(s)
        return " ; ".join(parts)
    return str(cmds).strip()


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            s = line.strip()
            if not s:
                continue
            try:
                out.append(json.loads(s))
            except json.JSONDecodeError as e:
                raise SystemExit(f"Invalid JSON on line {lineno} of {path}: {e}") from e
    return out


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", errors="ignore")


def _run_one(
    instance: dict[str, Any],
    platform: Literal["linux", "windows"],
    out_dir: Path,
    timeout_s: int,
    overwrite: bool,
) -> tuple[str, str | None]:
    instance_id = str(instance.get("instance_id") or "")
    if not instance_id:
        return "error", "missing instance_id"

    inst_out = out_dir / instance_id
    prev_path = inst_out / PREV_FILE_NAME
    after_path = inst_out / AFTER_FILE_NAME

    if (not overwrite) and prev_path.exists() and after_path.exists():
        return "skip", None

    image = instance.get("docker_image") or instance.get("image")
    if not image:
        return "error", "missing docker_image"

    rebuild_cmd = _join_cmds(instance.get("rebuild_cmds"))
    test_cmd = _join_cmds(instance.get("test_cmds"))
    print_cmd = _join_cmds(instance.get("print_cmds"))
    parser = instance.get("log_parser", instance.get("parser", "")) or ""
    test_patch = str(instance.get("test_patch") or "")
    patch = str(instance.get("patch") or "")

    if not test_cmd:
        return "error", "missing test_cmds"
    if not print_cmd:
        return "error", "missing print_cmds (needed to judge pass/fail)"
    if not str(parser).strip():
        return "error", "missing log_parser/parser (needed to judge pass/fail)"

    def run_variant(label: str, apply_solution: bool) -> str:
        container = SetupRuntime.from_launch_image(
            image,
            instance_id,
            platform,
            command_timeout=timeout_s,
        )
        try:
            if test_patch.strip():
                container.apply_patch(test_patch, verbose=True)
            if apply_solution and patch.strip():
                container.apply_patch(patch, verbose=True)
            if rebuild_cmd:
                container.send_command(rebuild_cmd)
            # Run tests (may be wrapped with '|| true' in organize.jsonl).
            container.send_command(test_cmd)
            # Fetch raw log and parse pass/fail.
            res = container.send_command(print_cmd)
            raw = res.output if hasattr(res, "output") else str(res)
            status_map = run_parser(str(parser), raw)
            has_fail = any(str(v).lower() == "fail" for v in status_map.values())
            # judge_fail2pass.py expects literal "echo OMNIGRIL_EXIT_CODE=<n>"
            exit_code = 1 if has_fail else 0
            return raw.rstrip() + "\n" + f"echo OMNIGRIL_EXIT_CODE={exit_code}\n"
        finally:
            try:
                container.cleanup()
            except Exception:
                pass

    try:
        prev_out = run_variant("prev", apply_solution=False)
        after_out = run_variant("after", apply_solution=True)
        _write_text(prev_path, prev_out)
        _write_text(after_path, after_out)
        return "ok", None
    except Exception as e:
        # Best effort: still write something to help debugging.
        inst_out.mkdir(parents=True, exist_ok=True)
        _write_text(inst_out / "error.txt", f"{type(e).__name__}: {e}\n")
        return "error", f"{type(e).__name__}: {e}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--input",
        default="launch/data/sbl_baseline/organize.jsonl",
        help="Input jsonl (organize.jsonl or validated_instances.jsonl).",
    )
    ap.add_argument(
        "--out-dir",
        default="baseline/sf_judge_f2p_outputs",
        help="Output directory containing per-instance subdirs.",
    )
    ap.add_argument("--platform", default="linux", choices=["linux", "windows"])
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--timeout-s", type=int, default=90 * 60)
    ap.add_argument("--overwrite", type=int, default=0)
    ap.add_argument("--limit", type=int, default=-1, help="Only process first N instances if >0.")
    args = ap.parse_args()

    in_path = Path(args.input).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve()
    overwrite = args.overwrite != 0

    if not in_path.exists():
        raise SystemExit(f"Input not found: {in_path}")

    instances = _load_jsonl(in_path)
    if args.limit and args.limit > 0:
        instances = instances[: args.limit]

    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Loaded {len(instances)} instances from {in_path}")
    print(f"Writing judge-compatible outputs to {out_dir}")

    ok = skip = err = 0
    with ThreadPoolExecutor(max_workers=max(1, int(args.workers))) as ex:
        futs = [
            ex.submit(_run_one, inst, args.platform, out_dir, int(args.timeout_s), overwrite)
            for inst in instances
        ]
        for fut in as_completed(futs):
            status, msg = fut.result()
            if status == "ok":
                ok += 1
            elif status == "skip":
                skip += 1
            else:
                err += 1
                if msg:
                    print(f"[error] {msg}", file=sys.stderr)

    print(f"Done. ok={ok} skip={skip} error={err}")


if __name__ == "__main__":
    main()
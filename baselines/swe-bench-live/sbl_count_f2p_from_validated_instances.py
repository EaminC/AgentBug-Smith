#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class Row:
    instance_id: str
    fail_to_pass: list[str]
    pass_to_pass: list[str]


def _iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            s = line.strip()
            if not s:
                continue
            try:
                yield json.loads(s)
            except json.JSONDecodeError as e:
                raise SystemExit(f"Invalid JSON on line {lineno} of {path}: {e}") from e


def _coerce_list_str(x: Any) -> list[str]:
    if x is None:
        return []
    if isinstance(x, list):
        out: list[str] = []
        for v in x:
            if v is None:
                continue
            out.append(str(v))
        return out
    return [str(x)]


def _parse_row(obj: dict[str, Any]) -> Row:
    instance_id = obj.get("instance_id")
    if not instance_id:
        raise SystemExit("Missing 'instance_id' in a validated_instances row.")
    return Row(
        instance_id=str(instance_id),
        fail_to_pass=_coerce_list_str(obj.get("FAIL_TO_PASS")),
        pass_to_pass=_coerce_list_str(obj.get("PASS_TO_PASS")),
    )


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            "Count F2P instances from SWE-bench-Live evaluation.validation output "
            "(validated_instances.jsonl)."
        )
    )
    ap.add_argument(
        "--input",
        default="logs/val/validated_instances.jsonl",
        help="Path to validated_instances.jsonl (default: logs/val/validated_instances.jsonl)",
    )
    ap.add_argument(
        "--top-n",
        type=int,
        default=20,
        help="Show top N instances by FAIL_TO_PASS size (default: 20)",
    )
    ap.add_argument(
        "--output-json",
        default="",
        help="Optional output report path (JSON). If empty, do not write.",
    )
    args = ap.parse_args()

    in_path = Path(args.input).expanduser().resolve()
    if not in_path.exists():
        raise SystemExit(f"Input not found: {in_path}")

    rows: list[Row] = []
    for obj in _iter_jsonl(in_path):
        rows.append(_parse_row(obj))

    total = len(rows)
    f2p_rows = [r for r in rows if len(r.fail_to_pass) > 0]
    f2p_count = len(f2p_rows)

    f2p_sizes = [len(r.fail_to_pass) for r in f2p_rows]
    ptp_sizes = [len(r.pass_to_pass) for r in rows]

    size_counter = Counter(f2p_sizes)
    top_n = max(0, int(args.top_n))
    top = sorted(((r.instance_id, len(r.fail_to_pass)) for r in f2p_rows), key=lambda x: (-x[1], x[0]))[:top_n]

    report = {
        "input": str(in_path),
        "total_instances": total,
        "f2p_instances": f2p_count,
        "f2p_ratio": (f2p_count / total) if total else 0.0,
        "f2p_size_histogram": dict(sorted(size_counter.items(), key=lambda kv: kv[0])),
        "top_f2p_instances": [{"instance_id": iid, "fail_to_pass_count": n} for iid, n in top],
        "ptp_counts": {
            "min": min(ptp_sizes) if ptp_sizes else 0,
            "max": max(ptp_sizes) if ptp_sizes else 0,
        },
    }

    print(json.dumps(report, ensure_ascii=False, indent=2))

    if args.output_json:
        out_path = Path(args.output_json).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()


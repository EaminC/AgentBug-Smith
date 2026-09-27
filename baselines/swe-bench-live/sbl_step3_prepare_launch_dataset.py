#!/usr/bin/env python3
"""
Step3 preparation helper:

Input:
  baseline/sbl_inputs/**/tasks/*-task-instances.jsonl
  (we only take non-empty files, i.e., instances that have test_patch)

Output:
  - baseline/sbl_task_instances_with_tests.jsonl
      Merged task instances (one JSON per line), with an added "language" field.
      Extra fields are kept; RepoLaunch should ignore what it doesn't need.
  - launch/data/sbl_baseline/dataset.jsonl
      Same content as above, stored where RepoLaunch expects it.
  - launch/data/sbl_baseline/config.json
      A ready-to-run RepoLaunch config (edit model/provider if needed).
  - baseline/sbl_step3_prepare_report.json
      Summary of what was included and the inferred language per instance.

Language inference:
  We infer language by looking at file extensions in diff headers inside "patch" and "test_patch".
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any
import os


DIFF_PATH_RE = re.compile(r"^diff --git a/(.*?) b/.*?$", re.MULTILINE)


EXT_TO_LANG = {
    ".py": "Python",
    ".ipynb": "Python",
    ".js": "JS/TS",
    ".jsx": "JS/TS",
    ".ts": "JS/TS",
    ".tsx": "JS/TS",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".kt": "Java",
    ".cs": "C#",
    ".c": "C",
    ".h": "C",
    ".cc": "C++",
    ".cpp": "C++",
    ".cxx": "C++",
    ".hpp": "C++",
    ".hh": "C++",
}


def infer_language_from_diff_text(*diff_texts: str) -> tuple[str, dict[str, int]]:
    exts: Counter[str] = Counter()
    for txt in diff_texts:
        if not txt:
            continue
        for p in DIFF_PATH_RE.findall(txt):
            # strip quotes/spaces just in case
            p = p.strip().strip('"').strip("'")
            suffix = Path(p).suffix.lower()
            if suffix:
                exts[suffix] += 1

    # Map ext counts to language counts.
    lang_counts: Counter[str] = Counter()
    for ext, n in exts.items():
        lang = EXT_TO_LANG.get(ext)
        if lang:
            lang_counts[lang] += n

    if not lang_counts:
        # Last resort fallback.
        return "Python", dict(exts)

    best_lang = lang_counts.most_common(1)[0][0]
    return best_lang, dict(exts)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    baseline_dir = repo_root / "baseline"
    sbl_inputs = baseline_dir / "sbl_inputs"
    if not sbl_inputs.exists():
        raise SystemExit(f"Not found: {sbl_inputs} (did you run step2?)")

    task_files = sorted(sbl_inputs.glob("*/tasks/*-task-instances.jsonl"))
    non_empty = [p for p in task_files if p.exists() and p.stat().st_size > 0]

    merged_instances: list[dict[str, Any]] = []
    report_instances: list[dict[str, Any]] = []

    for p in non_empty:
        instances = load_jsonl(p)
        for inst in instances:
            lang, ext_counts = infer_language_from_diff_text(
                inst.get("patch", ""), inst.get("test_patch", "")
            )
            inst = dict(inst)
            inst.setdefault("created_at", inst.get("created_at") or "")
            inst["language"] = lang
            merged_instances.append(inst)
            report_instances.append(
                {
                    "instance_id": inst.get("instance_id"),
                    "repo": inst.get("repo"),
                    "pull_number": inst.get("pull_number"),
                    "language": lang,
                    "ext_counts": ext_counts,
                    "source_file": str(p.relative_to(repo_root)),
                }
            )

    merged_out = baseline_dir / "sbl_task_instances_with_tests.jsonl"
    merged_out.write_text(
        "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in merged_instances),
        encoding="utf-8",
    )

    launch_data_dir = repo_root / "launch" / "data" / "sbl_baseline"
    launch_data_dir.mkdir(parents=True, exist_ok=True)
    (launch_data_dir / "dataset.jsonl").write_text(
        merged_out.read_text(encoding="utf-8"), encoding="utf-8"
    )

    # Write a runnable RepoLaunch config (based on launch/data/examples/config.json).
    #
    # NOTE: some OpenAI-compatible endpoints require a provider-prefixed model id
    # (e.g. "tensorblock/gpt-4.1"). We detect that case to avoid a silent 400 loop.
    base_url = os.getenv("OPENAI_BASE_URL", "") or ""
    default_model = "tensorblock/gpt-4.1-mini"


    config = {
        "mode": {"setup": True, "organize": True},
        "llm_provider_name": "OpenAI",
        "model_config": {"model_name": default_model, "temperature": 0.0},
        "workspace_root": "data/sbl_baseline/",
        "dataset": "data/sbl_baseline/dataset.jsonl",
        "print_to_console": False,
        "first_N_repos": -1,
        "overwrite": False,
        "max_workers": 4,
        "os": "linux",
        "max_trials": 2,
        "max_steps_setup": 60,
        "max_steps_verify": 20,
        "max_steps_organize": 40,
        "cmd_timeout": 60,
        "image_prefix": "repolaunch/dev",
    }
    (launch_data_dir / "config.json").write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    report = {
        "task_files_total": len(task_files),
        "task_files_non_empty": len(non_empty),
        "instances_merged": len(merged_instances),
        "merged_output": str(merged_out.relative_to(repo_root)),
        "launch_dataset": str((launch_data_dir / "dataset.jsonl").relative_to(repo_root)),
        "launch_config": str((launch_data_dir / "config.json").relative_to(repo_root)),
        "instances": report_instances,
        "next_commands": [
            "cd launch",
            "export OPENAI_API_KEY=...  # required by RepoLaunch",
            "export TAVILY_API_KEY=...  # required by RepoLaunch",
            "python -m launch.run --config-path data/sbl_baseline/config.json",
        ],
    }
    (baseline_dir / "sbl_step3_prepare_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(f"Merged {len(merged_instances)} instances -> {merged_out}")
    print("Next (RepoLaunch / step3):")
    for c in report["next_commands"]:
        print(c)


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Generate SWE-bench-Live curation entry files from `baseline/issue_pr_map.json`.

Input (JSON):
[
  {"repo": "owner/name", "issue_number": 123, "pr_number": 456},
  ...
]

Output (grouped by repo):
baseline/sbl_inputs/<owner>__<name>/prs/<name>-pull2issue-<cutoff>.jsonl
baseline/sbl_inputs/<owner>__<name>/tasks/   (empty dir; later filled by get_tasks_pipeline.py)

Purpose:
If you already know (repo, issue, PR), you can enter the pipeline directly at
"Issue-PR Pairs Crawling (task instance creation)".
We pre-create the pull2issue file so the crawler skips PR→issue discovery and
fetches only the PRs you listed.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def _shell_join(argv: list[str]) -> str:
    out: list[str] = []
    for a in argv:
        if any(c in a for c in [' ', '\t', '\n', '"', "'", "\\", "$", "&", "|", "(", ")", "<", ">", ";"]):
            out.append("'" + a.replace("'", "'\"'\"'") + "'")
        else:
            out.append(a)
    return " ".join(out)


def _repo_root_from_here() -> Path:
    # This file lives in SWE-bench-Live/baseline/, so repo root is its parent.
    return Path(__file__).resolve().parents[1]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--input",
        default=str(_repo_root_from_here() / "baseline" / "issue_pr_map.json"),
        help="Path to baseline/issue_pr_map.json",
    )
    ap.add_argument(
        "--out_root",
        default=str(_repo_root_from_here() / "baseline" / "sbl_inputs"),
        help="Where to write per-repo inputs (default: baseline/sbl_inputs).",
    )
    ap.add_argument(
        "--cutoff_date",
        default="20090101",
        help="Cutoff date string used by SWE-bench-Live file naming (YYYYMMDD). Should be <= PR close date.",
    )
    ap.add_argument(
        "--gh_token_file",
        default="tokens.txt",
        help="Token file path used by get_tasks_pipeline.py (one token per line).",
    )
    ap.add_argument(
        "--token_id",
        type=int,
        default=0,
        help="Which token id to use (0-based) for get_tasks_pipeline.py.",
    )
    args = ap.parse_args()

    repo_root = _repo_root_from_here()
    pipeline_py = repo_root / "curation" / "swe_task_crawling" / "get_tasks_pipeline.py"
    if not pipeline_py.exists():
        raise SystemExit(f"Cannot find pipeline script at: {pipeline_py}")

    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"Input not found: {input_path}")

    items = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(items, list):
        raise SystemExit("Input JSON must be a list.")

    # repo -> pr -> [issues...]
    repo_pr_issues: dict[str, dict[int, list[int]]] = defaultdict(lambda: defaultdict(list))
    for it in items:
        if not isinstance(it, dict):
            continue
        repo = it.get("repo")
        issue = it.get("issue_number")
        pr = it.get("pr_number")
        if not repo or issue is None or pr is None:
            raise SystemExit(f"Bad entry (need repo/issue_number/pr_number): {it}")
        repo_pr_issues[str(repo)][int(pr)].append(int(issue))

    out_root = Path(args.out_root)
    out_root.mkdir(parents=True, exist_ok=True)

    repos_sorted = sorted(repo_pr_issues.keys())
    print("Prepared pull2issue files:")
    cmds: list[list[str]] = []

    for repo in repos_sorted:
        owner, name = repo.split("/", 1)
        slug = f"{owner}__{name}"
        prs_dir = out_root / slug / "prs"
        tasks_dir = out_root / slug / "tasks"
        prs_dir.mkdir(parents=True, exist_ok=True)
        tasks_dir.mkdir(parents=True, exist_ok=True)

        pull2issue_path = prs_dir / f"{name}-pull2issue-{args.cutoff_date}.jsonl"
        pr_map = repo_pr_issues[repo]
        with pull2issue_path.open("w", encoding="utf-8") as f:
            for pr_num in sorted(pr_map.keys()):
                issues = sorted(set(pr_map[pr_num]))
                f.write(json.dumps({"pull": pr_num, "issue": issues}) + "\n")

        print(f"- {repo}: {pull2issue_path}")

        cmds.append(
            [
                "python",
                str(pipeline_py),
                "--repos",
                repo,
                "--gh_token_file",
                args.gh_token_file,
                "--token_ids",
                str(args.token_id),
                "--path_prs",
                str(prs_dir),
                "--path_tasks",
                str(tasks_dir),
                "--cutoff_date",
                args.cutoff_date,
            ]
        )

    print("\nNext: run SWE-bench-Live task crawling (per repo):")
    for cmd in cmds:
        print(_shell_join(cmd))


if __name__ == "__main__":
    main()
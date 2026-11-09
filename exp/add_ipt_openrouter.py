#!/usr/bin/env python3
"""Fill missing in-patch tests with one OpenRouter call per issue.

Accepts one directory, several directories, or a list of JSON files. Issues
whose ``linked_prs[0].test_paths_in_patch`` is already non-empty are copied
as-is. The rest are sent to OpenRouter together with one real with-IPT sample
(default ``issue_1222.json``). The model returns a unified diff for a new
test file; this script appends that diff to the existing gold ``patch`` and
sets ``test_paths_in_patch``, leaving every other field unchanged.

A flat directory is written to ``<name>_ipt/``. Nested or multiple inputs keep
their directory names so files like ``issue_56.json`` do not overwrite each
other. Each run also writes ``ipt_fill_log.jsonl``.

Usage (from the AgentBug-Smith repo root)::

    export OPENROUTER_API_KEY=...
    python exp/add_ipt_openrouter.py
    python exp/add_ipt_openrouter.py --limit 1
    python exp/add_ipt_openrouter.py data/issues/issues_80 data/issues/issue_run_new
    python exp/add_ipt_openrouter.py a.json b.json --output /tmp/ipt_out
    bash exp/add_ipt_batch.sh data/issues/issues_80 data/issues/issue_run_new
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "issues" / "issues_80"
DEFAULT_SAMPLE = DEFAULT_INPUT / "issue_1222.json"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-4.1-mini"


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _read_issue(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _test_paths(issue: dict) -> list:
    prs = issue.get("linked_prs") or []
    if not prs or not isinstance(prs[0], dict):
        return []
    paths = prs[0].get("test_paths_in_patch") or []
    return [p for p in paths if isinstance(p, str) and p.strip()]


def _truncate(text: object, limit: int) -> str:
    if not isinstance(text, str):
        return ""
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...[truncated]...\n"


def _test_diffs(patch: str) -> str:
    """Keep diff chunks whose path looks like a test file."""
    chunks = re.split(r"(?=^diff --git )", patch, flags=re.M)
    kept = []
    for chunk in chunks:
        header = chunk.splitlines()[0] if chunk.strip() else ""
        if re.search(r"(^|/)(test|tests|testing)(/|_|\.)", header, re.I):
            kept.append(chunk.strip())
    return "\n".join(kept)


def _sample_payload(issue: dict) -> dict:
    pr = (issue.get("linked_prs") or [{}])[0]
    patch = pr.get("patch") if isinstance(pr, dict) else ""
    return {
        "number": issue.get("number"),
        "title": issue.get("title"),
        "url": issue.get("url"),
        "test_paths_in_patch": _test_paths(issue),
        "test_diff_in_patch": _truncate(_test_diffs(patch or ""), 4000),
    }


def _target_payload(issue: dict) -> dict:
    pr = (issue.get("linked_prs") or [{}])[0]
    return {
        "number": issue.get("number"),
        "title": issue.get("title"),
        "url": issue.get("url"),
        "body": _truncate(issue.get("body"), 2500),
        "patch": _truncate(pr.get("patch") if isinstance(pr, dict) else "", 5000),
        "existing_test_paths": issue.get("existing_test_paths") or [],
    }


def _extract_json(text: str) -> dict:
    text = (text or "").strip()
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fenced:
        text = fenced.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("model did not return a JSON object")
    data = json.loads(text[start : end + 1])
    if not isinstance(data, dict):
        raise ValueError("model JSON is not an object")
    return data


def _call_openrouter(api_key: str, model: str, system: str, user: str) -> str:
    body = json.dumps(
        {
            "model": model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        OPENROUTER_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/EaminC/AgentBug-Smith",
            "X-Title": "AgentBug-Smith IPT fill",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenRouter HTTP {exc.code}: {detail[:500]}") from exc
    return payload["choices"][0]["message"]["content"] or ""


SYSTEM = """You add one in-patch test to a GitHub issue whose linked PR patch has no test file.
Follow the sample: the dataset field test_paths_in_patch lists the test file, and the gold patch contains a unified diff for that file.
Return JSON only, no markdown:
{
  "test_relpath": "tests/....py",
  "test_diff": "diff --git a/tests/....py b/tests/....py\\n..."
}
Rules:
- test_relpath must contain "test" and use forward slashes.
- test_diff is a new-file unified diff (--- /dev/null) for exactly that path.
- The test should fail on the buggy code described by the issue and pass after the existing gold patch. Keep it short.
- Match the language of the patched source files. Use pytest for Python.
- Do not repeat or edit the existing gold patch. Only return the new test diff.
"""


def _validate(result: dict, issue_number: object) -> tuple[str, str]:
    rel = str(result.get("test_relpath") or "").strip().replace("\\", "/")
    diff = str(result.get("test_diff") or "").strip()
    if not rel or "test" not in rel.lower():
        raise ValueError(f"bad test_relpath: {rel!r}")
    if not diff.startswith("diff --git "):
        raise ValueError("test_diff is not a unified diff")
    if rel not in diff:
        raise ValueError(f"test_diff does not mention {rel}")
    if not diff.endswith("\n"):
        diff += "\n"
    if f"issue_{issue_number}" not in rel and not rel.endswith(".py"):
        pass
    return rel, diff


def _apply(issue: dict, rel: str, diff: str) -> dict:
    updated = json.loads(json.dumps(issue))
    pr = updated["linked_prs"][0]
    patch = pr.get("patch") or ""
    if patch and not patch.endswith("\n"):
        patch += "\n"
    pr["patch"] = patch + diff
    pr["test_paths_in_patch"] = [rel]
    return updated


def _write(path: Path, issue: dict) -> None:
    path.write_text(json.dumps(issue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _json_files(path: Path) -> list[Path]:
    if path.is_file() and path.suffix == ".json":
        return [path]
    if not path.is_dir():
        print(f"[skip] not found: {path}", file=sys.stderr)
        return []
    found = []
    for item in sorted(path.rglob("*.json")):
        if any(part.endswith("_ipt") or part == "ipt_batch" for part in item.parts):
            continue
        found.append(item)
    return found


def _output_path(src: Path, root: Path | None, dst: Path, flat: bool) -> Path:
    if flat:
        return dst / src.name
    if root is None:
        return dst / src.parent.name / src.name
    return dst / root.name / src.relative_to(root)


def main() -> None:
    _load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path, help="JSON files or directories. Default: data/issues/issues_80")
    parser.add_argument("--input", action="append", type=Path, default=None, help="Extra directory or JSON. Repeatable.")
    parser.add_argument("--list", type=Path, default=None, help="Text file with one JSON or directory path per line.")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--sample", type=Path, default=DEFAULT_SAMPLE)
    parser.add_argument("--model", default=os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL))
    parser.add_argument("--limit", type=int, default=0, help="Max issues without IPT to rewrite. 0 means all.")
    parser.add_argument("--sleep", type=float, default=0.5)
    args = parser.parse_args()

    api_key = (os.getenv("OPENROUTER_API_KEY") or "").strip()
    if not api_key:
        print("Set OPENROUTER_API_KEY.", file=sys.stderr)
        sys.exit(1)

    raw_inputs: list[Path] = list(args.paths)
    if args.input:
        raw_inputs.extend(args.input)
    if args.list:
        for line in args.list.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                raw_inputs.append(Path(line))
    if not raw_inputs:
        raw_inputs = [DEFAULT_INPUT]

    jobs: list[tuple[Path, Path | None]] = []
    seen: set[Path] = set()
    for raw in raw_inputs:
        path = raw.expanduser().resolve()
        root = path if path.is_dir() else None
        for item in _json_files(path):
            item = item.resolve()
            if item in seen:
                continue
            seen.add(item)
            jobs.append((item, root))

    if not jobs:
        print("No JSON files found.", file=sys.stderr)
        sys.exit(1)

    dir_roots = {root for _, root in jobs if root is not None}
    file_parents = {src.parent for src, root in jobs if root is None}
    flat = (not dir_roots and len(file_parents) == 1) or (
        len(dir_roots) == 1
        and not file_parents
        and all(src.parent == next(iter(dir_roots)) for src, _ in jobs)
    )
    if args.output:
        dst = args.output.expanduser().resolve()
    elif flat and dir_roots:
        only = next(iter(dir_roots))
        dst = only.parent / f"{only.name}_ipt"
    elif flat and file_parents:
        only = next(iter(file_parents))
        dst = only.parent / f"{only.name}_ipt"
    else:
        dst = ROOT / "data" / "issues" / "ipt_batch"
    dst.mkdir(parents=True, exist_ok=True)

    sample = _sample_payload(_read_issue(args.sample.resolve()))
    sample_text = json.dumps(sample, ensure_ascii=False, indent=2)

    readable: list[tuple[Path, Path | None, dict]] = []
    for src, root in jobs:
        try:
            issue = _read_issue(src)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[skip] {src.name}: {exc}", file=sys.stderr)
            continue
        if not isinstance(issue, dict) or not issue.get("linked_prs"):
            print(f"[skip] {src.name}: not an issue JSON", file=sys.stderr)
            continue
        readable.append((src, root, issue))

    missing = [(src, root, issue) for src, root, issue in readable if not _test_paths(issue)]
    pending = missing[: args.limit] if args.limit > 0 else missing
    pending_ids = {src for src, _, _ in pending}
    print(
        f"output={dst} total={len(readable)} already_ipt={len(readable) - len(missing)} "
        f"to_fill={len(pending)} model={args.model}"
    )

    log_path = dst / "ipt_fill_log.jsonl"
    filled = 0
    for src, root, issue in readable:
        out = _output_path(src, root, dst, flat)
        label = str(out.relative_to(dst))
        if src not in pending_ids:
            out.parent.mkdir(parents=True, exist_ok=True)
            _write(out, issue)
            continue
        user = (
            "SAMPLE with an in-patch test (follow this shape):\n"
            f"{sample_text}\n\n"
            "ISSUE with no in-patch test. Add one test diff.\n"
            f"{json.dumps(_target_payload(issue), ensure_ascii=False, indent=2)}\n"
        )
        try:
            raw = _call_openrouter(api_key, args.model, SYSTEM, user)
            rel, diff = _validate(_extract_json(raw), issue.get("number"))
            out.parent.mkdir(parents=True, exist_ok=True)
            _write(out, _apply(issue, rel, diff))
            status = "filled"
            filled += 1
            detail = rel
        except Exception as exc:
            out.parent.mkdir(parents=True, exist_ok=True)
            _write(out, issue)
            status = "failed"
            detail = str(exc)
            print(f"[fail] {label}: {exc}", file=sys.stderr)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"file": label, "status": status, "detail": detail}, ensure_ascii=False) + "\n")
        print(f"[{status}] {label} {detail}")
        time.sleep(args.sleep)

    print(f"done filled={filled} log={log_path}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Keep or fill SWE-Factory instances that have no in-patch test.

``build_dataset.py`` writes every valid instance to ``<instances>.all`` and
writes only instances with a non-empty ``test_patch`` to ``<instances>``.
This script rewrites ``<instances>`` from the ``.all`` file:

* ``keep`` — pass empty ``test_patch`` through. The later pipeline still runs.
* ``agentless`` — one LLM call per empty ``test_patch`` (same Forge/OpenAI
  client settings as the rest of this baseline). The reply becomes a new-file
  unified diff under ``tests/``. If the call fails, a one-function placeholder
  is used so the instance is still not dropped.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path


def _load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    text = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
    path.write_text(text, encoding="utf-8")


def _has_test_patch(instance: dict) -> bool:
    patch = instance.get("test_patch")
    return isinstance(patch, str) and bool(patch.strip())


def _strip_fence(text: str) -> str:
    text = (text or "").strip()
    match = re.search(r"```(?:python)?\s*([\s\S]*?)```", text)
    if match:
        return match.group(1).strip()
    return text


def _new_file_diff(relpath: str, content: str) -> str:
    if not content.endswith("\n"):
        content += "\n"
    lines = content.splitlines()
    body = "".join(f"+{line}\n" for line in lines)
    return (
        f"diff --git a/{relpath} b/{relpath}\n"
        "new file mode 100644\n"
        "--- /dev/null\n"
        f"+++ b/{relpath}\n"
        f"@@ -0,0 +1,{len(lines)} @@\n"
        f"{body}"
    )


def _placeholder_test(pull_number: object) -> str:
    return (
        "def test_agentless_ipt_placeholder():\n"
        f'    """Synthetic in-patch test for PR {pull_number}. Not a fail2pass oracle."""\n'
        "    assert True\n"
    )


def _truncate(text: object, limit: int = 6000) -> str:
    if not isinstance(text, str):
        return ""
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...[truncated]...\n"


def _call_llm(system: str, user: str) -> str:
    """One chat completion. Env matches this baseline and ``src/forge/api.py``."""
    api_key = (
        os.getenv("FORGE_API_KEY")
        or os.getenv("OPENAI_KEY")
        or os.getenv("OPENAI_API_KEY")
        or ""
    ).strip()
    base_url = (
        os.getenv("FORGE_BASE_URL")
        or os.getenv("OPENAI_API_BASE_URL")
        or "https://api.forge.tensorblock.co/v1"
    ).strip()
    model = (os.getenv("MODEL") or "gpt-4.1-mini").strip()
    if not api_key:
        raise RuntimeError("FORGE_API_KEY (or OPENAI_KEY) is not set")

    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=base_url, timeout=120)
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
        max_tokens=2048,
    )
    return completion.choices[0].message.content or ""


def _agentless_test_patch(instance: dict) -> tuple[str, str]:
    pull = instance.get("pull_number")
    relpath = f"tests/agentless_ipt_{pull}.py"
    system = (
        "You write one small Python test file so a downstream eval pipeline has an in-patch test. "
        "Return only the test source, no markdown. "
        f"The file will be saved as {relpath}. "
        "Keep it short. A trivial assertion is acceptable when the issue is too vague to test. "
        "Do not modify product code."
    )
    user = (
        f"Repository: {instance.get('repo')}\n"
        f"Pull number: {pull}\n\n"
        "Problem statement:\n"
        f"{_truncate(instance.get('problem_statement'))}\n\n"
        "Gold patch (context only, do not repeat it):\n"
        f"{_truncate(instance.get('patch'))}\n"
    )
    try:
        body = _strip_fence(_call_llm(system, user))
    except Exception as exc:
        print(f"[agentless-ipt] LLM failed for {instance.get('instance_id')}: {exc}", file=sys.stderr)
        body = ""
    if not body.strip() or body.lstrip().startswith("diff --git"):
        body = _placeholder_test(pull)
        source = "placeholder"
    else:
        source = "agentless"
    return _new_file_diff(relpath, body), source


def prepare(mode: str, instances_path: Path) -> None:
    all_path = Path(str(instances_path) + ".all")
    if not all_path.is_file():
        raise SystemExit(f"Missing {all_path}. Run build_dataset.py first.")

    rows = _load_jsonl(all_path)
    filled_llm = 0
    filled_placeholder = 0
    kept_empty = 0
    already = 0
    out_rows: list[dict] = []
    for instance in rows:
        if _has_test_patch(instance):
            already += 1
            out_rows.append(instance)
            continue
        if mode == "keep":
            instance = dict(instance)
            instance["ipt_source"] = "kept_empty"
            kept_empty += 1
            out_rows.append(instance)
            continue
        patch, source = _agentless_test_patch(instance)
        instance = dict(instance)
        instance["test_patch"] = patch
        instance["ipt_source"] = source
        if source == "agentless":
            filled_llm += 1
        else:
            filled_placeholder += 1
        out_rows.append(instance)

    _write_jsonl(instances_path, out_rows)
    print(
        f"[prepare_instances] mode={mode} wrote {len(out_rows)} instances "
        f"(already_had_ipt={already}, kept_empty={kept_empty}, "
        f"agentless={filled_llm}, placeholder={filled_placeholder}) -> {instances_path}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("keep", "agentless"))
    parser.add_argument("instances", type=Path, help="instances.jsonl written by build_dataset.py")
    args = parser.parse_args()
    prepare(args.mode, args.instances)


if __name__ == "__main__":
    main()

"""Classify each downloaded issue into one of the primary taxonomy
categories (A / B / C / D / E / F) using the tu-zi gateway.

For every issue directory, we extract a short description (title + body)
from ``issue_<n>.json`` and call the LLM once. The result is a JSONL
``index`` file with one record per issue:

    {"id": "issue_1006", "path": ".../issue_1006_...", "repo": "...",
     "title": "...", "description": "...",
     "category": "E", "confidence": "high", "reason": "..."}

Usage::

    python utils/classify/run.py --in data/raw/<subdir> --out data/index.jsonl

Resumable: records that are already in ``--out`` are skipped on re-run.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

try:
    from openai import OpenAI
except ImportError:
    sys.exit("openai SDK not installed. Run: pip install openai>=1.0")


# ---------------------------------------------------------------------------
# Taxonomy handling
# ---------------------------------------------------------------------------
# We keep this self-contained: load the taxonomy markdown and pull out a
# minimal "category -> one-liner" map for the system prompt, rather than
# shoving the whole 800-line doc into every call.

def _load_category_summaries(taxonomy_md: Path) -> dict[str, str]:
    """Return {letter: short description} for A-F."""
    text = taxonomy_md.read_text(encoding="utf-8")
    summaries: dict[str, str] = {}
    # The taxonomy doc has inconsistent heading levels (`## A.`, `# B.`,
    # `### C.`, ...). We accept any 1–3 `#` marks followed by a single
    # uppercase letter + `. ` to find the six major categories.
    sections = re.split(r"^#{1,3}\s+", text, flags=re.MULTILINE)
    for sec in sections:
        heading = sec.split("\n", 1)[0].strip()
        m = re.match(r"^([A-F])\.\s+(.+)$", heading)
        if not m:
            continue
        letter, name = m.group(1), m.group(2).strip()
        # Skip F.<digit>.<...> sub-sections (they're under F).
        if re.match(rf"^{letter}\.\d", heading):
            continue
        body = sec.split("\n", 1)[1] if "\n" in sec else ""
        first_para = body.strip().split("\n\n", 1)[0]
        summaries[letter] = f"{letter}. {name} — {first_para[:300]}"
    return summaries


SYSTEM_PROMPT_TEMPLATE = """\
You are classifying GitHub issues in LLM-based agent systems into exactly \
one of six top-level categories from the agent-issue taxonomy below.

{taxonomy_block}

Rules:
- Reply with a single JSON object, no prose, no markdown fences.
- Pick exactly one primary letter in {{A, B, C, D, E, F}}.
- Use the description of the issue (title + body) to decide.
- If the issue does NOT describe an agent problem, still pick the closest \
letter (the spec says force a category), but set confidence="low" and \
mention "non-agent" in the reason.
- Be conservative — only assign to a category if the description clearly \
relates to that agent capability.

Output schema:
{{"category": "A"|"B"|"C"|"D"|"E"|"F",
  "confidence": "high"|"medium"|"low",
  "reason": "<= 25 words citing the key signal from the description>"}}
"""


def build_system_prompt(summaries: dict[str, str]) -> str:
    block = "\n\n".join(summaries[l] for l in sorted(summaries))
    return SYSTEM_PROMPT_TEMPLATE.format(taxonomy_block=block)


# ---------------------------------------------------------------------------
# Issue directory parsing
# ---------------------------------------------------------------------------
_REPO_RE = re.compile(r"^https?://github\.com/([^/]+)/([^/]+)/issues/\d+")


def parse_issue_dir(issue_dir: Path) -> dict[str, Any] | None:
    """Extract {id, path, repo, title, description} from an issue dir.

    Returns None if the directory lacks a usable issue_<n>.json.
    """
    issue_jsons = sorted(issue_dir.glob("issue_*.json"))
    if not issue_jsons:
        return None
    # Prefer one matching the directory name suffix when possible, else the
    # first.
    preferred = issue_dir.name.split("_")[1]  # e.g. "1006"
    picked = next((p for p in issue_jsons if preferred in p.stem), issue_jsons[0])
    try:
        data = json.loads(picked.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    title = (data.get("title") or "").strip()
    body = (data.get("body") or "").strip()
    if not title and not body:
        return None
    repo = None
    url = data.get("url") or ""
    m = _REPO_RE.match(url)
    if m:
        repo = f"{m.group(1)}/{m.group(2)}"
    description = title
    if body:
        description = f"{title}\n\n{body}" if title else body
    # Truncate descriptions to keep the prompt manageable.
    if len(description) > 6000:
        description = description[:6000] + "\n\n[... truncated ...]"
    return {
        "id": picked.stem.replace("issue_", "issue-"),
        "path": str(issue_dir.resolve()),
        "repo": repo,
        "title": title,
        "description": description,
    }


def iter_issue_dirs(root: Path) -> list[Path]:
    return sorted(p for p in root.iterdir() if p.is_dir())


# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------
def classify_one(client: OpenAI, model: str, system_prompt: str,
                 issue: dict[str, Any], max_retries: int) -> dict[str, Any]:
    """Call the LLM once and return ``issue`` augmented with the label."""
    user_msg = (
        f"Issue title:\n{issue['title']}\n\n"
        f"Issue body:\n{issue['description']}\n\n"
        "Reply with the JSON object only."
    )
    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.0,
                response_format={"type": "json_object"},
            )
            text = resp.choices[0].message.content or "{}"
            obj = json.loads(text)
            cat = obj.get("category", "").strip().upper()[:1]
            if cat not in {"A", "B", "C", "D", "E", "F"}:
                raise ValueError(f"bad category: {cat!r}")
            return {
                **issue,
                "category": cat,
                "confidence": obj.get("confidence", "low"),
                "reason": obj.get("reason", ""),
            }
        except Exception as e:  # JSON / API / network
            last_err = e
            time.sleep(2 ** attempt)
    # All retries failed — mark unknown so we don't lose the record.
    return {
        **issue,
        "category": "?",
        "confidence": "low",
        "reason": f"classification failed: {last_err}",
    }


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--in", dest="inp", type=Path, required=True,
                   help="Directory containing per-issue subdirs.")
    p.add_argument("--out", type=Path, required=True,
                   help="Output JSONL index file.")
    p.add_argument("--taxonomy", type=Path,
                   default=Path("docs/taxonomy.md"),
                   help="Path to the taxonomy markdown.")
    p.add_argument("--model", default=os.environ.get("DEFAULT_MODEL",
                                                    "gpt-4.1-mini"))
    p.add_argument("--base-url", default="https://api.tu-zi.com/v1")
    p.add_argument("--api-key", default=os.environ.get("TUZI_API_KEY"))
    p.add_argument("--concurrency", type=int, default=8)
    p.add_argument("--max-retries", type=int, default=3)
    p.add_argument("--limit", type=int, default=None,
                   help="Only classify the first N issues (for smoke tests).")
    args = p.parse_args()

    if not args.api_key:
        sys.exit("Set TUZI_API_KEY or pass --api-key.")

    summaries = _load_category_summaries(args.taxonomy)
    if set(summaries) != {"A", "B", "C", "D", "E", "F"}:
        sys.exit(f"Could not parse all six categories from {args.taxonomy}; "
                 f"got {sorted(summaries)}")
    system_prompt = build_system_prompt(summaries)

    issue_dirs = iter_issue_dirs(args.inp)
    print(f"Found {len(issue_dirs)} issue directories under {args.inp}")

    # Resumability: skip ids already present in the output file.
    done: set[str] = set()
    if args.out.exists():
        for line in args.out.read_text(encoding="utf-8").splitlines():
            try:
                done.add(json.loads(line)["id"])
            except Exception:
                pass
        print(f"Resuming: {len(done)} already classified")

    parsed: list[dict[str, Any]] = []
    skipped = 0
    for d in issue_dirs:
        rec = parse_issue_dir(d)
        if rec is None:
            skipped += 1
            continue
        if rec["id"] in done:
            continue
        parsed.append(rec)
        if args.limit and len(parsed) >= args.limit:
            break
    print(f"To classify: {len(parsed)} (skipped {skipped} dirs with no issue json)")

    if not parsed:
        print("Nothing to do.")
        return

    client = OpenAI(base_url=args.base_url, api_key=args.api_key)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fout = args.out.open("a", encoding="utf-8")

    with cf.ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futures = {
            ex.submit(classify_one, client, args.model, system_prompt, issue,
                      args.max_retries): issue
            for issue in parsed
        }
        completed = 0
        for fut in cf.as_completed(futures):
            issue = futures[fut]
            try:
                record = fut.result()
            except Exception as e:
                record = {**issue, "category": "?", "confidence": "low",
                          "reason": f"worker error: {e}"}
            fout.write(json.dumps(record, ensure_ascii=False) + "\n")
            fout.flush()
            completed += 1
            if completed % 25 == 0 or completed == len(parsed):
                print(f"  classified {completed}/{len(parsed)}")
    fout.close()
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()

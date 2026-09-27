#!/usr/bin/env python3
"""Raw LLM agent-issue judgment using forge_ai/run_forge_ai.py.

Five independent Forge/LLMClient calls per human-labelled issue, majority vote
against Human Golden. Writes result_raw.csv.
"""

from __future__ import annotations

import csv
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_RQ2_DIR = _SCRIPT_DIR.parent
_SWEGENT = Path("/home/anonymous/Desktop/paper/SWEGENT-BENCH")
sys.path.insert(0, str(_SWEGENT / "src" / "issue-hook"))
sys.path.insert(0, str(_SWEGENT / "src"))
sys.path.insert(0, str(_SCRIPT_DIR / "forge_ai"))

from forge.api import LLMClient  # noqa: E402
from run_forge_ai import _parse_yes_no  # noqa: E402

N_RUNS = 5
TEMPERATURE = 0.7  # raw API: allow vote variance
_UNTITLED = _RQ2_DIR.parent / "untitled folder"
HUMAN_CSV = _UNTITLED / "result_human.csv"
OUT_CSV = _UNTITLED / "result_raw.csv"
CKPT = _UNTITLED / "result_raw.checkpoint.json"
ISSUE_ROOT = _UNTITLED / "all_issues"
_ABS_DATA = Path("/home/anonymous/Desktop/paper/AgentBug-Smith")

RAW_SYSTEM = (
    "You classify GitHub issues. Answer with exactly one word: Yes or No. "
    "Do not use any extra taxonomy or checklist."
)


def _norm_yn(value: str) -> str:
    v = (value or "").strip().upper()
    if v.startswith("Y"):
        return "Y"
    if v.startswith("N"):
        return "N"
    return ""


def _vote_yn(answer: str) -> str:
    return "Y" if (answer or "").strip().lower().startswith("y") else "N"


def _load_human_rows() -> list[dict]:
    rows = []
    with HUMAN_CSV.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            num = (row.get("issue_number") or "").strip()
            url = (row.get("url") or "").strip()
            gold = _norm_yn(row.get("Human Golden") or "")
            if not num or not url or not gold:
                continue
            fname = url.rstrip("/").split("/")[-1]
            rows.append(
                {
                    "issue_number": num,
                    "url": url,
                    "folder": fname,
                    "ckpt_key": url,
                    "Human_Golden": gold,
                }
            )
    return rows


def _expected_github_url(csv_url: str) -> str:
    """Map AgentBug-Smith blob URL to the original GitHub issue URL when local data exists."""
    marker = "/data/"
    if marker not in csv_url:
        return ""
    rel = csv_url.split(marker, 1)[1]
    local = _ABS_DATA / "data" / rel
    if not local.is_file():
        return ""
    try:
        data = json.loads(local.read_text(encoding="utf-8"))
    except Exception:
        return ""
    return (data.get("url") or "") if isinstance(data, dict) else ""


def _issue_candidates(fname: str) -> list[Path]:
    stem = fname[:-5] if fname.endswith(".json") else fname
    out: list[Path] = []
    for p in (ISSUE_ROOT / fname, ISSUE_ROOT / f"{stem} copy.json"):
        if p.is_file() and p not in out:
            out.append(p)
    return out


def _extract_issue_fields(data: dict) -> dict:
    labels = data.get("labels") or []
    names = []
    if isinstance(labels, list):
        for lab in labels:
            if isinstance(lab, str):
                names.append(lab)
            elif isinstance(lab, dict) and lab.get("name"):
                names.append(str(lab["name"]))
    return {
        "number": data.get("number"),
        "title": data.get("title") or "",
        "body": data.get("body") or "",
        "state": data.get("state") or "",
        "labels": names,
    }


def _load_issue_json_only(folder: str, csv_url: str = "") -> dict:
    """Read only issue_*.json; drop PR patches, ai_judgment, original-repo URLs."""
    path = ISSUE_ROOT / folder
    matches: list[Path] = []
    if path.is_dir():
        matches = sorted(path.glob("issue_*.json"))
    else:
        matches = _issue_candidates(folder)
        expected = _expected_github_url(csv_url)
        if expected:
            for p in matches:
                try:
                    data = json.loads(p.read_text(encoding="utf-8"))
                except Exception:
                    continue
                if isinstance(data, dict) and (data.get("url") or "") == expected:
                    return _extract_issue_fields(data)

    if not matches:
        return {}
    try:
        data = json.loads(matches[0].read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    return _extract_issue_fields(data)


def _majority(votes: list[str]) -> str:
    c = Counter(v for v in votes if v in ("Y", "N"))
    if c["Y"] > c["N"]:
        return "Y"
    if c["N"] > c["Y"]:
        return "N"
    return votes[-1] if votes else "N"


def _conf(pred: str, gold: str) -> str:
    if pred == "Y" and gold == "Y":
        return "TP"
    if pred == "Y" and gold == "N":
        return "FP"
    if pred == "N" and gold == "N":
        return "TN"
    return "FN"


def main() -> None:
    if os.getenv("TUZI_API_KEY"):
        os.environ["FORGE_API_KEY"] = os.environ["TUZI_API_KEY"]
        os.environ["FORGE_BASE_URL"] = os.getenv("TUZI_BASE_URL", "https://api.tu-zi.com/v1")
        print("[info] using TUZI_API_KEY + api.tu-zi.com/v1", flush=True)
    elif not os.getenv("FORGE_API_KEY") and os.getenv("OPENAI_API_KEY"):
        os.environ["FORGE_API_KEY"] = os.environ["OPENAI_API_KEY"]
        os.environ.setdefault("FORGE_BASE_URL", "https://api.openai.com/v1")
        print("[info] FORGE_API_KEY missing; using OPENAI_API_KEY + api.openai.com", flush=True)

    rows = _load_human_rows()
    print(f"[info] human rows: {len(rows)}", flush=True)
    print(f"[info] HUMAN_CSV={HUMAN_CSV}", flush=True)
    print(f"[info] ISSUE_ROOT={ISSUE_ROOT}", flush=True)
    print("[info] RAW prompt (no agent_issue.md); gpt-4.1-mini; title/body only", flush=True)

    llm = LLMClient(model="gpt-4.1-mini")

    ckpt: dict[str, dict] = {}
    if CKPT.exists():
        ckpt = json.loads(CKPT.read_text(encoding="utf-8"))
        print(f"[info] resume checkpoint: {len(ckpt)}", flush=True)

    out_rows = []
    for i, row in enumerate(rows, 1):
        key = row["ckpt_key"]
        if key in ckpt and len(ckpt[key].get("votes", [])) == N_RUNS:
            votes = ckpt[key]["votes"]
        else:
            issue = _load_issue_json_only(row["folder"], row["url"])
            abs_id = row["issue_number"]
            print(f"[{i}/{len(rows)}] {row['folder']} issue_json#{abs_id}", flush=True)
            if not issue or not (issue.get("title") or issue.get("body")):
                votes = ["N"] * N_RUNS
            else:
                system_prompt = RAW_SYSTEM
                user_message = (
                    f"Issue Title: {issue.get('title', '')}\n\n"
                    f"Issue Description:\n{issue.get('body', '')}\n\n"
                    "Is this an agent issue? Reply with only Yes or No."
                )
                votes = []
                for r in range(N_RUNS):
                    answer = ""
                    for attempt in range(4):
                        try:
                            response = llm.simple_chat(
                                user_message=user_message,
                                system_prompt=system_prompt,
                                temperature=TEMPERATURE,
                            )
                            if (response or "").strip():
                                answer = _parse_yes_no(response)
                                break
                            raise RuntimeError("empty LLM response")
                        except Exception as e:
                            print(f"  LLM error attempt {attempt+1}: {e}", file=sys.stderr)
                            time.sleep(1.5 * (attempt + 1))
                    if not answer:
                        answer = "no"
                    v = _vote_yn(answer)
                    print(f"  run {r+1}/{N_RUNS} -> {v}", flush=True)
                    votes.append(v)
                    if r < N_RUNS - 1:
                        time.sleep(0.2)
            ckpt[key] = {"votes": votes}
            CKPT.write_text(json.dumps(ckpt, indent=2), encoding="utf-8")

        majority = _majority(votes)
        gold = row["Human_Golden"]
        label = _conf(majority, gold)
        out_rows.append(
            {
                "issue_number": row["issue_number"],
                "url": row["url"],
                "Human_Golden": gold,
                "llm1": votes[0],
                "llm2": votes[1],
                "llm3": votes[2],
                "llm4": votes[3],
                "llm5": votes[4],
                "majority": majority,
                "label": label,
            }
        )
        if i % 10 == 0 or i == len(rows):
            live = Counter(r["label"] for r in out_rows)
            print(
                f"[progress] {i}/{len(rows)}  "
                f"TP={live['TP']} FP={live['FP']} TN={live['TN']} FN={live['FN']}",
                flush=True,
            )

    counts = Counter(r["label"] for r in out_rows)
    tp, fp, tn, fn = counts["TP"], counts["FP"], counts["TN"], counts["FN"]
    n = len(out_rows)
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    spec = tn / (tn + fp) if (tn + fp) else 0.0
    acc = (tp + tn) / n if n else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0

    fields = [
        "issue_number", "url", "Human_Golden",
        "llm1", "llm2", "llm3", "llm4", "llm5",
        "majority", "label",
    ]
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out_rows)
        w.writerow(
            {
                "issue_number": "SUMMARY",
                "url": f"n={n}",
                "Human_Golden": "",
                "llm1": f"TP={tp}",
                "llm2": f"FP={fp}",
                "llm3": f"TN={tn}",
                "llm4": f"FN={fn}",
                "llm5": f"Acc={acc:.4f}",
                "majority": f"P={prec:.4f};R={rec:.4f}",
                "label": f"F1={f1:.4f};Spec={spec:.4f}",
            }
        )

    print(
        f"[done] {OUT_CSV}\n"
        f"  TP={tp} FP={fp} TN={tn} FN={fn}\n"
        f"  Acc={acc:.4f} Prec={prec:.4f} Rec={rec:.4f} F1={f1:.4f} Spec={spec:.4f}"
    )


if __name__ == "__main__":
    main()

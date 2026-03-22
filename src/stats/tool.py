"""
Forge API token / usage statistics (session start → end), adapted from SWEGENT-BENCH ``stats/entry.py``.

Uses ``GET {FORGE_BASE_URL}/stats/`` and ``GET .../statistic/usage/realtime`` with ``FORGE_API_KEY``.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from dotenv import load_dotenv

# Project root = parent of src/
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv() -> None:
    cwd = Path.cwd() / ".env"
    root = _PROJECT_ROOT / ".env"
    if cwd.exists():
        load_dotenv(cwd)
    if root.exists():
        load_dotenv(root, override=True)


def _getenv_stripped(key: str, default: str = "") -> str:
    v = os.getenv(key, default)
    if v is None:
        return default
    return str(v).strip().strip('"').strip("'")


def _http_get_json(url: str, headers: Dict[str, str], *, timeout: int = 60) -> Optional[Any]:
    req = Request(url, headers=headers, method="GET")
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw) if raw.strip() else None
    except (HTTPError, URLError, json.JSONDecodeError, OSError) as e:
        print(f"[stats] HTTP error: {e}", file=sys.stderr)
        return None


def _parse_model(model_config: str) -> Tuple[str, str]:
    s = model_config.strip().strip('"').strip("'")
    if "/" in s:
        a, b = s.split("/", 1)
        return a.strip() or "OpenAI", b.strip() or s
    return "OpenAI", s


def _normalize_items(data: Any) -> List[Dict[str, Any]]:
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        items = data.get("items")
        if isinstance(items, list):
            return [x for x in items if isinstance(x, dict)]
        return [data]
    return []


class StatsTool:
    """Record session wall-clock window and aggregate Forge usage for that window."""

    def __init__(
        self,
        *,
        model: Optional[str] = None,
        verbose: bool = False,
        stats_file: Optional[Path] = None,
    ) -> None:
        _load_dotenv()
        self.verbose = verbose
        self.stats_file = stats_file or (_PROJECT_ROOT / "data" / "agentsmith_stat.json")

        self.api_key = _getenv_stripped("FORGE_API_KEY")
        self.base_url = _getenv_stripped(
            "FORGE_BASE_URL",
            "https://api.forge.tensorblock.co/v1",
        ).rstrip("/")

        mc = model or _getenv_stripped("MODEL", "OpenAI/gpt-4o")
        self.provider, self.model = _parse_model(mc)

        if not self.api_key:
            print("[stats] warning: FORGE_API_KEY not set; stats API calls may fail.", file=sys.stderr)

    def get_api_stats(self) -> Optional[Any]:
        if not self.api_key:
            return None
        q = urlencode({"provider": self.provider, "model": self.model})
        url = f"{self.base_url}/stats/?{q}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        if self.verbose:
            print(f"[stats] GET {url}", file=sys.stderr)
        return _http_get_json(url, headers)

    def get_usage_realtime(self, started_at: str, ended_at: str) -> Optional[Any]:
        if not self.api_key:
            return None
        params = {
            "provider_name": self.provider,
            "model_name": self.model,
            "started_at": started_at,
            "ended_at": ended_at,
            "limit": 2000,
        }
        url = f"{self.base_url}/statistic/usage/realtime?{urlencode(params)}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        if self.verbose:
            print(f"[stats] GET {url[:120]}...", file=sys.stderr)
        return _http_get_json(url, headers, timeout=90)

    def load_existing(self) -> Dict[str, Any]:
        if self.stats_file.is_file():
            try:
                with open(self.stats_file, encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                print(f"[stats] warning: could not load {self.stats_file}: {e}", file=sys.stderr)
        return {
            "session_start": None,
            "session_end": None,
            "start_stats": None,
            "end_stats": None,
            "usage_delta": None,
            "api_info": {"provider_name": None, "model": None},
        }

    def save(self, data: Dict[str, Any]) -> None:
        try:
            self.stats_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.stats_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            if self.verbose:
                print(f"[stats] saved {self.stats_file}", file=sys.stderr)
        except OSError as e:
            print(f"[stats] error saving: {e}", file=sys.stderr)

    def start(self) -> None:
        """Call at run **begin**: store UTC ``session_start`` and optional snapshot from ``/stats/``."""
        print("[stats] session start (recording window for token usage)")
        now = datetime.now(timezone.utc).isoformat()
        blob = self.load_existing()
        blob["session_start"] = now
        blob["session_end"] = None
        blob["api_info"] = {"provider_name": self.provider, "model": self.model}

        snap = self.get_api_stats()
        blob["start_stats"] = snap

        self.save(blob)
        if self.verbose and snap is not None:
            print(f"[stats] snapshot (optional): {json.dumps(snap, ensure_ascii=False)[:500]}...", file=sys.stderr)

    def end(self) -> None:
        """Call at run **end**: query realtime usage from ``session_start`` to now; print summary."""
        print("[stats] session end (aggregating Forge usage for this window)")
        now = datetime.now(timezone.utc).isoformat()
        blob = self.load_existing()
        session_start = blob.get("session_start") or now
        blob["session_end"] = now

        raw = self.get_usage_realtime(session_start, now)
        items = _normalize_items(raw)

        if items:
            total_in = sum(int(i.get("input_tokens") or 0) for i in items)
            total_out = sum(int(i.get("output_tokens") or 0) for i in items)
            total_tok = sum(int(i.get("tokens") or i.get("total_tokens") or 0) for i in items)
            total_cost = sum(float(i.get("cost") or 0) for i in items)
            n_req = len(items)

            summary = {
                "provider_name": self.provider,
                "model": self.model,
                "input_tokens": total_in,
                "output_tokens": total_out,
                "total_tokens": total_tok,
                "requests_count": n_req,
                "cost": total_cost,
            }
            blob["end_stats"] = [summary]
            blob["usage_delta"] = summary

            print(
                f"[stats] window {session_start} → {now}\n"
                f"  requests: {n_req}\n"
                f"  input_tokens: {total_in:,}\n"
                f"  output_tokens: {total_out:,}\n"
                f"  total_tokens: {total_tok:,}\n"
                f"  cost: ${total_cost:.6f}"
            )
        else:
            blob["end_stats"] = []
            blob["usage_delta"] = None
            print("[stats] no usage rows returned for this time range (check API key / model names).")

        self.save(blob)


def main() -> None:
    import argparse

    p = argparse.ArgumentParser(description="Forge token usage stats (start | end | check)")
    p.add_argument("action", choices=["start", "end", "check"])
    p.add_argument("--model", default=None, help="Override MODEL (e.g. OpenAI/gpt-4.1-mini)")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args()

    t = StatsTool(model=args.model, verbose=args.verbose)
    if args.action == "start":
        t.start()
    elif args.action == "end":
        t.end()
    else:
        s = t.get_api_stats()
        print(json.dumps(s, indent=2, ensure_ascii=False) if s is not None else "{}")


if __name__ == "__main__":
    main()

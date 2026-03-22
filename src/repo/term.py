"""ANSI colors for repo CLI (stderr, respects NO_COLOR)."""

from __future__ import annotations

import os
import sys
from typing import TextIO


def color_on(stream: TextIO = sys.stderr) -> bool:
    return stream.isatty() and not (os.getenv("NO_COLOR") or "").strip()


def paint(code: str, text: str, *, stream: TextIO = sys.stderr) -> str:
    if not color_on(stream):
        return text
    return f"\033[{code}m{text}\033[0m"


def log_line(tag: str, *parts: str, tag_color: str = "1;33", stream: TextIO = sys.stderr) -> None:
    """Bold yellow tag, then space-separated message parts (already painted)."""
    body = " ".join(parts) if parts else ""
    print(f"{paint(tag_color, tag, stream=stream)} {body}".rstrip(), file=stream)

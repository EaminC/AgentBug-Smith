"""Helpers for ``exp/end-end.py``: config and dual-agent feedback formatting."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

DEFAULT_END_END_CONFIG_REL = "conf/dockerbuild/end-end.json"


@dataclass(frozen=True)
class EndEndConfig:
    max_outer_epochs: int
    max_docker_rounds: int
    max_f2p_rounds: int
    max_cofix_rounds: int


def load_end_end_config(
    project_root: Path | str,
    *,
    rel_path: str = DEFAULT_END_END_CONFIG_REL,
) -> EndEndConfig:
    root = Path(project_root).resolve()
    path = root / rel_path
    with open(path, encoding="utf-8") as f:
        raw: Any = json.load(f)
    if not isinstance(raw, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return EndEndConfig(
        max_outer_epochs=int(raw["max_outer_epochs"]),
        max_docker_rounds=int(raw["max_docker_rounds"]),
        max_f2p_rounds=int(raw["max_f2p_rounds"]),
        max_cofix_rounds=int(raw["max_cofix_rounds"]),
    )


def format_dual_feedback(
    docker_part: Optional[str],
    f2p_part: Optional[str],
) -> Optional[str]:
    """
    Merge docker-build and fail2pass verify feedback so both agents can see both channels
    from the second outer epoch onward.
    """
    parts: list[str] = []
    if docker_part and docker_part.strip():
        parts.append(
            "--- Docker build / dockerwrite feedback ---\n" + docker_part.strip()
        )
    if f2p_part and f2p_part.strip():
        parts.append(
            "--- Fail2pass / testgen verify feedback ---\n" + f2p_part.strip()
        )
    if not parts:
        return None
    return "\n\n".join(parts)


__all__ = [
    "DEFAULT_END_END_CONFIG_REL",
    "EndEndConfig",
    "format_dual_feedback",
    "load_end_end_config",
]

"""
Filter repos by presence of test paths.
Uses: 1) common test path patterns (incl. swe-factory-style rules), 2) heuristic paths from inlight test_path_patterns_topk.json.
"""
import json
import os
import re
from pathlib import Path
from typing import List, Set, Tuple, Optional

import requests

BASE_URL = "https://api.github.com"

# Common test directory prefixes (path starts with these or path segment)
COMMON_TEST_DIRS = (
    "tests/", "test/", "__tests__/", "spec/", "cypress/", "e2e/",
    "testing/", "unit_test/", "unit_tests/", "integration_tests/",
)
# Path segments that indicate test dir (swe-factory: "tests", "Tests", "test", "Test" in path.split("/"))
COMMON_TEST_SEGMENTS = frozenset(
    {"tests", "Tests", "test", "Test", "__tests__", "spec", "testing", "e2e", "cypress"}
)
# Common test-related file names (exact or suffix)
COMMON_TEST_FILES = (
    "pytest.ini", "jest.config.js", "jest.config.ts", "vitest.config.js",
    "karma.conf.js", "cypress.config.js", ".mocharc.js",
)
# Basename patterns: test_*.py, *_test.py, *.test.js, *.spec.js, etc.
COMMON_TEST_BASENAME_PATTERNS = [
    re.compile(r"^test_.*\.py$"),
    re.compile(r"^.*_test\.py$"),
    re.compile(r"^.*\.test\.(js|ts|jsx|tsx)$"),
    re.compile(r"^.*\.spec\.(js|ts|jsx|tsx)$"),
]
# swe-factory: basename starts with "test_" (any extension); path starts with "test_"
# mypy: path.endswith(".test")


def _headers(github_token: Optional[str] = None) -> dict:
    h = {"Accept": "application/vnd.github.v3+json"}
    token = github_token or os.getenv("GITHUB_TOKEN")
    if token:
        h["Authorization"] = f"token {token}"
    return h


def load_heuristic_paths(json_path: str) -> Set[str]:
    """Load path list from inlight test_path_patterns_topk.json. Returns set of path strings."""
    out = set()
    path = Path(json_path)
    if not path.exists():
        return out
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for p in data.get("paths") or []:
            if isinstance(p, str) and p.strip():
                out.add(p.strip())
    except Exception:
        pass
    return out


def fetch_repo_tree(repo: str, github_token: Optional[str] = None) -> List[str]:
    """Fetch full recursive file tree paths for repo. Returns list of paths."""
    try:
        r = requests.get(
            f"{BASE_URL}/repos/{repo}",
            headers=_headers(github_token),
            timeout=15,
        )
        r.raise_for_status()
        default_branch = r.json().get("default_branch") or "main"
    except Exception:
        return []

    try:
        r = requests.get(
            f"{BASE_URL}/repos/{repo}/git/trees/{default_branch}",
            headers=_headers(github_token),
            params={"recursive": "1"},
            timeout=30,
        )
        r.raise_for_status()
        tree = r.json().get("tree") or []
    except Exception:
        return []

    return [n.get("path") or "" for n in tree if n.get("path")]


def _norm(p: str) -> str:
    return p.replace("\\", "/").strip()


def path_matches_common(path: str) -> bool:
    """True if path matches common test dir/file patterns.
    Incorporates swe-factory-style rules: path segment in (tests, Tests, test, Test),
    path.startswith('test_'), basename.startswith('test_'), path.endswith('.test').
    """
    path = _norm(path)
    if not path:
        return False
    segments = path.split("/")
    base = segments[-1] if segments else ""

    # swe-factory: any path segment is tests/Tests/test/Test/__tests__/spec
    if any(seg in COMMON_TEST_SEGMENTS for seg in segments):
        return True
    # swe-factory: path starts with "test_"
    if path.startswith("test_"):
        return True
    # swe-factory: basename starts with "test_" (any extension)
    if base.startswith("test_"):
        return True
    # swe-factory: path endswith "_test.py"
    if path.endswith("_test.py"):
        return True
    # swe-factory (mypy): path endswith ".test"
    if path.endswith(".test"):
        return True

    # Dir prefix (our original rules)
    for d in COMMON_TEST_DIRS:
        if path == d.rstrip("/") or path.startswith(d) or ("/" + d) in path:
            return True
    # Exact file name
    if base in COMMON_TEST_FILES:
        return True
    # Basename pattern
    for pat in COMMON_TEST_BASENAME_PATTERNS:
        if pat.search(base):
            return True
    return False


def path_matches_heuristic(path: str, heuristic: Set[str]) -> bool:
    """True if path equals or is under a heuristic path."""
    path = _norm(path)
    if path in heuristic:
        return True
    for h in heuristic:
        h = _norm(h)
        if not h:
            continue
        if path.startswith(h + "/") or path == h:
            return True
        if h.endswith("/") and path.startswith(h):
            return True
    return False


def repo_has_test_paths(
    repo: str,
    heuristic_paths: Set[str],
    github_token: Optional[str] = None,
) -> Tuple[bool, List[str]]:
    """
    Check if repo has any test-related paths.
    Returns (has_test, list of matched paths).
    """
    paths = fetch_repo_tree(repo, github_token)
    if not paths:
        return False, []

    matched = []
    for p in paths:
        if path_matches_common(p) or path_matches_heuristic(p, heuristic_paths):
            matched.append(p)

    return bool(matched), sorted(set(matched))

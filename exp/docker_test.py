"""
Quick usage:
1) Default (auto clone ../langchain if missing, auto generate test Dockerfile, then run):
   python exp/docker_test.py
2) Custom repo path:
   python exp/docker_test.py /path/to/langchain
3) Custom repo + dockerfile:
   python exp/docker_test.py /path/to/langchain libs/langchain/test_runner.Dockerfile
"""

import sys
import subprocess
from pathlib import Path

_AGENTSMITH_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_AGENTSMITH_ROOT / "src"))

from testrun import (
    docker_test_repo_test,
    ensure_langchain_test_dockerfile,
    get_test_file_path,
)

_DEFAULT_LANGCHAIN_REPO = (_AGENTSMITH_ROOT.parent / "langchain").resolve()
_DEFAULT_LANGCHAIN_GIT_URL = "https://github.com/langchain-ai/langchain.git"
_DEFAULT_DOCKERFILE_REL = Path("libs/langchain/test_runner.Dockerfile")


if __name__ == "__main__":
    repo_path = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else _DEFAULT_LANGCHAIN_REPO
    dockerfile_path = Path(sys.argv[2]) if len(sys.argv) > 2 else _DEFAULT_DOCKERFILE_REL

    if not repo_path.exists():
        repo_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"[docker_test] Repo not found, cloning: {_DEFAULT_LANGCHAIN_GIT_URL} -> {repo_path}")
        subprocess.run(
            ["git", "clone", _DEFAULT_LANGCHAIN_GIT_URL, str(repo_path)],
            check=True,
        )

    if len(sys.argv) <= 2:
        dockerfile_path = ensure_langchain_test_dockerfile(repo_path, relpath=str(_DEFAULT_DOCKERFILE_REL))

    path_list = get_test_file_path(repo_path)
    if not path_list:
        print("No test paths found.")
        raise SystemExit(2)

    test_docker_result_0 = docker_test_repo_test(repo_path, dockerfile_path, path_list[0])
    print(test_docker_result_0)

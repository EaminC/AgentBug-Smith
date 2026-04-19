from __future__ import annotations

import argparse
import sys
from pathlib import Path

from testrun.docker_test_tool import docker_test_repo_test, get_test_file_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Quick docker test (without touching exp/end-end.py pipeline)."
    )
    parser.add_argument("repo_path", type=Path, help="Local repo path to test")
    parser.add_argument(
        "--dockerfile",
        type=Path,
        default=Path("env.dockerfile"),
        help="Dockerfile path (default: env.dockerfile, relative to repo)",
    )
    parser.add_argument(
        "--test-index",
        type=int,
        default=0,
        help="Index in Forge-returned test path list (default: 0)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Optional Forge model override for get_test_file_path",
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    repo_path = args.repo_path.resolve()
    dockerfile_path = args.dockerfile

    path_list = get_test_file_path(repo_path, model=args.model, verbose=args.verbose)
    if not path_list:
        print("No test files were found by Forge/fallback rules.")
        sys.exit(2)
    if args.test_index < 0 or args.test_index >= len(path_list):
        print(f"Invalid --test-index {args.test_index}; available range: 0..{len(path_list)-1}")
        sys.exit(2)

    print("Candidate test files:")
    for i, p in enumerate(path_list):
        print(f"  [{i}] {p}")

    test_docker_result_0 = docker_test_repo_test(
        repo_path, dockerfile_path, path_list[args.test_index], verbose=args.verbose
    )

    ok, report = test_docker_result_0
    print("\n=== docker test result ===")
    print("PASS" if ok else "FAIL")
    print(report)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

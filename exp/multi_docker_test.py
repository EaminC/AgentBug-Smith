"""
Run docker_test for multiple Dockerfiles and summarize the results.

Usage:
python exp/run_multi_docker.py [path/to/repo]
"""
import os
import sys
import subprocess
from pathlib import Path
import datetime

_AGENTSMITH_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_AGENTSMITH_ROOT / "src"))

from repo.term import log_line, paint

_DEFAULT_LANGCHAIN_REPO = (_AGENTSMITH_ROOT.parent / "langchain").resolve()
_DOCKERFILES_REL_PATH = "libs/langchain/dockerfiles"
_LOGS_DIR = _AGENTSMITH_ROOT / "logs"

def _banner(title: str, *, stream=sys.stderr) -> None:
    line = "=" * 72
    print(line, file=stream, flush=True)
    print(f"  {title}", file=stream, flush=True)
    print(line, file=stream, flush=True)

if __name__ == "__main__":
    # Create logs directory if it doesn't exist
    _LOGS_DIR.mkdir(exist_ok=True)
    
    # Setup logging
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file_path = _LOGS_DIR / f"run_multi_docker_{timestamp}.log"
    
    with open(log_file_path, "w") as log_file:
        
        def log_and_print(message, stream=sys.stderr):
            print(message, file=stream)
            log_file.write(message + "\n")

        repo_path = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else _DEFAULT_LANGCHAIN_REPO
        dockerfiles_path = repo_path / _DOCKERFILES_REL_PATH

        if not dockerfiles_path.is_dir():
            log_and_print(f"[run_multi_docker] {paint('31', f'Dockerfiles directory not found at: {dockerfiles_path}')}")
            raise SystemExit(1)

        dockerfiles = sorted([p for p in dockerfiles_path.glob("*.Dockerfile") if p.is_file()])

        if not dockerfiles:
            log_and_print(f"[run_multi_docker] {paint('31', f'No Dockerfiles found in: {dockerfiles_path}')}")
            raise SystemExit(1)

        log_and_print(f"[run_multi_docker] {paint('1;36', 'Found Dockerfiles to test:')}")
        for df in dockerfiles:
            log_and_print(f"[run_multi_docker] {paint('32', f'  - {df.relative_to(repo_path)}')}")
        
        log_and_print("", stream=sys.stderr)

        results = []

        for i, dockerfile in enumerate(dockerfiles):
            dockerfile_rel_path = dockerfile.relative_to(repo_path)
            _banner(f"Running Dockerfile {i+1}/{len(dockerfiles)}: {dockerfile_rel_path}")
            
            cmd = [
                sys.executable,
                str(_AGENTSMITH_ROOT / "exp" / "docker_test.py"),
                str(repo_path),
                str(dockerfile_rel_path),
            ]
            
            process = subprocess.run(cmd, capture_output=True, text=True, cwd=_AGENTSMITH_ROOT)
            
            stdout = process.stdout
            stderr = process.stderr

            # Print stderr for progress and log it
            log_and_print(stderr, stream=sys.stderr)
            log_file.write("\n--- stdout ---\n")
            log_file.write(stdout)
            log_file.write("\n--- stderr ---\n")
            log_file.write(stderr)


            success_count = 0
            total_tests = 0

            for line in stderr.splitlines():
                if "successful runs" in line:
                    # This is the line from docker_test.py: paint("32", f"{success_count} successful runs.")
                    # It will have ANSI color codes. A regex is a good way to extract the number.
                    import re
                    match = re.search(r"(\d+)\s+successful\s+runs", line)
                    if match:
                        success_count = int(match.group(1))

                if "test file(s)" in line:
                    parts = line.split()
                    for part in parts:
                        # The part can contain ANSI codes, so we need to filter them out.
                        plain_part = ''.join(filter(str.isdigit, part))
                        if plain_part.isdigit():
                            total_tests = int(plain_part)
                            break
            
            results.append({
                "dockerfile": str(dockerfile_rel_path),
                "success_count": success_count,
                "total_tests": total_tests,
                "exit_code": process.returncode
            })

        _banner("Final Summary")

        total_successful_dockerfile_runs = 0
        for result in results:
            status = paint("32", "SUCCESS") if result["exit_code"] == 0 else paint("31", "FAILED")
            summary_line = (
                f"[run_multi_docker] "
                f"Dockerfile: {result['dockerfile']} "
                f"Successful Runs: {result['success_count']}/{result['total_tests']} "
                
            )
            log_and_print(summary_line)
            if result["exit_code"] == 0:
                total_successful_dockerfile_runs += 1

        log_and_print("", stream=sys.stderr)
        summary_line = (
            f"[run_multi_docker] "
            f"{paint('1;36', 'Summary of Dockerfile runs:')} "
            f"{paint('32', f'{total_successful_dockerfile_runs}/{len(dockerfiles)} successful Dockerfile runs.')}"
        )
        log_and_print(summary_line)

        # Exit with a non-zero code if any of the dockerfile runs failed
        if any(r["exit_code"] != 0 for r in results):
            raise SystemExit(1)

"""
End-to-end: clone GitHub repo from an issue JSON, generate Dockerfile, optional cleanup.

Paths and repo name come from the same JSON as ``repo.load_issue_workspace`` (see ``data/issue_13.json``).
Docker prompts/config: ``conf/dockerbuild/init``, ``prompt/dockerbuild/init``;
write stage: ``conf/dockerbuild/write``, ``prompt/dockerbuild/write`` (``dockerwrite``);
``dockerbuild`` runs ``docker build`` and feeds failures back into ``dockerwrite`` as ``feedback``.

After a successful image build, ``testgen`` writes a test file (see ``src/testgen``). Then ``testrun.run_f2p_verify``
builds the image, runs the test, applies ``linked_prs[].patch``, rebuilds, runs the test again; outcome ``f2p`` means
fail2pass. Unless the outcome is ``f2p``, the script **resets the repo to ``base_sha``** (if present), feeds the
verify log back into ``testgen`` as ``feedback``, and repeats (same pattern as the dockerwrite/build loop).

At script start/end, :class:`stats.StatsTool` records a UTC window and aggregates Forge token usage
(see ``src/stats``, modeled on ``SWEGENT-BENCH/src/stats``).
"""
import sys
from pathlib import Path

_AGENTSMITH_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_AGENTSMITH_ROOT / "src"))

from dockerbuild.build import dockerbuild  # noqa: E402
from dockerbuild.init import dockerinit  # noqa: E402
from dockerbuild.write import dockerwrite  # noqa: E402
from repo import clone_issue_repo, load_issue_workspace, remove_issue_repo  # noqa: E402
from repo.git_ops import ensure_repo_at_commit, read_linked_pr_base_sha, reset_repo_to_base  # noqa: E402
from stats import StatsTool  # noqa: E402
from testgen import testgen  # noqa: E402
from testrun import run_f2p_verify  # noqa: E402

_ISSUE_JSON = _AGENTSMITH_ROOT / "data" / "issue_441.json"
_MODEL = "tensorblock/gpt-4.1-mini"


def _run() -> None:
    _ws = load_issue_workspace(_ISSUE_JSON)
    clone_issue_repo(_ws, verbose=True)
    _base = read_linked_pr_base_sha(_ISSUE_JSON)
    if _base:
        _co_ok, _co_err = ensure_repo_at_commit(_ws.local_repo_path, _base, verbose=True)
        if not _co_ok:
            print(_co_err, file=sys.stderr)
            sys.exit(1)
    dockerinit(
        _ws.local_repo_path,
        _ws.dockerfile_out,
        model=_MODEL,
        verbose=True,
    )

    _feedback = None
    _max_rounds = 5
    _build_ok = False
    for _round in range(1, _max_rounds + 1):
        dockerwrite(
            _ws.local_repo_path,
            verbose=True,
            model=_MODEL,
            project_root=_AGENTSMITH_ROOT,
            feedback=_feedback,
        )
        _build_ok, _log = dockerbuild(
            _ws.local_repo_path,
            dockerfile="env.dockerfile",
            verbose=True,
            project_root=_AGENTSMITH_ROOT,
        )
        if _build_ok:
            break
        _feedback = _log

    if _build_ok:
        _max_f2p = 5
        _f2p_feedback = None
        if _max_f2p > 1 and not _base:
            print(
                "warning: issue JSON has no `linked_prs[].base_sha`; multi-round reset uses `git reset --hard` only when base_sha is set.",
                file=sys.stderr,
            )
        for _f2p_round in range(1, _max_f2p + 1):
            if _f2p_round > 1 and _base:
                _rs_ok, _rs_err = reset_repo_to_base(_ws.local_repo_path, _base)
                if not _rs_ok:
                    print(_rs_err, file=sys.stderr)
                    break
            _tg_ok, _tg_report = testgen(
                _ws.local_repo_path,
                issue_json_path=_ISSUE_JSON,
                verbose=True,
                project_root=_AGENTSMITH_ROOT,
                model=_MODEL,
                feedback=_f2p_feedback,
            )
            print(_tg_report)
            if not _tg_ok:
                break
            _outcome, _f2p_report = run_f2p_verify(
                _ws.local_repo_path,
                issue_json_path=_ISSUE_JSON,
                dockerfile="env.dockerfile",
                verbose=True,
                project_root=_AGENTSMITH_ROOT,
            )
            print(_f2p_report)
            if _outcome == "f2p":
                break
            _f2p_feedback = f"Round {_f2p_round} verify outcome: {_outcome}\n\n{_f2p_report}"
    else:
        print("Skipping testgen / testrun: docker build did not succeed.", file=sys.stderr)

    # remove_issue_repo(_ws, verbose=True)


if __name__ == "__main__":
    _usage_stats = StatsTool(model=_MODEL, verbose=True)
    _usage_stats.start()
    try:
        _run()
    finally:
        _usage_stats.end()

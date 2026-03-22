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

An **outer epoch** loop (see ``conf/dockerbuild/end-end.json``) wraps the dockerwrite/build rounds and the f2p rounds.
The first epoch starts with no feedback; from the second epoch onward, ``dockerwrite`` and ``testgen`` each receive the
same merged text built from the last docker-build feedback and the last fail2pass verify feedback (see
``utils.format_dual_feedback``).

At script start/end, :class:`stats.StatsTool` records a UTC window and aggregates Forge token usage
(see ``src/stats``, modeled on ``SWEGENT-BENCH/src/stats``).

Each run creates ``result/<issue_stem>_<utc>/`` with ``run.log`` (full stdout/stderr), ``agentsmith_stat.json``,
``dockerbuild.txt``, ``f2p.txt``, ``summary.json``, plus copies of the issue JSON, ``env.dockerfile``, and the
generated test file when present.
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
from testgen import load_issue_testgen_context, testgen  # noqa: E402
from testrun import run_f2p_verify  # noqa: E402
from utils import (  # noqa: E402
    append_text,
    finalize_run_artifacts,
    format_dual_feedback,
    load_end_end_config,
    result_run_with_tee,
    write_summary_json,
)

_ISSUE_JSON = _AGENTSMITH_ROOT / "data" / "issue_441.json"
_MODEL = "tensorblock/gpt-4.1-mini"


def _run(run_dir: Path) -> None:
    _cfg = load_end_end_config(_AGENTSMITH_ROOT)
    _docker_log = run_dir / "dockerbuild.txt"
    _f2p_log = run_dir / "f2p.txt"
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

    if (_cfg.max_f2p_rounds > 1 or _cfg.max_outer_epochs > 1) and not _base:
        print(
            "warning: issue JSON has no `linked_prs[].base_sha`; multi-round / multi-epoch reset uses `git reset --hard` only when base_sha is set.",
            file=sys.stderr,
        )

    _stored_docker = None
    _stored_f2p = None
    _f2p_succeeded = False

    for _epoch in range(1, _cfg.max_outer_epochs + 1):
        if _epoch > 1 and _base:
            _rs_ok, _rs_err = reset_repo_to_base(_ws.local_repo_path, _base)
            if not _rs_ok:
                print(_rs_err, file=sys.stderr)
                break

        if _epoch == 1:
            _fb_outer_docker = None
            _fb_outer_f2p = None
        else:
            _merged = format_dual_feedback(_stored_docker, _stored_f2p)
            _fb_outer_docker = _merged
            _fb_outer_f2p = _merged

        _feedback = _fb_outer_docker
        _build_ok = False
        for _round in range(1, _cfg.max_docker_rounds + 1):
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
            append_text(
                _docker_log,
                f"epoch={_epoch} docker_round={_round} ok={_build_ok}",
                _log or "",
            )
            if _build_ok:
                break
            _feedback = _log

        _stored_docker = _feedback

        if not _build_ok:
            print("Skipping testgen / testrun: docker build did not succeed.", file=sys.stderr)
            continue

        _f2p_feedback = _fb_outer_f2p
        for _f2p_round in range(1, _cfg.max_f2p_rounds + 1):
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
            append_text(
                _f2p_log,
                f"epoch={_epoch} f2p_round={_f2p_round} outcome={_outcome}",
                _f2p_report,
            )
            print(_f2p_report)
            if _outcome == "f2p":
                _f2p_succeeded = True
                break
            _f2p_feedback = f"Round {_f2p_round} verify outcome: {_outcome}\n\n{_f2p_report}"

        _stored_f2p = _f2p_feedback

        if _f2p_succeeded:
            break

    _ctx = load_issue_testgen_context(_ISSUE_JSON)
    _n = _ctx.issue_number or 0
    _test_rel = f"tests/agentsmith_fail2pass_{_n or 'issue'}.py"
    write_summary_json(
        run_dir / "summary.json",
        issue_json_path=_ISSUE_JSON,
        run_dir=run_dir,
        f2p_succeeded=_f2p_succeeded,
        extra={"test_relpath": _test_rel.replace("\\", "/")},
    )
    finalize_run_artifacts(
        run_dir,
        issue_json_path=_ISSUE_JSON,
        repo_root=_ws.local_repo_path,
        dockerfile_relpath="env.dockerfile",
        test_relpath=_test_rel,
    )

    remove_issue_repo(_ws, verbose=True)


if __name__ == "__main__":
    with result_run_with_tee(_AGENTSMITH_ROOT, _ISSUE_JSON, banner="[end-end] result dir:") as _run_dir:
        _usage_stats = StatsTool(
            model=_MODEL,
            verbose=True,
            stats_file=_run_dir / "agentsmith_stat.json",
        )
        _usage_stats.start()
        try:
            _run(_run_dir)
        finally:
            _usage_stats.end()

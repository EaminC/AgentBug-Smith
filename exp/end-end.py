"""
End-to-end: clone GitHub repo from an issue JSON, generate Dockerfile, optional cleanup.

Paths and repo name come from the same JSON as ``repo.load_issue_workspace`` (see ``data/issue_13.json``).
Docker prompts/config: ``conf/dockerbuild/init``, ``prompt/dockerbuild/init``;
write stage: ``conf/dockerbuild/write``, ``prompt/dockerbuild/write`` (``dockerwrite``);
``dockerbuild`` runs ``docker build`` and feeds failures back into ``dockerwrite`` as ``feedback``.
"""
import sys
from pathlib import Path

_AGENTSMITH_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_AGENTSMITH_ROOT / "src"))

from dockerbuild.build import dockerbuild  # noqa: E402
from dockerbuild.init import dockerinit  # noqa: E402
from dockerbuild.write import dockerwrite  # noqa: E402
from repo import clone_issue_repo, load_issue_workspace, remove_issue_repo  # noqa: E402

_ISSUE_JSON = _AGENTSMITH_ROOT / "data" / "issue_13.json"

if __name__ == "__main__":
    _ws = load_issue_workspace(_ISSUE_JSON)
    clone_issue_repo(_ws, verbose=True)
    dockerinit(
        _ws.local_repo_path,
        _ws.dockerfile_out,
        model="tensorblock/gpt-4.1-mini",
        verbose=True,
    )

    _feedback = None
    _max_rounds = 5
    _build_ok = False
    for _round in range(1, _max_rounds + 1):
        dockerwrite(
            _ws.local_repo_path,
            verbose=True,
            model="tensorblock/gpt-4.1-mini",
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

    # remove_issue_repo(_ws, verbose=True)

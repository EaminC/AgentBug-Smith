#!/usr/bin/env bash
# ============================================================================
# setup-all.sh — one-shot bootstrap for the entire RQ4 stack on a fresh box.
#
# Run from the RQ4 repo root:
#     bash scripts/setup-all.sh
#
# What this does, in order:
#   0. Sanity-check host tooling (git, python3, uv, curl, docker, pandoc).
#   1. Verify Docker daemon is up and the host has ≥30 GB free.
#   2. Component 1 — mini-swe-agent:    bash scripts/setup.sh
#   3. Component 2 — openhands CLI:     bash scripts/setup-openhands.sh
#   4. Component 3 — utils data layer:  bash scripts/setup-utils.sh
#   5. Print a summary + the commands the user typically runs next.
#
# Idempotent: each component script is itself idempotent, so re-running
# setup-all just refreshes what is missing and reuses what is present.
#
# Environment overrides (all optional):
#   TUZI_API_KEY=<sk-...>      api key for the OpenAI-compatible gateway
#   TUZI_BASE_URL=https://...  override gateway URL (default: tu-zi)
#   DEFAULT_MODEL=openai/...   default model for smoke tests
#   SKIP_OPENHANDS=1           don't install openhands (CI w/o UI)
#   SKIP_PANDOC=1              don't check pandoc (PDF build is optional)
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

log()  { printf '\033[1;34m[setup-all]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[setup-all][warn]\033[0m %s\n' "$*" >&2; }
err()  { printf '\033[1;31m[setup-all][error]\033[0m %s\n' "$*" >&2; }
die()  { err "$*"; exit 1; }
section() { printf '\n\033[1;36m========== %s ==========\033[0m\n' "$*"; }

# ---------------------------------------------------------------------------
# 0. Host tooling
# ---------------------------------------------------------------------------
section "0/5  Host tooling"
need_cmd() {
    command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1"
}

for cmd in git python3 curl; do
    need_cmd "$cmd"
done

PY_MAJOR="$(python3 -c 'import sys; print(sys.version_info.major)')"
PY_MINOR="$(python3 -c 'import sys; print(sys.version_info.minor)')"
if (( PY_MAJOR < 3 || (PY_MAJOR == 3 && PY_MINOR < 10) )); then
    die "Python ≥ 3.10 required (found $PY_MAJOR.$PY_MINOR)."
fi
log "Python $PY_MAJOR.$PY_MINOR ✓"

if ! command -v uv >/dev/null 2>&1; then
    warn "uv not on PATH — installing via pip"
    python3 -m pip install --user uv \
        || die "Install uv manually: https://docs.astral.sh/uv/"
    export PATH="$HOME/.local/bin:$PATH"
fi
log "uv ✓"

# ---------------------------------------------------------------------------
# 1. Docker
# ---------------------------------------------------------------------------
section "1/5  Docker daemon"

if ! command -v docker >/dev/null 2>&1; then
    cat <<'EOF'
[!] Docker CLI is not installed. Install Docker Desktop (macOS / Windows)
    or docker engine (Linux). Then re-run this script.

    macOS:  https://docs.docker.com/desktop/install/mac-install/
    Linux:  https://docs.docker.com/engine/install/
EOF
    die "Docker is required for the verify pool (image builds)."
fi

# Check daemon is actually reachable (not just the CLI on PATH).
if ! docker info >/dev/null 2>&1; then
    cat <<'EOF'
[!] Docker CLI is present but the daemon is not responding.

    macOS / Windows: open Docker Desktop and wait for the whale icon to
      settle, then re-run.
    Linux:            sudo systemctl start docker
EOF
    die "Docker daemon unreachable."
fi
log "Docker daemon ✓"

# Disk headroom. The pilot-20 batch held ~50 GB of intermediate images;
# pilot-30 needs less but still benefits from headroom.
FREE_GB="$(df -g "$REPO_ROOT" | awk 'NR==2 {print $4}')"
if (( FREE_GB < 30 )); then
    warn "Only ${FREE_GB} GB free on $REPO_ROOT's filesystem."
    warn "Recommended: ≥30 GB before running pilot-30 (Docker image cache)."
    warn "Prune stale images with: docker system prune -af"
else
    log "${FREE_GB} GB free on the repo volume ✓"
fi

# ---------------------------------------------------------------------------
# 2. Component 1 — mini-swe-agent
# ---------------------------------------------------------------------------
section "2/5  Component 1: mini-swe-agent"
bash "$SCRIPT_DIR/setup.sh"

# ---------------------------------------------------------------------------
# 3. Component 2 — OpenHands CLI
# ---------------------------------------------------------------------------
section "3/5  Component 2: openhands CLI"

if [[ "${SKIP_OPENHANDS:-0}" == "1" ]]; then
    warn "SKIP_OPENHANDS=1 — skipping openhands setup."
else
    if ! command -v openhands >/dev/null 2>&1; then
        warn "openhands CLI not found; installing now."
        curl -fsSL https://install.openhands.dev/install.sh | sh \
            || die "OpenHands installer failed. Re-run manually."
        export PATH="$HOME/.local/bin:$PATH"
    fi
    bash "$SCRIPT_DIR/setup-openhands.sh"
fi

# ---------------------------------------------------------------------------
# 4. Component 3 — utils (data layer)
# ---------------------------------------------------------------------------
section "4/5  Component 3: utils"
bash "$SCRIPT_DIR/setup-utils.sh"

# ---------------------------------------------------------------------------
# 5. Optional: pandoc for progress.pdf
# ---------------------------------------------------------------------------
if [[ "${SKIP_PANDOC:-0}" == "1" ]]; then
    warn "SKIP_PANDOC=1 — not checking pandoc."
elif ! command -v pandoc >/dev/null 2>&1; then
    warn "pandoc not installed; progress.pdf won't render."
    warn "Install with: brew install pandoc   (macOS)"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
section "5/5  Setup complete"

cat <<'NEXT'
Next steps (from $REPO_ROOT):

  # 1. Re-derive the verify pool if data/verify/ is missing
  source agent/.venv/bin/activate && source utils/.env
  python utils/verify/build_verify.py --audit

  # 1b. Generate the pilot-30 index subsets (5 issues × 6 combos).
  #     Reads the 6 full combo indexes just written, samples 5 ids
  #     from mini-swe-agent_40 split=1 with seed=20260909 (matches
  #     docs/progress.md §9), and writes 12 pilot-30 indexes (one
  #     per combo × {with,without}-issue-1351).
  python utils/verify/make_pilot30_index.py

  # 2. Train skills (if agent/skills/ is missing)
  bash utils/train/run_all.sh

  # 3. Run a pilot (pilot-30 uses 5 issues × 6 combos)
  bash scripts/run_pilot30.sh

  # 4. Score + plot
  python utils/verify/score.py \
      --runs data/verify/runs \
      --out  results/rq4/pilot30_scores.csv
  python utils/verify/plot_pilot30.py

To re-run the whole setup (idempotent):
  bash scripts/setup-all.sh
NEXT

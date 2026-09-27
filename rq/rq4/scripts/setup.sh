#!/usr/bin/env bash
# ============================================================================
# setup.sh — bootstrap the first RQ4 component: mini-swe-agent, routed through
# the tu-zi OpenAI-compatible API gateway.
#
# Run from the RQ4 repo root:
#     bash scripts/setup.sh
#
# What this does, in order:
#   1. Sanity-check tooling (git, python3 ≥3.10, uv).
#   2. Verify the upstream mini-swe-agent clone at ./agent/mini-swe-agent/
#      (clones from https://github.com/SWE-agent/mini-swe-agent.git if absent).
#   3. Build an isolated uv venv at ./agent/.venv and pip install -e the agent.
#   4. Write ./agent/mini-swe-agent/.env so litellm talks to the tu-zi
#      gateway: OPENAI_API_BASE + OPENAI_API_KEY are set per-run by the
#      wrapper at ./agent/run_mini.sh.
#   5. Drop a small mini.yaml next to the agent for non-default options
#      (cost limit, yolo mode) and a smoke-test that drives a single tool
#      call round-trip through the gateway.
#   6. Run the smoke test.
#
# Idempotent: re-running will reuse the existing clone / venv / config.
# ============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

UPSTREAM_DIR="$REPO_ROOT/agent/mini-swe-agent"
CONFIG_DIR="$REPO_ROOT/agent/config"
VENV_DIR="$REPO_ROOT/agent/.venv"
ENV_FILE="$CONFIG_DIR/.env"
YAML_FILE="$CONFIG_DIR/mini.yaml"
RUNNER="$REPO_ROOT/agent/run_mini.sh"
SMOKE="$CONFIG_DIR/smoke_test.py"

UPSTREAM_REPO="https://github.com/SWE-agent/mini-swe-agent.git"

# ---------------------------------------------------------------------------
# tu-zi gateway configuration
# ---------------------------------------------------------------------------
TUZI_API_KEY="${TUZI_API_KEY:-sk-52RaA81V3pImnAGLRby5kMbDWVVDcXkZkmBPXlj4D7pUxLvv}"
TUZI_BASE_URL="${TUZI_BASE_URL:-https://api.tu-zi.com/v1}"
DEFAULT_MODEL="${DEFAULT_MODEL:-openai/gpt-4o-mini}"
COST_LIMIT="${COST_LIMIT:-3.0}"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
log()  { printf '\033[1;34m[setup]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[setup][warn]\033[0m %s\n' "$*" >&2; }
err()  { printf '\033[1;31m[setup][error]\033[0m %s\n' "$*" >&2; }
die()  { err "$*"; exit 1; }

# ---------------------------------------------------------------------------
# 1. Tooling checks
# ---------------------------------------------------------------------------
need_cmd() {
    command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1 — install it and re-run."
}

need_cmd git
need_cmd python3

PY_MAJOR="$(python3 -c 'import sys; print(sys.version_info.major)')"
PY_MINOR="$(python3 -c 'import sys; print(sys.version_info.minor)')"
if (( PY_MAJOR < 3 || (PY_MAJOR == 3 && PY_MINOR < 10) )); then
    die "Python ≥ 3.10 required (found $PY_MAJOR.$PY_MINOR)."
fi

if ! command -v uv >/dev/null 2>&1; then
    warn "uv not on PATH — installing via pip"
    python3 -m pip install --user uv \
        || die "Failed to install uv. Install it manually: https://docs.astral.sh/uv/"
    export PATH="$HOME/.local/bin:$PATH"
    command -v uv >/dev/null 2>&1 || die "uv still not on PATH after install. Add ~/.local/bin to PATH and re-run."
fi

log "Tooling OK (python $PY_MAJOR.$PY_MINOR, $(git --version), $(uv --version))"

# ---------------------------------------------------------------------------
# 2. Verify / clone upstream
# ---------------------------------------------------------------------------
if [[ ! -d "$UPSTREAM_DIR/.git" ]]; then
    log "Cloning $UPSTREAM_REPO → $UPSTREAM_DIR"
    git clone --depth 1 "$UPSTREAM_REPO" "$UPSTREAM_DIR"
else
    log "Upstream already present at $UPSTREAM_DIR (skipping clone)"
    # Sanity-check it's actually mini-swe-agent and not a stray repo.
    ORIGIN_URL="$(git -C "$UPSTREAM_DIR" config --get remote.origin.url || true)"
    if [[ "$ORIGIN_URL" != *SWE-agent/mini-swe-agent* ]]; then
        die "Upstream at $UPSTREAM_DIR has origin '$ORIGIN_URL' — refusing to touch it."
    fi
fi

# ---------------------------------------------------------------------------
# 3. venv + install
# ---------------------------------------------------------------------------
if [[ ! -d "$VENV_DIR" ]]; then
    log "Creating uv venv at $VENV_DIR"
    uv venv --python 3.11 "$VENV_DIR"
else
    log "Reusing venv at $VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
log "Installing mini-swe-agent (editable) into venv"
uv pip install -e "$UPSTREAM_DIR" >/dev/null

# ---------------------------------------------------------------------------
# 4. Write .env (per-run env loader) — outside the clone so re-clones don't wipe it
# ---------------------------------------------------------------------------
mkdir -p "$CONFIG_DIR"
cat > "$ENV_FILE" <<EOF
# Generated by RQ4 scripts/setup.sh — points litellm at the tu-zi gateway.
# Source this file before running mini-swe-agent:
#     set -a; source $ENV_FILE; set +a
OPENAI_API_KEY=$TUZI_API_KEY
OPENAI_API_BASE=$TUZI_BASE_URL
TUZI_API_KEY=$TUZI_API_KEY
TUZI_BASE_URL=$TUZI_BASE_URL
DEFAULT_MODEL=$DEFAULT_MODEL
COST_LIMIT=$COST_LIMIT
EOF
chmod 600 "$ENV_FILE"
log "Wrote $ENV_FILE (mode 600)"

# Write a fresh .env.example alongside it so re-clones / clean rebuilds
# don't drop the template that's tracked in git.
cat > "$CONFIG_DIR/.env.example" <<EOF
# tu-zi gateway credentials (OpenAI-compatible).
# Copy this file to \`.env\` and fill in the real key, or let scripts/setup.sh
# generate \`.env\` with a sensible default.
TUZI_API_KEY=sk-replace-me
TUZI_BASE_URL=https://api.tu-zi.com/v1

# Default model. Format: openai/<model-id> (litellm routes via the env vars above).
DEFAULT_MODEL=openai/gpt-4o-mini

# Per-run cost limit in USD.
COST_LIMIT=3.0
EOF
log "Wrote $CONFIG_DIR/.env.example"

# ---------------------------------------------------------------------------
# 5. mini.yaml — user-customizable extension point
# ---------------------------------------------------------------------------
# mini-swe-agent's config system SHALLOW-merges top-level keys. Specifying an
# agent block here would WIPE the default system_template / instance_template,
# so by default we leave this empty and pass cost / mode via CLI flags instead.
# Override it only when you need to change prompt templates or the model class.
cat > "$YAML_FILE" <<EOF
# Generated by RQ4 scripts/setup.sh.
# Intentionally empty — see the comment above. Pass options via the
# mini CLI instead, e.g.:
#     mini -c $YAML_FILE --cost-limit 3.0 --yolo -t "..."
# (When you do specify something here, only do so for keys that aren't
# already covered by CLI flags, to avoid clobbering defaults.)
EOF
log "Wrote $YAML_FILE"

# ---------------------------------------------------------------------------
# 6. Wrapper script — single command to invoke the agent
# ---------------------------------------------------------------------------
cat > "$RUNNER" <<EOF
#!/usr/bin/env bash
# run_mini.sh — invoke mini-swe-agent with the tu-zi gateway configured.
# Usage: bash agent/run_mini.sh -t "<task>" [-m <model>] [other mini flags...]
#
# IMPORTANT: we pass BOTH the upstream's built-in mini.yaml AND our local one.
# -c REPLACES the default config (it does not augment it), so if we only passed
# the local one the agent would lose system_template / instance_template.
# mini recursively merges specs left-to-right, so later wins.
#
# --exit-immediately lets the wrapper be used in non-interactive scripts
# (CI / batch runs) without hanging on a stdin prompt at the end.
set -euo pipefail
REPO_ROOT="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")/.." && pwd)"
set -a
source "$ENV_FILE"
set +a
source "$VENV_DIR/bin/activate"
cd "$UPSTREAM_DIR"
exec mini --yolo --cost-limit "\${COST_LIMIT:-3.0}" --exit-immediately \\
    -c "$UPSTREAM_DIR/src/minisweagent/config/mini.yaml" \\
    -c "$YAML_FILE" \\
    "\$@"
EOF
chmod +x "$RUNNER"
log "Wrote $RUNNER"

# ---------------------------------------------------------------------------
# 7. Smoke test — single tool-call round trip through the gateway
# ---------------------------------------------------------------------------
cat > "$SMOKE" <<'PY'
"""Smoke test: verify mini-swe-agent can drive a tool-calling round trip
through the tu-zi gateway.

Bypasses the full agent loop (which wants a TTY in interactive mode) and
exercises the model layer directly — that's the part that actually talks
to the gateway.
"""
import os
import sys
import json

# .env was sourced before we got here, but set defaults defensively.
os.environ.setdefault("OPENAI_API_BASE", os.environ["TUZI_BASE_URL"])
os.environ.setdefault("OPENAI_API_KEY",  os.environ["TUZI_API_KEY"])

from minisweagent.models.litellm_model import LitellmModel

model = LitellmModel(
    model_name=os.environ.get("DEFAULT_MODEL", "openai/gpt-4o-mini"),
    model_kwargs={
        "api_base": os.environ["TUZI_BASE_URL"],
        "api_key":  os.environ["TUZI_API_KEY"],
        "drop_params": True,
    },
)

result = model.query(
    [{"role": "user", "content": "Run `echo PONG` and report the output."}]
)

extra = result.get("extra", {})
actions = extra.get("actions", [])

if not actions:
    print("FAIL: model returned no tool call", file=sys.stderr)
    print(json.dumps(extra.get("response", {}), indent=2, default=str)[:2000], file=sys.stderr)
    sys.exit(1)

cmd = actions[0].get("command", "")
print(f"OK: model returned bash tool call -> {cmd!r}", file=sys.stderr)
print("SMOKE_OK")
PY

log "Running smoke test (one round-trip to $TUZI_BASE_URL)"
set +e
SMOKE_OUTPUT="$(set -a; source "$ENV_FILE"; set +a; python "$SMOKE" 2>&1)"
SMOKE_RC=$?
set -e

echo "$SMOKE_OUTPUT"
if (( SMOKE_RC != 0 )) || ! grep -q '^SMOKE_OK$' <<<"$SMOKE_OUTPUT"; then
    die "Smoke test failed — see output above."
fi

log "✅ Setup complete."
log ""
log "Next steps:"
log "  bash agent/run_mini.sh -t \"<your task here>\" -m $DEFAULT_MODEL"
log ""
log "Files of interest:"
log "  • venv         $VENV_DIR"
log "  • env loader   $ENV_FILE  (source it for custom runs)"
log "  • yaml config  $YAML_FILE"
log "  • upstream     $UPSTREAM_DIR  (read-only clone; do not edit)"
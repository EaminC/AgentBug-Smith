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
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
set -a
source "/home/anonymous/Desktop/RQ4/agent/config/.env"
set +a
source "/home/anonymous/Desktop/RQ4/agent/.venv/bin/activate"
cd "/home/anonymous/Desktop/RQ4/agent/mini-swe-agent"
exec mini --yolo --cost-limit "${COST_LIMIT:-3.0}" --exit-immediately \
    -c "/home/anonymous/Desktop/RQ4/agent/mini-swe-agent/src/minisweagent/config/mini.yaml" \
    -c "/home/anonymous/Desktop/RQ4/agent/config/mini.yaml" \
    "$@"

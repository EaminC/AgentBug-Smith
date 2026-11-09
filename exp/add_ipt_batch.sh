#!/usr/bin/env bash
# Batch-add an in-patch test to many issue JSON files via OpenRouter.
#
# From the AgentBug-Smith repo root:
#   export OPENROUTER_API_KEY=...
#   bash exp/add_ipt_batch.sh data/issues/issues_80
#   bash exp/add_ipt_batch.sh data/issues/issues_80 data/issues/issue_run_new
#   bash exp/add_ipt_batch.sh --limit 1 data/issues/issues_80/*.json
#   bash exp/add_ipt_batch.sh --list files.txt --output data/issues/ipt_batch
#
# One flat directory is written to <name>_ipt/.
# Several directories keep their names under data/issues/ipt_batch/.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ $# -eq 0 ]]; then
  echo "usage: bash exp/add_ipt_batch.sh [--limit N] [--output DIR] JSON_OR_DIR ..." >&2
  exit 1
fi

exec python3 exp/add_ipt_openrouter.py "$@"

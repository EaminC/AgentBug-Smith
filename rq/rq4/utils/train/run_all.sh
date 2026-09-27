#!/usr/bin/env bash
# run_all.sh — train all 6 skills (2 agents × 3 train_sizes).
#
# Each invocation re-uses already-written repos/<owner>__<name>.md files
# unless --force is passed to train_skill.py. To do a full rebuild, pass
# --force on the command line below.
#
# Usage:
#   bash utils/train/run_all.sh                 # train all 6, resume-safe
#   bash utils/train/run_all.sh --dry-run       # print prompts only
#   FORCE=1 bash utils/train/run_all.sh         # wipe & rebuild everything
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

# (agent, train_size) pairs. Per the prompt.md design notes, these three
# sizes hit the three coarse buckets of repo_disjoint.
PAIRS=(
  "mini-swe-agent 40"
  "mini-swe-agent 60"
  "mini-swe-agent 80"
  "openhands 40"
  "openhands 60"
  "openhands 80"
)

if [[ "${FORCE:-0}" == "1" ]]; then
  echo "[run_all] FORCE=1 — wiping agent/skills/"
  rm -rf agent/skills
fi

for pair in "${PAIRS[@]}"; do
  read -r AGENT TS <<<"$pair"
  echo
  echo "=== ${AGENT} / train_size=${TS} ==="
  agent/.venv/bin/python utils/train/train_skill.py \
      --agent "$AGENT" \
      --train-size "$TS" \
      --mode repo_disjoint \
      --seed 42 \
      --out "$REPO_ROOT/agent/skills" \
      "$@"
done

echo
echo "[run_all] done — 6 skills under agent/skills/"

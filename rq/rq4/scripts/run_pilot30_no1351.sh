#!/usr/bin/env bash
# run_pilot30_no1351.sh — like run_pilot30 but excludes issue-1351.
#
# Flags:
#   CLEANUP_IMAGES=1   remove each row's docker image after both skill
#                      modes finish (saves ~1-3 GB per row, disables
#                      cross-batch image reuse). Default: off.
#   PRUNE_AT_END=1     at the end of the run, run
#                      `solve.py prune-images` to sweep all rq4-* images.
#                      Default: on (the Mac nearly filled up; be safe).
set -u
cd "$(dirname "$0")/.."

LOG_DIR=logs/pilot30
mkdir -p "$LOG_DIR"

CLEANUP_FLAG=""
if [[ "${CLEANUP_IMAGES:-0}" == "1" ]]; then
    CLEANUP_FLAG="--cleanup-images"
fi

PRUNE_AT_END="${PRUNE_AT_END:-1}"

COMBOS=(mini-swe-agent_40 mini-swe-agent_60 mini-swe-agent_80 openhands_40 openhands_60 openhands_80)

for combo in "${COMBOS[@]}"; do
  echo "=== $(date +%H:%M:%S) START $combo ===" | tee -a "$LOG_DIR/summary_no1351.log"
  python3 -u utils/verify/solve.py rollout \
    --index "data/verify/issue_index_pilot30_${combo}_no1351.jsonl" \
    --skill-mode all \
    --max-rows 4 \
    $CLEANUP_FLAG \
    2>&1 | tee "$LOG_DIR/${combo}_no1351.log"
  ec=$?
  echo "=== $(date +%H:%M:%S) DONE $combo exit=$ec ===" | tee -a "$LOG_DIR/summary_no1351.log"
done

if [[ "$PRUNE_AT_END" == "1" ]]; then
  echo "=== $(date +%H:%M:%S) PRUNE rq4-* images ===" | tee -a "$LOG_DIR/summary_no1351.log"
  python3 -u utils/verify/solve.py prune-images 2>&1 | tee -a "$LOG_DIR/prune.log"
fi

echo "=== ALL DONE $(date +%H:%M:%S) ===" | tee -a "$LOG_DIR/summary_no1351.log"

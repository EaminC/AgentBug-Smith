#!/usr/bin/env bash
# End-to-end from your issue_pr_map.json: no top-repos, no full-repo PR fetch.
# Flow: fetch PRs in map -> build instances -> version -> SWE-Builder -> Fail2Pass -> judge.
# Usage: ./baseline/run_e2e_from_issue_map.sh [issue_pr_map.json]
# Example: ./baseline/run_e2e_from_issue_map.sh baseline/issue_pr_map.json

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

INPUT_MAP="${1:-}"
if [[ -z "$INPUT_MAP" ]]; then
  echo "Usage: $0 <issue_pr_map.json>" >&2
  echo "Example: $0 baseline/issue_pr_map.json" >&2
  exit 1
fi
if [[ ! -f "$INPUT_MAP" ]]; then
  echo "File not found: $INPUT_MAP" >&2
  exit 1
fi

TS="$(date +%Y%m%d_%H%M%S)"
RUN_DIR="data/runs/${TS}"
OUTPUT_BASE="output/run_${TS}"
RUN_INSTANCES_DIR="run_instances"
RUN_ID="run_${TS}"
REPORTS_DIR="reports"

mkdir -p "$RUN_DIR" "$REPORTS_DIR"

PRS="${RUN_DIR}/prs.jsonl"
INSTANCES="${RUN_DIR}/instances.jsonl"
# get_version writes instances_versions.jsonl next to instances.jsonl
INSTANCES_VERSIONS="${RUN_DIR}/instances_versions.jsonl"
RESULTS_JSON="${OUTPUT_BASE}/results/results.json"
GOLD_DIR="${RUN_INSTANCES_DIR}/${RUN_ID}/gold"
JUDGE_JSON="${REPORTS_DIR}/${RUN_ID}_gold.json"

echo "=============================================="
echo "Input: $INPUT_MAP"
echo "Timestamp: $TS"
echo "Run dir / output: $RUN_DIR, $OUTPUT_BASE, $RUN_INSTANCES_DIR"
echo "=============================================="

# 1. Fetch PRs listed in issue_pr_map -> prs.jsonl
echo "[1/6] fetch_prs_from_issue_map ..."
python data_collection/collect/fetch_prs_from_issue_map.py \
  "$INPUT_MAP" \
  "$PRS" \
  --language python

# 2. Build task instances
echo "[2/6] build_dataset ..."
python data_collection/collect/build_dataset.py \
  "$PRS" \
  "$INSTANCES" \
  --language python

# 3. Version tagging
echo "[3/6] get_version ..."
python data_collection/collect/get_version.py \
  --instance_path "$INSTANCES" \
  --testbed "${RUN_DIR}/github_testbed" \
  --max-workers 20

# 4. SWE-Builder
echo "[4/6] SWE-Builder (app.main swe-bench) ..."
python -m app.main swe-bench \
  --model tensorblock/gpt-4.1-mini \
  --tasks-map "$INSTANCES_VERSIONS" \
  --num-processes 10 \
  --model-temperature 0.2 \
  --conv-round-limit 10 \
  --output-dir "${OUTPUT_BASE}/mypy" \
  --setup-dir "testbed" \
  --results-path "${OUTPUT_BASE}/results"

# 5. Fail2Pass validation (dataset = results, not predictions)
echo "[5/6] run_evaluation (Fail2Pass) ..."
python evaluation/run_evaluation.py \
  --dataset_name "${OUTPUT_BASE}/results/results.json" \
  --predictions_path "gold" \
  --max_workers 5 \
  --run_id "$RUN_ID" \
  --output_path "$RUN_INSTANCES_DIR" \
  --timeout 3600 \
  --is_judge_fail2pass

# 6. Classify Fail2Pass status
echo "[6/6] judge_fail2pass ..."
if [[ -d "$GOLD_DIR" ]]; then
  python scripts/judge_fail2pass.py \
    "$GOLD_DIR" \
    "$JUDGE_JSON"
  echo "Report: $JUDGE_JSON"
else
  echo "Directory not found: $GOLD_DIR, skipping judge_fail2pass"
fi

echo "=============================================="
echo "Done. Timestamp: $TS"
echo "Intermediate: $RUN_DIR (prs, instances, instances_versions)"
echo "SWE-Builder: $OUTPUT_BASE"
echo "Fail2Pass logs: ${RUN_INSTANCES_DIR}/${RUN_ID}"
echo "=============================================="

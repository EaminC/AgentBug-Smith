#!/usr/bin/env bash
# End-to-end pipeline with a single master .txt log file
# Usage: ./run_pipeline.sh [issue_pr_map.json]
# Example: ./run_pipeline.sh baseline/issue_pr_map.json

set -euo pipefail

# ==============================================================================
# 0. ENVIRONMENT & SETUP
# ==============================================================================
echo "=============================================="
echo "Initializing Environment..."
echo "=============================================="

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [[ -f ".env" ]]; then
    echo "Loading variables from .env..."
    export $(grep -v '^#' .env | tr -d '\r' | xargs)
else
    echo "ERROR: .env file not found! Please create one." >&2
    exit 1
fi

if [[ -z "${FORGE_API_KEY:-}" ]]; then
    echo "ERROR: FORGE_API_KEY is missing in .env" >&2
    exit 1
fi

if [[ -z "${MODEL:-}" ]]; then
    echo "ERROR: MODEL is missing in .env (e.g., MODEL=tensorblock/gpt-4.1-mini)" >&2
    exit 1
fi

if ! docker info > /dev/null 2>&1; then
  echo "ERROR: Docker is not running or you don't have permissions." >&2
  exit 1
fi

# Safely append to PYTHONPATH even if it was previously empty
export PYTHONPATH="$REPO_ROOT:${PYTHONPATH:-}"

INPUT_MAP="${1:-}"
if [[ -z "$INPUT_MAP" ]] || [[ ! -f "$INPUT_MAP" ]]; then
  echo "Usage: $0 <issue_pr_map.json>" >&2
  exit 1
fi

count_jsonl() { if [[ -f "$1" ]]; then wc -l < "$1" | tr -d ' '; else echo "0"; fi }
count_json() { if [[ -f "$1" ]]; then python -c "import json; d=json.load(open('$1')); print(len(d) if isinstance(d, (list, dict)) else 0)" 2>/dev/null || echo "0"; else echo "0"; fi }

# ==============================================================================
# 1. INITIALIZE TRACKING & DIRECTORIES
# ==============================================================================
TS="$(date +%Y%m%d_%H%M%S)"
RUN_DIR="data/runs/${TS}"
OUTPUT_BASE="output/run_${TS}"
RUN_INSTANCES_DIR="run_instances"
RUN_ID="run_${TS}"
REPORTS_DIR="reports"
LOG_FILE="${RUN_DIR}/pipeline_log.txt"

mkdir -p "$RUN_DIR" "$REPORTS_DIR" "$OUTPUT_BASE"

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
echo "All output will be logged to: $LOG_FILE"
echo "=============================================="

# ==============================================================================
# 2. PIPELINE EXECUTION (Wrapped to capture all logs)
# ==============================================================================
{
  # Track start time (epoch seconds)
  PIPELINE_START_TIME=$(date +%s)
    echo "Starting cost tracker..."
    python stats/entry.py start || echo "Warning: Failed to start stats tracker"

    echo -e "\n[1/6] Fetching PRs from issue map..."
    python data_collection/collect/fetch_prs_from_issue_map.py "$INPUT_MAP" "$PRS" --language python
    COUNT_PRS=$(count_jsonl "$PRS")
    echo " -> Remaining after Step 1: $COUNT_PRS PRs"

    echo -e "\n[2/6] Building dataset instances..."
    python data_collection/collect/build_dataset.py "$PRS" "$INSTANCES" --language python
    COUNT_INSTANCES=$(count_jsonl "$INSTANCES")
    echo " -> Remaining after Step 2: $COUNT_INSTANCES instances"

    echo -e "\n[3/6] Fetching version tags..."
    python data_collection/collect/get_version.py --instance_path "$INSTANCES" --testbed "${RUN_DIR}/github_testbed" --max-workers 20
    COUNT_VERSIONS=$(count_jsonl "$INSTANCES_VERSIONS")
    echo " -> Remaining after Step 3: $COUNT_VERSIONS versioned instances"

    echo -e "\n[4/6] Running SWE-Builder (Agent Inference)..."
    # If there are no versioned instances, skip the agent inference step.
    if [[ -f "$INSTANCES_VERSIONS" ]] && [[ $(count_jsonl "$INSTANCES_VERSIONS") -gt 0 ]]; then
      python -m app.main swe-bench \
        --model "$MODEL" \
        --tasks-map "$INSTANCES_VERSIONS" \
        --num-processes 10 \
        --model-temperature 0.2 \
        --conv-round-limit 10 \
        --output-dir "${OUTPUT_BASE}/mypy" \
        --setup-dir "testbed" \
        --results-path "${OUTPUT_BASE}/results"
      COUNT_RESULTS=$(count_json "$RESULTS_JSON")
      echo " -> Remaining after Step 4: $COUNT_RESULTS agent results"
    else
      echo " -> No versioned instances found; skipping SWE-Builder (Step 4)."
      COUNT_RESULTS=0
    fi

    if [[ "$COUNT_RESULTS" -gt 0 ]]; then
      echo -e "\n[5/6] Running Fail2Pass evaluation..."
      python evaluation/run_evaluation.py \
        --dataset_name "$RESULTS_JSON" \
        --predictions_path "gold" \
        --max_workers 5 \
        --run_id "$RUN_ID" \
        --output_path "$RUN_INSTANCES_DIR" \
        --timeout 3600 \
        --is_judge_fail2pass
    else
      echo "\n[5/6] Skipping Fail2Pass evaluation because no agent results were produced."
    fi

    echo -e "\n[6/6] Classifying Fail2Pass Status..."
    if [[ -d "$GOLD_DIR" ]]; then
      python scripts/judge_fail2pass.py "$GOLD_DIR" "$JUDGE_JSON"
      echo "Report generated: $JUDGE_JSON"
    else
      echo "Directory not found: $GOLD_DIR, skipping judge_fail2pass"
    fi

    # ==============================================================================
    # 3. END TRACKING & METRICS REPORT
    # ==============================================================================
    echo "Waiting 5 seconds for API metrics to sync..."
    sleep 5

    echo "\nEnding cost tracker..."
    python stats/entry.py end || echo "Warning: Failed to end stats tracker"

    # Calculate and print total duration
    PIPELINE_END_TIME=$(date +%s)
    PIPELINE_DURATION=$((PIPELINE_END_TIME - PIPELINE_START_TIME))
    DURATION_HR=$((PIPELINE_DURATION / 3600))
    DURATION_MIN=$(((PIPELINE_DURATION % 3600) / 60))
    DURATION_SEC=$((PIPELINE_DURATION % 60))

    echo -e "\n=============================================="
    echo "          PIPELINE FUNNEL REPORT              "
    echo "=============================================="
    echo "1. Initial JSON map        : $(count_json "$INPUT_MAP") items"
    echo "2. Fetched PRs             : $COUNT_PRS"
    echo "3. Built Instances         : $COUNT_INSTANCES"
    echo "4. Versioned Instances     : $COUNT_VERSIONS"
    echo "5. Agent Results Generated : $COUNT_RESULTS"

    echo "=============================================="
    echo "Master Log File   : $LOG_FILE"
    echo "SWE-Builder output: $OUTPUT_BASE"
    echo "Fail2Pass logs    : ${RUN_INSTANCES_DIR}/${RUN_ID}"
    echo "=============================================="
    echo "Total pipeline duration: ${DURATION_HR}h ${DURATION_MIN}m ${DURATION_SEC}s"

} 2>&1 | tee -a "$LOG_FILE"
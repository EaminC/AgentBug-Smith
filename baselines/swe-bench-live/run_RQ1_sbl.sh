#!/usr/bin/env bash
# SWE-bench-Live End-to-End Pipeline with Telemetry, Logging, & Funnel Report

# Exit immediately if a command fails, treat unset variables as an error
set -euo pipefail

# This allows 'conda activate' to work inside a bash script
eval "$(conda shell.bash hook)"

ENV_NAME="sbl"
ENV_PATH="/home/cc/miniconda3/envs/$ENV_NAME"

echo "============================================================"
echo " Provisioning Conda Environment: $ENV_NAME"
echo "============================================================"

if ! conda info --envs | grep -q "^$ENV_NAME "; then
    echo "Creating new conda environment '$ENV_NAME' with Python 3.12..."
    conda create -y -n "$ENV_NAME" python=3.12
else
    echo "Environment '$ENV_NAME' already exists. Skipping creation."
fi

echo "Activating '$ENV_NAME'..."
conda activate "$ENV_NAME"

echo "Installing core dependencies..."
# Direct call to the env's python to run pip
"$ENV_PATH/bin/python" -m pip install --upgrade pip
"$ENV_PATH/bin/python" -m pip install openai requests python-dotenv python-dateutil

# Install the editable package
echo "Installing SWE-bench-Live in editable mode..."
"$ENV_PATH/bin/python" -m pip install -e . "chardet<6"

# ==============================================================================
# LOGGING, TELEMETRY, & PATH SETUP
# ==============================================================================
SBL_ROOT="/home/cc/SWE-bench-Live"
INPUT_MAP="baseline/issue_pr_map.json"
ORGANIZE_JSONL="launch/data/sbl_baseline/organize.jsonl"
VALIDATED_JSONL="logs/val/validated_instances.jsonl"
SUMMARY_JSON="baseline/sf_judge_f2p_summary.json"

# Overall timeout for Step 9 (seconds). Can be overridden in environment.
STEP9_TIMEOUT=${STEP9_TIMEOUT:-3600} # default 2 hours

# Setup master logging directory
LOG_DIR="$SBL_ROOT/logs/runs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/pipeline_$(date +%Y%m%d_%H%M%S).log"

# Redirect ALL script output (stdout and stderr) to both the terminal and the log file
exec > >(tee -a "$LOG_FILE") 2>&1

# Helper functions for calculations and formatting
count_jsonl() { if [[ -f "$1" ]]; then wc -l < "$1" | tr -d ' '; else echo "0"; fi }
count_json() { if [[ -f "$1" ]]; then python -c "import json; d=json.load(open('$1')); print(len(d) if isinstance(d, (list, dict)) else 0)" 2>/dev/null || echo "0"; else echo "0"; fi }
format_duration() {
    local total_seconds=$1
    local hours=$((total_seconds / 3600))
    local minutes=$(((total_seconds % 3600) / 60))
    local seconds=$((total_seconds % 60))
    printf "%02d:%02d:%02d" "$hours" "$minutes" "$seconds"
}

# --- START PIPELINE TIMER ---
PIPELINE_START_TS=$(date +%s)

echo "============================================================"
echo " Starting SWE-bench-Live Pipeline"
echo " Master Log File: $LOG_FILE"
echo "============================================================"

# ==============================================================================
# Step 1: Activate conda environment
# ==============================================================================
echo -e "\n[1] Activating Conda environment (sbl)..."
if ! conda info --envs | grep -q "^sbl "; then
    echo "ERROR: Conda environment 'sbl' not found."
    echo "Please execute 'bash setup_env.sh' to provision the infrastructure before running the pipeline."
    exit 1
fi
conda activate sbl

# ==============================================================================
# INITIALIZE TOKEN TRACKING
# ==============================================================================
STATS_SCRIPT="$SBL_ROOT/stats/entry.py"
echo -e "\n[Telemetry] Starting token and cost tracker..."
if [[ -f "$STATS_SCRIPT" ]]; then
    "$ENV_PATH/bin/python" "$STATS_SCRIPT" start || echo "Warning: Failed to start stats tracker."
else
    echo "Warning: Stats script not found at $STATS_SCRIPT"
fi

# ==============================================================================
# Step 2: Prepare Pull2Issue
# ==============================================================================
echo -e "\n[2] Preparing Pull2Issue from Map..."
cd baseline/
"$ENV_PATH/bin/python" sbl_prepare_pull2issue_from_issue_pr_map.py \
  --input issue_pr_map.json \
  --cutoff_date 20090101 \
  --gh_token_file tokens.txt \
  --token_id 0

# ==============================================================================
# Step 3: Install Root Dependencies
# ==============================================================================
echo -e "\n[3] Go back to root SWE-bench-Live..."
cd ..


# ==============================================================================
# Step 4: Curation Pipeline
# ==============================================================================
echo -e "\n[4] Running Curation Pipeline (setup.sh)..."
bash baseline/setup.sh 

# ==============================================================================
# Step 5: Prepare Launch Config
# ==============================================================================
echo -e "\n[5] Merging Task Instances & Preparing Launch Config..."
"$ENV_PATH/bin/python" baseline/sbl_step3_prepare_launch_dataset.py

# ==============================================================================
# Step 6: Export API Keys
# ==============================================================================
echo -e "\n[6] Exporting API Keys..."
# REMINDER: Replace these placeholders with your actual keys before running!
export OPENAI_API_KEY=forge-key
export TAVILY_API_KEY=tvly-dev-key
export OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1

# ==============================================================================
# Step 7: RepoLaunch Execution
# ==============================================================================
echo -e "\n[7] Executing RepoLaunch (Generating testable containers)..."
cd launch/
"$ENV_PATH/bin/python" -m pip install -e .
"$ENV_PATH/bin/python" -m launch.run --config-path data/sbl_baseline/config.json

# ==============================================================================
# Step 8: Validation (F2P Dataset)
# ==============================================================================
echo -e "\n[8] Building F2P Dataset (Validation)..."
cd ..
"$ENV_PATH/bin/python" -m evaluation.validation \
  --input_dir "$ORGANIZE_JSONL" \
  --platform linux \
  --workers 4 \
  --output_dir logs/val \
  --overwrite 1

# ==============================================================================
# Step 9: Prepare Judge Folder
# ==============================================================================
echo -e "\n[9] Preparing SWE-Factory Judge format..."
if ! timeout --preserve-status --kill-after=60s "$STEP9_TIMEOUT" \
    "$ENV_PATH/bin/python" baseline/sf_make_judge_f2p_folder_from_organize_jsonl.py \
      --input "$ORGANIZE_JSONL" \
      --out-dir baseline/sf_judge_f2p_outputs \
      --platform linux \
      --workers 2 \
      --timeout-s 1200 \
      --overwrite 1
then
  echo "Warning: Step 9 timed out or exited with non-zero status. Continuing pipeline." >&2
fi

# ==============================================================================
# Step 10: Judge Fail2Pass
# ==============================================================================
echo -e "\n[10] Classifying Fail2Pass Status (SWE-Factory)..."
"$ENV_PATH/bin/python" baseline/judge_fail2pass.py \
  "$SBL_ROOT/baseline/sf_judge_f2p_outputs" \
  "$SBL_ROOT/$SUMMARY_JSON" \
  --processes 20

# ==============================================================================
# FINALIZE TOKEN TRACKING
# ==============================================================================
echo -e "\n[Telemetry] Waiting 5 seconds for API metrics to sync..."
sleep 5
echo "Ending cost tracker..."
if [[ -f "$STATS_SCRIPT" ]]; then
    "$ENV_PATH/bin/python" "$STATS_SCRIPT" end || echo "Warning: Failed to end stats tracker."
fi

# --- END PIPELINE TIMER ---
PIPELINE_END_TS=$(date +%s)
PIPELINE_DURATION_SEC=$((PIPELINE_END_TS - PIPELINE_START_TS))

# ==============================================================================
# SBL PIPELINE FUNNEL REPORT
# ==============================================================================
echo -e "\n=============================================="
echo "       SBL PIPELINE FUNNEL REPORT             "
echo "=============================================="
echo "1. Initial JSON map        : $(count_json "$INPUT_MAP") items"
echo "2. RepoLaunch Generated    : $(count_jsonl "$ORGANIZE_JSONL") instances (organize.jsonl)"
echo "3. Validated F2P/P2P       : $(count_jsonl "$VALIDATED_JSONL") instances"
echo "=============================================="
echo "Pipeline Duration : $(format_duration $PIPELINE_DURATION_SEC) ($PIPELINE_DURATION_SEC total seconds)"
echo "Master Log File   : $LOG_FILE"
echo "SWE-Factory Judge : $SBL_ROOT/$SUMMARY_JSON"
echo "=============================================="

echo -e "\n============================================================"
echo " ✓ Pipeline Completed Successfully!"
echo "============================================================"
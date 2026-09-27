#!/usr/bin/env bash
# Environment Provisioning for SWE-bench-Live Pipeline

# Exit immediately if a command fails, treat unset variables as an error
set -euo pipefail

# Initialize conda for bash script execution
eval "$(conda shell.bash hook)"

ENV_NAME="sbl-main"

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
pip install openai requests

# Pinning chardet<6 to prevent the RequestsDependencyWarning
pip install -e . "chardet<6"

echo "============================================================"
echo " ✓ Environment provisioning complete."
echo "   You may now execute 'run_RQ1_sbl.sh'."
echo "============================================================"
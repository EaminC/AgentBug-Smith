#!/usr/bin/env bash
# run_openhands.sh — invoke the OpenHands CLI headless with our env loaded.
# Usage: bash agent/run_openhands.sh -t "your task"   (or pass any openhands flags)
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
set -a
source "/home/anonymous/Desktop/RQ4/agent/openhands-config/.env"
set +a
exec openhands --headless --override-with-envs --yolo "$@"

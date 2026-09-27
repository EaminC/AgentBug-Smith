#!/usr/bin/env bash
# Smoke test for the OpenHands CLI: issues a tiny task and verifies that
# the agent actually produced the requested artifact. This exercises:
#   - wrapper / .env loading
#   - --override-with-envs flowing LLM_API_KEY / LLM_BASE_URL / LLM_MODEL
#     into the CLI
#   - the tu-zi gateway responding
#   - the agent's tool-execution sandbox (writing files to a tmp dir)
set -euo pipefail

WORK_DIR="$(mktemp -d /tmp/rq4-oh-smoke.XXXXXX)"
EXPECTED_FILE="$WORK_DIR/smoke.txt"
EXPECTED_CONTENT="rq4-component2-smoke"
LOG_FILE="$WORK_DIR/trajectory.log"

cleanup() {
    rm -rf "$WORK_DIR"
}
trap cleanup EXIT

echo "[smoke] work dir:    $WORK_DIR"
echo "[smoke] expected:     $EXPECTED_FILE"
echo "[smoke] trajectory:   $LOG_FILE"

cd "$WORK_DIR"
# Issue a simple task the agent can complete in one turn.
# Headless mode already auto-approves, but --yolo is defensive.
openhands --headless --override-with-envs --yolo \
    --exit-without-confirmation \
    --json \
    -t "Create a file at $EXPECTED_FILE containing exactly the text '$EXPECTED_CONTENT' (no other characters, no trailing newline). Just write the file and stop — do not run any other commands." \
    >"$LOG_FILE" 2>&1

if [[ ! -f "$EXPECTED_FILE" ]]; then
    echo "[smoke] FAIL: $EXPECTED_FILE was not created." >&2
    echo "[smoke] trajectory (tail):" >&2
    tail -n 60 "$LOG_FILE" >&2 || true
    exit 1
fi

ACTUAL_CONTENT="$(cat "$EXPECTED_FILE")"
if [[ "$ACTUAL_CONTENT" != "$EXPECTED_CONTENT" ]]; then
    echo "[smoke] FAIL: expected '$EXPECTED_CONTENT', got '$ACTUAL_CONTENT'" >&2
    tail -n 60 "$LOG_FILE" >&2 || true
    exit 1
fi

echo "[smoke] OK: $EXPECTED_FILE contains the requested text"
echo "SMOKE_OK"

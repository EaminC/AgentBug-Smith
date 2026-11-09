#!/usr/bin/env bash
# Rebuttal3 baseline that fills a one-shot agentless test_patch when the PR has none.
# Usage: ./run_rebuttal3_swe-factory_agentless_ipt.sh <issue_pr_map.json>
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/run_rebuttal3_swe-factory_ipt.sh" agentless "$@"

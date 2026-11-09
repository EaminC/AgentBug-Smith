#!/usr/bin/env bash
# Rebuttal3 baseline that keeps instances with no in-patch test.
# Usage: ./run_rebuttal3_swe-factory_keep_no_ipt.sh <issue_pr_map.json>
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/run_rebuttal3_swe-factory_ipt.sh" keep "$@"

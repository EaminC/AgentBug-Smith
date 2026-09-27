#!/bin/bash
# Example: Run merge tool with different modes

echo "=== Example 1: Simple mode (default) - repository names list only ==="
python main.py

echo ""
echo "=== Example 2: Detailed mode - with stars, sources and statistics ==="
python main.py --detailed

echo ""
echo "=== Example 3: Custom output path ==="
# python main.py --output ~/my_agent_repos.json

echo ""
echo "=== Example 4: Specify data directory ==="
# python main.py --data-dir /path/to/your/data

echo ""
echo "Done! View output file:"
echo "  cat /home/cc/SWGENT-Bench/data/hooked_repo/agent_repo.json"


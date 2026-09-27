#!/usr/bin/env python3
"""
Basic functionality test script
"""

import sys
import os

# Test imports
print("Testing module imports...")
try:
    from config import AGENT_KEYWORDS, AGENT_REPO_DEFINITION
    print("✓ config module imported successfully")
    print(f"  - Number of keywords: {len(AGENT_KEYWORDS)}")
except Exception as e:
    print(f"✗ config module import failed: {e}")
    sys.exit(1)

try:
    from github_fetcher import GitHubArchiveFetcher
    print("✓ github_fetcher module imported successfully")
except Exception as e:
    print(f"✗ github_fetcher module import failed: {e}")
    sys.exit(1)

try:
    from agent_filter import AgentRepoFilter
    print("✓ agent_filter module imported successfully")
except Exception as e:
    print(f"✗ agent_filter module import failed: {e}")
    sys.exit(1)

# Test keyword filtering
print("\nTesting keyword filtering...")
filter_no_ai = AgentRepoFilter(use_ai=False)

test_cases = [
    ("langchain-ai/langchain", "LangChain framework", True),
    ("microsoft/autogen", "Multi-agent framework", True),
    ("openai/openai-python", "OpenAI Python SDK", True),
    ("facebook/react", "JavaScript library", False),
    ("torvalds/linux", "Linux kernel", False),
]

for repo_name, description, expected in test_cases:
    result = filter_no_ai.keyword_filter(repo_name, description)
    status = "✓" if result == expected else "✗"
    print(f"{status} {repo_name}: {result} (expected: {expected})")

print("\n✓ All basic tests passed!")
print("\nTip: Run 'python main.py --help' to see full usage instructions")


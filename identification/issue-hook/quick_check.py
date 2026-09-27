#!/usr/bin/env python3
"""
Quick Check Script for Agent Issue Detection
Quick validation tool to check if a single issue/PR would be classified as an agent issue
"""

import sys
import re
from issue_crawler import GitHubIssueCrawler


def check_agent_issue_only(repo, issue_number, github_token=None):
    """
    只做「是否为 agent issue」判断：用 crawler 拉取 issue，再用 AI（_is_agent_issue）判断。
    不检查 closed、关联 PR、是否合并等。供 RQ2 等复用。

    Args:
        repo: "owner/repo"
        issue_number: issue 号
        github_token: 可选

    Returns:
        (is_agent: bool, llm_response: str, issue: dict | None) 拉取失败或为 PR 时 issue 为 None、llm_response 为空串，is_agent 为 False
    """
    crawler = GitHubIssueCrawler(repo, github_token, use_local_clone=False)
    url = f"{crawler.base_url}/repos/{repo}/issues/{issue_number}"
    issue = crawler._make_request(url)
    if not issue or "pull_request" in issue:
        return False, "", None
    is_agent, llm_response = crawler._is_agent_issue(issue)
    return is_agent, (llm_response or "").strip(), issue


def parse_input(input_str):
    """
    Parse input string to extract repo and issue number
    
    Supports:
    - URL: https://github.com/owner/repo/issues/123
    - URL: https://github.com/owner/repo/pull/456
    - Format: owner/repo#123
    - Direct number (requires repo parameter)
    
    Returns:
        (repo, issue_number) tuple or (None, None) if parsing fails
    """
    # Try URL format
    url_pattern = r'github\.com/([^/]+/[^/]+)/(?:issues|pull)/(\d+)'
    match = re.search(url_pattern, input_str)
    if match:
        return match.group(1), int(match.group(2))
    
    # Try owner/repo#123 format
    short_pattern = r'([^/]+/[^#]+)#(\d+)'
    match = re.match(short_pattern, input_str)
    if match:
        return match.group(1), int(match.group(2))
    
    # Try direct number
    if input_str.isdigit():
        return None, int(input_str)
    
    return None, None


def quick_check(repo, issue_number, github_token=None):
    """
    Quick check if an issue would be classified as an agent issue
    
    Args:
        repo: Repository in format "owner/repo"
        issue_number: Issue or PR number
        github_token: Optional GitHub token
        
    Returns:
        None (prints results to console)
    """
    print(f"\n{'='*70}")
    print(f"Quick Check: {repo} #{issue_number}")
    print(f"{'='*70}\n")
    
    # Create crawler instance (no local clone, just API mode)
    crawler = GitHubIssueCrawler(repo, github_token, use_local_clone=False)
    
    # Fetch issue data
    print(f"[Step 1/5] Fetching issue data...")
    url = f"{crawler.base_url}/repos/{repo}/issues/{issue_number}"
    issue = crawler._make_request(url)
    
    if not issue:
        print(f"✗ Failed to fetch issue #{issue_number}")
        return
    
    # Check if it's a PR (GitHub API returns PRs in issues endpoint)
    if 'pull_request' in issue:
        print(f"✓ Found (this is a Pull Request)")
    else:
        print(f"✓ Found (this is an Issue)")
    
    print(f"  Title: {issue.get('title', 'N/A')}")
    print(f"  State: {issue.get('state', 'N/A')}")
    print(f"  URL: {issue.get('html_url', 'N/A')}")
    
    # Check 1: Is closed?
    print(f"\n[Step 2/5] Checking if closed...")
    if issue.get('state') != 'closed':
        print(f"✗ FAILED: Issue is not closed (state: {issue.get('state')})")
        print(f"\n{'='*70}")
        print(f"Result: Would NOT be processed (not closed)")
        print(f"{'='*70}\n")
        return
    print(f"✓ PASS: Issue is closed")
    
    # Check 2: Has text description?
    print(f"\n[Step 3/5] Checking if has text description...")
    if not crawler._has_text_description(issue):
        print(f"✗ FAILED: No text description")
        print(f"\n{'='*70}")
        print(f"Result: Would NOT be processed (no description)")
        print(f"{'='*70}\n")
        return
    print(f"✓ PASS: Has text description")
    
    # Check 3: Has linked PRs?
    print(f"\n[Step 4/5] Checking linked PRs...")
    linked_prs = crawler._get_issue_linked_prs(issue_number, issue.get('body', ''))
    
    if not linked_prs:
        print(f"✗ FAILED: No linked PRs found")
        print(f"\n{'='*70}")
        print(f"Result: Would NOT be processed (no linked PRs)")
        print(f"{'='*70}\n")
        return
    
    print(f"✓ PASS: Found {len(linked_prs)} linked PR(s)")
    for pr in linked_prs:
        print(f"  - PR #{pr['number']}: {pr['title']} (merged: {pr.get('merged', False)})")
    
    # Check 4: Has PR merged to main?
    print(f"\n[Step 5/5] Checking if any PR is merged to main/master...")
    merged_prs = [pr for pr in linked_prs if crawler._check_pr_merged_to_main(pr)]
    
    if not merged_prs:
        print(f"✗ FAILED: No PRs merged to main/master branch")
        print(f"\n{'='*70}")
        print(f"Result: Would NOT be processed (no PRs merged to main)")
        print(f"{'='*70}\n")
        return
    
    print(f"✓ PASS: {len(merged_prs)} PR(s) merged to main/master")
    for pr in merged_prs:
        print(f"  - PR #{pr['number']}: {pr['title']} (base: {pr.get('base_branch', 'N/A')})")
    
    # All checks passed, now do AI judgment
    print(f"\n[AI Judgment] Checking if this is an agent issue...")
    is_agent, ai_response = crawler._is_agent_issue(issue)
    
    print(f"\n{'='*70}")
    if is_agent:
        print(f"✓✓ Result: Would be ACCEPTED as an agent issue")
    else:
        print(f"✗✗ Result: Would be REJECTED (not an agent issue)")
    print(f"{'='*70}")
    
    print(f"\nAI Reasoning:")
    print(f"{ai_response}")
    print(f"\n{'='*70}\n")


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Quick Check: Validate if an issue/PR would be classified as an agent issue',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using full GitHub URL
  python quick_check.py https://github.com/TsinghuaDatabaseGroup/DB-GPT/issues/123
  
  # Using owner/repo#number format
  python quick_check.py TsinghuaDatabaseGroup/DB-GPT#123
  
  # Using separate repo and issue number
  python quick_check.py TsinghuaDatabaseGroup/DB-GPT 123
  
  # Check a Pull Request
  python quick_check.py https://github.com/TsinghuaDatabaseGroup/DB-GPT/pull/456
  
  # With GitHub token
  python quick_check.py TsinghuaDatabaseGroup/DB-GPT#123 --token YOUR_TOKEN
        """
    )
    
    parser.add_argument('input', type=str, 
                       help='Issue/PR identifier (URL, owner/repo#number, or just number)')
    parser.add_argument('number', type=int, nargs='?',
                       help='Issue/PR number (optional, if not in first argument)')
    parser.add_argument('--token', type=str, 
                       help='GitHub API token (or set GITHUB_TOKEN env var)')
    
    args = parser.parse_args()
    
    # Parse input
    repo, issue_number = parse_input(args.input)
    
    # If number provided separately, use it
    if args.number:
        if not repo:
            repo = args.input
        issue_number = args.number
    
    # Validate
    if not repo or not issue_number:
        print("Error: Could not parse repository and issue number")
        print("\nPlease use one of the following formats:")
        print("  - https://github.com/owner/repo/issues/123")
        print("  - owner/repo#123")
        print("  - owner/repo 123")
        sys.exit(1)
    
    # Run quick check
    try:
        quick_check(repo, issue_number, args.token)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()


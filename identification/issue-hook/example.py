#!/usr/bin/env python3
"""
Example script
Demonstrates how to use issue_crawler
"""

from issue_crawler import GitHubIssueCrawler
import os

def main():
    # Example: Crawl TsinghuaDatabaseGroup/DB-GPT repository
    print("="*60)
    print("Example: Crawling agent issues from TsinghuaDatabaseGroup/DB-GPT")
    print("="*60)
    
    repo = "TsinghuaDatabaseGroup/DB-GPT"
    
    # Get GitHub token from environment variable (if available)
    github_token = os.getenv("GITHUB_TOKEN")
    
    if not github_token:
        print("Note: GITHUB_TOKEN environment variable not set")
        print("Recommended to set it to avoid API rate limits")
        print("export GITHUB_TOKEN=your_token_here")
        print()
    
    # Create crawler instance - using local clone mode (recommended)
    # use_local_clone=True: will clone repo locally for analysis, more accurate
    # use_local_clone=False: only use GitHub API, faster but may miss some associations
    # max_workers: number of concurrent workers for filtering (default: 5, increase for faster processing)
    crawler = GitHubIssueCrawler(
        repo, 
        github_token, 
        use_local_clone=True,
        max_workers=10  # Use 10 concurrent workers for faster processing
    )
    
    # Run crawling and filtering
    output_file = crawler.run()
    
    if output_file:
        print(f"\n✓ Complete! Results saved to: {output_file}")
    else:
        print("\n✗ No issues meeting criteria found")


if __name__ == "__main__":
    main()

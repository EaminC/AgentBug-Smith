#!/usr/bin/env python3
"""
GitHub Awesome Repository Agent Collector

Extract agent-related repositories from GitHub awesome lists
"""

import json
import os
from datetime import datetime
from typing import List, Dict
from pathlib import Path
import argparse
from dotenv import load_dotenv

from awesome_search import AwesomeRepoSearcher
from repo_extractor import RepoExtractor

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '../../../.env'))


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Collect Agent repositories from GitHub Awesome lists')
    parser.add_argument('--keywords', type=str, nargs='+', 
                       default=['awesome-agent', 'awesome-llm', 'awesome-ai-agents'],
                       help='Search keywords list')
    parser.add_argument('--min-stars', type=int, default=50, 
                       help='Minimum star count (default: 50)')
    parser.add_argument('--github-token', type=str, default=None, 
                       help='GitHub token (for API access, avoid rate limits)')
    parser.add_argument('--limit', type=int, default=None, 
                       help='Limit the number of output repositories')
    parser.add_argument('--max-awesome-repos', type=int, default=10,
                       help='Maximum number of awesome repos per keyword (default: 10)')
    args = parser.parse_args()
    
    # Use token from environment variable if not provided via command line
    if not args.github_token:
        args.github_token = os.getenv('GITHUB_TOKEN')
    
    if not args.github_token:
        print("⚠️  Warning: No GitHub Token provided, API rate limits may affect execution")
        print("   Recommend setting GITHUB_TOKEN in .env file or via --github-token parameter")
    
    print("=" * 60)
    print("GitHub Awesome Repository Agent Collector")
    print(f"Search keywords: {', '.join(args.keywords)}")
    print(f"Minimum stars: {args.min_stars}")
    print(f"Max repos per keyword: {args.max_awesome_repos} awesome repos")
    print("=" * 60)
    
    # Step 1: Search awesome repositories
    print("\n[Phase 1] Searching Awesome Repositories...")
    searcher = AwesomeRepoSearcher(github_token=args.github_token)
    awesome_repos = []
    
    for keyword in args.keywords:
        print(f"\n  Searching keyword: {keyword}")
        repos = searcher.search_awesome_repos(
            keyword=keyword, 
            min_stars=args.min_stars,
            max_results=args.max_awesome_repos
        )
        awesome_repos.extend(repos)
        print(f"  Found {len(repos)} qualified awesome repositories")
    
    # Remove duplicates
    unique_repos = []
    seen = set()
    for repo in awesome_repos:
        if repo['name'] not in seen:
            unique_repos.append(repo)
            seen.add(repo['name'])
    
    print(f"\nTotal found {len(unique_repos)} unique awesome repositories")
    
    if not unique_repos:
        print("❌ No qualified awesome repositories found")
        return
    
    # Step 2: Extract agent repositories from awesome repository READMEs
    print("\n[Phase 2] Extracting Agent Repository List from READMEs...")
    extractor = RepoExtractor(github_token=args.github_token)
    
    all_agent_repos = []
    repo_sources = {}  # Track which awesome repo each repo comes from
    
    for awesome_repo in unique_repos:
        print(f"\n  Processing: {awesome_repo['name']} ({awesome_repo['stars']} ⭐)")
        
        # Get README
        readme = extractor.get_readme(awesome_repo['name'])
        if not readme:
            print(f"    ⚠️  Unable to get README, skipping")
            continue
        
        # Use AI to extract repository list
        agent_repos = extractor.extract_repos_from_readme(
            readme=readme,
            awesome_repo_name=awesome_repo['name']
        )
        
        print(f"    ✓ Extracted {len(agent_repos)} agent repositories")
        
        # Record sources
        for repo in agent_repos:
            if repo not in all_agent_repos:
                all_agent_repos.append(repo)
            
            if repo not in repo_sources:
                repo_sources[repo] = []
            repo_sources[repo].append(awesome_repo['name'])
    
    print(f"\nTotal extracted {len(all_agent_repos)} unique agent repositories")
    
    # Filter repositories containing 'china'
    filtered_repos = []
    for repo in all_agent_repos:
        if 'china' not in repo.lower():
            filtered_repos.append(repo)
    
    all_agent_repos = filtered_repos
    print(f"\nAfter filtering: {len(all_agent_repos)} repositories remaining")
    
    # Apply limit
    if args.limit and len(all_agent_repos) > args.limit:
        all_agent_repos = all_agent_repos[:args.limit]
        print(f"Limited output to first {args.limit} repositories")
    
    # Step 3: Save results
    print("\n[Phase 3] Saving results...")
    # Get output directory (relative to script location)
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent.parent.parent
    output_dir = str(project_root / "data" / "hooked_repo")
    os.makedirs(output_dir, exist_ok=True)
    
    date_str = datetime.now().strftime('%Y-%m-%d')
    output_file = os.path.join(output_dir, f"github_repo_{date_str}.json")
    
    result = {
        "date": date_str,
        "search_keywords": args.keywords,
        "min_stars": args.min_stars,
        "awesome_repos_count": len(unique_repos),
        "agent_repos_count": len(all_agent_repos),
        "awesome_repos": [
            {
                "name": repo['name'],
                "stars": repo['stars'],
                "description": repo.get('description', '')
            }
            for repo in unique_repos
        ],
        "agent_repos": all_agent_repos,
        "repo_sources": repo_sources  # Track the source of each repo
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Results saved to: {output_file}")
    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  - Search keywords: {', '.join(args.keywords)}")
    print(f"  - Awesome repository count: {len(unique_repos)}")
    print(f"  - Extracted agent repository count: {len(all_agent_repos)}")
    print("=" * 60)
    
    # Display partial results
    if all_agent_repos:
        print("\nAgent repository examples:")
        for i, repo in enumerate(all_agent_repos[:20], 1):
            sources = repo_sources.get(repo, [])
            sources_str = sources[0] if sources else "unknown"
            if len(sources) > 1:
                sources_str += f" (+{len(sources)-1} more)"
            print(f"  {i}. {repo} (source: {sources_str})")
        if len(all_agent_repos) > 20:
            print(f"  ... and {len(all_agent_repos) - 20} more repositories")


if __name__ == "__main__":
    main()


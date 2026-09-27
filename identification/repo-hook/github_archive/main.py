#!/usr/bin/env python3
"""
GitHub Archive Agent Repository Collection Tool

Collect agent-related repositories that have been modified in the last day from GitHub Archive
"""

import json
import os
from datetime import datetime, timedelta
from typing import List, Dict
from pathlib import Path
import argparse
from dotenv import load_dotenv

from github_fetcher import GitHubArchiveFetcher
from agent_filter import AgentRepoFilter

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '../../../.env'))


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Collect agent-related repositories from GitHub Archive')
    parser.add_argument('--no-ai', action='store_true', help='Do not use AI for secondary filtering (keyword filtering only)')
    parser.add_argument('--date', type=str, help='Specify date (format: YYYY-MM-DD), defaults to yesterday. Cannot be used with --time-window')
    parser.add_argument('--limit', type=int, default=None, help='Limit the number of output repositories')
    parser.add_argument('--github-token', type=str, default=None, help='GitHub token for API access (to avoid rate limits)')
    parser.add_argument('--min-stars', type=int, default=10, help='Minimum stars required (default: 10)')
    parser.add_argument('--time-window', type=str, default=None, 
                       help='Time window from yesterday: 1h, 6h, 12h, 24h (e.g., --time-window 1h = last 1 hour from yesterday). Cannot be used with --date')
    args = parser.parse_args()
    
    # Use environment variable if token not provided via command line
    if not args.github_token:
        args.github_token = os.getenv('GITHUB_TOKEN')
    
    # Check that date and time-window are mutually exclusive
    if args.date and args.time_window:
        print("Error: Cannot use --date and --time-window together. Choose one:")
        print("  --date YYYY-MM-DD : Analyze a specific date")
        print("  --time-window Nh  : Analyze last N hours from now")
        return
    
    # Parse time window and determine date range
    time_window_hours = None
    target_dates = []
    
    if args.time_window:
        # Time window mode: from yesterday backwards (GitHub Archive has ~1 day delay)
        time_str = args.time_window.lower()
        if time_str.endswith('h'):
            try:
                time_window_hours = int(time_str[:-1])
            except ValueError:
                print(f"Invalid time window format: {args.time_window}")
                return
        else:
            print(f"Invalid time window format: {args.time_window}. Use format like: 1h, 6h, 12h, 24h")
            return
        
        # Calculate which dates to fetch (starting from yesterday)
        yesterday = datetime.now() - timedelta(days=1)
        start_time = yesterday - timedelta(hours=time_window_hours)
        
        # We need to fetch all days that overlap with the time window
        current_date = start_time.date()
        end_date = yesterday.date()
        
        while current_date <= end_date:
            target_dates.append(current_date)
            current_date += timedelta(days=1)
        
        date_str = f"{yesterday.strftime('%Y-%m-%d')}-{time_window_hours}h"  # For filename
        
    elif args.date:
        # Specific date mode
        try:
            target_date = datetime.strptime(args.date, '%Y-%m-%d')
            target_dates = [target_date.date()]
            date_str = args.date
        except ValueError:
            print(f"Error: Invalid date format, should be YYYY-MM-DD")
            return
    else:
        # Default: yesterday
        yesterday = datetime.now() - timedelta(days=1)
        target_dates = [yesterday.date()]
        date_str = yesterday.strftime('%Y-%m-%d')
    
    print("=" * 60)
    print(f"GitHub Archive Agent Repository Collection Tool")
    if time_window_hours:
        yesterday = datetime.now() - timedelta(days=1)
        print(f"Mode: Time window (last {time_window_hours}h from yesterday)")
        print(f"Reference time: {yesterday.strftime('%Y-%m-%d %H:%M')}")
        print(f"Dates to fetch: {', '.join(d.strftime('%Y-%m-%d') for d in target_dates)}")
    else:
        print(f"Mode: Specific date")
        print(f"Target date: {date_str}")
    print(f"AI filtering: {'No' if args.no_ai else 'Yes'}")
    print(f"Min stars: {args.min_stars}")
    print("=" * 60)
    
    # Step 1: Fetch GitHub Archive data
    print("\n[Phase 1] Fetching GitHub Archive data...")
    fetcher = GitHubArchiveFetcher()
    
    all_events = []
    
    if time_window_hours:
        # Time window mode: only fetch specific hours
        yesterday = datetime.now() - timedelta(days=1)
        end_hour = yesterday.hour
        start_hour = end_hour - time_window_hours
        
        # Calculate which hours to fetch
        hours_to_fetch = []
        
        if start_hour >= 0:
            # All in the same day
            for h in range(start_hour, end_hour + 1):
                hours_to_fetch.append((yesterday.date(), h))
        else:
            # Spans two days
            day_before = (yesterday - timedelta(days=1)).date()
            # Hours from previous day
            for h in range(24 + start_hour, 24):
                hours_to_fetch.append((day_before, h))
            # Hours from yesterday
            for h in range(0, end_hour + 1):
                hours_to_fetch.append((yesterday.date(), h))
        
        print(f"Fetching {len(hours_to_fetch)} hour(s) of data...")
        from tqdm import tqdm
        for date, hour in tqdm(hours_to_fetch, desc="Downloading hourly archives"):
            events = fetcher.fetch_hour_data(date.year, date.month, date.day, hour)
            all_events.extend(events)
        
        # Filter events by timestamp
        start_time = yesterday - timedelta(hours=time_window_hours)
        end_time = yesterday
        
        print(f"Filtering events from {start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%Y-%m-%d %H:%M')}...")
        filtered_events = []
        for event in all_events:
            if 'created_at' in event:
                try:
                    event_time = datetime.strptime(event['created_at'], '%Y-%m-%dT%H:%M:%SZ')
                    if start_time <= event_time <= end_time:
                        filtered_events.append(event)
                except:
                    continue
        
        print(f"Filtered {len(all_events)} events to {len(filtered_events)} events in time window")
        all_events = filtered_events
            
    else:
        # Specific date mode: fetch full day(s)
        for target_date in target_dates:
            events = fetcher.fetch_day_data(
                target_date.year,
                target_date.month,
                target_date.day
            )
            all_events.extend(events)
    
    events = all_events
    
    if not events:
        print("Error: No data retrieved")
        return
    
    # Step 2: Extract repository information
    print("\n[Phase 2] Extracting repository information...")
    repos = fetcher.extract_repos(events)  # No need to filter by time, already fetched only needed hours
    print(f"Found {len(repos)} active repositories")
    
    # Prepare minimal repo info (description will be fetched later if needed)
    repos_info = [{"name": repo_name} for repo_name in repos]
    print(f"Prepared {len(repos_info)} repositories for filtering")
    
    # Step 3: Filter Agent Repositories
    print("\n[Phase 3] Filtering Agent Repositories...")
    filter_obj = AgentRepoFilter(use_ai=not args.no_ai, github_token=args.github_token)
    agent_repos = filter_obj.filter_repos(repos_info, min_stars=args.min_stars)
    
    # Limit quantity
    if args.limit and len(agent_repos) > args.limit:
        agent_repos = agent_repos[:args.limit]
        print(f"Limited output to first {args.limit} repositories")
    
    # Step 4: Save results
    print("\n[Phase 4] Saving results...")
    # Get output directory (relative to script location)
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent.parent.parent
    output_dir = str(project_root / "data" / "hooked_repo")
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(
        output_dir,
        f"github_archive_repo_{date_str}.json"
    )
    
    result = {
        "date": date_str,
        "time_window_hours": time_window_hours,
        "total_events": len(events),
        "total_repos": len(repos),
        "agent_repos_count": len(agent_repos),
        "used_ai_filter": not args.no_ai,
        "min_stars": args.min_stars,
        "agent_repos": agent_repos
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"\nResults saved to: {output_file}")
    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  - Total events: {len(events)}")
    print(f"  - Active repositories: {len(repos)}")
    print(f"  - Agent repositories: {len(agent_repos)}")
    print("=" * 60)
    
    # Display partial results
    if agent_repos:
        print("\nSample of Agent repositories:")
        for repo in agent_repos[:10]:
            if isinstance(repo, dict):
                print(f"  - {repo['name']} ({repo.get('stars', 0)} stars)")
            else:
                print(f"  - {repo}")
        if len(agent_repos) > 10:
            print(f"  ... and {len(agent_repos) - 10} more repositories")


if __name__ == "__main__":
    main()


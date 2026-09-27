"""
GitHub Archive data fetching module
"""

import gzip
import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from typing import List, Dict, Set
from tqdm import tqdm


class GitHubArchiveFetcher:
    """Fetch data from GitHub Archive"""
    
    BASE_URL = "https://data.gharchive.org"
    
    def __init__(self):
        self.repos_cache: Set[str] = set()
    
    def fetch_hour_data(self, year: int, month: int, day: int, hour: int) -> List[Dict]:
        """
        Fetch GitHub Archive data for a specific hour
        
        Args:
            year: Year
            month: Month
            day: Day
            hour: Hour (0-23)
            
        Returns:
            List of events
        """
        url = f"{self.BASE_URL}/{year:04d}-{month:02d}-{day:02d}-{hour}.json.gz"
        
        try:
            events = []
            with urllib.request.urlopen(url, timeout=30) as response:
                with gzip.GzipFile(fileobj=response) as gz:
                    for line in gz:
                        try:
                            event = json.loads(line)
                            events.append(event)
                        except json.JSONDecodeError:
                            continue
            return events
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"Warning: Data does not exist {url}")
            else:
                print(f"HTTP error {e.code}: {url}")
            return []
        except Exception as e:
            print(f"Error fetching data {url}: {e}")
            return []
    
    def fetch_day_data(self, year: int, month: int, day: int) -> List[Dict]:
        """
        Fetch GitHub Archive data for a specific day
        
        Args:
            year: Year
            month: Month
            day: Day
            
        Returns:
            List of events
        """
        all_events = []
        print(f"Fetching data for {year}-{month:02d}-{day:02d}...")
        
        for hour in tqdm(range(24), desc="Hour progress"):
            events = self.fetch_hour_data(year, month, day, hour)
            all_events.extend(events)
        
        print(f"Total {len(all_events)} events fetched")
        return all_events
    
    def fetch_yesterday_data(self) -> List[Dict]:
        """
        Fetch yesterday's GitHub Archive data
        
        Returns:
            List of events
        """
        yesterday = datetime.now() - timedelta(days=1)
        return self.fetch_day_data(yesterday.year, yesterday.month, yesterday.day)
    
    def extract_repos(self, events: List[Dict]) -> Set[str]:
        """
        Extract all repository names from event list
        
        Args:
            events: List of events
            
        Returns:
            Set of repository names
        """
        repos = set()
        
        for event in events:
            if 'repo' in event and 'name' in event['repo']:
                repos.add(event['repo']['name'])
        
        return repos
    
    def get_repo_info(self, events: List[Dict], repo_name: str) -> Dict:
        """
        Get additional repository information from events
        
        Args:
            events: List of events
            repo_name: Repository name
            
        Returns:
            Repository information dictionary
        """
        repo_info = {
            "name": repo_name,
            "description": "",
            "events": []
        }
        
        for event in events:
            if event.get('repo', {}).get('name') == repo_name:
                # Collect event types
                event_type = event.get('type', '')
                if event_type:
                    repo_info["events"].append(event_type)
                
                # Try to extract description from payload
                if not repo_info["description"]:
                    payload = event.get('payload', {})
                    if 'repository' in payload:
                        desc = payload['repository'].get('description', '')
                        if desc:
                            repo_info["description"] = desc
        
        # Deduplicate event types
        repo_info["events"] = list(set(repo_info["events"]))
        
        return repo_info


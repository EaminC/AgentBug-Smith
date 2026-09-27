"""
Awesome Repository Search Module

Search awesome-related repositories using GitHub Search API
"""

import urllib.request
import urllib.parse
import json
import time
from typing import List, Dict, Optional


class AwesomeRepoSearcher:
    """Awesome Repository Searcher"""
    
    def __init__(self, github_token: Optional[str] = None):
        """
        Initialize searcher
        
        Args:
            github_token: GitHub token (optional, recommended to avoid rate limits)
        """
        self.token = github_token
        self.base_url = "https://api.github.com"
    
    def _make_request(self, url: str, method: str = 'GET') -> Optional[Dict]:
        """
        Make API request
        
        Args:
            url: API URL
            method: HTTP method
            
        Returns:
            Response JSON data, None if failed
        """
        try:
            req = urllib.request.Request(url, method=method)
            req.add_header('Accept', 'application/vnd.github.v3+json')
            
            if self.token:
                req.add_header('Authorization', f'token {self.token}')
            
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode('utf-8'))
                return data
                
        except urllib.error.HTTPError as e:
            if e.code == 403:
                print(f"    ⚠️  Rate limit reached, waiting 60 seconds...")
                time.sleep(60)
                return self._make_request(url, method)
            elif e.code == 422:
                print(f"    ⚠️  Invalid search query")
                return None
            else:
                print(f"    ⚠️  HTTP error {e.code}")
                return None
        except Exception as e:
            print(f"    ⚠️  Request error: {e}")
            return None
    
    def search_awesome_repos(self, 
                            keyword: str, 
                            min_stars: int = 50,
                            max_results: int = 10) -> List[Dict]:
        """
        Search awesome repositories
        
        Args:
            keyword: Search keyword
            min_stars: Minimum star count
            max_results: Maximum number of results to return
            
        Returns:
            Repository information list
        """
        # Build search query
        # Search repos containing keyword in name or description, sorted by stars
        query = f"{keyword} in:name,description stars:>={min_stars}"
        encoded_query = urllib.parse.quote(query)
        
        # Sort by stars in descending order
        url = f"{self.base_url}/search/repositories?q={encoded_query}&sort=stars&order=desc&per_page={max_results}"
        
        data = self._make_request(url)
        
        if not data or 'items' not in data:
            return []
        
        results = []
        for item in data['items'][:max_results]:
            repo_name = item['full_name']
            repo_desc = item.get('description', '') or ''
            
            # Filter repositories containing 'china' (case insensitive)
            if 'china' in repo_name.lower() or 'china' in repo_desc.lower():
                continue
            
            results.append({
                'name': repo_name,
                'stars': item['stargazers_count'],
                'description': repo_desc,
                'url': item['html_url']
            })
        
        return results
    
    def search_repos_batch(self, 
                          keywords: List[str], 
                          min_stars: int = 50,
                          max_results_per_keyword: int = 10) -> List[Dict]:
        """
        Batch search multiple keywords
        
        Args:
            keywords: List of keywords
            min_stars: Minimum star count
            max_results_per_keyword: Maximum results per keyword
            
        Returns:
            Deduplicated repository information list
        """
        all_repos = []
        seen = set()
        
        for keyword in keywords:
            print(f"  Searching: {keyword}")
            repos = self.search_awesome_repos(keyword, min_stars, max_results_per_keyword)
            
            for repo in repos:
                if repo['name'] not in seen:
                    all_repos.append(repo)
                    seen.add(repo['name'])
            
            # Avoid rate limits
            time.sleep(1)
        
        return all_repos


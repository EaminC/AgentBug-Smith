"""
GitHub API module for fetching repository details
"""

import urllib.request
import urllib.error
import json
import base64
from typing import Optional, Dict, List
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


class GitHubAPI:
    """GitHub API client for fetching repository information"""
    
    BASE_URL = "https://api.github.com"
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize GitHub API client
        
        Args:
            token: GitHub personal access token (optional, but recommended to avoid rate limits)
        """
        self.token = token
        self.request_count = 0
        self.rate_limit_remaining = 60  # Default for unauthenticated requests
        self.cache = {}  # Simple cache to avoid duplicate requests
    
    def _make_request(self, url: str) -> Optional[Dict]:
        """
        Make a request to GitHub API
        
        Args:
            url: API endpoint URL
            
        Returns:
            Response JSON or None if failed
        """
        try:
            req = urllib.request.Request(url)
            req.add_header('Accept', 'application/vnd.github.v3+json')
            
            if self.token:
                req.add_header('Authorization', f'token {self.token}')
            
            with urllib.request.urlopen(req, timeout=10) as response:
                # Update rate limit info
                self.rate_limit_remaining = int(response.headers.get('X-RateLimit-Remaining', 60))
                data = json.loads(response.read().decode('utf-8'))
                self.request_count += 1
                return data
                
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            elif e.code == 403:
                print(f"Rate limit exceeded, waiting...")
                time.sleep(60)
                return self._make_request(url)  # Retry after waiting
            else:
                print(f"HTTP error {e.code} for {url}")
                return None
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def get_repo_readme(self, repo_name: str) -> Optional[str]:
        """
        Get repository README content
        
        Args:
            repo_name: Repository name in format "owner/repo"
            
        Returns:
            README content as string, or None if not found
        """
        url = f"{self.BASE_URL}/repos/{repo_name}/readme"
        data = self._make_request(url)
        
        if not data or 'content' not in data:
            return None
        
        try:
            # Decode base64 content
            content = base64.b64decode(data['content']).decode('utf-8')
            # Limit to first 3000 characters to avoid too long prompts
            return content[:3000]
        except Exception as e:
            print(f"Error decoding README for {repo_name}: {e}")
            return None
    
    def get_repo_info(self, repo_name: str) -> Optional[Dict]:
        """
        Get repository basic information
        
        Args:
            repo_name: Repository name in format "owner/repo"
            
        Returns:
            Repository info dict or None
        """
        # Check cache first
        if repo_name in self.cache:
            return self.cache[repo_name]
        
        url = f"{self.BASE_URL}/repos/{repo_name}"
        data = self._make_request(url)
        
        if not data:
            return None
        
        result = {
            'name': data.get('full_name', repo_name),
            'description': data.get('description', ''),
            'language': data.get('language', ''),
            'stars': data.get('stargazers_count', 0),
            'topics': data.get('topics', [])
        }
        
        # Cache the result
        self.cache[repo_name] = result
        
        return result
    
    def get_repos_info_batch_graphql(self, repo_names: List[str], batch_size: int = 50) -> Dict[str, Optional[Dict]]:
        """
        Get repository information using GraphQL (batch query, more efficient)
        
        Args:
            repo_names: List of repository names (format: "owner/repo")
            batch_size: Number of repos per GraphQL query (max ~100)
            
        Returns:
            Dict mapping repo names to their info
        """
        from tqdm import tqdm
        results = {}
        
        # Calculate number of batches
        num_batches = (len(repo_names) + batch_size - 1) // batch_size
        
        # Process in batches with progress bar
        for i in tqdm(range(0, len(repo_names), batch_size), total=num_batches, desc="GraphQL batches"):
            batch = repo_names[i:i + batch_size]
            
            # Build GraphQL query for this batch
            query_parts = []
            aliases = {}
            
            for idx, repo_name in enumerate(batch):
                if '/' not in repo_name:
                    continue
                    
                owner, name = repo_name.split('/', 1)
                alias = f"repo{idx}"
                aliases[alias] = repo_name
                
                query_parts.append(f'''
                    {alias}: repository(owner: "{owner}", name: "{name}") {{
                        nameWithOwner
                        description
                        stargazerCount
                        primaryLanguage {{ name }}
                        repositoryTopics(first: 10) {{ nodes {{ topic {{ name }} }} }}
                    }}
                ''')
            
            if not query_parts:
                continue
            
            query = "query {" + " ".join(query_parts) + "}"
            
            # Make GraphQL request
            try:
                req = urllib.request.Request(
                    "https://api.github.com/graphql",
                    data=json.dumps({"query": query}).encode('utf-8'),
                    headers={
                        'Content-Type': 'application/json',
                        'Authorization': f'token {self.token}' if self.token else ''
                    }
                )
                
                with urllib.request.urlopen(req, timeout=30) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    
                    # Check for errors in response
                    if 'errors' in data:
                        # Handle NOT_FOUND errors gracefully (repos that don't exist)
                        not_found_repos = set()
                        other_errors = []
                        
                        for error in data['errors']:
                            if error.get('type') == 'NOT_FOUND' and 'path' in error:
                                # Extract alias from path (e.g., ['repo23'])
                                alias = error['path'][0] if error['path'] else None
                                if alias and alias in aliases:
                                    not_found_repos.add(aliases[alias])
                            else:
                                other_errors.append(error)
                        
                        # Mark not found repos as None
                        for repo_name in not_found_repos:
                            results[repo_name] = None
                        
                        # If there are other errors, print them but continue
                        if other_errors:
                            print(f"\nGraphQL errors (non-NOT_FOUND): {other_errors}")
                    
                    if 'data' in data and data['data']:
                        for alias, repo_name in aliases.items():
                            repo_data = data['data'].get(alias)
                            
                            if repo_data:
                                topics = []
                                if repo_data.get('repositoryTopics') and repo_data['repositoryTopics'].get('nodes'):
                                    topics = [t['topic']['name'] for t in repo_data['repositoryTopics']['nodes'] if t.get('topic')]
                                
                                # Safely get language
                                language = ''
                                if repo_data.get('primaryLanguage'):
                                    language = repo_data['primaryLanguage'].get('name', '')
                                
                                results[repo_name] = {
                                    'name': repo_data.get('nameWithOwner', repo_name),
                                    'description': repo_data.get('description') or '',
                                    'stars': repo_data.get('stargazerCount', 0),
                                    'language': language,
                                    'topics': topics
                                }
                            else:
                                results[repo_name] = None
                    else:
                        # No data returned, fallback
                        for repo_name in aliases.values():
                            results[repo_name] = self.get_repo_info(repo_name)
                                
            except Exception as e:
                print(f"GraphQL batch query error: {e}")
                # Fallback to individual queries for this batch
                for repo_name in batch:
                    results[repo_name] = self.get_repo_info(repo_name)
        
        return results
    
    def get_repos_info_batch(self, repo_names: List[str], max_workers: int = 10) -> Dict[str, Optional[Dict]]:
        """
        Get repository information for multiple repos in parallel
        
        Args:
            repo_names: List of repository names
            max_workers: Maximum number of concurrent threads
            
        Returns:
            Dict mapping repo names to their info
        """
        # Use GraphQL if token is available (more efficient)
        if self.token:
            return self.get_repos_info_batch_graphql(repo_names, batch_size=50)
        
        # Fallback to parallel REST API calls
        results = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_repo = {
                executor.submit(self.get_repo_info, repo_name): repo_name 
                for repo_name in repo_names
            }
            
            for future in as_completed(future_to_repo):
                repo_name = future_to_repo[future]
                try:
                    results[repo_name] = future.result()
                except Exception as e:
                    print(f"Error fetching {repo_name}: {e}")
                    results[repo_name] = None
        
        return results


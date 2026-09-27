"""
Repository Extraction Module

Extract agent repository list from Awesome repository README
"""

import sys
import os
import urllib.request
import json
import base64
import re
from typing import List, Optional

# Add forge directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../forge'))

from api import LLMClient


class RepoExtractor:
    """Extract repository list from README"""
    
    def __init__(self, github_token: Optional[str] = None):
        """
        Initialize extractor
        
        Args:
            github_token: GitHub token（optional）
        """
        self.token = github_token
        self.base_url = "https://api.github.com"
        self.llm = LLMClient(model="OpenAI/gpt-4o-mini")
        
        # Load agent repo definition
        agent_def_path = os.path.join(
            os.path.dirname(__file__), 
            '../agent_repo.md'
        )
        with open(agent_def_path, 'r', encoding='utf-8') as f:
            self.agent_definition = f.read()
    
    def get_readme(self, repo_name: str) -> Optional[str]:
        """
        Get repository README content
        
        Args:
            repo_name: Repository name（format: owner/repo）
            
        Returns:
            README content, None if failed
        """
        url = f"{self.base_url}/repos/{repo_name}/readme"
        
        try:
            req = urllib.request.Request(url)
            req.add_header('Accept', 'application/vnd.github.v3+json')
            
            if self.token:
                req.add_header('Authorization', f'token {self.token}')
            
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode('utf-8'))
                
                if 'content' not in data:
                    return None
                
                # Decode base64 content
                content = base64.b64decode(data['content']).decode('utf-8', errors='ignore')
                return content
                
        except Exception as e:
            print(f"      Failed to get README: {e}")
            return None
    
    def extract_repos_from_readme(self, 
                                  readme: str, 
                                  awesome_repo_name: str) -> List[str]:
        """
        Extract agent repository list from README
        
        Args:
            readme: README content
            awesome_repo_name: awesome repository name (for prompt)
            
        Returns:
            Repository name list (format: owner/repo)
        """
        # First try to extract GitHub repository links using regex
        # This can be used as a candidate list
        github_urls = re.findall(
            r'github\.com/([a-zA-Z0-9_-]+/[a-zA-Z0-9_.-]+)',
            readme
        )
        
        # Deduplicate and clean
        candidate_repos = set()
        for url in github_urls:
            # Remove possible .git suffix
            repo = url.rstrip('/')
            if repo.endswith('.git'):
                repo = repo[:-4]
            # Remove possible path parts (e.g., /tree/main, etc.)
            parts = repo.split('/')
            if len(parts) >= 2:
                repo = f"{parts[0]}/{parts[1]}"
            candidate_repos.add(repo)
        
        # If README is too long, truncate（Avoid exceeding LLM context limits）
        max_length = 15000
        if len(readme) > max_length:
            readme_preview = readme[:max_length] + "\n\n... (Content too long, truncated)"
        else:
            readme_preview = readme
        
        # Build prompt for AI to extract agent-related repositories
        prompt = f"""Please read this README file and extract a list of **open-source agent repositories** mentioned in it.

## What is an Agent Repository

{self.agent_definition}

## Task

This is the README content of a GitHub repository `{awesome_repo_name}`. Please extract all **open-source repositories that fit the Agent Repository definition**.

## README Content:

```
{readme_preview}
```

## Requirements

1. Only extract explicitly mentioned GitHub repositories (format: username/reponame)
2. Only include repositories that fit the Agent Repository definition (containing LLM agent systems or related frameworks)
3. Do not include documentation, tutorials, paper collections, or other non-code repositories
4. Do not include pure utility libraries (unless they are agent frameworks)
5. One repository per line, format: owner/repo

Please output the repository list directly, one per line, without any other explanations. If no qualifying repositories are found, output "NONE" only.

Repository list:
"""
        
        try:
            response = self.llm.simple_chat(
                user_message=prompt,
                temperature=0.3
            )
            
            # Parse response
            if not response or response.strip().upper() == "NONE":
                return []
            
            # Extract repository names
            repos = []
            lines = response.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith('#') or line.startswith('//'):
                    continue
                
                # Remove possible markdown list markers
                line = re.sub(r'^[-*+]\s+', '', line)
                line = re.sub(r'^\d+\.\s+', '', line)
                
                # Extract repository names（format: owner/repo）
                match = re.search(r'([a-zA-Z0-9_-]+/[a-zA-Z0-9_.-]+)', line)
                if match:
                    repo = match.group(1)
                    # Clean possible suffixes
                    if repo.endswith('.git'):
                        repo = repo[:-4]
                    
                    # Filter repositories containing 'china' (case insensitive)
                    if 'china' not in repo.lower():
                        repos.append(repo)
            
            return repos
            
        except Exception as e:
            print(f"      AI extraction failed: {e}")
            # Return empty list if AI fails
            return []
    
    def validate_repo(self, repo_name: str) -> bool:
        """
        Validate if repository exists
        
        Args:
            repo_name: Repository name
            
        Returns:
            Whether exists
        """
        url = f"{self.base_url}/repos/{repo_name}"
        
        try:
            req = urllib.request.Request(url, method='HEAD')
            if self.token:
                req.add_header('Authorization', f'token {self.token}')
            
            urllib.request.urlopen(req, timeout=10)
            return True
        except:
            return False


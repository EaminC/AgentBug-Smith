#!/usr/bin/env python3
"""
GitHub Issue Crawler for Agent Issues
Crawls GitHub repository issues and filters agent-related issues
"""

import os
import sys
import json
import requests
import time
import subprocess
import shutil
import re
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Set
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import stat

# Add forge directory to Python path (for LLMClient when crawler is used)
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))


def _remove_readonly(func, path, excinfo):
    """
    Error handler for shutil.rmtree.
    Clears the readonly bit and re-attempts the removal.
    """
    # Clear the read-only bit
    os.chmod(path, stat.S_IWRITE)
    # Re-run the function that failed (usually os.unlink or os.rmdir)
    func(path)


def fetch_issue_for_rq2(repo: str, issue_number: int, github_token: Optional[str] = None) -> Optional[Dict]:
    """
    Fetch a single issue by repo and issue number via GitHub API.
    For reuse by RQ2 or other callers. Returns None if fetch fails or item is a PR.
    """
    token = github_token or os.getenv("GITHUB_TOKEN")
    base_url = "https://api.github.com"
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    url = f"{base_url}/repos/{repo}/issues/{issue_number}"
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        if "pull_request" in data:
            return None
        return data
    except Exception:
        return None


def is_agent_issue_by_rules(issue: Dict) -> bool:
    """
    Rule-based agent-issue check using indicators from agent_issue.md (no LLM).
    For reuse by RQ2 rule_based method.
    """
    keywords = [
        "llm", "lm provider", "openai", "anthropic", "claude", "gpt", "model name", "api key",
        "prompt", "prompt template", "prompt management",
        "memory", "history", "storage", "retriev", "message attribute",
        "tool", "tool invocation", "tool config", "tool implementation", "tool parameter",
        "workflow", "orchestrat", "agent loop", "hang", "infinite loop",
        "token", "context length", "tiktoken", "rag", "retriever", "embedder",
    ]
    text = ((issue.get("title") or "") + "\n" + (issue.get("body") or "")).lower()
    if not text.strip():
        return False
    return any(kw in text for kw in keywords)


def load_agent_criteria() -> str:
    """Load agent_issue.md content for reuse by RQ2 (forge_ai, claude_agent)."""
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent.parent
    criteria_path = project_root / "prompt" / "issue" / "agent_issue.md"
    try:
        with open(criteria_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def build_agent_issue_prompt(issue: Dict, repo: str, issue_number: int, criteria: str) -> tuple:
    """
    Build (system_prompt, user_message) for agent-issue yes/no judgment.
    criteria should be the content of agent_issue.md. For reuse by RQ2 forge_ai and claude_agent.
    """
    system_prompt = (
        f"You are a GitHub issue classification expert. Determine if the given issue is an \"agent issue\".\n\n"
        f"Agent Issue Definition and Criteria:\n{criteria}\n\n"
        "Answer with \"Yes\" or \"No\" only (one word)."
    )
    user_message = (
        f"Issue Title: {issue.get('title', '')}\n\n"
        f"Issue Description:\n{issue.get('body', '')}\n\n"
        f"Repository: {repo} #{issue_number}. Is this an agent issue? Yes or No."
    )
    return system_prompt, user_message


class GitHubIssueCrawler:
    """GitHub Issue Crawler Class"""
    
    def __init__(self, repo: str, github_token: Optional[str] = None, use_local_clone: bool = False,
                 max_workers: int = 5,
                 min_added: Optional[int] = None, max_added: Optional[int] = None,
                 min_deleted: Optional[int] = None, max_deleted: Optional[int] = None,
                 min_total_lines: Optional[int] = None, max_total_lines: Optional[int] = None):
        """
        Initialize crawler

        Args:
            repo: GitHub repository in format "owner/repo"
            github_token: GitHub API token (optional but recommended to avoid rate limits)
            use_local_clone: Whether to use local clone mode (more accurate but requires disk space)
            max_workers: Maximum number of concurrent workers for issue filtering (default: 5)
            min_added: Minimum added lines in PR patch (inclusive); None = no filter
            max_added: Maximum added lines in PR patch (inclusive); None = no filter
            min_deleted: Minimum deleted lines in PR patch (inclusive); None = no filter
            max_deleted: Maximum deleted lines in PR patch (inclusive); None = no filter
            min_total_lines: Minimum (added+deleted) lines in PR patch (inclusive); None = no filter
            max_total_lines: Maximum (added+deleted) lines in PR patch (inclusive); None = no filter
        """
        self.repo = repo
        self.github_token = github_token or os.getenv("GITHUB_TOKEN")
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        if self.github_token:
            self.headers["Authorization"] = f"token {self.github_token}"
        
        # Patch line bounds (None = no filter)
        self.min_added = min_added
        self.max_added = max_added
        self.min_deleted = min_deleted
        self.max_deleted = max_deleted
        self.min_total_lines = min_total_lines
        self.max_total_lines = max_total_lines

        # Initialize LLM client (lazy import so RQ2 rule_based can use fetch_issue_for_rq2 without openai)
        from forge.api import LLMClient
        self.llm_client = LLMClient()
        
        # Load agent issue criteria
        self.agent_issue_criteria = self._load_agent_criteria()
        
        # Local clone mode
        self.use_local_clone = use_local_clone
        self.local_repo_path = None
        if use_local_clone:
            # Use relative path from script location
            script_dir = Path(__file__).resolve().parent
            project_root = script_dir.parent.parent
            self.cached_repo_dir = project_root / "data" / "cached_repo"
            self.cached_repo_dir.mkdir(parents=True, exist_ok=True)
        
        # Concurrent processing
        self.max_workers = max_workers
        self.print_lock = Lock()
    
    def _count_patch_lines(self, patch_text: str) -> Tuple[int, int]:
        """
        Count added and deleted lines in a unified diff patch.
        Returns (added_lines, deleted_lines). Excludes +++/--- header lines.
        """
        added = 0
        deleted = 0
        for line in patch_text.splitlines():
            if line.startswith('+') and not line.startswith('+++'):
                added += 1
            elif line.startswith('-') and not line.startswith('---'):
                deleted += 1
        return (added, deleted)
    
    def _get_patch_file_paths(self, patch_text: str) -> List[str]:
        """Extract changed file paths from unified diff (e.g. 'diff --git a/path b/path')."""
        seen = set()
        for line in patch_text.splitlines():
            if line.startswith('diff --git '):
                parts = line.split()
                if len(parts) >= 4:
                    p = parts[2]
                    if p.startswith('a/'):
                        seen.add(p[2:])
            elif line.startswith('--- ') or line.startswith('+++ '):
                s = line.split(None, 1)
                if len(s) >= 2:
                    p = s[1].strip().split('\t')[0]
                    if p.startswith('a/'):
                        seen.add(p[2:])
                    elif p.startswith('b/'):
                        seen.add(p[2:])
        return [p for p in seen if p and p != '/dev/null']

    # Test path rules (swe-factory-style + common patterns), used when require_test_patch=True
    _TEST_SEGMENTS = frozenset(
        {"tests", "Tests", "test", "Test", "__tests__", "spec", "testing", "e2e", "cypress"}
    )
    _TEST_DIR_PREFIXES = (
        "tests/", "test/", "__tests__/", "spec/", "cypress/", "e2e/",
        "testing/", "unit_test/", "unit_tests/", "integration_tests/",
    )
    _TEST_FILES = (
        "pytest.ini", "jest.config.js", "jest.config.ts", "vitest.config.js",
        "karma.conf.js", "cypress.config.js", ".mocharc.js",
    )

    def _is_test_path(self, path: str) -> bool:
        """True if path looks like a test file/dir (swe-factory-style + common). Used when require_test_patch=True."""
        p = (path or "").replace("\\", "/").strip()
        if not p:
            return False
        segments = p.split("/")
        base = segments[-1] if segments else ""
        if any(seg in self._TEST_SEGMENTS for seg in segments):
            return True
        if p.startswith("test_"):
            return True
        if base.startswith("test_"):
            return True
        if p.endswith("_test.py"):
            return True
        if p.endswith(".test"):
            return True
        for d in self._TEST_DIR_PREFIXES:
            if p == d.rstrip("/") or p.startswith(d) or ("/" + d) in p:
                return True
        if base in self._TEST_FILES:
            return True
        if re.match(r"^test_.*\.py$", base) or re.match(r"^.*_test\.py$", base):
            return True
        if re.match(r"^.*\.(test|spec)\.(js|ts|jsx|tsx)$", base):
            return True
        return False

    def _patch_has_test_file(self, pr: Dict) -> bool:
        """True if PR patch touches at least one path that is a test file/dir."""
        patch = pr.get("patch") or ""
        paths = self._get_patch_file_paths(patch)
        return any(self._is_test_path(p) for p in paths)

    def _get_test_paths_in_patch(self, pr: Dict) -> List[str]:
        """Return list of paths in PR patch that are test files/dirs (swe-factory-style)."""
        patch = pr.get("patch") or ""
        paths = self._get_patch_file_paths(patch)
        return sorted({p for p in paths if self._is_test_path(p)})

    def _patch_must_kick(self, pr: Dict) -> bool:
        """
        Must-kick filter: exclude PRs that are not meaningful for agent-issue evaluation.
        Returns True if the patch should be excluded (kick).
        """
        patch = pr.get('patch')
        if not patch or not patch.strip():
            return False  # No patch to analyze; let other filters handle
        
        paths = self._get_patch_file_paths(patch)
        if not paths:
            return False
        
        def norm(p: str) -> str:
            p = p.replace('\\', '/').lower()
            return p
        
        # Only docs: docs/, README, *.md, *.rst
        doc_patterns = ('docs/', 'readme', '.md', '.rst')
        if all(
            norm(p).startswith('docs/') or 'readme' in norm(p).split('/')[-1] or
            norm(p).endswith('.md') or norm(p).endswith('.rst')
            for p in paths
        ):
            return True
        
        # Only config/lock and generated: package-lock.json, yarn.lock, poetry.lock, Pipfile.lock, Cargo.lock, go.sum, *.pb.go, dist/, build/
        config_names = {
            'package-lock.json', 'yarn.lock', 'poetry.lock', 'pipfile.lock',
            'cargo.lock', 'go.sum'
        }
        if all(
            norm(p).split('/')[-1] in config_names or
            norm(p).endswith('.pb.go') or norm(p).startswith('dist/') or norm(p).startswith('build/')
            for p in paths
        ):
            return True
        
        # Only vendor/third_party: vendor/, third_party/, node_modules/
        vendor_patterns = ('vendor/', 'third_party/', 'node_modules/')
        if all(any(norm(p).startswith(s) for s in vendor_patterns) for p in paths):
            return True
        
        # Binary / generated assets: images, models, zip, pdf, audio
        binary_ext = (
            '.png', '.jpg', '.jpeg', '.gif', '.webp', '.ico', '.svg',
            '.zip', '.tar', '.gz', '.pdf', '.mp3', '.wav', '.ogg', '.mp4',
            '.bin', '.pb.go', '.model', '.onnx', '.pt', '.pth', '.h5', '.pickle'
        )
        if all(any(norm(p).endswith(ext) for ext in binary_ext) for p in paths):
            return True
        
        # Only formatting: high ratio of lines that are purely whitespace change
        added, deleted = self._count_patch_lines(patch)
        total_add_del = added + deleted
        if total_add_del >= 20:
            content_count = 0
            for line in patch.splitlines():
                if (line.startswith('+') and not line.startswith('+++')) or (line.startswith('-') and not line.startswith('---')):
                    rest = line[1:].strip()
                    if rest:
                        content_count += 1
            if total_add_del > 0 and content_count / total_add_del < 0.05:
                return True
        
        return False
    
    def _patch_in_bounds(self, pr: Dict) -> bool:
        """Check if PR patch (if present) is within configured line bounds. If no min/max is set, no limit (always True)."""
        patch = pr.get('patch')
        if not patch:
            # No patch: exclude only when any bound is set
            if (self.min_added is not None or self.max_added is not None or
                self.min_deleted is not None or self.max_deleted is not None or
                self.min_total_lines is not None or self.max_total_lines is not None):
                return False
            return True
        
        added, deleted = self._count_patch_lines(patch)
        total = added + deleted
        
        if self.min_added is not None and added < self.min_added:
            return False
        if self.max_added is not None and added > self.max_added:
            return False
        if self.min_deleted is not None and deleted < self.min_deleted:
            return False
        if self.max_deleted is not None and deleted > self.max_deleted:
            return False
        if self.min_total_lines is not None and total < self.min_total_lines:
            return False
        if self.max_total_lines is not None and total > self.max_total_lines:
            return False
        return True
    
    def _load_agent_criteria(self) -> str:
        """Load agent issue criteria"""
        criteria_path = Path(__file__).parent.parent.parent / "prompt" / "issue" / "agent_issue.md"
        try:
            with open(criteria_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Warning: Failed to load agent issue criteria: {e}")
            return ""
    
    def _clone_repo(self) -> bool:
        """
        Clone repository to local disk
        
        Returns:
            Whether clone was successful
        """
        repo_name = self.repo.replace('/', '-')
        self.local_repo_path = self.cached_repo_dir / repo_name
        
        # Delete if already exists
        if self.local_repo_path.exists():
            print(f"Removing existing cached repository: {self.local_repo_path}")
            shutil.rmtree(self.local_repo_path)
        
        # Clone repository
        clone_url = f"https://github.com/{self.repo}.git"
        print(f"Cloning repository: {clone_url}")
        print(f"Target location: {self.local_repo_path}")
        
        try:
            cmd = ["git", "clone", "-c", "core.longpaths=true", clone_url, str(self.local_repo_path)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            
            if result.returncode == 0:
                print(f"✓ Repository cloned successfully")
                return True
            else:
                print(f"✗ Clone failed: {result.stderr}")
                return False
        except Exception as e:
            print(f"✗ Clone error: {e}")
            return False
    
    def _cleanup_repo(self):
        """
        Clean up local cloned repository (temporary cache only)
        Note: This only deletes the cloned repo in data/cached_repo/
        Results in data/hooked_issue/ are preserved
        """
        if self.local_repo_path and self.local_repo_path.exists():
            print(f"\nCleaning up cached repository: {self.local_repo_path}")
            print("(Results in data/hooked_issue/ are preserved)")
            try:
                shutil.rmtree(self.local_repo_path)
                print("✓ Cleanup complete")
            except Exception as e:
                print(f"✗ Cleanup failed: {e}")
    
    def _get_issue_linked_prs_from_git(self, issue_number: int) -> Set[int]:
        """
        Find linked PR numbers from local git repository
        
        Args:
            issue_number: Issue number
            
        Returns:
            Set of PR numbers
        """
        if not self.local_repo_path:
            return set()
        
        pr_numbers = set()
        
        try:
            # Search commits that mention this issue
            cmd = ["git", "log", "--all", "--oneline", "--grep", f"#{issue_number}"]
            result = subprocess.run(
                cmd, 
                cwd=self.local_repo_path,
                capture_output=True, 
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and result.stdout:
                commit_lines = result.stdout.strip().split('\n')
                
                for line in commit_lines:
                    # Extract commit SHA
                    parts = line.split(maxsplit=1)
                    if len(parts) < 2:
                        continue
                    commit_sha = parts[0]
                    
                    # Get full commit message
                    cmd = ["git", "show", "--format=%B", "-s", commit_sha]
                    result = subprocess.run(
                        cmd,
                        cwd=self.local_repo_path,
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    if result.returncode == 0:
                        commit_msg = result.stdout
                        
                        if not re.search(rf'#{issue_number}\b', commit_msg):
                            continue
                        
                        # Find PR number in commit message
                        pr_match = re.search(r'Merge pull request #(\d+)', commit_msg)
                        if pr_match:
                            pr_numbers.add(int(pr_match.group(1)))
                        
                        # Squash merge format
                        pr_match = re.search(r'\(#(\d+)\)', commit_msg)
                        if pr_match:
                            pr_numbers.add(int(pr_match.group(1)))
            
        except Exception as e:
            print(f"    Git analysis error: {e}")
        
        return pr_numbers
    
    def _make_request(self, url: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Send GitHub API request
        
        Args:
            url: Request URL
            params: Request parameters
            
        Returns:
            Response JSON data or None
        """
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API request error: {e}")
            return None
    
    def _get_all_closed_issues(self) -> List[Dict]:
        """
        Get all closed issues, excluding those closed as 'not planned'.
        
        Returns:
            List of issues
        """
        issues = []
        page = 1
        per_page = 100
        
        print(f"Fetching closed issues from repository {self.repo}...")
        
        while True:
            url = f"{self.base_url}/repos/{self.repo}/issues"
            params = {
                "state": "closed",
                "per_page": per_page,
                "page": page
            }
            
            data = self._make_request(url, params)
            if not data:
                break
            
            if len(data) == 0:
                break
            
            # Filter page results
            page_issues = []
            for item in data:
                # 1. Skip Pull Requests (GitHub API includes PRs in the issues endpoint)
                if 'pull_request' in item:
                    continue
                
                # 2. Skip issues "Closed as not planned"
                # state_reason can be 'completed', 'not_planned', or None (legacy/default)
                if item.get('state_reason') != 'completed':
                    continue
                
                page_issues.append(item)
            
            issues.extend(page_issues)
            
            print(f"Fetched page {page}, total {len(issues)} issues so far")
            page += 1
            
            # If fewer results than per_page, this is the last page
            if len(data) < per_page:
                break
        
        print(f"Total {len(issues)} closed issues fetched (excluding 'not_planned')")
        return issues
    
    def _get_issue_linked_prs(self, issue_number: int, issue_body: str = "") -> List[Dict]:
        """
        Get linked PRs for an issue (using multiple detection methods)
        
        Args:
            issue_number: Issue number
            issue_body: Issue content
            
        Returns:
            List of linked PRs
        """
        linked_prs = []
        pr_numbers = set()
        
        # If local clone mode is enabled, use git analysis first
        if self.use_local_clone and self.local_repo_path:
            git_prs = self._get_issue_linked_prs_from_git(issue_number)
            pr_numbers.update(git_prs)
            if git_prs:
                print(f"    Found {len(git_prs)} PR(s) from Git history: {sorted(git_prs)}")
        
        # If not local mode or no results found, use API methods
        if not self.use_local_clone or not pr_numbers:
            # Method 1: Timeline API
            url = f"{self.base_url}/repos/{self.repo}/issues/{issue_number}/timeline"
            headers = self.headers.copy()
            headers["Accept"] = "application/vnd.github.mockingbird-preview+json"
            
            try:
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                events = response.json()
                
                for event in events:
                    if event.get('event') in ['cross-referenced', 'connected']:
                        source = event.get('source')
                        if source and source.get('issue') and source['issue'].get('pull_request'):
                            pr = source['issue']
                            pr_numbers.add(pr['number'])
            except Exception:
                pass
            
            # Method 2: Find PRs that closed this issue
            try:
                url = f"{self.base_url}/repos/{self.repo}/issues/{issue_number}/events"
                response = requests.get(url, headers=self.headers)
                response.raise_for_status()
                events = response.json()
                
                for event in events:
                    if event.get('event') == 'closed':
                        commit_id = event.get('commit_id')
                        if commit_id:
                            # Find PRs containing this commit
                            prs = self._find_prs_with_commit(commit_id)
                            for pr_num in prs:
                                pr_numbers.add(pr_num)
            except Exception:
                pass
            
            # Method 3: Search PRs mentioning this issue (only in non-local mode to avoid rate limits)
            if not self.use_local_clone:
                try:
                    url = f"{self.base_url}/search/issues"
                    params = {
                        'q': f'repo:{self.repo} type:pr #{issue_number}',
                        'per_page': 10
                    }
                    # Search API has stricter rate limits, add delay
                    time.sleep(2)
                    response = requests.get(url, headers=self.headers, params=params)
                    response.raise_for_status()
                    data = response.json()
                    
                    for item in data.get('items', []):
                        if item.get('pull_request'):
                            pr_numbers.add(item['number'])
                except Exception as e:
                    # Ignore search API errors (likely rate limit)
                    pass
        
        # Get detailed info for all found PRs
        for pr_num in pr_numbers:
            pr_info = self._get_pr_info(pr_num)
            if pr_info:
                linked_prs.append(pr_info)
        
        return linked_prs
    
    def _find_prs_with_commit(self, commit_sha: str) -> List[int]:
        """
        Find PRs containing a specific commit
        
        Args:
            commit_sha: Commit SHA
            
        Returns:
            List of PR numbers
        """
        try:
            url = f"{self.base_url}/repos/{self.repo}/commits/{commit_sha}/pulls"
            headers = self.headers.copy()
            headers["Accept"] = "application/vnd.github.groot-preview+json"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            prs = response.json()
            return [pr['number'] for pr in prs]
        except Exception:
            return []
    
    def _get_pr_patch(self, pr_number: int) -> Optional[str]:
        """
        Fetch full PR diff/patch. If fetch fails, return None (do not fail the crawl).
        """
        try:
            diff_url = f"{self.base_url}/repos/{self.repo}/pulls/{pr_number}.diff"
            diff_headers = {"Accept": "application/vnd.github.v3.diff"}
            if self.github_token:
                diff_headers["Authorization"] = f"token {self.github_token}"
            diff_response = requests.get(diff_url, headers=diff_headers, timeout=30)
            diff_response.raise_for_status()
            patch_text = diff_response.text
            if not patch_text or not patch_text.strip():
                return None
            return patch_text
        except Exception:
            return None

    def _get_pr_info(self, pr_number: int) -> Optional[Dict]:
        """
        Get detailed PR information including base_sha (commit before PR), head_sha, and full patch.
        If patch fetch fails, PR info is still returned without patch.
        """
        try:
            url = f"{self.base_url}/repos/{self.repo}/pulls/{pr_number}"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            pr = response.json()
            base_sha = pr.get('base', {}).get('sha', '')
            head_sha = pr.get('head', {}).get('sha', '')
            pr_info = {
                'number': pr['number'],
                'state': pr['state'],
                'title': pr['title'],
                'url': pr['html_url'],
                'merged': pr.get('merged', False),
                'base_branch': pr.get('base', {}).get('ref', ''),
                'base_sha': base_sha,
                'head_sha': head_sha,
            }
            patch = self._get_pr_patch(pr_number)
            if patch is not None:
                pr_info['patch'] = patch
            return pr_info
        except Exception:
            return None
    
    def _check_pr_merged_to_main(self, pr_info: Dict) -> bool:
        """
        Check if PR is merged to main branch
        
        Args:
            pr_info: PR information dictionary
            
        Returns:
            Whether PR is merged to main
        """
        # Check if PR is merged
        if not pr_info.get('merged'):
            return False
        
        # Check if merged to main or master branch
        base_branch = pr_info.get('base_branch', '')
        return base_branch in ['main', 'master']
    
    def _has_text_description(self, issue: Dict) -> bool:
        """
        Check if issue has text description
        
        Args:
            issue: Issue data
            
        Returns:
            Whether issue has text description
        """
        body = issue.get('body', '')
        return body is not None and len(body.strip()) > 0
    
    def _is_agent_issue(self, issue: Dict) -> Tuple[bool, str]:
        """
        Use AI to determine if issue is an agent issue
        
        Args:
            issue: Issue data
            
        Returns:
            (is_agent_issue, AI response)
        """
        # Build prompt: 只允许回答 Yes 或 No，便于解析且减少随机性
        system_prompt = f"""You are a GitHub issue classification expert. Your task is to determine if a given issue is an "agent issue".

Agent Issue Definition and Criteria:
{self.agent_issue_criteria}

Based on the above criteria, determine if the given issue is an agent issue.
You must answer with exactly one word: "Yes" or "No". Do not add any explanation or other text."""

        user_message = f"""Issue Title: {issue.get('title', '')}

Issue Description:
{issue.get('body', '')}

Is this an agent issue? Reply with only one word: Yes or No."""

        try:
            response = self.llm_client.simple_chat(
                user_message=user_message,
                system_prompt=system_prompt,
                temperature=0.0
            )
            response_lower = (response or "").strip().lower()
            # 只认首词或整段为 yes/no
            first_word = response_lower.split()[0] if response_lower.split() else ""
            is_agent = first_word == "yes" or response_lower == "yes"
            return is_agent, response
        except Exception as e:
            print(f"AI judgment error: {e}")
            return False, f"Judgment failed: {str(e)}"
    
    def _process_single_issue(self, issue: Dict, idx: int, total: int) -> Optional[Dict]:
        """
        Process a single issue to check if it meets criteria (without AI judgment)
        
        Args:
            issue: Issue data
            idx: Current index (for progress display)
            total: Total number of issues
            
        Returns:
            Filtered issue dict if meets criteria, None otherwise
        """
        issue_number = issue['number']
        
        with self.print_lock:
            print(f"\nProgress: {idx}/{total} - Issue #{issue_number}")
        
        # Condition 1: Already filtered (state=closed)
        
        # Condition 2: Check if has text description
        if not self._has_text_description(issue):
            with self.print_lock:
                print(f"  ✗ No text description")
            return None
        
        with self.print_lock:
            print(f"  ✓ Has text description")
        
        # Condition 3: Get linked PRs
        linked_prs = self._get_issue_linked_prs(issue_number, issue.get('body', ''))
        if not linked_prs:
            with self.print_lock:
                print(f"  ✗ No linked PRs")
            return None
        
        with self.print_lock:
            print(f"  ✓ Found {len(linked_prs)} linked PR(s)")
        
        # Condition 4: Check if any PR is merged to main
        merged_prs = []
        for pr in linked_prs:
            if self._check_pr_merged_to_main(pr):
                merged_prs.append(pr)
        
        if not merged_prs:
            with self.print_lock:
                print(f"  ✗ No PRs merged to main branch")
            return None
        
        with self.print_lock:
            print(f"  ✓ {len(merged_prs)} PR(s) merged to main")
        
        # Condition 5 (must-kick): Exclude PRs that are docs-only, config-only, vendor-only, binary, or formatting-only
        merged_prs = [pr for pr in merged_prs if not self._patch_must_kick(pr)]
        if not merged_prs:
            with self.print_lock:
                print(f"  ✗ No PRs after must-kick filter (docs/config/vendor/binary/formatting-only)")
            return None
        with self.print_lock:
            print(f"  ✓ {len(merged_prs)} PR(s) passed must-kick filter")
        
        # Condition 6 (optional): Filter by patch line bounds (added, deleted, total)
        if (self.min_added is not None or self.max_added is not None or self.min_deleted is not None or self.max_deleted is not None or
            self.min_total_lines is not None or self.max_total_lines is not None):
            merged_prs = [pr for pr in merged_prs if self._patch_in_bounds(pr)]
            if not merged_prs:
                with self.print_lock:
                    print(f"  ✗ No PRs within patch line bounds (min/max added, min/max deleted)")
                return None
            with self.print_lock:
                print(f"  ✓ {len(merged_prs)} PR(s) within patch line bounds")

        # Add test_paths_in_patch to each PR (no filter: issues without test in patch are kept)
        merged_prs = [
            {**pr, 'test_paths_in_patch': self._get_test_paths_in_patch(pr)}
            for pr in merged_prs
        ]

        # Create filtered issue (without AI judgment yet)
        filtered_issue = {
            'number': issue_number,
            'title': issue['title'],
            'url': issue['html_url'],
            'state': issue['state'],
            'created_at': issue['created_at'],
            'closed_at': issue['closed_at'],
            'body': issue['body'],
            'labels': [label['name'] for label in issue.get('labels', [])],
            'linked_prs': merged_prs,
        }
        
        with self.print_lock:
            print(f"  ✓✓ Issue #{issue_number} meets all criteria!")
        
        return filtered_issue
    
    def filter_issues(self, issues: List[Dict]) -> List[Dict]:
        """
        Filter issues that meet criteria (without AI judgment)
        Uses concurrent processing in local clone mode for better performance
        
        Args:
            issues: Original issues list
            
        Returns:
            Filtered issues list (without AI judgment)
        """
        filtered_issues = []
        total = len(issues)
        
        # Use concurrent processing only in local clone mode
        # Online API mode uses sequential processing to avoid rate limits
        if self.use_local_clone:
            print(f"\nFiltering issues with {self.max_workers} concurrent workers (local clone mode)...")
            
            # Use ThreadPoolExecutor for concurrent processing
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all tasks
                future_to_issue = {
                    executor.submit(self._process_single_issue, issue, idx, total): issue
                    for idx, issue in enumerate(issues, 1)
                }
                
                # Process completed tasks
                for future in as_completed(future_to_issue):
                    try:
                        result = future.result()
                        if result is not None:
                            filtered_issues.append(result)
                    except Exception as e:
                        issue = future_to_issue[future]
                        with self.print_lock:
                            print(f"  ✗ Error processing issue #{issue['number']}: {e}")
            
            # Sort by issue number for consistent output
            filtered_issues.sort(key=lambda x: x['number'])
        else:
            # Sequential processing for API mode (to avoid rate limits)
            print(f"\nFiltering issues sequentially (API mode - avoiding rate limits)...")
            
            for idx, issue in enumerate(issues, 1):
                result = self._process_single_issue(issue, idx, total)
                if result is not None:
                    filtered_issues.append(result)
        
        print(f"\nFiltering complete! Found {len(filtered_issues)} issues meeting criteria")
        return filtered_issues

    def _deduplicate_issues_by_pr(self, filtered_issues: List[Dict]) -> List[Dict]:
        """
        Deduplicate issues by linked PR: when multiple issues link to the same PR,
        keep only one issue per PR (the one with the smallest issue number) so that
        each fix (PR) corresponds to at most one issue in the final dataset.

        Args:
            filtered_issues: List of filtered issues (each has 'linked_prs').

        Returns:
            Deduplicated list (one issue per unique first-linked PR).
        """
        if not filtered_issues:
            return []

        # Group by first linked PR number
        by_pr: Dict[int, List[Dict]] = {}
        for issue in filtered_issues:
            prs = issue.get('linked_prs') or []
            if not prs:
                continue
            pr_num = prs[0]['number']
            by_pr.setdefault(pr_num, []).append(issue)

        # For each PR, keep the issue with the smallest issue number
        deduplicated = []
        for pr_num, group in sorted(by_pr.items()):
            chosen = min(group, key=lambda x: x['number'])
            deduplicated.append(chosen)
            if len(group) > 1:
                with self.print_lock:
                    others = sorted(i['number'] for i in group if i['number'] != chosen['number'])
                    print(f"  [Dedup] PR #{pr_num}: kept issue #{chosen['number']}, dropped issues {others} (same PR)")

        deduplicated.sort(key=lambda x: x['number'])
        dropped = len(filtered_issues) - len(deduplicated)
        if dropped > 0:
            print(f"\nDeduplication: {len(filtered_issues)} -> {len(deduplicated)} issues ({dropped} dropped, same PR)")
        return deduplicated

    def batch_ai_judgment(self, issues: List[Dict]) -> List[Dict]:
        """
        Batch AI judgment for all filtered issues
        
        Args:
            issues: Filtered issues list
            
        Returns:
            Issues with AI judgment results
        """
        if not issues:
            return []
        
        print(f"\n{'='*60}")
        print(f"Starting batch AI judgment for {len(issues)} issues")
        print(f"{'='*60}\n")
        
        agent_issues = []
        
        for idx, issue in enumerate(issues, 1):
            issue_number = issue['number']
            print(f"AI Judgment Progress: {idx}/{len(issues)} - Issue #{issue_number}")
            
            is_agent, ai_response = self._is_agent_issue(issue)
            
            issue['ai_judgment'] = {
                'is_agent_issue': is_agent,
                'response': ai_response
            }
            
            if is_agent:
                agent_issues.append(issue)
                print(f"  ✓ AI: This is an agent issue")
                print(f"    Reason: {ai_response[:100]}...")
            else:
                print(f"  ✗ AI: Not an agent issue")
                print(f"    Reason: {ai_response[:100]}...")
        
        print(f"\n{'='*60}")
        print(f"AI judgment complete!")
        print(f"Total: {len(issues)} issues | Agent issues: {len(agent_issues)}")
        print(f"{'='*60}\n")
        
        return agent_issues
    
    def _get_repo_existing_test_paths(self) -> List[str]:
        """
        Load 已有 test paths for current repo from hooked repo (agent_repo.json).
        hooked issue 从 hooked repo 继承：repo 的 test_paths 写入每个 issue 的 existing_test_paths.
        """
        script_dir = Path(__file__).resolve().parent
        project_root = script_dir.parent.parent
        agent_repo_json = project_root / "data" / "hooked_repo" / "agent_repo.json"
        if not agent_repo_json.exists():
            return []
        try:
            data = json.loads(agent_repo_json.read_text(encoding="utf-8"))
        except Exception:
            return []
        repos = data.get("repositories") if isinstance(data, dict) else None
        if not repos or not isinstance(repos, list):
            return []
        for r in repos:
            if isinstance(r, dict) and (r.get("name") or "") == self.repo:
                paths = r.get("test_paths")
                return list(paths) if isinstance(paths, list) else []
        return []

    def save_results(self, issues: List[Dict]) -> str:
        """
        Save results to JSON file
        
        Args:
            issues: Filtered issues (each may have existing_test_paths from hooked repo)
            
        Returns:
            Output file path
        """
        # Create output directory - use relative path from script location
        # This script is in: SWGENT-Bench/src/issue-hook/issue_crawler.py
        # Target directory: SWGENT-Bench/data/hooked_issue/
        script_dir = Path(__file__).resolve().parent  # src/issue-hook/
        project_root = script_dir.parent.parent       # SWGENT-Bench/
        base_dir = project_root / "data" / "hooked_issue"
        base_dir.mkdir(parents=True, exist_ok=True)
        
        # Create repository subdirectory (format: reponame-date)
        repo_name = self.repo.replace('/', '-')
        date_str = datetime.now().strftime('%Y%m%d')
        output_dir = base_dir / f"{repo_name}-{date_str}"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save JSON file
        output_file = output_dir / "issue.json"
        result = {
            'repo': self.repo,
            'crawl_time': datetime.now().isoformat(),
            'total_count': len(issues),
            'issues': issues
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"\nResults saved to: {output_file}")
        return str(output_file)
    
    def run(self) -> str:
        """
        Run complete crawling and filtering workflow
        
        Returns:
            Output file path
        """
        try:
            # 0. Clone repository if local clone mode is enabled
            if self.use_local_clone:
                if not self._clone_repo():
                    print("✗ Failed to clone repository, exiting")
                    return ""
            
            # 1. Get all closed issues
            issues = self._get_all_closed_issues()
            
            if not issues:
                print("No closed issues found")
                return ""
            
            # 2. Filter issues that meet criteria (without AI)
            filtered_issues = self.filter_issues(issues)
            
            if not filtered_issues:
                print("No issues meeting criteria found")
                # Save empty result
                output_file = self.save_results([])
                return output_file

            # 2b. Deduplicate by PR: at most one issue per linked PR
            filtered_issues = self._deduplicate_issues_by_pr(filtered_issues)
            if not filtered_issues:
                print("No issues left after PR deduplication")
                output_file = self.save_results([])
                return output_file
            
            # 3. Batch AI judgment
            agent_issues = self.batch_ai_judgment(filtered_issues)
            
            # 3b. 从 hooked repo 继承已有 test：每个 issue 写入 existing_test_paths
            repo_existing = self._get_repo_existing_test_paths()
            for iss in agent_issues:
                iss["existing_test_paths"] = repo_existing
            if repo_existing:
                print(f"Inherited {len(repo_existing)} repo test paths (existing_test_paths) from hooked repo for all issues")
            
            # 4. Save results (these will be preserved)
            output_file = self.save_results(agent_issues)
            
            return output_file
            
        finally:
            # 5. Clean up temporary cloned repository (results in hooked_issue/ are kept)
            if self.use_local_clone:
                self._cleanup_repo()


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='GitHub Issue Crawler for Agent Issues',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using API mode (default)
  python issue_crawler.py TsinghuaDatabaseGroup/DB-GPT
  
  # Using local clone mode (more accurate, recommended)
  python issue_crawler.py TsinghuaDatabaseGroup/DB-GPT --local-clone
  
  # Specify GitHub token and concurrent workers
  python issue_crawler.py TsinghuaDatabaseGroup/DB-GPT --token YOUR_TOKEN --local-clone --workers 10
  
  # More concurrent workers for faster processing (be mindful of rate limits)
  python issue_crawler.py TsinghuaDatabaseGroup/DB-GPT --local-clone --workers 20
  
  # Filter by patch line counts (added/deleted lines in PR diff)
  python issue_crawler.py owner/repo --min-added 1 --max-added 500 --min-deleted 1 --max-deleted 500
        """
    )
    parser.add_argument('repo', type=str, help='GitHub repository (format: owner/repo)')
    parser.add_argument('--token', type=str, help='GitHub API token (or set GITHUB_TOKEN env var)')
    parser.add_argument('--local-clone', action='store_true',
                       help='Use local clone mode: clone repo locally for analysis (more accurate but requires time and disk space)')
    parser.add_argument('--workers', type=int, default=10,
                       help='Maximum number of concurrent workers for issue filtering (default: 10, recommended: 5-20)')
    parser.add_argument('--min-added', type=int, default=None,
                       help='Minimum added lines in PR patch (inclusive); PRs without patch or below this are excluded')
    parser.add_argument('--max-added', type=int, default=None,
                       help='Maximum added lines in PR patch (inclusive)')
    parser.add_argument('--min-deleted', type=int, default=None,
                       help='Minimum deleted lines in PR patch (inclusive)')
    parser.add_argument('--max-deleted', type=int, default=None,
                       help='Maximum deleted lines in PR patch (inclusive)')
    parser.add_argument('--min-total-lines', type=int, default=None,
                       help='Minimum (added + deleted) lines in PR patch (inclusive); default no limit')
    parser.add_argument('--max-total-lines', type=int, default=None,
                       help='Maximum (added + deleted) lines in PR patch (inclusive); default no limit')
    
    args = parser.parse_args()
    
    # Create crawler instance and run
    crawler = GitHubIssueCrawler(
        args.repo,
        args.token,
        use_local_clone=args.local_clone,
        max_workers=args.workers,
        min_added=args.min_added,
        max_added=args.max_added,
        min_deleted=args.min_deleted,
        max_deleted=args.max_deleted,
        min_total_lines=args.min_total_lines,
        max_total_lines=args.max_total_lines,
    )
    
    if args.local_clone:
        # Get project root for displaying paths
        script_dir = Path(__file__).resolve().parent
        project_root = script_dir.parent.parent
        cache_dir = project_root / "data" / "cached_repo"
        
        print("\n" + "="*60)
        print("Using local clone mode")
        print(f"Repository will be cloned to: {cache_dir}")
        print("Cloned repo will be deleted after analysis (results are preserved)")
        print(f"Concurrent workers: {args.workers} (parallel processing enabled)")
        print("="*60 + "\n")
    else:
        print("\n" + "="*60)
        print("Using API mode")
        print("Sequential processing (to avoid API rate limits)")
        print("Tip: Use --local-clone for faster concurrent processing")
        print("="*60 + "\n")
    
    crawler.run()


if __name__ == "__main__":
    main()

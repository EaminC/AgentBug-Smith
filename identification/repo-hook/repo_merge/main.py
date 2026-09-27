#!/usr/bin/env python3
"""
GitHub Agent Repository Merge Tool

Intelligently read and merge agent repository data from different tools.
Optional: filter to repos that contain test paths (common patterns + inlight heuristic JSON).
"""

import json
import os
import time
from datetime import datetime
from typing import Dict, List, Set
from pathlib import Path
import argparse

try:
    from .repo_test_filter import load_heuristic_paths, repo_has_test_paths
except ImportError:
    from repo_test_filter import load_heuristic_paths, repo_has_test_paths


class RepoMerger:
    """Repository Merger"""
    
    def __init__(self, data_dir: str):
        """
        Initialize merger
        
        Args:
            data_dir: Data file directory
        """
        self.data_dir = data_dir
        self.repos = {}  # {repo_name: {sources: [], stars: int, first_seen: str}}
        
    def detect_json_type(self, data: dict, filename: str) -> str:
        """
        Detect JSON file type
        
        Args:
            data: JSON data
            filename: Filename
            
        Returns:
            File type: 'github_archive' or 'github_repo' or 'unknown'
        """
        # Method 1: Detect by filename prefix
        if filename.startswith('github_archive_repo_'):
            return 'github_archive'
        elif filename.startswith('github_repo_'):
            return 'github_repo'
        
        # Method 2: Detect by data structure
        if 'agent_repos' in data:
            agent_repos = data['agent_repos']
            if agent_repos and isinstance(agent_repos, list):
                if isinstance(agent_repos[0], dict) and 'name' in agent_repos[0]:
                    return 'github_archive'
                elif isinstance(agent_repos[0], str):
                    return 'github_repo'
        
        return 'unknown'
    
    def extract_repos_from_github_archive(self, data: dict, source_file: str) -> List[Dict]:
        """
        Extract repositories from github_archive format
        
        Args:
            data: JSON data
            source_file: Source filename
            
        Returns:
            Repository list
        """
        repos = []
        agent_repos = data.get('agent_repos', [])
        
        for repo_info in agent_repos:
            if isinstance(repo_info, dict):
                repos.append({
                    'name': repo_info.get('name'),
                    'stars': repo_info.get('stars', 0),
                    'source': source_file,
                    'source_type': 'github_archive'
                })
        
        return repos
    
    def extract_repos_from_github_repo(self, data: dict, source_file: str) -> List[Dict]:
        """
        Extract repositories from github_repo format
        
        Args:
            data: JSON data
            source_file: Source filename
            
        Returns:
            Repository list
        """
        repos = []
        agent_repos = data.get('agent_repos', [])
        repo_sources = data.get('repo_sources', {})
        
        for repo_name in agent_repos:
            # Try to get stars info from awesome_repos
            stars = 0
            awesome_repos = data.get('awesome_repos', [])
            for awesome in awesome_repos:
                if awesome.get('name') == repo_name:
                    stars = awesome.get('stars', 0)
                    break
            
            # Get original sources
            original_sources = repo_sources.get(repo_name, [])
            
            repos.append({
                'name': repo_name,
                'stars': stars,
                'source': source_file,
                'source_type': 'github_repo',
                'original_sources': original_sources if original_sources else None
            })
        
        return repos
    
    def merge_repo(self, repo_info: Dict):
        """
        Merge single repository information
        
        Args:
            repo_info: Repository information
        """
        repo_name = repo_info['name']
        
        if repo_name not in self.repos:
            self.repos[repo_name] = {
                'name': repo_name,
                'stars': repo_info.get('stars', 0),
                'sources': [],
                'source_types': set(),
                'original_sources': set(),
                'first_seen': repo_info['source']
            }
        
        # Update information
        repo = self.repos[repo_name]
        
        # Add source
        if repo_info['source'] not in repo['sources']:
            repo['sources'].append(repo_info['source'])
        
        # Add source types
        repo['source_types'].add(repo_info['source_type'])
        
        # Update stars (take maximum)
        if repo_info.get('stars', 0) > repo['stars']:
            repo['stars'] = repo_info['stars']
        
        # Add original sources (for github_repo type)
        if repo_info.get('original_sources'):
            for src in repo_info['original_sources']:
                repo['original_sources'].add(src)
    
    def process_json_file(self, filepath: str) -> int:
        """
        Process single JSON file
        
        Args:
            filepath: File path
            
        Returns:
            Number of extracted repositories
        """
        filename = os.path.basename(filepath)
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Detect file type
            file_type = self.detect_json_type(data, filename)
            
            if file_type == 'unknown':
                print(f"  ⚠️  Skipping unknown format: {filename}")
                return 0
            
            # Extract repositories by type
            if file_type == 'github_archive':
                repos = self.extract_repos_from_github_archive(data, filename)
            else:  # github_repo
                repos = self.extract_repos_from_github_repo(data, filename)
            
            # Merge repositories
            for repo_info in repos:
                self.merge_repo(repo_info)
            
            print(f"  ✓ {filename} ({file_type}): {len(repos)} repositories")
            return len(repos)
            
        except Exception as e:
            print(f"  ❌ Processing {filename} failed: {e}")
            return 0
    
    def merge_all(self) -> Dict:
        """
        Merge all JSON files
        
        Returns:
            Merge result
        """
        json_files = list(Path(self.data_dir).glob('*.json'))
        
        if not json_files:
            print(f"❌ in {self.data_dir} No JSON files found")
            return {}
        
        print(f"\nFound {len(json_files)} JSON files")
        print("\nProcessing files...")
        
        total_extracted = 0
        for json_file in sorted(json_files):
            # Skip output file
            if json_file.name == 'agent_repo.json':
                continue
            
            count = self.process_json_file(str(json_file))
            total_extracted += count
        
        print(f"\nTotal extracted {total_extracted} repository records")
        print(f"Remaining after deduplication {len(self.repos)} unique repositories")
        
        return self.build_result()
    
    def build_result(self) -> Dict:
        """
        Build final result
        
        Returns:
            Result dictionary
        """
        # Convert to list and sort
        repo_list = []
        for repo_name, repo_info in self.repos.items():
            repo_list.append({
                'name': repo_name,
                'stars': repo_info['stars'],
                'sources': repo_info['sources'],
                'source_types': list(repo_info['source_types']),
                'original_sources': list(repo_info['original_sources']) if repo_info['original_sources'] else None,
                'source_count': len(repo_info['sources'])
            })
        
        # Sort by stars in descending order
        repo_list.sort(key=lambda x: x['stars'], reverse=True)
        
        # Statistics
        stats = {
            'total_repos': len(repo_list),
            'from_github_archive': len([r for r in repo_list if 'github_archive' in r['source_types']]),
            'from_github_repo': len([r for r in repo_list if 'github_repo' in r['source_types']]),
            'from_both': len([r for r in repo_list if len(r['source_types']) > 1]),
            'multi_source': len([r for r in repo_list if r['source_count'] > 1])
        }
        
        return {
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'statistics': stats,
            'repositories': repo_list
        }


def main():
    """Main function"""
    # Get default data directory (relative to script location)
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent.parent.parent
    default_data_dir = str(project_root / "data" / "hooked_repo")
    
    parser = argparse.ArgumentParser(description='Merge agent repository data from multiple sources')
    parser.add_argument('--data-dir', type=str, 
                       default=default_data_dir,
                       help='Data file directory')
    parser.add_argument('--output', type=str,
                       default=None,
                       help='Output file path (default: agent_repo.json in data directory)')
    parser.add_argument('--detailed', action='store_true',
                       help='Detailed output (include stars, sources, etc.)')
    default_test_patterns = str(project_root / "data" / "inlight" / "test_path_patterns_topk.json")
    parser.add_argument('--filter-has-test', action='store_true',
                       help='Only keep repos that contain test paths (common patterns + heuristic JSON)')
    parser.add_argument('--test-patterns-json', type=str, default=default_test_patterns,
                       help=f'Path to heuristic test paths JSON (default: {default_test_patterns})')
    parser.add_argument('--github-token', type=str, default=None,
                       help='GitHub token for API (or set GITHUB_TOKEN); needed when using --filter-has-test')
    args = parser.parse_args()

    if not args.github_token:
        args.github_token = os.getenv('GITHUB_TOKEN')
    
    # Determine output path
    if args.output is None:
        args.output = os.path.join(args.data_dir, 'agent_repo.json')
    
    print("=" * 60)
    print("GitHub Agent Repository Merge Tool")
    print(f"Data directory: {args.data_dir}")
    print(f"Output file: {args.output}")
    print(f"Output mode: {'Detailed' if args.detailed else 'Simple'}")
    if args.filter_has_test:
        print("Filter: only repos with test paths (common + heuristic)")
        print(f"Test patterns: {args.test_patterns_json}")
    print("=" * 60)
    
    # Create merger and execute merge
    merger = RepoMerger(args.data_dir)
    result = merger.merge_all()
    
    if not result:
        return
    
    # Optional: filter to repos that have test paths and attach test_paths to each repo
    if args.filter_has_test:
        heuristic = load_heuristic_paths(args.test_patterns_json)
        print(f"\n[Filter] Loaded {len(heuristic)} heuristic paths from {args.test_patterns_json}")
        if not args.github_token:
            print("Warning: No GITHUB_TOKEN; API rate limits may block tree fetches.")
        merged_count = len(result['repositories'])
        filtered = []
        for i, repo in enumerate(result['repositories'], 1):
            name = repo['name']
            print(f"  [{i}/{merged_count}] {name} ...", end=" ", flush=True)
            has_test, test_paths = repo_has_test_paths(name, heuristic, args.github_token)
            if has_test:
                repo = dict(repo)
                repo['test_paths'] = test_paths
                filtered.append(repo)
                print(f"✓ {len(test_paths)} test paths")
            else:
                print("✗ no test paths")
            time.sleep(0.3)
        result['repositories'] = filtered
        result['statistics']['total_repos'] = len(filtered)
        result['statistics']['from_github_archive'] = len([r for r in filtered if 'github_archive' in r['source_types']])
        result['statistics']['from_github_repo'] = len([r for r in filtered if 'github_repo' in r['source_types']])
        result['statistics']['from_both'] = len([r for r in filtered if len(r['source_types']) > 1])
        result['statistics']['multi_source'] = len([r for r in filtered if r['source_count'] > 1])
        print(f"\nAfter test filter: {len(filtered)} repositories (from {merged_count} merged)")
        # When filtering by test we always output detailed so test_paths are included
        args.detailed = True
    
    # Generate output by mode
    if args.detailed:
        # Detailed mode: include all information (and test_paths if --filter-has-test)
        output = result
    else:
        # Simple mode (default): output repository names list only
        output = [repo['name'] for repo in result['repositories']]
    
    # Save results
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Results saved to: {args.output}")
    print("\n" + "=" * 60)
    print("Statistics:")
    print(f"  - Total repositories: {result['statistics']['total_repos']}")
    print(f"  - From GitHub Archive: {result['statistics']['from_github_archive']}")
    print(f"  - From Awesome lists: {result['statistics']['from_github_repo']}")
    print(f"  - From both sources: {result['statistics']['from_both']}")
    print(f"  - Multiple appearances: {result['statistics']['multi_source']}")
    print("=" * 60)
    
    # Display Top 10
    if result['repositories']:
        print("\nTop 10 repositories (sorted by stars):")
        for i, repo in enumerate(result['repositories'][:10], 1):
            sources_info = f"{repo['source_count']} sources" if repo['source_count'] > 1 else "1 sources"
            test_info = f", {len(repo.get('test_paths', []))} test paths" if repo.get('test_paths') else ""
            print(f"  {i}. {repo['name']} ({repo['stars']} ⭐, {sources_info}{test_info})")


if __name__ == "__main__":
    main()


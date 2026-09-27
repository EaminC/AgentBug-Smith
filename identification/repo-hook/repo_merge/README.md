# GitHub Agent Repository Merge Tool

Intelligently merge agent repository data collected from different tools.

## Features

- 🔍 **Smart Detection**: Automatically identify two different JSON formats
  - `github_archive_repo_*.json` - Data collected from GitHub Archive
  - `github_repo_*.json` - Data extracted from Awesome lists
- 🔄 **Deduplication**: Automatically remove duplicate repositories
- 📊 **Statistics**: Provide detailed statistical information
- ⭐ **Stars Tracking**: Keep the highest star count
- 📝 **Source Tracking**: Record all sources for each repository

## Usage

### Basic Usage

```bash
cd /home/cc/SWGENT-Bench/src/repo-hook/repo_merge
python main.py
```

### Advanced Options

```bash
# Specify data directory
python main.py --data-dir /path/to/data

# Specify output file
python main.py --output /path/to/output.json

# Detailed output (include stars, sources, statistics)
python main.py --detailed

# Only keep repos that contain test paths (common patterns + inlight heuristic JSON); writes test_paths per repo
python main.py --detailed --filter-has-test

# Custom heuristic path list (default: data/inlight/test_path_patterns_topk.json)
python main.py --filter-has-test --test-patterns-json /path/to/test_path_patterns_topk.json
```

### Parameter Description

- `--data-dir`: Data file directory (default: `data/hooked_repo`)
- `--output`: Output file path (default: `agent_repo.json` in data directory)
- `--detailed`: Detailed output mode, include stars, sources and statistics
- `--filter-has-test`: Only keep repos that have test paths (common dirs/files + heuristic JSON); adds `test_paths` to each repo and forces detailed output
- `--test-patterns-json`: Path to heuristic test paths JSON (default: `data/inlight/test_path_patterns_topk.json`)
- `--github-token`: GitHub token for tree API (or set `GITHUB_TOKEN`); required when using `--filter-has-test`

## Output Format

### Simple Mode (Default)

```json
[
  "Shubhamsaboo/awesome-llm-apps",
  "microsoft/autogen",
  "geekan/MetaGPT",
  ...
]
```

### Detailed Mode

```json
{
  "generated_at": "2025-10-13 12:00:00",
  "statistics": {
    "total_repos": 220,
    "from_github_archive": 4,
    "from_github_repo": 216,
    "from_both": 0,
    "multi_source": 50
  },
  "repositories": [
    {
      "name": "Shubhamsaboo/awesome-llm-apps",
      "stars": 71852,
      "sources": ["github_repo_2025-10-13.json"],
      "source_types": ["github_repo"],
      "original_sources": ["Shubhamsaboo/awesome-llm-apps", "rohitg00/awesome-ai-apps"],
      "source_count": 1,
      "test_paths": ["tests", "tests/test_example.py", "pytest.ini"]
    }
  ]
}
```

When using `--filter-has-test`, each repository in `repositories` includes a `test_paths` array (paths in that repo that matched common or heuristic test patterns).

## Workflow

1. **Scan Directory**: Read all JSON files in the specified directory
2. **Smart Detection**: Identify JSON type by filename and data structure
3. **Data Extraction**: 
   - GitHub Archive format: Extract `{name, stars}` objects
   - GitHub Repo format: Extract string list and associate stars
4. **Deduplication**: 
   - Keep highest stars for same repository
   - Merge all source information
5. **Sort Output**: Sort by stars in descending order

## Supported JSON Formats

### Format 1: GitHub Archive

```json
{
  "agent_repos": [
    {"name": "owner/repo", "stars": 1234}
  ]
}
```

### Format 2: GitHub Repo (Awesome lists)

```json
{
  "agent_repos": ["owner/repo1", "owner/repo2"],
  "awesome_repos": [
    {"name": "owner/repo1", "stars": 1234}
  ],
  "repo_sources": {
    "owner/repo1": ["awesome-list-1", "awesome-list-2"]
  }
}
```

## Examples

```bash
# Merge all data and generate simple list (default)
python main.py

# Generate detailed report with stars and sources
python main.py --detailed

# Custom output location
python main.py --output ~/my_agent_repos.json
```

## Notes

- The tool automatically skips files named `agent_repo.json` to avoid duplicate processing
- If the same repository appears in multiple sources, all source information is retained
- Star count takes the maximum value from all sources
- Output repository list is sorted by stars in descending order

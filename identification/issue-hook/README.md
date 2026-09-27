# GitHub Issue Crawler for Agent Issues

A tool for crawling GitHub repository issues, specifically designed to filter and identify Agent-related issues.

## Features

This tool automatically completes the following tasks:

1. **Crawl closed issues**: Fetch all closed issues from specified GitHub repository
2. **Multi-condition filtering**:
   - Issue must be closed
   - Issue must be linked to a Pull Request
   - The PR must be merged to main/master branch
   - Issue must have text description
3. **AI-powered judgment**: Use LLM to determine if issue is an agent issue (batch processing)
4. **Structured output**: Save results in JSON format

## Installation

```bash
cd /home/cc/SWGENT-Bench/src/issue-hook
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the **project root** (SWEGENT-BENCH/.env). The Forge/LLM client (used for AI judgment) loads it from there:

```bash
# GitHub API Token (optional but strongly recommended to avoid rate limits)
GITHUB_TOKEN=your_github_token_here

# Forge API (required for AI judgment)
FORGE_API_KEY=your_forge_api_key_here
FORGE_BASE_URL=https://api.forge.tensorblock.co/v1
MODEL=tensorblock/gpt-4.1-mini
AI_TEMPERATURE=0.7
```

### How to Get GitHub Token

1. Visit https://github.com/settings/tokens
2. Click "Generate new token" -> "Generate new token (classic)"
3. Select permissions: `repo` (read repository information)
4. Generate and copy token

## Usage

### Quick Check Single Issue/PR

Use `quick_check.py` to quickly validate if a single issue or PR would be classified as an agent issue:

```bash
# Check by URL
python quick_check.py https://github.com/owner/repo/issues/123

# Check by repo and number
python quick_check.py owner/repo#123
```

### Full Repository Crawling

The tool provides two modes:

### 1. API Mode (Default)
Uses only GitHub API to fetch data. Faster but may miss some issue-PR associations.

```bash
cd /home/cc/SWGENT-Bench/src/issue-hook
python issue_crawler.py <owner>/<repo>
```

### 2. Local Clone Mode (Recommended) ⭐
Clones repository locally and uses git commands to analyze commit history for more accurate issue-PR associations.

```bash
python issue_crawler.py <owner>/<repo> --local-clone
```

### Examples

**Recommended usage** (using local clone mode):

```bash
python issue_crawler.py TsinghuaDatabaseGroup/DB-GPT --local-clone
```

Using API mode:

```bash
python issue_crawler.py TsinghuaDatabaseGroup/DB-GPT
```

With GitHub token:

```bash
python issue_crawler.py TsinghuaDatabaseGroup/DB-GPT --token your_github_token --local-clone
```

With concurrent workers for faster processing (only in local clone mode):

```bash
# Use 10 concurrent workers (default is 5, only works with --local-clone)
python issue_crawler.py TsinghuaDatabaseGroup/DB-GPT --local-clone --workers 10

# Use 20 concurrent workers for even faster processing
python issue_crawler.py TsinghuaDatabaseGroup/DB-GPT --local-clone --workers 20
```

**Note**: Concurrent processing is only enabled in local clone mode. API mode uses sequential processing to avoid rate limits.

### Must-kick patch filter (always on)

PRs whose patch falls into the following categories are **always excluded** (strongly recommended for agent-issue relevance):

- **Docs only**: all changed files under `docs/`, or README, `*.md`, `*.rst`
- **Config/lock only**: `package-lock.json`, `yarn.lock`, `poetry.lock`, `Pipfile.lock`, `Cargo.lock`, `go.sum`, `*.pb.go`, `dist/`, `build/`
- **Vendor/third_party only**: `vendor/`, `third_party/`, `node_modules/`
- **Binary / generated assets**: images (`.png`, `.jpg`, …), archives (`.zip`, …), `.pdf`, audio, `.pb.go`, model files, etc.
- **Formatting only**: patch has many changed lines but &lt;5% are non-whitespace (e.g. “run formatter”)

### Patch line bounds (optional)

Filter issues by PR patch size (added/deleted/total lines). **Not set = no limit.**

```bash
# Only keep PRs with 1–500 added lines and 1–500 deleted lines
python issue_crawler.py owner/repo --min-added 1 --max-added 500 --min-deleted 1 --max-deleted 500

# Total (added + deleted) between 10 and 1000 lines
python issue_crawler.py owner/repo --min-total-lines 10 --max-total-lines 1000

# Only minimum (e.g. at least 5 lines changed)
python issue_crawler.py owner/repo --min-added 5 --min-deleted 5
```

- `--min-added`, `--max-added`: min/max **added** lines in PR patch (inclusive).
- `--min-deleted`, `--max-deleted`: min/max **deleted** lines in PR patch (inclusive).
- `--min-total-lines`, `--max-total-lines`: min/max **(added + deleted)** lines; default no limit.
- If any of these is set, PRs without a fetched patch are excluded.

### Mode Comparison

| Feature | API Mode | Local Clone Mode |
|---------|----------|------------------|
| Speed | Fast | Slower (requires clone) |
| Accuracy | Medium | **High** |
| API Calls | Many | **Few** |
| Disk Space | None | Required (temporary, auto-deleted) |
| Concurrent Processing | ❌ No (sequential) | ✅ Yes (parallel) |
| Use Case | Quick testing | Production crawling |

## Output Format

Results are saved to `/home/cc/SWGENT-Bench/data/hooked_issue/<reponame>-<date>/issue.json`

JSON file structure:

```json
{
  "repo": "owner/repo",
  "crawl_time": "2025-10-13T10:30:00",
  "total_count": 10,
  "issues": [
    {
      "number": 123,
      "title": "Issue title",
      "url": "https://github.com/owner/repo/issues/123",
      "state": "closed",
      "created_at": "2024-01-01T00:00:00Z",
      "closed_at": "2024-01-10T00:00:00Z",
      "body": "Issue detailed description...",
      "labels": ["bug", "enhancement"],
      "linked_prs": [
        {
          "number": 124,
          "state": "closed",
          "title": "Fix issue #123",
          "url": "https://github.com/owner/repo/pull/124",
          "base_sha": "commit SHA before this PR (for buggy version)",
          "head_sha": "commit SHA of this PR tip (for fixed version)",
          "patch": "full PR diff (optional; omitted if fetch failed)"
        }
      ],
      "ai_judgment": {
        "is_agent_issue": true,
        "response": "Yes. This issue involves LLM provider parameter configuration..."
      }
    }
  ]
}
```

## Agent Issue Criteria

The tool uses AI to determine if an issue is an agent issue based on criteria defined in `agent_issue.md`.

Main criteria dimensions include:
- Incompatibility with LLM providers
- Tool-related issues
- Memory-related issues
- LLM operation issues
- Workflow issues
- Utility issues

For detailed criteria, see [agent_issue.md](./agent_issue.md)

## Workflow

### API Mode Workflow

```
1. Fetch all closed issues (GitHub API)
   ↓
2. Check if issue has text description
   ↓
3. Get linked PRs (3 API methods)
   ↓
4. Check if PR is merged to main branch
   ↓
5. Batch AI judgment for all qualified issues
   ↓
6. Save qualified issues to JSON
```

### Local Clone Mode Workflow (Recommended)

```
0. Clone repository to /home/cc/SWGENT-Bench/data/cached_repo
   ↓
1. Fetch all closed issues (GitHub API)
   ↓
2. Check if issue has text description
   ↓
3. Analyze linked PRs from git history
   - git log to find commits mentioning issue
   - Analyze merge commits to find PR numbers
   - Support "Merge pull request #123" format
   - Support "(#123)" squash merge format
   ↓
4. Check if PR is merged to main branch (GitHub API)
   ↓
5. Batch AI judgment for all qualified issues
   ↓
6. Save qualified issues to JSON
   ↓
7. Automatically delete cloned repository
```

## Important Notes

1. **API Rate Limits**: 
   - Unauthenticated: 60 requests/hour
   - Authenticated: 5000 requests/hour
   - Strongly recommend configuring GITHUB_TOKEN
   - Local Clone mode uses fewer API calls, less likely to hit limits

2. **Processing Time**: 
   - For large repositories (hundreds of issues), processing may take a while
   - Each issue requires API calls and AI judgment
   - Local Clone mode: Initial clone takes time (depends on repo size)
   - **Batch AI processing**: All AI judgments happen at once, more efficient

3. **Disk Space**:
   - Local Clone mode requires temporary storage for repository
   - Temporary cache location: `<project_root>/data/cached_repo` (auto-deleted)
   - Results location: `<project_root>/data/hooked_issue` (**preserved**)
   - Only the cloned repo is deleted, results are kept permanently
   - Recommend at least 1GB temporary space (depends on target repo size)
   - Note: All paths are relative to project root, portable across different systems

4. **Costs**: 
   - Each qualifying issue makes one AI API call
   - Be mindful of API usage quotas
   - **Batch processing**: More efficient, all AI calls happen together

5. **Git Dependencies**:
   - Local Clone mode requires git command installed
   - Check: `git --version`

6. **Concurrent Workers** (Local Clone Mode Only):
   - **API Mode**: Always uses sequential processing (no concurrency) to avoid rate limits
   - **Local Clone Mode**: 
     - Default: 5 workers (balanced performance)
     - Recommended: 5-20 workers depending on your network
     - Higher workers = faster processing (no API rate limit concerns)
     - Safe to use 10-20 workers since most operations are local git commands
   - The `--workers` parameter only affects local clone mode

## Troubleshooting

### GitHub API Error

```bash
API request error: 403 Client Error: rate limit exceeded
```

**Solution**: Configure GITHUB_TOKEN environment variable

### AI Judgment Failed

```bash
AI judgment error: LLM call error
```

**Solution**: Check if FORGE_API_KEY is correctly configured

### No Issues Meeting Criteria

**Possible reasons**:
1. Repository issues are not actually linked to PRs
2. PRs are not merged to main branch
3. AI judges they are not agent issues

## Development

### Project Structure

```
src/issue-hook/
├── issue_crawler.py      # Main program
├── agent_issue.md        # Agent issue criteria
├── requirements.txt      # Python dependencies
└── README.md            # This document

src/forge/
└── api.py               # LLM unified interface

data/hooked_issue/
└── <reponame-date>/
    └── issue.json       # Output results
```

### Extending Functionality

To add custom filtering criteria, modify the `filter_issues` method in the `GitHubIssueCrawler` class.

## Key Improvements

### Concurrent Issue Filtering ⭐⭐ (Local Clone Mode Only)
- **Parallel Processing**: Filter multiple issues simultaneously using ThreadPoolExecutor
- **Smart Mode Selection**: 
  - Local Clone Mode: Concurrent processing enabled (5-20 workers)
  - API Mode: Sequential processing (to avoid rate limits)
- **Configurable Workers**: Adjust concurrency level with `--workers` parameter (default: 5)
- **Thread-Safe Output**: Uses locks to prevent garbled console output
- **Significant Speedup**: 5-10x faster for large repositories in local clone mode
- **Usage**: `--local-clone --workers 10` for 10 concurrent workers

### Batch AI Processing ⭐
- **Before**: AI judgment for each issue during filtering
- **After**: Filter all issues first, then batch AI judgment
- **Benefits**: 
  - More efficient processing
  - Better progress tracking
  - Easier to debug
  - Clear separation of concerns

### English Interface ⭐
- All messages and comments in English
- Better for international collaboration
- Easier to debug

## License

MIT

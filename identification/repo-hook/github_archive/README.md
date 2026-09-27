# GitHub Archive Agent Repository Collector

A tool to collect and filter agent-related repositories from GitHub Archive using keyword matching and AI-powered analysis.

## Quick Start

```bash
cd /home/cc/SWGENT-Bench/src/repo-hook/github_archive

# Install dependencies
pip install -r requirements.txt

# Run (analyzes yesterday's data by default)
python3 main.py
```

## Features

- **Three-stage filtering**:
  1. Keyword matching (78 agent-related keywords + README content)
  2. Star filtering (default: ≥10 stars)
  3. AI deep analysis (based on agent repository definition)

- **Flexible time modes**:
  - Specific date: `--date 2025-10-12`
  - Time window: `--time-window 1h` (last N hours from now)

- **Multi-threaded processing** for fast README fetching
- **Automatic GitHub token support** from environment variables

## Usage

### Basic Examples

```bash
# Analyze last 1 hour
python3 main.py --time-window 1h

# Analyze specific date
python3 main.py --date 2025-10-12

# Quick filter (keyword only, no AI)
python3 main.py --time-window 6h --no-ai

# High-quality repos (50+ stars)
python3 main.py --time-window 1h --min-stars 50
```

### All Options

```bash
python3 main.py \
  --date 2025-10-12          # Specific date (YYYY-MM-DD)
  --time-window 1h           # OR time window (1h/6h/12h/24h)
  --min-stars 10             # Minimum stars (default: 10)
  --limit 50                 # Limit results
  --no-ai                    # Keyword filtering only
  --github-token TOKEN       # GitHub token (or use env var)
```

## Configuration

### 1. GitHub Token (Recommended)

Create `/home/cc/SWGENT-Bench/.env`:

```bash
FORGE_API_KEY=your_forge_api_key
GITHUB_TOKEN=your_github_token
```

Get GitHub token: https://github.com/settings/tokens/new
- Scopes: `public_repo` only
- Rate limit: 60/hour (no token) → 5000/hour (with token)

### 2. Keywords

Edit `config.py` to customize the 78 agent-related keywords.

### 3. Agent Definition

Modify `AGENT_REPO_DEFINITION` in `config.py` to adjust AI judgment criteria.

## Output

Results saved to: `/home/cc/SWGENT-Bench/data/hooked_repo/github_archive_repo_{date}.json`

```json
{
  "date": "2025-10-12",
  "time_window_hours": 1,
  "total_events": 15534,
  "total_repos": 11860,
  "agent_repos_count": 5,
  "min_stars": 10,
  "agent_repos": [
    {"name": "langchain-ai/langchain", "stars": 89234},
    {"name": "microsoft/autogen", "stars": 25678}
  ]
}
```

## Performance

| Stage | Time (255 repos) |
|-------|------------------|
| Keyword filtering | 20-30s (multi-threaded) |
| Star filtering | 3-5min (with token) |
| AI filtering | Depends on count |

## Files

- `main.py` - Entry point
- `github_fetcher.py` - GitHub Archive data fetching
- `github_api.py` - GitHub API client
- `agent_filter.py` - Filtering logic
- `config.py` - Keywords and prompts
- `test_basic.py` - Basic tests

## Testing

```bash
python3 test_basic.py
```

## Notes

- GitHub Archive data has ~1 day delay
- Time window mode automatically handles cross-day scenarios
- AI filtering uses `gpt-4o-mini` for cost efficiency
- Results include star counts for quality assessment






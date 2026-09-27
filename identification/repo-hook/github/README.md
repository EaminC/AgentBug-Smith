# GitHub Awesome Agent Repository Collector

Automatically extract agent-related repositories from GitHub awesome lists (such as awesome-agent, awesome-llm, etc.).

## Features

- 🔍 Search for awesome-related repositories using GitHub API
- ⭐ Support star count filtering (default 50+)
- 🤖 Intelligently extract agent repository list from README using AI
- 📊 Automatically generate JSON format repository list

## Usage

### Basic Usage

```bash
cd /home/cc/SWGENT-Bench/src/repo-hook/github
python main.py
```

### Advanced Options

```bash
# Custom search keywords
python main.py --keywords awesome-agent awesome-llm awesome-ai

# Set minimum star count
python main.py --min-stars 100

# Limit the number of awesome repos per keyword
python main.py --max-awesome-repos 5

# Limit total output repositories
python main.py --limit 100

# Provide GitHub Token (recommended to avoid rate limits)
python main.py --github-token YOUR_TOKEN
```

### Full Parameter Description

- `--keywords`: List of search keywords (default: awesome-agent awesome-llm awesome-ai-agents)
- `--min-stars`: Minimum star count (default: 50)
- `--max-awesome-repos`: Maximum number of awesome repos per keyword (default: 10)
- `--limit`: Limit the number of output repositories
- `--github-token`: GitHub token (recommended to set GITHUB_TOKEN in .env)

## Output Format

The tool generates `github_repo_{date}.json` in `/home/cc/SWGENT-Bench/data/hooked_repo/` directory.

JSON structure:
```json
{
  "date": "2025-10-13",
  "search_keywords": ["awesome-agent", "awesome-llm"],
  "min_stars": 50,
  "awesome_repos_count": 10,
  "agent_repos_count": 156,
  "awesome_repos": [
    {
      "name": "owner/repo",
      "stars": 1234,
      "description": "..."
    }
  ],
  "agent_repos": ["owner/repo1", "owner/repo2"],
  "repo_sources": {
    "owner/repo1": ["awesome-list-1", "awesome-list-2"]
  }
}
```

## Workflow

1. **Search Phase**: Use GitHub Search API to search for repositories containing specified keywords
2. **Filter Phase**: Filter repositories by star count
3. **Extraction Phase**: 
   - Get README from each awesome repository
   - Analyze README content using AI
   - Extract mentioned agent-related repositories
4. **Save Phase**: Generate JSON format result file

## Environment Configuration

Configure in the `.env` file in the project root directory:

```
GITHUB_TOKEN=your_github_token_here
FORGE_API_KEY=your_forge_api_key_here
```

## Dependencies

- python-dotenv: Environment variable management
- openai: LLM API calling

Install dependencies:
```bash
pip install -r requirements.txt
```

## Agent Repository Definition

The tool uses the standards defined in `/home/cc/SWGENT-Bench/src/repo-hook/agent_repo.md` to determine what constitutes an agent repository.

Main characteristics include:
- LLM-controlled "brain" (planning, memory)
- Perception component (environmental input processing)
- Action/tool component (external tool invocation)
- Single/multi-agent architecture support
- Integration with LLM providers

## Notes

- Using GitHub Token is recommended to avoid API rate limits
- AI extraction depends on README quality, false positives may occur
- Processing large numbers of repositories may take considerable time

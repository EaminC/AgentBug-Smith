FROM python:3.12-slim AS test_builder

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ENV ANTHROPIC_SMALL_FAST_MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-dev-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

WORKDIR /app

# Copy entire repository
COPY . .

# Preflight check for required files
RUN [ -f pyproject.toml ] || { echo "pyproject.toml not found"; exit 1; }

# Install system dependencies if needed (from evidence: uv is a dependency)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv globally (as per project's dependency management)
RUN pip install --no-cache-dir uv

# Install project dependencies using uv (as per pyproject.toml and .github/workflows/tests.yml)
# Use --dev and --all-extras to match the test workflow
RUN uv sync --dev --all-extras

# CRITICAL: Install the local project in editable mode
RUN pip install -e .

# Install mandatory testing frameworks (pytest, etc.) explicitly
RUN pip install --no-cache-dir pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# Preflight import check to ensure core modules can be imported
RUN python -c "import crewai; import pytest; print('preflight ok')"

# Set PYTHONPATH to /app to avoid duplicate module loading (src layout)
ENV PYTHONPATH=/app

# Default command (as per evidence: crewai CLI is the entry point)
CMD ["crewai", "--help"]
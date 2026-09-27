FROM python:3.12-slim

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

# Install system dependencies for Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy the entire repository
COPY . .

# Set PYTHONPATH to include the project root and autogpt directory
ENV PYTHONPATH=/app:/app/autogpt:$PYTHONPATH

# Determine package manager and install dependencies
# The repository uses Poetry (pyproject.toml + poetry.lock in autogpt/)
WORKDIR /app/autogpt

# Check for lockfile and install with Poetry; otherwise fallback to pip
# The CI workflows show Poetry usage; there is also a requirements.txt in autogpt/
RUN python -m pip install --upgrade pip wheel setuptools && \
    if [ -f pyproject.toml ] && [ -f poetry.lock ]; then \
        pip install poetry && \
        poetry config virtualenvs.create false && \
        poetry install --no-interaction --no-ansi --no-root; \
    else \
        if [ -f requirements.txt ]; then \
            pip install -r requirements.txt; \
        fi; \
    fi && \
    # Install the project in editable mode
    pip install -e . && \
    # Install mandatory test dependencies
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# Preflight import check to ensure core modules are available
RUN python -c "import autogpt; import pytest; print('preflight ok')"

# The repository includes a CLI script at root (run) but the main entrypoint is not clearly defined.
# Use bash as default command; the test harness will override.
CMD ["/bin/bash"]
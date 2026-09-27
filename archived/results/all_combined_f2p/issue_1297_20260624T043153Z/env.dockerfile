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

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ git \
    && rm -rf /var/lib/apt/lists/*

# Fix safe directory for git operations
RUN git config --global --add safe.directory '*' || true

# Set working directory to /app
WORKDIR /app

# Copy entire repository
COPY . /app

# Upgrade pip, setuptools, and wheel
RUN python -m pip install --no-cache-dir --upgrade pip "setuptools<=81.0.0" wheel

# Install mcp pinned to <2.0.0 first to prevent mcp 2.x breaking change,
# then install agentscope in editable mode and the test runners
RUN pip install --no-cache-dir "mcp<2.0.0" && \
    pip install --no-cache-dir -e ".[dev]" && \
    pip install --no-cache-dir "mcp<2.0.0" "setuptools<=81.0.0" \
        pytest pytest-mock pytest-asyncio pytest-cov anyio litellm pytest-xdist pytest-timeout

# Ensure /app/src has top priority in PYTHONPATH
ENV PYTHONPATH="/app/src:/app"

# Preflight import check
RUN python -c "import agentscope, pytest; print('preflight ok')"

CMD ["/bin/bash"]
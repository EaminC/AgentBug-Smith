# CrewAI Environment Dockerfile - Optimized
FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tuzi-kimi-k2.5/kimi-k2.5"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tuzi-kimi-k2.5/kimi-k2.5"
ENV ANTHROPIC_SMALL_FAST_MODEL="tuzi-kimi-k2.5/kimi-k2.5"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-dev-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

WORKDIR /app

# Install system dependencies and Python packages in a single layer to minimize size
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libxml2-dev libxslt1-dev python3-dev git \
    && rm -rf /var/lib/apt/lists/* /var/tmp/* /tmp/*

# Upgrade pip and install build tools
RUN pip install --no-cache-dir --upgrade pip wheel setuptools "setuptools<=81.0.0" hatchling

# Copy dependency files first for layer caching
COPY pyproject.toml ./
RUN if [ -f "uv.lock" ]; then cp uv.lock ./; fi

# Copy entire repository
COPY . .

# Install the project with all dependencies in one go
# Using pip to install from pyproject.toml directly
RUN pip install --no-cache-dir -e ".[tools,embeddings,mem0]" \
    && pip install --no-cache-dir \
        pytest>=8.0.0 \
        pytest-mock \
        pytest-asyncio \
        pytest-cov \
        pytest-timeout \
        pytest-vcr \
        pytest-subprocess \
        pytest-xdist \
        mem0ai>=0.1.29 \
        tiktoken>=0.7.0 \
    && pip cache purge \
    && rm -rf /root/.cache/pip /tmp/*

# Environment variables for Forge API and project configuration
ENV FORGE_API_KEY="forge-key" \
    FORGE_BASE_URL="https://api.forge.tensorblock.co/v1" \
    MODEL="tuzi-kimi-k2.5/kimi-k2.5" \
    AI_TEMPERATURE="0.7" \
    AI_MAX_TOKENS="1000" \
    AI_TOP_P="1" \
    AI_FREQUENCY_PENALTY="0" \
    AI_PRESENCE_PENALTY="0" \
    ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1" \
    ANTHROPIC_AUTH_TOKEN="forge-key" \
    ANTHROPIC_MODEL="tuzi-kimi-k2.5/kimi-k2.5" \
    ANTHROPIC_SMALL_FAST_MODEL="tuzi-kimi-k2.5/kimi-k2.5" \
    OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1" \
    OPENAI_API_KEY="forge-key" \
    TAVILY_API_KEY="tvly-dev-key" \
    GITHUB_TOKEN="ghp_key" \
    PYTHONUNBUFFERED="1" \
    PYTHONDONTWRITEBYTECODE="1" \
    PYTHONPATH="/app/src:/app" \
    PIP_NO_CACHE_DIR="1" \
    PIP_DISABLE_PIP_VERSION_CHECK="1"

# Pre-flight checks - verify key imports work
RUN python -c "import crewai; print('crewai ok')" && \
    python -c "import pytest; print('pytest ok')" && \
    python -c "import litellm; print('litellm ok')"

CMD ["/bin/bash"]

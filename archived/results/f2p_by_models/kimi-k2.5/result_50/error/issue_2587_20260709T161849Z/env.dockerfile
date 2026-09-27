# CrewAI Dockerfile - Python 3.12 with Forge API configuration
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

# Set all environment variables in a single layer
ENV FORGE_API_KEY="forge-key" \
    FORGE_BASE_URL="https://api.forge.tensorblock.co/v1" \
    MODEL="tuzi-kimi-k2.5/kimi-k2.5" \
    AI_TEMPERATURE="0.7" \
    ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1" \
    ANTHROPIC_AUTH_TOKEN="forge-key" \
    ANTHROPIC_MODEL="tuzi-kimi-k2.5/kimi-k2.5" \
    ANTHROPIC_SMALL_FAST_MODEL="tuzi-kimi-k2.5/kimi-k2.5" \
    OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1" \
    OPENAI_API_KEY="forge-key" \
    TAVILY_API_KEY="tvly-dev-key" \
    GITHUB_TOKEN="ghp_key" \
    PYTHONPATH=/app/src \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies in a minimal layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    git \
    libxml2-dev \
    libxslt1-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Upgrade pip and install build tools
RUN pip install --no-cache-dir --upgrade pip wheel "setuptools<=81.0.0" hatchling

# Copy project first to leverage caching for dependencies
COPY . .

# Install Python dependencies:
# 1. Install core deps from pyproject.toml (via pip install -e .)
# 2. Add test dependencies explicitly
# 3. Clean up cache
RUN pip install --no-cache-dir -e . \
    && pip install --no-cache-dir \
        pytest>=8.0.0 \
        pytest-mock \
        pytest-asyncio>=0.23.7 \
        pytest-cov \
        pytest-xdist \
        pytest-timeout \
        pytest-vcr>=1.0.2 \
        pytest-subprocess>=1.5.2 \
        anyio \
        mem0ai>=0.1.29 \
    && rm -rf ~/.cache/pip /tmp/* /var/tmp/*

# Remove build dependencies to save space
RUN apt-get purge -y --auto-remove gcc python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Preflight verification
RUN python -c "import sys; print(f'Python {sys.version}')" && \
    python -c "import pytest; print('pytest ok')" && \
    python -c "import litellm; print('litellm ok')" && \
    python -c "from crewai import Agent, Crew, Task; print('crewai imports ok')"

CMD ["/bin/bash"]

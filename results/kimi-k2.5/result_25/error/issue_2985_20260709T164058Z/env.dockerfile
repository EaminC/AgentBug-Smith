# CrewAI Dockerfile with Forge API Configuration
FROM python:3.11-slim

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

# Environment variables for Forge API and Python settings (single layer)
ENV FORGE_API_KEY="forge-key" \
    FORGE_BASE_URL="https://api.forge.tensorblock.co/v1" \
    OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1" \
    OPENAI_API_KEY="forge-key" \
    ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1" \
    ANTHROPIC_AUTH_TOKEN="forge-key" \
    ANTHROPIC_MODEL="tuzi-kimi-k2.5/kimi-k2.5" \
    ANTHROPIC_SMALL_FAST_MODEL="tuzi-kimi-k2.5/kimi-k2.5" \
    MODEL="tuzi-kimi-k2.5/kimi-k2.5" \
    AI_TEMPERATURE="0.7" \
    TAVILY_API_KEY="tvly-dev-key" \
    GITHUB_TOKEN="ghp_key" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/src

# Copy entire repository
COPY . /app

# Install dependencies and cleanup in single layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libxml2-dev \
    libxslt1-dev \
    python3-dev \
    && pip install --no-cache-dir --upgrade pip wheel "setuptools<=81.0.0" \
    && pip install --no-cache-dir \
        pytest \
        pytest-mock \
        pytest-asyncio \
        pytest-timeout \
        litellm \
        mem0ai \
    && apt-get purge -y --auto-remove gcc g++ python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /root/.cache/pip /tmp/* /var/tmp/*

# Verify installation (crewai imports from PYTHONPATH, not from pip install)
RUN python -c "import sys; sys.path.insert(0, '/app/src'); from crewai import Agent; print('crewai OK')" \
    && python -c "import pytest; print('pytest OK')"

CMD ["/bin/bash"]

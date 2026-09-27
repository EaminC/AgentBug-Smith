# CrewAI Project Dockerfile - Single Stage Build for Forge API
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

# Set environment variables for Forge API
ENV FORGE_API_KEY="forge-key" \
    FORGE_BASE_URL="https://api.forge.tensorblock.co/v1" \
    MODEL="tuzi-kimi-k2.5/kimi-k2.5" \
    AI_TEMPERATURE="0.7" \
    AI_MAX_TOKENS=1000 \
    AI_TOP_P=1 \
    AI_FREQUENCY_PENALTY=0 \
    AI_PRESENCE_PENALTY=0 \
    ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1" \
    ANTHROPIC_AUTH_TOKEN="forge-key" \
    ANTHROPIC_MODEL="tuzi-kimi-k2.5/kimi-k2.5" \
    ANTHROPIC_SMALL_FAST_MODEL="tuzi-kimi-k2.5/kimi-k2.5" \
    OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1" \
    OPENAI_API_KEY="forge-key" \
    TAVILY_API_KEY="tvly-dev-key" \
    GITHUB_TOKEN="ghp_key" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/src

WORKDIR /app

# Install system dependencies and Python packages in a single layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ python3-dev libxml2-dev libxslt1-dev libffi-dev libssl-dev git \
    && python -m pip install --upgrade pip wheel setuptools "setuptools<=81.0.0" \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/* /tmp/* /var/tmp/*

# Copy the entire repository
COPY . .

# Install the project and dependencies
RUN pip install --no-cache-dir -e . \
    && pip install --no-cache-dir \
    pytest>=8.0.0 \
    pytest-asyncio>=0.23.7 \
    pytest-mock \
    pytest-timeout>=2.3.1 \
    pytest-xdist>=3.6.1 \
    pytest-cov \
    pandas>=2.2.3 \
    pillow>=10.2.0 \
    tiktoken>=0.8.0 \
    mem0ai>=0.1.94 \
    httpx \
    aiohttp \
    anyio

# Verify critical imports work
RUN python -c "import crewai; print('crewai import ok')" \
    && python -c "import pytest; print('pytest import ok')" \
    && echo "preflight ok"

CMD ["/bin/bash"]

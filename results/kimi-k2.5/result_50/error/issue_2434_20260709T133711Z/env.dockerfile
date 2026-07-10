# CrewAI Dockerfile with Forge API - Optimized single-layer build
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
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Copy only necessary files first for better caching
COPY pyproject.toml ./
COPY src/ ./src/
COPY README.md ./
COPY uv.lock ./

# Install dependencies in a single RUN to minimize layers
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc g++ libxml2-dev libxslt1-dev python3-dev && \
    pip install --no-cache-dir --upgrade pip wheel "setuptools<=81.0.0" && \
    pip install --no-cache-dir pytest pytest-mock pytest-asyncio pytest-cov pytest-timeout && \
    pip install --no-cache-dir litellm mem0ai && \
    pip install --no-cache-dir -e . && \
    apt-get purge -y --auto-remove gcc g++ python3-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /root/.cache

# Copy the rest of the repository
COPY . .

# Verify installation
RUN python -c "import pytest; from crewai import Agent, Task, Crew; print('Environment OK')"

CMD ["/bin/bash"]

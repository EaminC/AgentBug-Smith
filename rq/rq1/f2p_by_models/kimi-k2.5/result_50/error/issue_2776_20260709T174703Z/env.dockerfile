# CrewAI Dockerfile - Space-optimized build with Forge API configuration
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

# Set working directory
WORKDIR /app

# Install system dependencies, Python packages, and cleanup in a single RUN to minimize layers
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libxml2-dev \
    libxslt1-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* \
    && pip install --no-cache-dir --upgrade pip wheel setuptools

# Copy only necessary files for dependency installation first (better caching)
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install the package and test dependencies in a single RUN
RUN pip install --no-cache-dir -e . \
    && pip install --no-cache-dir \
    pytest \
    pytest-asyncio \
    pytest-subprocess \
    pytest-recording \
    pytest-randomly \
    pytest-timeout \
    pytest-xdist \
    pytest-mock \
    pytest-cov \
    anyio \
    "setuptools<=81.0.0" \
    mem0ai \
    litellm \
    && rm -rf /root/.cache/pip /tmp/* /var/tmp/*

# Copy the rest of the repository
COPY . .

# Set Python path for src layout
ENV PYTHONPATH=/app/src

# Pre-flight check
RUN python -c "from crewai import Agent, Crew, Task; print('crewai import ok')" && \
    python -c "import pytest; print('pytest import ok')"

# Environment variables for Forge API (consolidated into single ENV)
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
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

CMD ["/bin/bash"]

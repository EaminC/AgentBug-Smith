# CrewAI Dockerfile for Forge API
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
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies and Python packages in a single RUN to minimize layers
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    gcc \
    python3-dev \
    libxml2-dev \
    libxslt1-dev \
    && pip install --no-cache-dir --upgrade pip uv \
    && rm -rf /var/lib/apt/lists/* /root/.cache

# Copy the entire repository
COPY . .

# Install Python dependencies
# Install test dependencies first, then crewai packages
RUN uv pip install --system --no-cache \
    pytest>=8.4.2 \
    pytest-asyncio>=1.2.0 \
    pytest-mock>=3.14.0 \
    pytest-timeout>=2.4.0 \
    pytest-xdist>=3.8.0 \
    pytest-subprocess>=1.5.3 \
    "setuptools<=81.0.0" \
    litellm>=1.74.9 \
    mem0ai>=0.1.94 \
    && uv pip install --system --no-cache -e ./lib/crewai \
    && uv pip install --system --no-cache -e ./lib/crewai-tools \
    && rm -rf /root/.cache

# Verify installation
RUN python -c "import crewai; print('crewai imported successfully')" \
    && python -c "import pytest; print('pytest imported successfully')"

CMD ["/bin/bash"]

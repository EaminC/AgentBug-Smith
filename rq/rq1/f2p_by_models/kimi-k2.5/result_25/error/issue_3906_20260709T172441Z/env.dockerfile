# CrewAI Environment Dockerfile - Space Optimized
# Configured to use Forge API instead of OpenAI API

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

# --- Environment Variables ---
ENV FORGE_API_KEY="forge-key" \
    FORGE_BASE_URL="https://api.forge.tensorblock.co/v1" \
    OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1" \
    OPENAI_API_KEY="forge-key" \
    ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1" \
    ANTHROPIC_AUTH_TOKEN="forge-key" \
    ANTHROPIC_MODEL="tuzi-kimi-k2.5/kimi-k2.5" \
    ANTHROPIC_SMALL_FAST_MODEL="tuzi-kimi-k2.5/kimi-k2.5" \
    MODEL="tuzi-kimi-k2.5/kimi-k2.5" \
    TAVILY_API_KEY="tvly-dev-key" \
    GITHUB_TOKEN="ghp_key" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app

WORKDIR /app

# Copy repository
COPY . .

# Single-layer install to minimize disk usage
RUN apt-get update && apt-get install -y --no-install-recommends \
    git gcc python3-dev libxml2-dev libxslt1-dev \
    && pip install --no-cache-dir --upgrade pip wheel "setuptools<=81.0.0" hatchling \
    && pip install --no-cache-dir \
        pytest pytest-asyncio pytest-mock pytest-cov \
        pytest-timeout pytest-xdist pytest-subprocess \
        vcrpy pytest-recording pytest-randomly \
        anyio litellm mem0ai boto3 \
    && pip install --no-cache-dir ./lib/crewai \
    && (pip install --no-cache-dir ./lib/crewai-tools 2>/dev/null || true) \
    && if [ -f "pyproject.toml" ]; then pip install --no-cache-dir -e . 2>/dev/null || true; fi \
    && apt-get purge -y --auto-remove gcc python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/* \
    && rm -rf /root/.cache/pip /tmp/* /var/tmp/*

# Verification
RUN python -c "import pytest; import crewai; print('preflight ok')"

CMD ["/bin/bash"]

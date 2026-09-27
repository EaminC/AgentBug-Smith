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

# Combine all ENV into single layer, using provided values
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/src \
    FORGE_API_KEY=forge-key \
    FORGE_BASE_URL=https://api.forge.tensorblock.co/v1 \
    MODEL=tuzi-kimi-k2.5/kimi-k2.5 \
    AI_TEMPERATURE=0.7 \
    ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co/v1 \
    ANTHROPIC_AUTH_TOKEN=forge-key \
    ANTHROPIC_MODEL=tuzi-kimi-k2.5/kimi-k2.5 \
    ANTHROPIC_SMALL_FAST_MODEL=tuzi-kimi-k2.5/kimi-k2.5 \
    OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1 \
    OPENAI_API_KEY=forge-key \
    TAVILY_API_KEY=tvly-dev-key \
    GITHUB_TOKEN=ghp_key

# Single RUN: system deps + pip upgrade + cleanup
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc python3-dev libxml2-dev libxslt1-dev zlib1g-dev && \
    pip install --no-cache-dir --upgrade pip wheel "setuptools<=81.0.0" && \
    apt-get purge -y --auto-remove && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/* /tmp/* /root/.cache /var/tmp/*

# Copy repo (including test cassettes)
COPY . .

# Single RUN: install package + test deps + aggressive cleanup
RUN pip install --no-cache-dir -e ".[tools]" && \
    pip install --no-cache-dir pytest pytest-asyncio pytest-mock pytest-xdist pytest-timeout pytest-cov pytest-recording pytest-subprocess anyio httpx aiohttp tiktoken~=0.7.0 mem0ai>=0.1.94 litellm docling>=2.12.0 && \
    rm -rf /root/.cache/pip /root/.cache/uv /tmp/* /var/tmp/*

# Pre-flight check
RUN python -c "import crewai; import pytest; print('preflight ok')"

CMD ["/bin/bash"]

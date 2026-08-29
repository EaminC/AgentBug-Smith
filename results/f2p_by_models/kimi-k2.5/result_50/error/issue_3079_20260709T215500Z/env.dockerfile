# AutoGPT Dockerfile with Forge API configuration - Ultra minimal
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

ENV FORGE_API_KEY="forge-key" \
    OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1" \
    OPENAI_API_KEY="forge-key" \
    ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co" \
    ANTHROPIC_AUTH_TOKEN="forge-key" \
    ANTHROPIC_MODEL="tuzi-kimi-k2.5/kimi-k2.5" \
    ANTHROPIC_SMALL_FAST_MODEL="tuzi-kimi-k2.5/kimi-k2.5" \
    MODEL="tuzi-kimi-k2.5/kimi-k2.5" \
    AI_TEMPERATURE="0.7" \
    GITHUB_TOKEN="ghp_key" \
    TAVILY_API_KEY="tvly-dev-key" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app

COPY . .

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc python3-dev libxml2-dev libxslt1-dev git && \
    pip install --no-cache-dir --upgrade pip wheel "setuptools<=81.0.0" && \
    pip install --no-cache-dir -r requirements.txt 2>/dev/null || true && \
    pip install --no-cache-dir -e . && \
    pip install --no-cache-dir pytest pytest-asyncio pytest-cov pytest-mock pytest-xdist pytest-timeout litellm mem0ai && \
    apt-get purge -y --auto-remove gcc python3-dev libxml2-dev libxslt1-dev && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /root/.cache/* /var/cache/apt/* && \
    python -c "import pytest; print('pytest ok')"

CMD ["/bin/bash"]

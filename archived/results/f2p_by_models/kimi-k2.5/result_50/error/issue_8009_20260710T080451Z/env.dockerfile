# AutoGPT Environment Dockerfile with Forge API Configuration
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

# Combined ENV to reduce layers
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app \
    FORGE_API_KEY="forge-key" \
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
    PATH="/venv/bin:$PATH"

# Single RUN for system deps, venv, and test tools - aggressive cleanup
RUN apt-get update && \
    apt-get install -y --no-install-recommends git gcc g++ libffi-dev libxml2-dev libxslt1-dev python3-dev && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/* /tmp/* /var/tmp/* && \
    python3 -m venv /venv && \
    /venv/bin/pip install --no-cache-dir --upgrade pip wheel "setuptools<=81.0.0" && \
    /venv/bin/pip install --no-cache-dir pytest pytest-mock pytest-asyncio pytest-cov pytest-xdist pytest-timeout litellm mem0ai && \
    rm -rf /root/.cache/pip /tmp/* /var/tmp/* /venv/share/man /venv/share/doc

# Copy repository
COPY . .

# Install packages - conditional and with immediate cleanup
RUN set -e; \
    if [ -f "/app/benchmark/setup.py" ] || [ -f "/app/benchmark/pyproject.toml" ]; then \
        cd /app/benchmark && /venv/bin/pip install --no-cache-dir -e . 2>/dev/null || true; \
    fi; \
    if [ -f "/app/forge/setup.py" ] || [ -f "/app/forge/pyproject.toml" ]; then \
        cd /app/forge && /venv/bin/pip install --no-cache-dir -e . 2>/dev/null || true; \
    fi; \
    if [ -f "/app/autogpt/setup.py" ] || [ -f "/app/autogpt/pyproject.toml" ]; then \
        cd /app/autogpt && /venv/bin/pip install --no-cache-dir -e . 2>/dev/null || true; \
    fi; \
    if [ -d "/app/rnd/autogpt_libs" ] && ([ -f "/app/rnd/autogpt_libs/setup.py" ] || [ -f "/app/rnd/autogpt_libs/pyproject.toml" ]); then \
        cd /app/rnd/autogpt_libs && /venv/bin/pip install --no-cache-dir -e . 2>/dev/null || true; \
    fi; \
    if [ -d "/app/rnd/autogpt_server" ] && ([ -f "/app/rnd/autogpt_server/setup.py" ] || [ -f "/app/rnd/autogpt_server/pyproject.toml" ]); then \
        cd /app/rnd/autogpt_server && /venv/bin/pip install --no-cache-dir -e . 2>/dev/null || true; \
    fi; \
    find /app -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true; \
    find /app -type f -name "*.pyc" -delete 2>/dev/null || true; \
    rm -rf /root/.cache/pip /tmp/* /var/tmp/* /venv/share/man /venv/share/doc

# Pre-flight check
RUN /venv/bin/python -c "import pytest; print('preflight ok')"

CMD ["/bin/bash"]

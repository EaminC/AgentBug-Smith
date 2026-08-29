# Multi-stage build to minimize final image size
FROM python:3.11-slim as builder

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

# Install build dependencies first (in a separate layer that will be discarded)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install wheel
RUN pip install --no-cache-dir --upgrade pip wheel "setuptools<=81.0.0"

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies into a virtual environment
RUN python3 -m venv /venv && \
    /venv/bin/pip install --no-cache-dir --upgrade pip wheel && \
    /venv/bin/pip install --no-cache-dir \
        pytest pytest-mock pytest-asyncio pytest-cov anyio litellm mem0ai && \
    /venv/bin/pip install --no-cache-dir -r requirements.txt || true

# Final stage - smaller base
FROM python:3.11-slim

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /venv /venv

# Copy entire repository
COPY . .

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
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app \
    VIRTUAL_ENV=/venv \
    PATH="/venv/bin:$PATH"

# Install the package in editable mode using the virtual environment
# and clean up in a single RUN to minimize layers
RUN /venv/bin/pip install --no-cache-dir -e . && \
    /venv/bin/python -c "import pytest; print('preflight ok')" && \
    rm -rf /root/.cache/pip /tmp/* /var/tmp/*

CMD ["/bin/bash"]

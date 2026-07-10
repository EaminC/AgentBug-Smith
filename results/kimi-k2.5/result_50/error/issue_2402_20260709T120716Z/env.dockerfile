# CrewAI Environment Dockerfile - Multi-stage build for minimal disk usage
FROM python:3.12-slim AS builder

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

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    python3-dev \
    libxml2-dev \
    libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install build tools
RUN python -m pip install --no-cache-dir --upgrade pip wheel "setuptools<=81.0.0" hatchling

# Install all Python dependencies in one layer
RUN python -m pip install --no-cache-dir \
    pydantic \
    openai \
    "litellm==1.67.2" \
    instructor \
    pdfplumber \
    regex \
    opentelemetry-api \
    opentelemetry-sdk \
    opentelemetry-exporter-otlp-proto-http \
    chromadb \
    openpyxl \
    pyvis \
    auth0-python \
    python-dotenv \
    click \
    appdirs \
    jsonref \
    "json-repair>=0.25.2" \
    uv \
    tomli-w \
    tomli \
    blinker \
    json5 \
    pytest \
    pytest-asyncio \
    pytest-mock \
    pytest-timeout \
    pytest-xdist \
    pytest-cov \
    pytest-subprocess \
    pytest-recording \
    anyio \
    mem0ai \
    anthropic \
    "crewai-tools~=0.42.2" \
    lxml \
    beautifulsoup4 \
    requests \
    numpy \
    tiktoken \
    pandas

# Final stage
FROM python:3.12-slim

# Set all environment variables in a single layer
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
    AI_MAX_TOKENS="1000" \
    TAVILY_API_KEY="tvly-dev-key" \
    GITHUB_TOKEN="ghp_key" \
    PYTHONPATH=/app/src \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_ROOT_USER_ACTION=ignore \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100

WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy source code
COPY . .

# Verification - combined with cache cleanup
RUN python -c "import pytest, openai, anthropic, litellm; from crewai import Agent, Task, Crew; print('preflight ok')" \
    && rm -rf /root/.cache /tmp/* /var/tmp/*

CMD ["/bin/bash"]

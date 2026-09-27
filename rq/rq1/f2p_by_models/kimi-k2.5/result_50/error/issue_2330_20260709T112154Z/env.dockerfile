# syntax=docker/dockerfile:1
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
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/src

WORKDIR /app

# Install system dependencies (keep for builds)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libxml2-dev libxslt1-dev python3-dev \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/*

# Upgrade pip first
RUN pip install --no-cache-dir --upgrade pip wheel "setuptools<=81.0.0"

# Install core dependencies first (smaller layer)
RUN pip install --no-cache-dir \
    pydantic>=2.4.2 \
    openai>=1.13.3 \
    litellm==1.60.2 \
    instructor>=1.3.3

# Install text processing and data handling
RUN pip install --no-cache-dir \
    pdfplumber>=0.11.4 \
    regex>=2024.9.11 \
    chromadb>=0.5.23 \
    openpyxl>=3.1.5 \
    pyvis>=0.3.2 \
    pandas>=2.2.3

# Install telemetry and monitoring
RUN pip install --no-cache-dir \
    opentelemetry-api>=1.30.0 \
    opentelemetry-sdk>=1.30.0 \
    opentelemetry-exporter-otlp-proto-http>=1.30.0

# Install authentication and configuration
RUN pip install --no-cache-dir \
    auth0-python>=4.7.1 \
    python-dotenv>=1.0.0 \
    click>=8.1.7 \
    appdirs>=1.4.4 \
    jsonref>=1.1.0 \
    json-repair>=0.25.2 \
    uv>=0.4.25 \
    tomli-w>=1.1.0 \
    tomli>=2.0.2 \
    blinker>=1.9.0 \
    json5>=0.10.0 \
    requests

# Install CrewAI extras
RUN pip install --no-cache-dir \
    crewai-tools~=0.38.0 \
    tiktoken>=0.7.0 \
    fastembed>=0.4.1 \
    mem0ai>=0.1.29 \
    docling>=2.12.0 \
    aisuite>=0.1.10

# Install test dependencies
RUN pip install --no-cache-dir \
    pytest>=8.0.0 \
    pytest-vcr>=1.0.2 \
    pytest-asyncio>=0.23.7 \
    pytest-subprocess>=1.5.2 \
    pytest-mock \
    pytest-xdist \
    pytest-timeout \
    pytest-cov

# Copy entire repository
COPY . .

# Install the package itself (editable mode for src layout)
RUN pip install --no-cache-dir -e .

# Cleanup build dependencies and pip cache
RUN apt-get purge -y --auto-remove gcc g++ python3-dev \
    && rm -rf /root/.cache/pip /tmp/* /var/tmp/* \
    && find /usr/local/lib/python*/site-packages -name "*.pyc" -delete 2>/dev/null || true \
    && find /usr/local/lib/python*/site-packages -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Verify installation
RUN python -c "import crewai; import pytest; print('Installation OK')"

CMD ["/bin/bash"]

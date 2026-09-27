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

# Set environment variables for Forge API
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tuzi-kimi-k2.5/kimi-k2.5"
ENV AI_TEMPERATURE="0.7"
ENV AI_MAX_TOKENS="1000"
ENV AI_TOP_P="1"
ENV AI_FREQUENCY_PENALTY="0"
ENV AI_PRESENCE_PENALTY="0"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tuzi-kimi-k2.5/kimi-k2.5"
ENV ANTHROPIC_SMALL_FAST_MODEL="tuzi-kimi-k2.5/kimi-k2.5"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-dev-key"
ENV GITHUB_TOKEN="ghp_key"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

WORKDIR /app

# Install system dependencies and Python packages in a single layer to minimize disk usage
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libxml2-dev \
    libxslt1-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip wheel hatchling

# Copy source
COPY . .

# Install the package and all test dependencies
# CrewAI uses src/ layout - set PYTHONPATH instead of editable install
RUN pip install --no-cache-dir \
    "setuptools<=81.0.0" \
    pytest>=8.0.0 \
    pytest-vcr>=1.0.2 \
    pytest-asyncio>=0.23.7 \
    pytest-subprocess>=1.5.2 \
    pytest-mock \
    pytest-xdist \
    pytest-timeout \
    pytest-cov \
    litellm \
    mem0ai \
    crewai-tools>=0.37.0 \
    tiktoken~=0.7.0 \
    pandas>=2.2.3 \
    chromadb>=0.5.23 \
    openpyxl>=3.1.5 \
    pdfplumber>=0.11.4 \
    regex>=2024.9.11 \
    opentelemetry-api>=1.30.0 \
    opentelemetry-sdk>=1.30.0 \
    opentelemetry-exporter-otlp-proto-http>=1.30.0 \
    pyvis>=0.3.2 \
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
    openai>=1.13.3 \
    instructor>=1.3.3 \
    pydantic>=2.4.2

# Verify installation
RUN python -c "import sys; sys.path.insert(0, '/app/src'); import crewai; import pytest; print('preflight ok')"

CMD ["/bin/bash"]

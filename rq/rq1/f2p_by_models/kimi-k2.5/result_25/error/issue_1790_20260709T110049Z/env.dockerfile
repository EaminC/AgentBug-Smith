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

# Set all environment variables in a single ENV directive
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
    PYTHONPATH=/app/src

WORKDIR /app

# Copy only necessary files first for better caching
COPY pyproject.toml .
COPY uv.lock .
COPY README.md .
COPY src ./src

# Install dependencies, the project, and test tools in a single RUN to minimize layers
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    git \
    libxml2-dev \
    libxslt1-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --no-cache-dir --upgrade pip wheel \
    && python -m pip install --no-cache-dir \
        pydantic \
        openai \
        opentelemetry-api \
        opentelemetry-sdk \
        opentelemetry-exporter-otlp-proto-http \
        instructor \
        regex \
        click \
        python-dotenv \
        appdirs \
        jsonref \
        json-repair \
        auth0-python \
        litellm \
        pyvis \
        uv \
        tomli-w \
        tomli \
        chromadb \
        pdfplumber \
        openpyxl \
        blinker \
        pytest \
        pytest-mock \
        pytest-asyncio \
        pytest-cov \
        pytest-xdist \
        pytest-timeout \
        pytest-vcr \
        "setuptools<=81.0.0" \
        mem0ai \
    && python -m pip install --no-cache-dir -e . \
    && apt-get purge -y --auto-remove gcc python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /root/.cache/pip /root/.cache/uv \
    && python -c "import crewai; import pytest; print('Preflight OK')"

# Copy remaining files (tests, docs, etc.)
COPY . .

CMD ["/bin/bash"]

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

# Set working directory
WORKDIR /app

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
    AI_TOP_P="1" \
    TAVILY_API_KEY="tvly-dev-key" \
    GITHUB_TOKEN="ghp_key" \
    PYTHONUNBUFFERED="1" \
    PYTHONDONTWRITEBYTECODE="1" \
    PIP_NO_CACHE_DIR="1" \
    PIP_DISABLE_PIP_VERSION_CHECK="1"

# Install system dependencies in a single layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    libffi-dev \
    libssl-dev \
    git \
    curl \
    libxml2 \
    libxslt1.1 \
    zlib1g \
    libffi8 \
    libssl3 \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Upgrade pip and install base test dependencies
RUN pip install --no-cache-dir --upgrade pip wheel "setuptools<=81.0.0" \
    && pip install --no-cache-dir \
        pytest pytest-mock pytest-asyncio pytest-cov pytest-xdist \
        pytest-timeout asynctest anyio litellm mem0ai

# Copy requirements first for better caching
COPY requirements.txt .

# Install requirements (with conditional check)
RUN if [ -f "requirements.txt" ]; then \
        pip install --no-cache-dir -r requirements.txt; \
    fi

# Copy the entire application
COPY . .

# Install the package in editable mode (works with both setup.py and pyproject.toml)
RUN pip install --no-cache-dir -e .

# Verify Python and key imports work
RUN python -c "import sys; print('Python version:', sys.version)" \
    && python -c "import pytest; print('pytest version:', pytest.__version__)"

CMD ["/bin/bash"]

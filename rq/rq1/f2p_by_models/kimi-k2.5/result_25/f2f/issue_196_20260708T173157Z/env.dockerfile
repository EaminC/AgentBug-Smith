# AgentScope Multi-Agent Platform Dockerfile
# Using Forge API instead of OpenAI API

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

# Set working directory
WORKDIR /app

# Install system dependencies with robust retry logic for transient network failures
# Install packages one by one to avoid cascading failures
RUN set -eux; \
    # Configure apt for better reliability
    echo 'Acquire::Retries "10";' > /etc/apt/apt.conf.d/80-retries; \
    echo 'Acquire::http::Timeout "180";' >> /etc/apt/apt.conf.d/80-retries; \
    echo 'Acquire::https::Timeout "180";' >> /etc/apt/apt.conf.d/80-retries; \
    # Update package lists with retry
    for i in 1 2 3 4 5; do \
        apt-get update --fix-missing && break; \
        echo "APT update attempt $i failed, waiting before retry..."; \
        sleep $(($i * 10)); \
    done; \
    # Install essential build tools first
    for i in 1 2 3 4 5; do \
        apt-get install -y --no-install-recommends --fix-missing gcc && break; \
        echo "gcc install attempt $i failed, waiting before retry..."; \
        sleep $(($i * 10)); \
    done; \
    for i in 1 2 3 4 5; do \
        apt-get install -y --no-install-recommends --fix-missing g++ && break; \
        echo "g++ install attempt $i failed, waiting before retry..."; \
        sleep $(($i * 10)); \
    done; \
    for i in 1 2 3 4 5; do \
        apt-get install -y --no-install-recommends --fix-missing libxml2-dev && break; \
        echo "libxml2-dev install attempt $i failed, waiting before retry..."; \
        sleep $(($i * 10)); \
    done; \
    for i in 1 2 3 4 5; do \
        apt-get install -y --no-install-recommends --fix-missing libxslt1-dev && break; \
        echo "libxslt1-dev install attempt $i failed, waiting before retry..."; \
        sleep $(($i * 10)); \
    done; \
    for i in 1 2 3 4 5; do \
        apt-get install -y --no-install-recommends --fix-missing python3-dev && break; \
        echo "python3-dev install attempt $i failed, waiting before retry..."; \
        sleep $(($i * 10)); \
    done; \
    for i in 1 2 3 4 5; do \
        apt-get install -y --no-install-recommends --fix-missing git && break; \
        echo "git install attempt $i failed, waiting before retry..."; \
        sleep $(($i * 10)); \
    done; \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Upgrade pip and install wheel
RUN python -m pip install --upgrade pip wheel --no-cache-dir

# --- Forge API Environment Configuration ---
# OpenAI SDK compatibility
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key

# Anthropic SDK compatibility
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co
ENV ANTHROPIC_AUTH_TOKEN=forge-key

# Additional project environment variables
ENV FORGE_API_KEY=forge-key
ENV FORGE_BASE_URL=https://api.forge.tensorblock.co/v1
ENV MODEL=tuzi-kimi-k2.5/kimi-k2.5
ENV AI_TEMPERATURE=0.7
ENV AI_MAX_TOKENS=1000
ENV AI_TOP_P=1
ENV AI_FREQUENCY_PENALTY=0
ENV AI_PRESENCE_PENALTY=0

# Copy the entire repository
COPY . .

# Install Python dependencies in the correct order:
# 1. First install core dependencies including matplotlib (needed for examples/game_gomoku)
# 2. Install project in editable mode
# 3. Install test dependencies
RUN pip install --no-cache-dir \
    docstring_parser \
    loguru==0.6.0 \
    tiktoken \
    Pillow \
    requests \
    chardet \
    inputimeout \
    "openai>=1.3.0" \
    numpy \
    matplotlib \
    Flask==3.0.0 \
    Flask-Cors==4.0.0 \
    Flask-SocketIO==5.3.6 \
    dashscope==1.14.1 \
    "ollama>=0.1.7" \
    "google-generativeai>=0.4.0" \
    zhipuai \
    pytest \
    pytest-mock \
    pytest-asyncio \
    pytest-cov \
    pytest-xdist \
    pytest-timeout \
    "setuptools<=81.0.0" \
    litellm \
    mem0ai

# Install the project in editable mode
RUN pip install --no-cache-dir -e .

# Set PYTHONPATH for proper module resolution (both src/ and root)
ENV PYTHONPATH=/app/src:/app

# Pre-flight verification - check that key packages can be imported
RUN python -c "import sys; print('Python version:', sys.version)" && \
    python -c "import pytest; print('pytest:', pytest.__version__)" && \
    python -c "import requests; print('requests:', requests.__version__)" && \
    python -c "import numpy; print('numpy:', numpy.__version__)" && \
    python -c "import matplotlib; print('matplotlib:', matplotlib.__version__)" && \
    python -c "from matplotlib import pyplot as plt, patches; print('matplotlib patches imported successfully')" && \
    python -c "import agentscope; print('agentscope version:', agentscope.__version__)" && \
    echo "All pre-flight checks passed"

# Default command
CMD ["/bin/bash"]

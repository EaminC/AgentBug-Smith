# Open Interpreter - Python Project Dockerfile with Node.js support
# This project uses Poetry for dependency management and needs Node.js for JS execution

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

# Set environment variables for Forge API (OpenAI-compatible)
ENV FORGE_API_KEY=forge-key
ENV FORGE_BASE_URL=https://api.forge.tensorblock.co/v1

# OpenAI SDK compatibility
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key

# Anthropic SDK compatibility
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co/v1
ENV ANTHROPIC_AUTH_TOKEN=forge-key

# Other API keys from environment
ENV GITHUB_TOKEN=ghp_key
ENV TAVILY_API_KEY=tvly-dev-key

# Model configuration
ENV MODEL=tuzi-kimi-k2.5/kimi-k2.5
ENV ANTHROPIC_MODEL=tuzi-kimi-k2.5/kimi-k2.5
ENV ANTHROPIC_SMALL_FAST_MODEL=tuzi-kimi-k2.5/kimi-k2.5

# Prevent Python from writing bytecode and buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8

# Install system dependencies including Node.js with retry logic
RUN set -e; \
    for i in 1 2 3; do \
        echo "Attempt $i: Installing system dependencies..."; \
        apt-get update && \
        apt-get install -y --no-install-recommends --fix-missing \
            gcc \
            python3-dev \
            libxml2-dev \
            libxslt1-dev \
            git \
            curl \
            ca-certificates \
            gnupg \
        && rm -rf /var/lib/apt/lists/* && break || { \
            echo "Attempt $i failed. Retrying in 5 seconds..."; \
            sleep 5; \
        }; \
    done

# Install Node.js 20.x (needed for JavaScript code execution)
RUN set -e; \
    mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list && \
    apt-get update && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Verify Node.js installation
RUN node --version && npm --version

# Upgrade pip and install poetry
RUN python3 -m pip install --upgrade pip wheel "setuptools<=81.0.0" && \
    python3 -m pip install poetry==1.7.1

# Configure poetry to not create virtualenvs (install packages globally)
RUN poetry config virtualenvs.create false

# Copy the entire repository
COPY . .

# Install dependencies using poetry
# The --no-interaction and --no-ansi flags make it suitable for Docker
RUN poetry install --no-interaction --no-ansi

# Also install pytest via pip to ensure it's available globally
RUN pip install pytest==7.4.0 pytest-mock pytest-asyncio pytest-cov anyio litellm

# Verify installation by importing key modules
RUN python3 -c "import interpreter; print('Interpreter imported successfully')" && \
    python3 -c "import pytest; print('Pytest imported successfully')" && \
    python3 -c "import rich; print('Rich imported successfully')"

# Set final working directory
WORKDIR /app

# Default command
CMD ["/bin/bash"]

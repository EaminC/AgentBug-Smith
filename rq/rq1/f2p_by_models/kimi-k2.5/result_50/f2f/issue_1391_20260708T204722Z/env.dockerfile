# Base image with Python 3.11
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

# Install system dependencies with retry logic for transient network failures
RUN apt-get update -qq || (sleep 5 && apt-get update -qq) && \
    apt-get install -y --no-install-recommends --fix-missing \
    gcc \
    python3-dev \
    libxml2-dev \
    libxslt1-dev \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install build tools
RUN python -m pip install --upgrade pip wheel setuptools

# Copy the entire repository first
COPY . .

# Set PYTHONPATH for src/ layout
ENV PYTHONPATH=/app/src

# Install the package with distribute extras (includes grpcio, grpcio-tools for protobuf support)
# Use editable install (-e) for src/ layout to make imports work properly
# Also install testing tools and litellm
RUN pip install --no-cache-dir -e ".[distribute]" && \
    pip install --no-cache-dir \
    pytest \
    pytest-mock \
    pytest-asyncio \
    pytest-cov \
    pre-commit \
    litellm

# Preflight check - verify key packages are importable
RUN python -c "import agentscope; import pytest; import openai; print('preflight ok')"

# Final command
CMD ["/bin/bash"]

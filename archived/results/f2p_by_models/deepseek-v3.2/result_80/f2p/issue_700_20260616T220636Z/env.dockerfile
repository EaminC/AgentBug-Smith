FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ENV ANTHROPIC_SMALL_FAST_MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-dev-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

WORKDIR /app

# Set environment variables for Forge API
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co/v1
ENV ANTHROPIC_AUTH_TOKEN=forge-key
ENV MODEL=tuzi-deepseek-v3.2/deepseek-v3.2
ENV AI_TEMPERATURE=0.7
ENV AI_MAX_TOKENS=1000
ENV AI_TOP_P=1
ENV AI_FREQUENCY_PENALTY=0
ENV AI_PRESENCE_PENALTY=0
ENV TAVILY_API_KEY=tvly-dev-key
ENV GITHUB_TOKEN=ghp_key
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    universal-ctags \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy entire repository (including any externally injected test scripts)
COPY . .

# Upgrade packaging tools early
RUN python -m pip install --upgrade pip setuptools wheel

# Install dependencies from requirements.txt and the project itself
# branch: python/requirements.txt
RUN pip install -r requirements.txt && \
    pip install -e . && \
    pip install pytest pytest-mock pytest-asyncio pytest-cov pytest-xdist pytest-timeout "setuptools<=81.0.0" litellm mem0ai anyio

# Preflight import check to verify core modules are available
RUN python -c 'import pkg_resources, pytest, aider; print("preflight ok")'

# Ensure the environment supports standalone Python scripts
RUN python -c "import sys, os, json, requests, pytest, unittest, tempfile, shutil, subprocess; print('Standalone script environment ready')"

# Default command - bash shell for testing environment
CMD ["/bin/bash"]
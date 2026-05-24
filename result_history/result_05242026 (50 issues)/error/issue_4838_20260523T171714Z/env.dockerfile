# syntax=docker/dockerfile:1

FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tensorblock/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV GITHUB_TOKEN="ghp_key"
ENV TAVILY_API_KEY="tvly-key"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tensorblock/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="tensorblock/gpt-4.1-mini"
ENV OPENAI_API_KEY="forge-key"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
# --- end inject ---

# Set environment variables for Forge API compatibility
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"

WORKDIR /app

# Install system dependencies needed for Python builds and testing
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc build-essential git libffi-dev libssl-dev python3-dev libxml2-dev libxslt1-dev zlib1g-dev ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy entire repo
COPY . .

# Upgrade pip, setuptools, wheel
RUN python -m pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --upgrade setuptools wheel

# Improved install to avoid PyYAML build error on Python 3.12
RUN set -eux; \
    pip install --upgrade build setuptools wheel; \
    if [ -f requirements.txt ]; then \
        pip install --no-cache-dir -r requirements.txt; \
    fi; \
    # Install all sub-packages in editable mode if multi-package layout detected
    # Assuming sub-packages in libs/ and packages/ if exist
    if [ -d libs ]; then \
        for d in libs/*; do \
            if [ -f "$d/setup.py" ] || [ -f "$d/pyproject.toml" ]; then \
                pip install --no-cache-dir -e "$d"; \
            fi; \
        done; \
    fi; \
    if [ -d packages ]; then \
        for d in packages/*; do \
            if [ -f "$d/setup.py" ] || [ -f "$d/pyproject.toml" ]; then \
                pip install --no-cache-dir -e "$d"; \
            fi; \
        done; \
    fi; \
    # Install root package in editable mode unconditionally
    pip install --no-cache-dir -e .; \
    pip install --no-cache-dir pytest pytest-mock pytest-asyncio pytest-cov anyio litellm pytest-xdist pytest-timeout mem0ai

# Set PYTHONPATH to include all source directories for multi-package repo
ENV PYTHONPATH=/app:/app/libs:/app/packages

# Preflight test imports
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

# Default command to open bash shell
CMD ["/bin/bash"]
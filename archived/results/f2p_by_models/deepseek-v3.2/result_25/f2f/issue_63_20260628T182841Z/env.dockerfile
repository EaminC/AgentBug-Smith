FROM python:3.12-slim AS test_builder

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

# Install system dependencies required for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip, setuptools and wheel to latest versions
RUN python -m pip install --upgrade pip setuptools wheel

# Copy entire repository into container
COPY . .

# Install dependencies with robust conditional logic
RUN set -eux; \
    if [ -f "requirements.txt" ]; then \
        pip install -r requirements.txt; \
    elif [ -f "pyproject.toml" ] && [ -f "poetry.lock" ]; then \
        pip install poetry; \
        poetry install --no-root; \
    elif [ -f "pyproject.toml" ]; then \
        pip install -e .; \
    fi; \
    # Always install editable local package to ensure imports work \
    pip install -e .; \
    # Install test dependencies \
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio pytest-xdist pytest-timeout

# Explicitly set PYTHONPATH to include source directories
ENV PYTHONPATH=/app:/app/src

# Preflight check for pytest
RUN python -c 'import pytest; print("preflight ok")'

# Default command for testing environment
CMD ["/bin/bash"]
FROM python:3.12-slim

# Set working directory
WORKDIR /app

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
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1" \
    OPENAI_API_KEY="forge-key" \
    ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co" \
    ANTHROPIC_AUTH_TOKEN="forge-key"

# Install system dependencies required for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip, setuptools and wheel to latest versions
RUN python -m pip install --upgrade pip setuptools wheel

# Copy entire repository into container
COPY . .

# Install dependencies with robust conditional logic and ensure test tooling
RUN set -eux; \
    if [ -f "requirements.txt" ]; then \
        pip install -r requirements.txt; \
    elif [ -f "pyproject.toml" ] && [ -f "poetry.lock" ]; then \
        pip install poetry; \
        poetry install; \
    elif [ -f "pyproject.toml" ]; then \
        pip install -e .; \
    fi; \
    # Always install editable local package to ensure imports work \
    pip install -e .; \
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio pytest-xdist pytest-timeout "setuptools<=81.0.0" litellm

# Explicitly set PYTHONPATH to include source directories to avoid import errors
ENV PYTHONPATH=/app/src:/app

# Preflight check for pytest and dependencies
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

# Default command for testing environment
CMD ["/bin/bash"]

# branch: python/requirements.txt or pyproject.toml
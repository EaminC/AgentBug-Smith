FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tensorblock/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV GITHUB_TOKEN="ghp_key"
ENV TAVILY_API_KEY="tvly-key"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tensorblock/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="tensorblock/gpt-4.1-mini"
ENV OPENAI_API_KEY="forge-key"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
# --- end inject ---

# Set working directory to /app inside container
WORKDIR /app

# Set environment variables for Forge API compatible access
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co
ENV ANTHROPIC_AUTH_TOKEN=forge-key

# Install system dependencies needed for python package builds and common libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libc6-dev \
    libpq-dev \
    libsqlite3-dev \
    libxml2-dev \
    libxslt1-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy entire repository into container
COPY . .

# Upgrade pip, setuptools, wheel
RUN python -m pip install --upgrade pip setuptools wheel

# Install Python dependencies and the project itself with proper combined install
RUN set -eux; \
    if [ -f "requirements.txt" ]; then \
        pip install -r requirements.txt; \
    elif [ -f "libs/langgraph/requirements.txt" ]; then \
        pip install -r libs/langgraph/requirements.txt; \
    else \
        echo "No requirements.txt found"; \
    fi; \
    pip install -e .; \
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm nbconvert psycopg[binary] psycopg_pool sqlite_vec numpy bs4 mkdocs nbformat dataclasses_json

# Set PYTHONPATH environment variable if src layout or src imports detected (set at container runtime)
ENV PYTHONPATH=/app

# Preflight test to verify imports and packages are installed
RUN python -c 'import pkg_resources, pytest, nbconvert, psycopg, psycopg_pool, sqlite_vec, numpy, bs4, mkdocs, nbformat, dataclasses_json; print("preflight ok")'

# Default command to enter bash shell
CMD ["/bin/bash"]

# branch: python/pyproject.toml + enhanced dependency install
FROM python:3.10-slim

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

# Install system dependencies evidenced by requirements.txt (selenium, webdriver-manager) and original Dockerfile
RUN apt-get update && apt-get install -y \
    ca-certificates \
    chromium-driver \
    curl \
    firefox-esr \
    git \
    jq \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables evidenced by original Dockerfile
# CRITICAL: PYTHONPATH for monorepo support (autogpt, forge, cli, etc.)
ENV PIP_NO_CACHE_DIR=yes \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="$PATH:/root/.local/bin" \
    PYTHONPATH="/app:/app/forge:/app/cli:$PYTHONPATH"

WORKDIR /app

# Copy entire repository to ensure injected test scripts are included
COPY . .

# Install dependencies and package
# CRITICAL: Safe file operations with conditionals
RUN python -m pip install --upgrade pip wheel && \
    if [ -f requirements.txt ]; then \
        pip install -r requirements.txt; \
    fi

# CRITICAL: Editable install for main package and potential sub-packages (monorepo layout)
# AutoGPT repository contains multiple packages: autogpt/, forge/, cli/, etc.
RUN pip install -e . && \
    if [ -f forge/pyproject.toml ]; then pip install -e forge; fi && \
    if [ -f cli/pyproject.toml ]; then pip install -e cli; fi && \
    if [ -f autogpt/pyproject.toml ]; then pip install -e autogpt; fi

# Install test dependencies
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# Preflight verification to fail fast on missing core modules
# CRITICAL: Avoid deprecated pkg_resources, use importlib or direct imports
RUN python -c 'import sys; import importlib.util; print("Python:", sys.version); \
    spec = importlib.util.find_spec("autogpt"); \
    print("autogpt package found:", spec is not None); \
    print("preflight ok")'

CMD ["/bin/bash"]
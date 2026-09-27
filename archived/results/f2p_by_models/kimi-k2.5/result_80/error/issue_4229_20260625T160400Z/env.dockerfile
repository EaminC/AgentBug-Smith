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

# Install system dependencies evidenced by requirements.txt (selenium, webdriver-manager) and existing Dockerfile
RUN apt-get update && apt-get install -y \
    chromium-driver \
    firefox-esr \
    ca-certificates \
    curl \
    jq \
    wget \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy entire repository as required by test harness
COPY . .

# Install dependencies: requirements.txt (conditional), local package, and mandatory test tooling
RUN python -m pip install --upgrade pip wheel && \
    if [ -f requirements.txt ]; then pip install -r requirements.txt; fi && \
    pip install -e . && \
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# Handle potential monorepo/multi-package layout by setting PYTHONPATH
# This ensures imports work for both src/ and lib/ style layouts
ENV PYTHONPATH=/app:/app/src:/app/libs:/app/packages

# Preflight verification to fail fast on missing core modules
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

CMD ["/bin/bash"]
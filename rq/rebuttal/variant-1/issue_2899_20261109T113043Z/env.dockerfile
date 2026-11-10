# branch: python/pyproject.toml
FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="openrouter2/openai/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="openrouter2/openai/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="openrouter2/openai/gpt-4.1-mini"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

# Set environment variables for Forge API compatibility
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co
ENV ANTHROPIC_AUTH_TOKEN=forge-key
ENV FORGE_API_KEY=forge-key
ENV FORGE_BASE_URL=https://api.forge.tensorblock.co/v1

WORKDIR /app

COPY . .

# Install system packages needed for Python deps and build
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libpq-dev \
    python3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip, install dependencies including test packages except for pytest-block-network which fails install
RUN python -m pip install --upgrade pip setuptools wheel && \
    if [ -f requirements.txt ]; then pip install -r requirements.txt; fi && \
    pip install -e . && \
    pip install --no-cache-dir pytest pytest-mock pytest-asyncio pytest-cov anyio pytest-xdist pytest-timeout "setuptools<=81.0.0" litellm

# Set PYTHONPATH to include /app and /app/src
ENV PYTHONPATH=/app:/app/src

# Preflight check
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

CMD ["/bin/bash"]

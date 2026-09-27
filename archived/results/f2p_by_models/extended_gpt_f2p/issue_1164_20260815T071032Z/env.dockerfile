FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tuzi-deepseek-v3.2/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tuzi-deepseek-v3.2/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="tuzi-deepseek-v3.2/gpt-4.1-mini"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV OPENAI_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-dev-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

# Set working directory
WORKDIR /app

# Copy entire repository
COPY . .

# Install system dependencies including Node.js and npm
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       git \
       gcc \
       python3-dev \
       libffi-dev \
       libssl-dev \
       nodejs \
       npm \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip, setuptools, wheel
RUN python -m pip install --upgrade pip setuptools wheel

# Install Python dependencies including missing 'moto' package for tests
RUN set -eux; \
    if [ -f requirements.txt ]; then pip install -r requirements.txt; fi; \
    pip install -e .; \
    # If there are sub-packages, install them editable too (adjust paths as needed)
    if [ -d libs/langgraph ]; then pip install -e libs/langgraph[tests]; fi; \
    if [ -d libs/prebuilt ]; then pip install -e libs/prebuilt; fi; \
    if [ -d libs/sdk-py ]; then pip install -e libs/sdk-py; fi; \
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio moto "setuptools<=81.0.0" litellm anthropic mistralai

# Preflight check that essential packages are installed
RUN python -c 'import pkg_resources, pytest, moto; print("preflight ok")'

# Set PYTHONPATH to include /app and sub-package paths for local imports
ENV PYTHONPATH=/app

CMD ["/bin/bash"]
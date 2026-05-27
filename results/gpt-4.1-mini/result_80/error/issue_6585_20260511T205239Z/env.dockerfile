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

# Set Forge API environment variables (OpenAI and Anthropic compatible)
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1 \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co \
    ANTHROPIC_AUTH_TOKEN=forge-key

# Set working directory
WORKDIR /app

# Copy entire repository
COPY . .

# Install system dependencies for building Python packages and libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libpq-dev \
    libxml2-dev \
    libxslt1-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip, setuptools, and wheel
RUN python -m pip install --upgrade pip setuptools wheel

# Install global testing dependencies and pandas
RUN pip install pytest pytest-mock pytest-asyncio pytest-xdist pytest-timeout litellm "setuptools<=81.0.0" pandas redis

# Editable install of all libs to fix import errors
RUN pip install -e libs/checkpoint \
    && pip install -e libs/checkpoint-postgres \
    && pip install -e libs/checkpoint-sqlite \
    && pip install -e libs/langgraph \
    && pip install -e libs/cli \
    && pip install -e libs/prebuilt \
    && pip install -e libs/sdk-py

# Install the main project in editable mode unconditionally
RUN pip install -e .

# Fix PYTHONPATH for local imports
ENV PYTHONPATH=/app

# Sanity check imports
RUN python -c 'import setuptools, pytest, pandas, redis; print("preflight ok")'

# Default to bash CLI
CMD ["/bin/bash"]

# branch: python/multi-lib-edits + Forge API env vars + test deps + preflight + redis fix + main editable install
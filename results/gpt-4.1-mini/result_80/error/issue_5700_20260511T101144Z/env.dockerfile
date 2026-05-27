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

# Set environment variables for Forge API compatibility (OpenAI and Anthropic SDKs)
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1 \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co/v1 \
    ANTHROPIC_AUTH_TOKEN=forge-key \
    FORGE_API_KEY=forge-key

WORKDIR /app

# Install system dependencies needed for building and common libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libsqlite3-dev \
    sqlite3 \
    git \
    curl \
    libxml2-dev \
    libxslt1-dev \
    python3-dev \
  && rm -rf /var/lib/apt/lists/*

# Copy all repo contents
COPY . .

# Upgrade pip, setuptools, wheel
RUN python -m pip install --upgrade pip setuptools wheel

# Install project dependencies + extra needed packages including the missing ones from build errors
RUN if [ -f requirements.txt ]; then \
      pip install -r requirements.txt ; \
    fi && \
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm nbconvert psycopg_pool numpy bs4 mkdocs nbformat psycopg[binary] dataclasses-json aiosqlite langchain-core pandas sqlite-vec ormsgpack && \
    pip install -e .

# Preflight to verify Python, pytest, and ormsgpack
RUN python -c 'import pkg_resources, pytest, ormsgpack; print("preflight ok")'

# Start container in bash
CMD ["/bin/bash"]
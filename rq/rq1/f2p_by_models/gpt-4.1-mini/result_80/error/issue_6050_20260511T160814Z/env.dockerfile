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

# Set environment variables for Forge API compatibility
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1 \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co \
    ANTHROPIC_AUTH_TOKEN=forge-key \
    FORGE_API_KEY=forge-key

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc python3-dev libpq-dev libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --upgrade pip setuptools wheel

COPY . .

# Install the local project in editable mode (critical for langgraph and sdk-py modules to be found)
RUN pip install -e .

# Install testing and essential packages including pandas
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pandas bs4 mkdocs nbformat nbconvert psycopg[binary] psycopg_pool aiosqlite dataclasses_json requests sqlite_vec numpy redis

# Verify installed packages and local modules importability
RUN python -c 'import pkg_resources, pytest, bs4, mkdocs, nbformat, nbconvert, psycopg, psycopg_pool, aiosqlite, dataclasses_json, requests, sqlite_vec, numpy, redis, pandas; import langgraph.cache.sqlite; print("preflight ok")'

CMD ["/bin/bash"]

# branch: python with libs langgraph and sdk-py editable installs, pandas added, Forge API env vars
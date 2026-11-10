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
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1 \
    OPENAI_API_KEY=$FORGE_API_KEY \
    ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co/v1 \
    ANTHROPIC_AUTH_TOKEN=$FORGE_API_KEY

# Set working directory
WORKDIR /app

# Copy whole repository
COPY . .

# Install system dependencies for Python build and runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libffi-dev \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip, setuptools, and wheel; then install dependencies and test packages
RUN python -m pip install --upgrade pip setuptools wheel && \
    if [ -f requirements.txt ]; then pip install -r requirements.txt; fi && \
    pip install --no-cache-dir pytest pytest-mock pytest-asyncio pytest-cov pytest-timeout pytest-block-network \
    "setuptools<=81.0.0" litellm mem0ai vcrpy json_repair chromadb syrupy respx langgraph-checkpoint-sqlite \
    aiosqlite langgraph-checkpoint-postgres "psycopg[binary,pool]" redis apscheduler fastapi fakeredis mcp \
    "ray[default]" boto3 agno pydantic-ai fastmcp

# Install local packages in editable mode unconditionally
RUN pip install -e . && \
    if [ -d libs/langgraph ]; then pip install -e libs/langgraph[tests]; fi && \
    if [ -d libs/prebuilt ]; then pip install -e libs/prebuilt; fi && \
    if [ -d libs/sdk-py ]; then pip install -e libs/sdk-py; fi

# Set PYTHONPATH to support src/ layout and libs packages
ENV PYTHONPATH=/app:/app/src:/app/libs/langgraph:/app/libs/prebuilt:/app/libs/sdk-py

# Default command to run bash shell
CMD ["/bin/bash"]

# branch: python/pyproject.toml-src-layout-forge-config
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

# Set working directory
WORKDIR /app

# Copy entire repository
COPY . .

# Install system dependencies needed for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libssl-dev \
    curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Upgrade pip, setuptools, wheel
RUN python -m pip install --upgrade pip setuptools wheel

# Install main project and sub-packages in editable mode unconditionally
# Detect sub-packages by presence of setup.py or pyproject.toml in subdirs if needed
# Here we assume a monorepo with /app and /app/src as main packages
RUN pip install -e . -e ./src

# Install test dependencies
RUN pip install --no-cache-dir \
    pytest pytest-mock pytest-asyncio pytest-cov anyio pytest-timeout \
    "setuptools<=81.0.0" litellm mem0ai vcrpy json_repair chromadb syrupy respx langgraph-checkpoint-sqlite \
    aiosqlite langgraph-checkpoint-postgres "psycopg[binary,pool]" redis apscheduler fastapi fakeredis mcp \
    "ray[default]" boto3 agno pydantic-ai fastmcp

# Set environment variables for Forge API compatibility
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1 \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co/v1 \
    ANTHROPIC_AUTH_TOKEN=forge-key \
    FORGE_API_KEY=forge-key \
    FORGE_BASE_URL=https://api.forge.tensorblock.co/v1

# Set PYTHONPATH for correct imports with /src layout and root
ENV PYTHONPATH=/app:/app/src

# Default command to keep the container running for testing
CMD ["/bin/bash"]
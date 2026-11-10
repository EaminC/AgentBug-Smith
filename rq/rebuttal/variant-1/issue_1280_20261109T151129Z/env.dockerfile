# Use official Python 3.12 slim base image
FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="openrouter3/openai/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="openrouter3/openai/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="openrouter3/openai/gpt-4.1-mini"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

# Set working directory
WORKDIR /app

# Set Forge API environment variables for OpenAI and Anthropic SDK compatibility
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1" \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1" \
    ANTHROPIC_AUTH_TOKEN=forge-key

# Install system dependencies needed for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip, setuptools, wheel early
RUN python -m pip install --upgrade pip setuptools wheel

# Copy the entire repository into the container
COPY . .

# Install Python dependencies unconditionally in editable mode
# Also install from requirements.txt if present
RUN if [ -f "requirements.txt" ]; then pip install -r requirements.txt; fi
RUN pip install -e .

# Install pytest and essential test packages unconditionally
RUN pip install --no-cache-dir \
    pytest pytest-mock pytest-asyncio pytest-cov anyio pytest-timeout \
    "setuptools<=81.0.0" litellm mem0ai vcrpy json_repair chromadb syrupy \
    respx langgraph-checkpoint-sqlite aiosqlite langgraph-checkpoint-postgres \
    "psycopg[binary,pool]" redis apscheduler fastapi fakeredis mcp \
    "ray[default]" boto3 agno pydantic-ai fastmcp

# Preflight check to verify critical packages are importable
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

# Set PYTHONPATH to include the root and src/ folder (since this repo uses src/ layout)
ENV PYTHONPATH=/app:/app/src

# Default command to keep container open in bash shell
CMD ["/bin/bash"]
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

# Copy entire repository
COPY . .

# Upgrade pip, setuptools, wheel
RUN python -m pip install --upgrade pip setuptools wheel

# Install system dependencies needed for Python builds
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    python3-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies, fallback if requirements.txt fails due to litellm version
RUN if [ -f "requirements.txt" ]; then \
      pip install --no-cache-dir -r requirements.txt || true; \
    fi

# Install local packages in editable mode unconditionally
# Detecting multi-package layout and installing all key packages if present
RUN pip install --no-cache-dir -e . \
    && if [ -d "libs/langgraph" ]; then pip install --no-cache-dir -e libs/langgraph; fi \
    && if [ -d "libs/prebuilt" ]; then pip install --no-cache-dir -e libs/prebuilt; fi \
    && if [ -d "libs/sdk-py" ]; then pip install --no-cache-dir -e libs/sdk-py; fi

# Install additional Python dependencies
RUN pip install --no-cache-dir pytest pytest-mock pytest-xdist pytest-timeout pytest-block-network setuptools<=81.0.0 litellm==0.1.563 mem0ai vcrpy json_repair chromadb syrupy respx langgraph-checkpoint-sqlite aiosqlite langgraph-checkpoint-postgres "psycopg[binary,pool]" redis apscheduler fastapi fakeredis mcp "ray[default]" boto3 agno pydantic-ai fastmcp

# Set environment variables for Forge API compatibility
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1" \
    OPENAI_API_KEY="forge-key" \
    ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co" \
    ANTHROPIC_AUTH_TOKEN="forge-key"

# Export direct forge keys
ENV FORGE_API_KEY="forge-key" \
    FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"

# Set PYTHONPATH including all relevant source directories for multi-package repo
ENV PYTHONPATH=/app:/app/libs/langgraph:/app/libs/prebuilt:/app/libs/sdk-py

# Preflight check
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

# Default command
CMD ["/bin/bash"]
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

# Set working directory
WORKDIR /app

# Set Forge API environment variables for OpenAI and Anthropic compatibility
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co
ENV ANTHROPIC_AUTH_TOKEN=forge-key

# Install system dependencies needed for Python package builds
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the entire repository
COPY . .

# Upgrade pip, setuptools, wheel
RUN python -m pip install --upgrade pip setuptools wheel

# Install dependencies from requirements.txt if exists, else install editable package
RUN if [ -f "requirements.txt" ]; then \
        pip install -r requirements.txt; \
    fi

# Always pip install the package in editable mode
RUN pip install -e .

# Install pytest and related test dependencies explicitly (without pytest-block-network)
RUN pip install --no-cache-dir pytest pytest-mock pytest-asyncio pytest-cov anyio pytest-timeout \
    "setuptools<=81.0.0" litellm mem0ai vcrpy json_repair chromadb syrupy respx langgraph-checkpoint-sqlite \
    aiosqlite langgraph-checkpoint-postgres "psycopg[binary,pool]" redis apscheduler fastapi fakeredis mcp \
    "ray[default]" boto3 agno pydantic-ai fastmcp

# Preflight check - verify pytest import
RUN python -c "import pkg_resources, pytest; print('preflight ok')"

# Set PYTHONPATH for source layout
ENV PYTHONPATH=/app:/app/src

# Set the default command for the container
CMD ["/bin/bash"]

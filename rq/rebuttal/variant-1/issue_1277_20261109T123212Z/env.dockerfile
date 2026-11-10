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

# Set environment variables for Forge API compatibility (avoid duplicates)
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"

# Set working directory to /app
WORKDIR /app

# Copy entire repository to /app
COPY . .

# Set PYTHONPATH to handle src/ and tests/ directories to avoid import errors
ENV PYTHONPATH=/app:/app/src:/app/tests

# Upgrade pip, setuptools and wheel
# Install dependencies and the project itself unconditionally in editable mode
# Install pytest and common test dependencies to ensure tests can run
RUN set -eux; \
    python -m pip install --upgrade pip setuptools wheel; \
    if [ -f requirements.txt ]; then \
        pip install -r requirements.txt; \
    fi; \
    pip install -e .; \
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio pytest-timeout pytest-block-network \
    "setuptools<=81.0.0" litellm mem0ai vcrpy json_repair chromadb syrupy respx langgraph-checkpoint-sqlite aiosqlite langgraph-checkpoint-postgres \
    "psycopg[binary,pool]" redis apscheduler fastapi fakeredis mcp "ray[default]" boto3 agno pydantic-ai fastmcp

# Preflight check to verify installation of pytest and pkg_resources
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

# Default command to keep container open in bash shell
CMD ["/bin/bash"]
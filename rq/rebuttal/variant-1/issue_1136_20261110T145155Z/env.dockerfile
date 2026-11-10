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

# Environment variables for Forge API compatibility
ENV FORGE_API_KEY=forge-key \
    FORGE_BASE_URL=https://api.forge.tensorblock.co/v1 \
    OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1 \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co/v1 \
    ANTHROPIC_AUTH_TOKEN=forge-key

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev libssl-dev python3-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and setuptools
RUN python -m pip install --upgrade pip setuptools wheel

# Copy entire project
COPY . .

# Install dependencies, project, and testing tools
RUN if [ -f "requirements.txt" ]; then \
    pip install --no-cache-dir -r requirements.txt; \
    fi

# Editable install of the main project unconditionally
RUN pip install --no-cache-dir -e .

# If the repo has sub-packages, install them editable as well
# (Assuming from typical monorepo layouts; adjust paths if needed)
RUN pip install --no-cache-dir -e ./libs/langgraph[tests] -e ./libs/prebuilt -e ./libs/sdk-py || true

# Install test dependencies and other packages
RUN pip install --no-cache-dir \
    pytest pytest-mock pytest-xdist pytest-timeout pytest-block-network \
    "setuptools<=81.0.0" litellm mem0ai vcrpy json_repair chromadb syrupy respx langgraph-checkpoint-sqlite \
    aiosqlite langgraph-checkpoint-postgres "psycopg[binary,pool]" redis apscheduler fastapi fakeredis \
    mcp>=1.13 ray[default] boto3 agno pydantic-ai fastmcp sqlalchemy[asyncio]

# Set PYTHONPATH for src layout and sub-packages
ENV PYTHONPATH=/app:/app/src:/app/libs/langgraph:/app/libs/prebuilt:/app/libs/sdk-py

CMD ["/bin/bash"]
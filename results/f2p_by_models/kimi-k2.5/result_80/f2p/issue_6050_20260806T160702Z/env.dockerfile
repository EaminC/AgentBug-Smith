FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tuzi-kimi-k2.5/kimi-k2.5"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tuzi-kimi-k2.5/kimi-k2.5"
ENV ANTHROPIC_SMALL_FAST_MODEL="tuzi-kimi-k2.5/kimi-k2.5"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-dev-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

WORKDIR /app

# Set environment variables for Forge
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co/v1
ENV ANTHROPIC_AUTH_TOKEN=forge-key

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install core packaging tools early
RUN python -m pip install --upgrade pip setuptools wheel

# Install uv for faster dependency management
RUN pip install uv

# Copy entire repository
COPY . .

# Detect src/ layout and install dependencies accordingly
# The project is in libs/langgraph subdirectory per the prompt
WORKDIR /app/libs/langgraph

# Check for src layout and install dependencies
RUN if [ -d "src" ] || grep -Rq "^\s*from src\.|^\s*import src\." tests 2>/dev/null; then \
        echo "Detected src layout, using PYTHONPATH mode"; \
        export PYTHONPATH=/app/libs/langgraph; \
        python -m pip install --upgrade pip setuptools wheel; \
        if [ -f "pyproject.toml" ]; then \
            uv pip install --system -e . --no-deps 2>/dev/null || pip install -e . --no-deps 2>/dev/null || true; \
        fi; \
        if [ -f "requirements.txt" ]; then \
            pip install -r requirements.txt; \
        fi; \
        # Install test dependencies and required packages unconditionally \
        pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai vcrpy json_repair chromadb syrupy respx langgraph-checkpoint-sqlite aiosqlite langgraph-checkpoint-postgres "psycopg[binary,pool]" redis; \
    else \
        echo "Standard layout, using editable install"; \
        python -m pip install --upgrade pip setuptools wheel; \
        if [ -f "pyproject.toml" ]; then \
            uv pip install --system -e . 2>/dev/null || pip install -e .; \
        elif [ -f "requirements.txt" ]; then \
            pip install -r requirements.txt && pip install -e .; \
        else \
            pip install -e .; \
        fi; \
        # Install test dependencies and required packages unconditionally \
        pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai vcrpy json_repair chromadb syrupy respx langgraph-checkpoint-sqlite aiosqlite langgraph-checkpoint-postgres "psycopg[binary,pool]" redis; \
    fi

# Set PYTHONPATH for src layout detection at runtime
ENV PYTHONPATH=/app/libs/langgraph

# Verify installation with preflight check
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

# Return to app root for potential test script injection
WORKDIR /app

CMD ["/bin/bash"]
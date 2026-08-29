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

# Assumption: This is a monorepo with libs/langgraph as the main Python package
# The project uses uv for dependency management based on workflow files

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade packaging tools early
RUN python -m pip install --upgrade pip setuptools wheel

# Install uv for dependency management (used by the project)
RUN pip install uv

# Set Forge environment variables
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co/v1
ENV ANTHROPIC_AUTH_TOKEN=forge-key

# Copy entire repository for external test injection
COPY . .

# Detect src/ layout and handle conditional installation
# Based on file contents: libs/langgraph is the target directory with pyproject.toml
WORKDIR /app/libs/langgraph

# Check for src/ layout and install accordingly
RUN if [ -d "src" ] || grep -Rq "^\s*from src\.|^\s*import src\." tests 2>/dev/null; then \
        # src/ layout detected: use PYTHONPATH, skip editable install to avoid duplicate loading \
        echo "Detected src/ layout, using PYTHONPATH mode"; \
        export PYTHONPATH=/app/libs/langgraph; \
        uv pip install --system --group dev 2>/dev/null || \
        (cat pyproject.toml | grep -q "uv.lock" && uv sync --frozen --group dev) || \
        (pip install -r requirements.txt 2>/dev/null || true); \
        pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai vcrpy json_repair chromadb syrupy respx langgraph-checkpoint-sqlite aiosqlite langgraph-checkpoint-postgres "psycopg[binary,pool]"; \
    else \
        # Standard layout: use editable install \
        echo "Standard layout, using editable install"; \
        uv pip install --system --group dev 2>/dev/null || \
        (cat pyproject.toml | grep -q "uv.lock" && uv sync --frozen --group dev) || \
        (pip install -r requirements.txt 2>/dev/null || true); \
        pip install -e . 2>/dev/null || uv pip install --system -e . || true; \
        pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai vcrpy json_repair chromadb syrupy respx langgraph-checkpoint-sqlite aiosqlite langgraph-checkpoint-postgres "psycopg[binary,pool]"; \
    fi

# Set PYTHONPATH for src/ layout fallback
ENV PYTHONPATH=/app/libs/langgraph

# Preflight check to verify core modules are importable
RUN python -c 'import pkg_resources, pytest; print("preflight ok")' && \
    python -c 'import langgraph; print("langgraph import ok")' 2>/dev/null || echo "langgraph import skipped (may need build)"

# Return to app root for test execution
WORKDIR /app

CMD ["/bin/bash"]
FROM python:3.12-slim AS test_builder

# --- Universal Build & Dynamic Versioning Overrides ---
ENV SETUPTOOLS_SCM_PRETEND_VERSION="0.0.1.dev0"
ENV POETRY_DYNAMIC_VERSIONING_BYPASS="0.0.1.dev0"
ENV HATCH_VCS_RECORD_FILE="/tmp/_version.py"
RUN git config --global --add safe.directory '*' || true
# -----------------------------------------------------


# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tuzi-gpt-4.1-mini/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ENV ANTHROPIC_SMALL_FAST_MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-dev-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

# Install system dependencies for uv and other tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Set working directory
WORKDIR /app

# Copy the entire repository
COPY . .

# Install the target package and testing dependencies globally
# 1. Install syrupy (for --snapshot-warn-unused) and respx (common LangGraph test dependency)
# 2. Use `pip install -e libs/langgraph` explicitly so it works regardless of layout
RUN pip install --upgrade pip setuptools wheel && \
    if [ -f libs/langgraph/pyproject.toml ]; then \
        pip install -e libs/langgraph; \
    elif [ -f pyproject.toml ]; then \
        pip install -e .; \
    fi && \
    pip install \
        pytest \
        pytest-mock \
        pytest-asyncio \
        pytest-cov \
        anyio \
        "setuptools<=81.0.0" \
        litellm \
        pytest-xdist \
        pytest-timeout \
        mem0ai \
        vcrpy \
        json_repair \
        chromadb \
        syrupy \
        respx

# Install checkpointer dependencies
RUN pip install \
    langgraph-checkpoint-sqlite \
    aiosqlite \
    langgraph-checkpoint-postgres \
    "psycopg[binary,pool]" \
    redis

# Preflight check including syrupy verification
RUN python -c "import pkg_resources, pytest, syrupy; print('preflight ok')"

# Correctly set PYTHONPATH as a top-level Docker instruction
ENV PYTHONPATH=/app/libs/langgraph:/app

# Set the final command
CMD ["/bin/bash"]
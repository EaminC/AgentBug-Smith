FROM python:3.12-slim

# --- Universal Build & Dynamic Versioning Overrides ---
ENV SETUPTOOLS_SCM_PRETEND_VERSION="0.0.1.dev0"
ENV POETRY_DYNAMIC_VERSIONING_BYPASS="0.0.1.dev0"
ENV HATCH_VCS_RECORD_FILE="/tmp/_version.py"
RUN git config --global --add safe.directory '*' || true
# -----------------------------------------------------


# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge_key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="openai/tuzi-deepseek-v3.2/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="anthropic_base_url"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tuzi-deepseek-v3.2/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="tuzi-deepseek-v3.2/gpt-4.1-mini"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvlv_key"
ENV GITHUB_TOKEN="github_key"
# --- end inject ---

# Set Forge environment variables required
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV ANTHROPIC_BASE_URL="anthropic_base_url"
ENV ANTHROPIC_AUTH_TOKEN=forge-key

WORKDIR /app

COPY . .

# Install dependencies and the local project in editable mode unconditionally
RUN python -m pip install --upgrade pip setuptools wheel && \
    pip install -e . && \
    if [ -f requirements.txt ]; then \
        pip install -r requirements.txt; \
    elif [ -f poetry.lock ] && [ -f pyproject.toml ]; then \
        pip install poetry && \
        poetry config virtualenvs.create false && \
        poetry install --no-interaction --no-ansi; \
    fi && \
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai vcrpy json_repair chromadb syrupy respx langgraph-checkpoint-sqlite aiosqlite langgraph-checkpoint-postgres "psycopg[binary,pool]" redis apscheduler fastapi fakeredis

# If the repo has sub-packages, install them here in editable mode (example)
# RUN pip install -e libs/langgraph[tests] -e libs/prebuilt -e libs/sdk-py

# Set PYTHONPATH to include all source directories if multi-package repo
# ENV PYTHONPATH=/app/libs/langgraph:/app/libs/prebuilt:/app/libs/sdk-py

RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

CMD ["/bin/bash"]

# Install mini-swe-agent and set configuration flag
RUN pip install --no-cache-dir mini-swe-agent && \
    mkdir -p /root/.config/mini-swe-agent && \
    echo "MSWEA_CONFIGURED=true" > /root/.config/mini-swe-agent/.env

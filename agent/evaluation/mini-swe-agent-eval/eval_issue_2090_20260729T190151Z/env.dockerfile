FROM python:3.12-slim

# --- Universal Build & Dynamic Versioning Overrides ---
ENV SETUPTOOLS_SCM_PRETEND_VERSION="0.0.1.dev0"
ENV POETRY_DYNAMIC_VERSIONING_BYPASS="0.0.1.dev0"
ENV HATCH_VCS_RECORD_FILE="/tmp/_version.py"
RUN git config --global --add safe.directory '*' || true
ENV SETUPTOOLS_SCM_PRETEND_VERSION_FOR_AGENTSCOPE="0.0.1.dev0"
# -----------------------------------------------------


# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="openai/tuzi-gpt-4.1-mini/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tuzi-gpt-4.1-mini/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="tuzi-gpt-4.1-mini/gpt-4.1-mini"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-dev-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

WORKDIR /app

COPY . .

ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN=forge-key

RUN python -m pip install --upgrade pip setuptools wheel && \
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai fakeredis apscheduler fastapi

# Detect if 'src/' directory or 'import src.' usage in tests exists, to decide install mode
RUN if [ -d "src" ] || grep -Rq "^\s*from src\.|^\s*import src\." tests 2>/dev/null; then \
        echo "src layout detected, skipping editable install, setting PYTHONPATH"; \
        export PYTHONPATH=/app; \
    else \
        pip install -e .; \
    fi

# Install dependencies unconditionally (no requirements.txt, no poetry.lock, but pyproject.toml exists)
RUN if [ -f "requirements.txt" ]; then \
        pip install -r requirements.txt && pip install -e .; \
    elif [ -f "pyproject.toml" ] && [ -f "poetry.lock" ]; then \
        pip install poetry && poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi && pip install -e .; \
    elif [ -f "pyproject.toml" ]; then \
        pip install -e .; \
    fi && \
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai apscheduler fastapi

RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

CMD ["/bin/bash"]
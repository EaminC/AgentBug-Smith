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
ENV DASHSCOPE_API_KEY="test_key"
# --- end inject ---

WORKDIR /app

# Install system dependencies that may be required for building some packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy entire repository (mandatory for external test script injection)
COPY . .

# Upgrade pip and setuptools/wheel
RUN python -m pip install --upgrade pip wheel

# Detect package manager and install dependencies + project + test packages
# The repo uses pyproject.toml with setuptools as build-backend, and has a dev extra.
# We install the dev extra to get all development dependencies (including pytest).
# Since the project uses a src/ layout (src/agentscope), we should NOT do an editable install
# to avoid duplicate module loading. Instead we'll set PYTHONPATH and install dependencies.
# The dev extra includes pytest and other dev tools.
RUN if [ -f pyproject.toml ]; then \
        pip install -e .[dev] && \
        pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai dashscope; \
    else \
        echo "No pyproject.toml found, falling back to requirements.txt if exists" && \
        if [ -f requirements.txt ]; then \
            pip install -r requirements.txt && pip install -e . && \
            pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai dashscope; \
        else \
            pip install -e . && \
            pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai dashscope; \
        fi; \
    fi

# Preflight import check to ensure core modules can be loaded
RUN python -c "import agentscope; import pytest; import dashscope; print('preflight ok')"

CMD ["/bin/bash"]
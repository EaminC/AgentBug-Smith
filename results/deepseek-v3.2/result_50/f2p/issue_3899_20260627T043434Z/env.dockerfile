FROM python:3.12-slim AS test_builder

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
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

WORKDIR /app

# Install system dependencies needed for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and wheel
RUN python -m pip install --upgrade pip wheel

# Copy entire repository
COPY . .

# Determine package manager based on evidence
# Repository uses uv (pyproject.toml shows tool.uv.workspace, CI uses uv sync)
# However, we must install the project dependencies and the project itself.
# The CI uses uv sync --all-groups --all-extras. We'll try uv if uv.lock exists, else fallback to pip.
# The project has a pyproject.toml and appears to be a workspace with members.
# We'll install dependencies using uv if lockfile exists, otherwise use pip with pyproject.toml.
# Critical: we must install the project itself (crewai) and dev dependencies for tests.
# The CI installs with `uv sync --all-groups --all-extras`.
# We'll attempt to replicate that, but we also need to install the project in development mode.
# Since the workspace includes lib/crewai and lib/crewai-tools, we need to install them.
# The standard approach: install dependencies, then install the local packages.

# Check for uv.lock (evidence from CI: uv.lock referenced in workflows)
RUN if [ -f uv.lock ]; then \
    pip install uv && \
    uv sync --all-groups --all-extras --no-install-project; \
    else \
    # fallback: install dependencies from pyproject.toml using pip
    pip install .[all]; \
    fi

# Install the local packages (crewai and crewai-tools) in development mode
# The workspace members are lib/crewai and lib/crewai-tools.
# We must install them with pip install -e so tests can import.
RUN if [ -d lib/crewai ]; then \
    pip install -e ./lib/crewai; \
    fi && \
    if [ -d lib/crewai-tools ]; then \
    pip install -e ./lib/crewai-tools; \
    fi

# Mandatory test framework installation (pytest, etc.)
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# Preflight import check to ensure core modules are available
RUN python -c "import pkg_resources, pytest; print('preflight ok')"

# Set environment variables for tests (as seen in CI)
ENV OPENAI_API_KEY=fake-api-key \
    PYTHONUNBUFFERED=1 \
    BRAVE_API_KEY=fake-brave-key \
    SNOWFLAKE_USER=fake-snowflake-user \
    SNOWFLAKE_PASSWORD=fake-snowflake-password \
    SNOWFLAKE_ACCOUNT=fake-snowflake-account \
    SNOWFLAKE_WAREHOUSE=fake-snowflake-warehouse \
    SNOWFLAKE_DATABASE=fake-snowflake-database \
    SNOWFLAKE_SCHEMA=fake-snowflake-schema \
    EMBEDCHAIN_DB_URI=sqlite:///test.db

# Default command (inferred from CI: tests are run via pytest)
CMD ["/bin/bash"]
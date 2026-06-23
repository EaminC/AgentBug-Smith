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

# Install system dependencies for Python packages (including tkinter for CI)
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-tk \
    && rm -rf /var/lib/apt/lists/*

# Copy the entire repository into the container
COPY . .

# Install the project using Poetry (as per README and Makefile)
# Since pyproject.toml exists and poetry.lock is not provided, we assume no lockfile.
# We install Poetry, configure it to not create virtualenvs, then install dependencies.
# Then install the project in editable mode and mandatory test dependencies.
# The project uses a src/ layout? Check for src/ directory and test import patterns.
# The repository does not have a src/ directory at the top level (from file list).
# However, the module is likely 'gpt_engineer' (dash replaced by underscore).
# We'll install editable to allow imports, but also set PYTHONPATH to /app for safety.
ENV PYTHONPATH=/app

RUN python -m pip install --upgrade pip wheel && \
    pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --with dev,experimental && \
    pip install -e . && \
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# Preflight import check to ensure core modules are importable
RUN python -c "import gpt_engineer, pytest; print('preflight ok')"

# The default command (as per the project: the CLI entrypoint is 'gpte', 'ge', 'gpt-engineer')
# The test harness will override this, but we set a default that matches typical usage.
CMD ["gpte", "--help"]
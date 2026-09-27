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

# Install system dependencies needed for some Python packages (e.g., pillow, opencv, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy the entire repository
COPY . .

# Install project dependencies using Poetry (since pyproject.toml and poetry.lock exist)
# First upgrade pip and install poetry
RUN python -m pip install --upgrade pip wheel && \
    pip install poetry && \
    poetry config virtualenvs.create false

# Install dependencies including dev group (for pytest etc.)
# The project uses tox for testing; install tox as well.
RUN poetry install --no-interaction --no-ansi --with dev

# Install additional testing packages that might be missing from dev dependencies
RUN pip install pytest-mock pytest-asyncio anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# CRITICAL: Install the local project in editable mode
RUN pip install -e .

# Preflight import check to ensure core modules are available
RUN python -c "import pkg_resources, pytest, gpt_engineer; print('preflight ok')"

# The final command is inferred from the project's CLI scripts defined in pyproject.toml
# The primary CLI entrypoint is 'gpt-engineer', but we default to bash for testing.
CMD ["/bin/bash"]
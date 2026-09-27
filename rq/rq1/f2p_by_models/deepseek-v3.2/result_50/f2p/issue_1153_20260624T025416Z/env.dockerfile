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

# Install system dependencies required for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy entire repository (mandatory for external test script injection)
COPY . .

# Upgrade pip and wheel
RUN python -m pip install --upgrade pip wheel

# Install the project and dependencies using Poetry (since pyproject.toml and poetry.lock exist)
# Check for poetry.lock existence
RUN if [ -f poetry.lock ]; then \
        pip install poetry && \
        poetry config virtualenvs.create false && \
        poetry install --no-interaction --no-ansi --with dev,docs; \
    else \
        # Fallback: install via pip editable install (no lockfile)
        pip install -e . && \
        pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai; \
    fi

# Ensure test dependencies are installed even if poetry install didn't include them
# This is a safety net; poetry install --with dev should already include pytest & pytest-cov
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# Preflight import check to fail fast if core modules are missing
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

# Set PYTHONPATH to ensure tests can import the module correctly (no src/ layout detected)
ENV PYTHONPATH=/app

# Final command (required by test harness)
CMD ["/bin/bash"]
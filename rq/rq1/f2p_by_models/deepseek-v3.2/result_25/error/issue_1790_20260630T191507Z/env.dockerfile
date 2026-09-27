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

# Install system dependencies for building Python packages and any optional extras
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        pkg-config \
        gcc \
        g++ \
        git \
        && rm -rf /var/lib/apt/lists/*

# Copy entire repository (mandatory for test harness)
COPY . .

# CRITICAL: Install the local project in editable mode
RUN pip install -e .

# Install project and test dependencies using uv (since uv.lock not present, but uv is in dependencies)
# Use uv sync for dev dependencies and extras as seen in CI workflow
RUN python -m pip install --upgrade pip wheel setuptools && \
    pip install "setuptools<=81.0.0" && \
    # Install uv (specified in dependencies) and use it for installation
    pip install uv>=0.4.25 && \
    uv sync --dev --all-extras && \
    # Install additional test dependencies required by the test harness
    pip install pytest-mock pytest-asyncio pytest-cov anyio litellm pytest-xdist pytest-timeout mem0ai

# Safe installation of requirements if they exist
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
RUN if [ -f requirements-dev.txt ]; then pip install -r requirements-dev.txt; fi
RUN if [ -f pyproject.toml ]; then pip install -e .[dev]; fi

# Set PYTHONPATH for multi-package layouts
ENV PYTHONPATH=/app:/app/src:/app/lib:/app/libs:$PYTHONPATH

# Preflight import check to ensure core modules can be imported
RUN python -c "import crewai; import pytest; import pydantic; import openai; print('Preflight import check passed')"

# Set environment variable for telemetry to avoid interference during tests
ENV OTEL_SDK_DISABLED=true

# Default command for interactive shell (as required by test harness)
CMD ["/bin/bash"]
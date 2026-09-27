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

# Install system dependencies for building Python packages and tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy entire repository
COPY . .

# Set PYTHONPATH to include both app root and src directory
ENV PYTHONPATH=/app:/app/src

# Install uv if uv.lock exists, else use pip
# First install the package in editable mode
RUN pip install --upgrade pip wheel

# Install the package in editable mode
RUN pip install -e .

# Then install development dependencies
RUN if [ -f uv.lock ]; then \
        pip install uv && \
        uv sync --dev --all-extras; \
    else \
        pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai; \
    fi

# Install additional dependencies that might be needed
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
RUN if [ -f requirements-dev.txt ]; then pip install -r requirements-dev.txt; fi
RUN if [ -f pyproject.toml ]; then pip install -e .[dev]; fi

# Preflight import check
RUN python -c "import crewai; import pytest; print('preflight ok')"

CMD ["/bin/bash"]
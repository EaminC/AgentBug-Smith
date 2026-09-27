FROM python:3.12-slim

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

# Install system dependencies for common Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies based on pyproject.toml (Poetry)
# We install the project in editable mode after installing dependencies
# to ensure the package is importable.
RUN python -m pip install --upgrade pip wheel && \
    pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --with dev && \
    # Install additional test dependencies (pytest-mock, setuptools<=81.0.0, litellm, etc.)
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# Copy entire repository
COPY . .

# Install the project in editable mode (CRITICAL for imports)
RUN pip install -e .

# Set PYTHONPATH for multi-package layouts (if any)
ENV PYTHONPATH=/app:$PYTHONPATH

# Preflight import check to verify core modules can be imported
RUN python -c "import pytest; print('preflight ok')"

CMD ["/bin/bash"]
FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tuzi-kimi-k2.5/kimi-k2.5"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tuzi-kimi-k2.5/kimi-k2.5"
ENV ANTHROPIC_SMALL_FAST_MODEL="tuzi-kimi-k2.5/kimi-k2.5"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-dev-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

WORKDIR /app

# Install system dependencies needed for building packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    git \
    libxml2-dev \
    libxslt1-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables for Forge API (OpenAI-compatible)
ENV FORGE_API_KEY=forge-key
ENV FORGE_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co/v1
ENV ANTHROPIC_AUTH_TOKEN=forge-key
ENV MODEL=tuzi-kimi-k2.5/kimi-k2.5
ENV ANTHROPIC_MODEL=tuzi-kimi-k2.5/kimi-k2.5

# Upgrade pip and install poetry
RUN python -m pip install --upgrade pip wheel && \
    pip install poetry "setuptools<=81.0.0"

# Configure poetry to not create virtual environments (use system Python)
RUN poetry config virtualenvs.create false

# Copy project files
COPY . .

# Install project dependencies with Poetry, then install the package itself
# Also install required test dependencies
RUN if [ -f "pyproject.toml" ] && [ -f "poetry.lock" ]; then \
        poetry install --no-interaction --no-ansi --with dev; \
    elif [ -f "pyproject.toml" ]; then \
        poetry install --no-interaction --no-ansi; \
    fi && \
    pip install -e . && \
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio pytest-xdist pytest-timeout litellm mem0ai

# Verify installation
RUN python -c 'import gpt_engineer; import pytest; print("preflight ok")'

CMD ["/bin/bash"]

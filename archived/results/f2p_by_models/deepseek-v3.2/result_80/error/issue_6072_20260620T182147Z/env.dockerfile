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

# Copy entire repository
COPY . .

# Install system dependencies if needed for build
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

# First, upgrade pip and install uv if uv.lock exists
RUN python -m pip install --upgrade pip wheel

# Install the project in editable mode to ensure all packages are available
# This is CRITICAL for monorepo setups
RUN pip install -e .

# Additionally install sub-packages from libs/ directory if they exist
RUN if [ -d "libs" ]; then \
    find libs -name "pyproject.toml" -o -name "setup.py" | while read f; do \
        dir=$(dirname "$f"); \
        echo "Installing package from $dir"; \
        pip install -e "$dir" || true; \
    done; \
fi

# Install mandatory testing dependencies
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# Set comprehensive PYTHONPATH for monorepo
ENV PYTHONPATH=/app:/app/libs:/app/libs/langgraph:/app/libs/cli:/app/libs/checkpoint:/app/libs/checkpoint-sqlite:/app/libs/checkpoint-postgres:/app/libs/prebuilt:/app/libs/sdk-py

# Verify core modules can be imported
RUN python -c "import pytest; import setuptools; print('preflight ok')"

# Default command
CMD ["/bin/bash"]
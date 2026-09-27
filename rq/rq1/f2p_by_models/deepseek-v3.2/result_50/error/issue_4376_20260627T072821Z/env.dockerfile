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

# Install system dependencies required by the project (from Dockerfile and requirements)
RUN apt-get update && apt-get install -y \
    chromium-driver firefox-esr ca-certificates curl jq wget git \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PIP_NO_CACHE_DIR=yes \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="$PATH:/root/.local/bin"

# Copy the entire repository
COPY . .

# Set PYTHONPATH to include the app directory
ENV PYTHONPATH=/app

# Install dependencies with conditional checks
RUN python -m pip install --upgrade pip wheel

# Install requirements.txt if it exists
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

# Install pyproject.toml dependencies if it exists
RUN if [ -f pyproject.toml ]; then pip install -e .; fi

# Install mandatory testing frameworks
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# If no pyproject.toml but setup.py exists, install that way
RUN if [ ! -f pyproject.toml ] && [ -f setup.py ]; then pip install -e .; fi

# Preflight check to verify core modules can be imported
RUN python -c "import pytest; print('pytest import ok')" && \
    # Try to import autogpt if it exists
    (python -c "import autogpt; print('autogpt import ok')" 2>/dev/null || echo "autogpt not found, continuing")

# Default command for test harness
CMD ["/bin/bash"]
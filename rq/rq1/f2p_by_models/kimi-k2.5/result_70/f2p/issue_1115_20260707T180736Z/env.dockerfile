# GPT Engineer Dockerfile with Forge API configuration
FROM python:3.11-slim

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

# Set working directory
WORKDIR /app

# Avoid interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies required for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip, wheel, and setuptools (quoted to handle special characters in version constraint)
RUN python -m pip install --upgrade pip wheel 'setuptools<=81.0.0'

# Install Poetry
RUN pip install poetry

# Configure Poetry to not create virtual environments (we're in a container)
ENV POETRY_VIRTUALENVS_CREATE=false

# Copy the entire repository
COPY . .

# Install project dependencies using Poetry
# Poetry will read pyproject.toml and poetry.lock
RUN poetry install --no-interaction --no-ansi

# Additionally install test dependencies that may be needed
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov pytest-xdist pytest-timeout litellm mem0ai

# Install the project itself in editable mode
RUN pip install -e .

# Set environment variables for Forge API (OpenAI-compatible)
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co/v1
ENV ANTHROPIC_AUTH_TOKEN=forge-key

# Additional model configuration
ENV MODEL=tuzi-kimi-k2.5/kimi-k2.5
ENV ANTHROPIC_MODEL=tuzi-kimi-k2.5/kimi-k2.5
ENV ANTHROPIC_SMALL_FAST_MODEL=tuzi-kimi-k2.5/kimi-k2.5

# AI generation parameters
ENV AI_TEMPERATURE=0.7
ENV AI_MAX_TOKENS=1000
ENV AI_TOP_P=1
ENV AI_FREQUENCY_PENALTY=0
ENV AI_PRESENCE_PENALTY=0

# Preflight check to verify installation
RUN python -c "import gpt_engineer; import pytest; print('preflight ok')"

# Default command
CMD ["/bin/bash"]

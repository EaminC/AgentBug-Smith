# branch: python/poetry
FROM python:3.11-slim

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

# Set Forge API environment variables for OpenAI and Anthropic SDK compatibility
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ENV ANTHROPIC_SMALL_FAST_MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"

# Additional environment variables from project .env
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ENV AI_TEMPERATURE="0.7"
ENV TAVILY_API_KEY="tvly-dev-key"
ENV GITHUB_TOKEN="ghp_key"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy entire repository for external test injection
COPY . .

# Upgrade packaging tools early
RUN python -m pip install --upgrade pip setuptools wheel

# Instead of using poetry which has lock file issues, install dependencies directly with pip
# Install core dependencies from pyproject.toml
RUN pip install \
    openai==0.28 \
    termcolor==2.3.0 \
    typer>=0.3.2 \
    rudder-sdk-python>=2.0.2 \
    dataclasses-json==0.5.7 \
    tiktoken>=0.0.4 \
    tabulate==0.9.0 \
    python-dotenv>=0.21.0 \
    langchain>=0.0.335

# Install test dependencies unconditionally (from pyproject.toml dev dependencies)
RUN pip install \
    pytest>=7.3.1 \
    pytest-cov>=4.1.0 \
    pytest-mock \
    pytest-asyncio \
    pytest-xdist \
    pytest-timeout \
    black==23.3.0 \
    mypy==1.3.0 \
    ruff>=0.0.272 \
    pre-commit==3.3.3 \
    tox>=3.0.0 \
    anyio \
    "setuptools<=81.0.0"

# Install experimental dependencies if needed (but skip llama-index due to openai version conflicts)
RUN pip install \
    rank-bm25>=0.2.2 \
    tree_sitter_languages>=1.8.0

# Install the project in editable mode
RUN pip install -e .

# Set PYTHONPATH for proper module resolution
ENV PYTHONPATH=/app

# Preflight import check
RUN python -c 'import pytest, gpt_engineer, openai, langchain; print("preflight ok")'

# Default command (required by test harness)
CMD ["/bin/bash"]
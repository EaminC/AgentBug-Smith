# branch: python/poetry
FROM python:3.11-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ENV ANTHROPIC_SMALL_FAST_MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-dev-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

WORKDIR /app

# Copy entire repository (required for test harness)
COPY . .

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install poetry
RUN python -m pip install --upgrade pip setuptools wheel && \
    pip install poetry

# Configure poetry to not create virtualenvs inside container
RUN poetry config virtualenvs.create false

# Install project dependencies - dev group and test extras
# Note: In pyproject.toml, 'dev' is a group and 'test' is an extra
RUN poetry install --no-interaction --no-ansi --with dev --extras test

# DO NOT install langchain-community here - we want to test the fallback mechanism
# Install additional test packages that may be needed for test harness
RUN pip install pytest-mock pytest-asyncio pytest-xdist pytest-timeout anyio "setuptools<=81.0.0" litellm

# Install the project in editable mode for proper imports (required by instructions)
RUN pip install -e .

# Set Forge environment variables for AI API compatibility
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co
ENV ANTHROPIC_AUTH_TOKEN=forge-key
ENV FORGE_API_KEY=forge-key
ENV FORGE_BASE_URL=https://api.forge.tensorblock.co/v1
ENV MODEL=tuzi-deepseek-v3.2/deepseek-v3.2
ENV AI_TEMPERATURE=0.7
ENV AI_MAX_TOKENS=1000
ENV AI_TOP_P=1
ENV AI_FREQUENCY_PENALTY=0
ENV AI_PRESENCE_PENALTY=0
ENV TAVILY_API_KEY=tvly-dev-key
ENV GITHUB_TOKEN=ghp_key

# Preflight import check - verify critical packages are importable
RUN python -c 'import pkg_resources, pytest, gpt_engineer, openai, langchain, tiktoken; print("preflight ok")'

# Final command for test harness
CMD ["/bin/bash"]
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

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy entire repository
COPY . .

# Set workdir to the Python project subdirectory (evidence: ./autogpt)
WORKDIR /app/autogpt

# Install dependencies based on evidence (poetry.lock exists)
# Evidence: .github/workflows/autogpt-ci.yml shows poetry install in autogpt directory
RUN python -m pip install --upgrade pip wheel && \
    pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi

# CRITICAL: Install the project in editable mode
# This ensures the package is properly installed and importable
RUN pip install -e .

# Install pytest and other test utilities (mandatory)
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# Set PYTHONPATH to include the project root
ENV PYTHONPATH=/app/autogpt:$PYTHONPATH

# Preflight import check to fail fast
RUN python -c "import autogpt, pytest; print('preflight ok')"

CMD ["/bin/bash"]
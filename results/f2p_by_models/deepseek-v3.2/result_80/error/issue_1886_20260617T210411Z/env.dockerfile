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

# Install system dependencies including libpq for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    postgresql-client \
    libxml2-dev \
    libxslt1-dev \
    python3-dev \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the entire repository
COPY . .

# Set Forge environment variables for OpenAI and Anthropic SDK compatibility
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co/v1
ENV ANTHROPIC_AUTH_TOKEN=forge-key
ENV MODEL=tuzi-deepseek-v3.2/deepseek-v3.2
ENV AI_TEMPERATURE=0.7
ENV AI_MAX_TOKENS=1000
ENV AI_TOP_P=1
ENV AI_FREQUENCY_PENALTY=0
ENV AI_PRESENCE_PENALTY=0
ENV TAVILY_API_KEY=tvly-dev-key
ENV GITHUB_TOKEN=ghp_key

# Upgrade packaging tools
RUN python -m pip install --upgrade pip setuptools wheel

# Navigate to the main Python project directory
WORKDIR /app/wren-ai-service

# Install specific poetry version to match lock file
RUN pip install poetry==2.4.1

# Configure poetry to not create virtual environments
RUN poetry config virtualenvs.create false

# Install psycopg2-binary first to avoid compilation issues
RUN pip install psycopg2-binary

# Fix virtualenv issue by ensuring proper version
RUN pip install virtualenv==20.31.2

# First install core dependencies (excluding dev, eval groups)
RUN poetry install --no-interaction --no-ansi --without dev,eval --no-root

# Install dev dependencies including psycopg2
RUN poetry install --no-interaction --no-ansi --only dev --no-root

# Install test dependencies
RUN poetry install --no-interaction --no-ansi --only test --no-root

# Install additional test packages required for pytest
RUN pip install pytest-mock pytest-asyncio pytest-cov pytest-xdist pytest-timeout anyio "setuptools<=81.0.0" litellm mem0ai

# Install the project in editable mode for proper imports
RUN pip install -e .

# Set comprehensive PYTHONPATH for imports
ENV PYTHONPATH=/app/wren-ai-service/src:/app/wren-ai-service:/app/wren-ai-service/tests:/app

# Create tests directory if it doesn't exist
RUN mkdir -p /app/wren-ai-service/tests

# Go back to root directory for standalone script execution
WORKDIR /app

# Preflight import check
RUN python -c "import pkg_resources, pytest; print('preflight ok')"

# Default command - required for testing environment
CMD ["/bin/bash"]
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

# Install system dependencies needed for some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy entire repository
COPY . .

# Set PYTHONPATH for monorepo structure
ENV PYTHONPATH=/app:/app/src:/app/tests:$PYTHONPATH

# Install uv first
RUN python -m pip install --upgrade pip wheel && \
    pip install uv

# Install dependencies using uv
RUN uv sync --dev --all-extras

# Install the package in development mode (editable)
RUN pip install -e .

# Install additional test dependencies
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio pytest-xdist pytest-timeout

# Preflight check to ensure core modules can be imported
RUN python -c "import crewai, pytest, litellm; print('preflight ok')"

# Default command - run tests
CMD ["pytest", "-v", "--tb=short", "tests/"]
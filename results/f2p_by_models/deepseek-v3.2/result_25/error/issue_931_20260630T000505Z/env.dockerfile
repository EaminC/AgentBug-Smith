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

# Install system dependencies including git and curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy entire repository
COPY . .

# Set Python path for src/ layout
ENV PYTHONPATH=/app/src:/app

# Install project dependencies using pip directly instead of uv
# to avoid hash mismatch issues with uv dependency
RUN python -m pip install --upgrade pip wheel

# Install the project in editable mode first
RUN pip install -e .

# Install test dependencies
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio \
    "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# Preflight import check to verify core modules can be imported
RUN python -c "import crewai, pytest; print('preflight ok')"

# Default command for test harness
CMD ["/bin/bash"]
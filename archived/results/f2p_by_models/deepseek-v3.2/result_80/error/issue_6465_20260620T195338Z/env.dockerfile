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

# Install system dependencies needed for uv and general build
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv (preferred package manager according to CI files)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh -s -- -c /usr/local/bin && \
    chmod +x /usr/local/bin/uv

# Copy entire repository
COPY . .

# Set PYTHONPATH to include the langgraph source
ENV PYTHONPATH=/app/libs/langgraph/src:$PYTHONPATH

# Check for project-specific files and install dependencies accordingly
# The project is located at ./libs/langgraph (as per metadata)
WORKDIR /app/libs/langgraph

# Install dependencies using uv (as per CI workflows)
# The CI uses `uv sync --frozen --group test --no-dev`
# We'll install test dependencies and the package itself.
RUN uv venv && \
    uv sync --group test --no-dev && \
    # Ensure the package is installed in development mode (editable) for tests
    uv pip install -e . && \
    # Install mandatory test framework packages (required by LLM instruction)
    uv pip install pytest pytest-mock setuptools<=81.0.0 litellm pytest-asyncio pytest-cov anyio pytest-xdist pytest-timeout mem0ai

# Preflight import check to verify core modules are accessible
RUN python -c "import langgraph; import pytest; print('preflight ok')"

# Set CMD to run pytest directly instead of make test
CMD ["pytest", "-v", "--tb=short"]
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

# Install system dependencies for building Python packages if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy entire repository
COPY . .

# Upgrade pip and install dependencies with proper error handling
RUN python -m pip install --upgrade pip wheel && \
    # Check for requirements.txt (present)
    if [ -f requirements.txt ]; then \
        pip install -r requirements.txt; \
    fi && \
    # Install the project in editable mode (no src/ layout detected)
    pip install -e . && \
    # Mandatory test framework and additional common test utilities
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# Set PYTHONPATH to include current directory for imports
ENV PYTHONPATH=/app:$PYTHONPATH

# Preflight import check to fail fast
RUN python -c "import sys; print(f'Python {sys.version}'); import pytest; print('pytest ok')"

# Set default command to bash (as required by test harness)
CMD ["/bin/bash"]
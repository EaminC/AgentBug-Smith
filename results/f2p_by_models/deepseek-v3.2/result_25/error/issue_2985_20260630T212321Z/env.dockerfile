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

# Install system dependencies for building Python packages and runtime
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl gcc g++ && \
    rm -rf /var/lib/apt/lists/*

# Copy entire repository (critical for external test script injection)
COPY . .

# Install uv for dependency management
RUN pip install --upgrade pip wheel uv

# Install project in editable mode with all extras
RUN uv pip install -e ".[test,dev,all]"

# Install additional test dependencies
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# Set environment variable for telemetry (as in tests.yml)
ENV OPENAI_API_KEY=fake-api-key

# Set PYTHONPATH to include src directory for proper imports
ENV PYTHONPATH=/app/src:$PYTHONPATH

# Verify installation
RUN python -c "import crewai; print('preflight ok')"

CMD ["/bin/bash"]
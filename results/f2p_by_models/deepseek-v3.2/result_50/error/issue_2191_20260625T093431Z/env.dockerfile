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

# Copy entire repository (critical for test script injection)
COPY . .

# Upgrade pip and wheel
RUN python -m pip install --upgrade pip wheel

# Set PYTHONPATH for monorepo structure
ENV PYTHONPATH=/app:/app/src:/app/lib:/app/libs:/app/packages:$PYTHONPATH

# Install the project in editable mode FIRST (critical for imports)
RUN pip install -e .

# Install uv if uv.lock exists, else install dependencies via pip
# Evidence from .github/workflows/tests.yml shows uv is used for dev install
RUN if [ -f uv.lock ]; then \
        pip install uv && \
        uv sync --dev --all-extras; \
    else \
        # Install additional dependencies if not using uv
        if [ -f requirements.txt ]; then pip install -r requirements.txt; fi && \
        if [ -f requirements-dev.txt ]; then pip install -r requirements-dev.txt; fi && \
        if [ -f pyproject.toml ]; then pip install .[dev]; fi; \
    fi

# Install test dependencies regardless (some may be missing from uv.lock path)
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# Preflight import check - verify core packages
RUN python -c 'import pytest; import crewai; import litellm; print("preflight ok")'

CMD ["/bin/bash"]
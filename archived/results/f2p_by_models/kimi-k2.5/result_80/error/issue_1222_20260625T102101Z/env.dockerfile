FROM python:3.12-slim AS test_builder

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tuzi-kimi-k2.5/kimi-k2.5"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tuzi-kimi-k2.5/kimi-k2.5"
ENV ANTHROPIC_SMALL_FAST_MODEL="tuzi-kimi-k2.5/kimi-k2.5"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-dev-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

WORKDIR /app

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY . .

# Ensure Python recognizes the local packages and handle monorepo structure
ENV PYTHONPATH=/app:$PYTHONPATH

# Install dependencies: requirements.txt exists per repository evidence
# Conditionally install dev requirements if present, then install package and test frameworks
RUN python -m pip install --upgrade pip wheel setuptools && \
    if [ -f requirements.txt ]; then \
        pip install -r requirements.txt; \
    fi && \
    if [ -f requirements/requirements-dev.txt ]; then \
        pip install -r requirements/requirements-dev.txt; \
    fi && \
    pip install -e . && \
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# Handle potential sub-package installations for monorepo layouts common in agent frameworks
RUN if [ -f setup.py ] || [ -f pyproject.toml ]; then \
        pip install -e .[test] 2>/dev/null || pip install -e . || true; \
    fi

# Preflight verification to ensure environment is correctly configured
RUN python -c 'import sys; print("Python path:", sys.path); import agentscope; print("agentscope imported successfully"); print("preflight ok")'

CMD ["/bin/bash"]
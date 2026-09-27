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

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy entire repository
COPY . .

# Install uv if not present and sync dependencies
RUN python -m pip install --upgrade pip wheel && \
    if command -v uv > /dev/null 2>&1; then \
        echo "Using uv from system"; \
        uv sync --all-groups --all-extras; \
    else \
        echo "Installing uv"; \
        pip install uv && \
        uv sync --all-groups --all-extras; \
    fi

# Install mandatory test dependencies
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# Install all workspace packages in editable mode
# Based on pyproject.toml workspace members: lib/crewai, lib/crewai-tools, lib/devtools
RUN if [ -d "lib/crewai" ]; then cd lib/crewai && pip install -e .; fi && \
    if [ -d "lib/crewai-tools" ]; then cd lib/crewai-tools && pip install -e .; fi && \
    if [ -d "lib/devtools" ]; then cd lib/devtools && pip install -e .; fi

# Also install the root package if it exists
RUN if [ -f "pyproject.toml" ] || [ -f "setup.py" ] || [ -f "setup.cfg" ]; then pip install -e .; fi

# Set comprehensive PYTHONPATH to include all source directories
ENV PYTHONPATH=/app:/app/lib/crewai/src:/app/lib/crewai-tools/src:/app/lib/devtools/src:$PYTHONPATH

# Preflight import check to verify core modules can be imported
RUN python -c "import crewai; import crewai_tools; import pytest; print('preflight ok')"

CMD ["/bin/bash"]